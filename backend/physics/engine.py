"""SI-unit, lumped motor / transmission / belt model with explicit energy balance."""
from dataclasses import dataclass
import math
import numpy as np

FAULTS = ['healthy', 'motor_efficiency', 'gearbox_friction', 'gearbox_degradation', 'conveyor_resistance', 'abnormal_load', 'sensor_noise', 'sensor_drift', 'sensor_failure']

@dataclass
class Configuration:
    speed_rpm: float = 1200
    load_kg: float = 80
    ambient_c: float = 25
    dt: float = .1
    duration: float = 600
    seed: int = 42
    fault: str = 'healthy'
    severity: float = 0

def motor_efficiency(omega, torque):
    return float(np.clip(.91 - .045*(omega/160-1)**2 - .035*(torque/12-1)**2, .65, .93))

def healthy_prediction(s):
    w = max(s['motor_speed']*2*math.pi/60, 0)
    v = w/15*.12
    force = 25 + .035*s['load']*9.81 + 3*v
    out = force*v
    gear = out/.94 + .015*w*w
    shaft = gear + .8*w*s.get('acceleration', 0)
    eff = motor_efficiency(w, max(shaft/max(w,1),0))
    return (shaft/eff if shaft>=0 else shaft*eff) + 90

class Twin:
    ratio = 15
    radius = .12
    inertia = .8
    def __init__(self, config=None):
        self.config = config or Configuration()
        self.rng = np.random.default_rng(self.config.seed)
        self.time = self.omega = 0.
        self.motor_temp = self.gear_temp = self.config.ambient_c

    def step(self):
        c = self.config
        f, q = c.fault, c.severity
        # Exact integration of first-order speed servo, deterministic at fixed dt.
        target = c.speed_rpm*2*math.pi/60
        old = self.omega
        self.omega = target + (old-target)*math.exp(-c.dt/2)
        w = (old+self.omega)/2
        a = (self.omega-old)/c.dt
        v = w/self.ratio*self.radius
        load = c.load_kg*(1+.015*math.sin(self.time/7))
        actual_load = load*(1+q*.9*(f=='abnormal_load'))
        force = 25 + .035*actual_load*9.81 + 3*v + 140*q*(f=='conveyor_resistance')
        output = force*v
        ge = .94 - .18*q*(f=='gearbox_degradation')
        friction = (.015+.065*q*(f=='gearbox_friction'))*w*w
        gear_input = output/ge + friction
        kinetic = self.inertia*w*a
        shaft = gear_input + kinetic
        torque = shaft/max(w,1e-8)
        me = motor_efficiency(w,torque)*(1-.32*q*(f=='motor_efficiency'))
        # Ideal four-quadrant drive: braking can return signed active power.
        electrical = (shaft/me if shaft>=0 else shaft*me) + 90
        motor_loss = electrical-shaft
        gear_loss = gear_input-output
        self.motor_temp += c.dt*(motor_loss-12*(self.motor_temp-c.ambient_c))/8000
        self.gear_temp += c.dt*(gear_loss-9*(self.gear_temp-c.ambient_c))/5000
        pf, voltage = .86, 400.
        observable = dict(timestamp=self.time, motor_speed=w*60/(2*math.pi), gearbox_input_speed=w*60/(2*math.pi), gearbox_output_speed=w*60/(2*math.pi)/15,
            conveyor_speed=v, load=load, motor_torque=torque, gearbox_output_torque=force*self.radius,
            voltage=voltage,current=electrical/(math.sqrt(3)*voltage*pf),power_factor=pf,power=electrical,
            mechanical_power=output,motor_temperature=self.motor_temp,gearbox_temperature=self.gear_temp,
            vibration=.15+.0009*w+q*(1.4*(f=='gearbox_degradation')+.65*(f=='gearbox_friction')),
            acceleration=a,ambient=c.ambient_c)
        truth = dict(motor_efficiency=me,gearbox_efficiency=ge,motor_loss=motor_loss,gearbox_loss=gear_loss,
            kinetic_power=kinetic,shaft_power=shaft,electrical_power=electrical,output_power=output,
            fault=f,severity=q,anomaly=int(f!='healthy' and q>0),component=component(f),actual_load=actual_load)
        # Independent sensor measurement perturbations; physical truth remains separate.
        for key, noise in [('power',.007),('current',.006),('motor_speed',.001),('vibration',.025),('motor_torque',.005)]:
            observable[key] *= 1 + self.rng.normal(0,noise*(1+15*q*(f=='sensor_noise')))
        if f=='sensor_drift': observable['power'] *= 1+q*self.time/100
        if f=='sensor_failure': observable['power'] = 0
        observable['expected_power'] = healthy_prediction(observable)
        self.time = round(self.time+c.dt,10)
        return {'sensors':observable,'truth':truth}

def component(f):
    if f.startswith('motor'): return 'motor'
    if f.startswith('gearbox'): return 'gearbox'
    if f in ('conveyor_resistance','abnormal_load'): return 'conveyor'
    if f.startswith('sensor'): return 'sensor'
    return 'healthy'
