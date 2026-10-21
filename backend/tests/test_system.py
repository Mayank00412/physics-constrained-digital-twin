import math,zipfile
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.physics.engine import Twin,Configuration,FAULTS,healthy_prediction
from backend.datasets.synthetic import generate,validate
from backend.ai.models import Suite,FEATURES
from backend.energy.analysis import Energy
from backend.diagnostics.localize import diagnose
from backend.datasets.public import safe_extract,vibration_windows,download

@pytest.mark.parametrize('fault',FAULTS)
def test_power_conservation(fault):
    twin=Twin(Configuration(fault=fault,severity=.7))
    for _ in range(50):
        packet=twin.step();t=packet['truth'];s=packet['sensors']
        assert t['electrical_power']==pytest.approx(t['output_power']+t['motor_loss']+t['gearbox_loss']+t['kinetic_power'])
        assert s['gearbox_input_speed']/s['gearbox_output_speed']==pytest.approx(15)
        assert s['gearbox_output_torque']*s['gearbox_output_speed']*2*math.pi/60==pytest.approx(t['output_power'])
        assert t['motor_loss']>=0 and t['gearbox_loss']>=0

def test_seed_and_sensor_isolation():
    a=Twin(Configuration(seed=8));b=Twin(Configuration(seed=8))
    assert a.step()==b.step()
    bad=Twin(Configuration(fault='sensor_failure',severity=1)).step()
    assert bad['sensors']['power']==0 and bad['truth']['electrical_power']>0
    assert not any(k in FEATURES for k in ['severity','fault','component','motor_efficiency','gearbox_efficiency'])

def test_healthy_baseline():
    twin=Twin()
    for _ in range(100): p=twin.step()
    assert abs(p['sensors']['power']/p['sensors']['expected_power']-1)<.04

def test_deceleration_balance():
    twin=Twin()
    for _ in range(150):twin.step()
    twin.config.speed_rpm=300
    for _ in range(40):
        t=twin.step()['truth']
        assert t['motor_loss']>=0
        assert t['electrical_power']==pytest.approx(t['output_power']+t['motor_loss']+t['gearbox_loss']+t['kinetic_power'])

def test_energy_units():
    energy=Energy();s=dict(power=2000,expected_power=1000,mechanical_power=500)
    r=energy.update(s,3600)
    assert r['excess_wh']==1000 and r['efficiency']==.25

def test_localization_sensor():
    t=Twin(Configuration(fault='sensor_failure',severity=1))
    for _ in range(200): p=t.step()
    assert diagnose(p['sensors'],True)['component']=='sensor'

@pytest.fixture(scope='module')
def frame(tmp_path_factory):return generate(108,30,42,tmp_path_factory.mktemp('dataset'))
def test_splits(frame):
    validate(frame)
    assert frame.groupby('run_id').split.nunique().max()==1
    assert set(frame[frame.split=='ood'].operating_point_rpm).isdisjoint(set(frame[frame.split=='train'].operating_point_rpm))
    assert set(frame[frame.split=='ood'].operating_load_kg).isdisjoint(set(frame[frame.split=='train'].operating_load_kg))
    broken=frame.copy();broken.loc[0,'power']=np.nan
    with pytest.raises(ValueError):validate(broken)

def test_training(frame,tmp_path):
    suite=Suite();suite.train(frame,epochs=2,root=tmp_path)
    result=suite.evaluate(frame)
    assert set(result)=={'test','ood'}
    assert 0<=result['test']['models']['hybrid']['f1']<=1
    restored=Suite();assert restored.load(tmp_path)
    before=suite.scores(frame.iloc[:5]);after=restored.scores(frame.iloc[:5])
    assert np.allclose(before['hybrid'],after['hybrid'])
    hidden=frame.iloc[:5].copy();hidden['truth_severity']=999
    assert np.allclose(before['hybrid'],suite.scores(hidden)['hybrid'])
    broken=frame.iloc[:5].copy();broken.loc[0,'power']=np.nan
    with pytest.raises(ValueError):suite.scores(broken)

def test_archive_guard(tmp_path):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.txt','bad')
    with pytest.raises(ValueError):safe_extract(archive,tmp_path/'out')
    with pytest.raises(ValueError):download('https://example.com/data',tmp_path/'data',True)

def test_preprocess(tmp_path):
    path=tmp_path/'signal.txt';np.savetxt(path,np.sin(np.arange(4096)))
    result=vibration_windows(path)
    assert len(result)==2 and result.recording_id.nunique()==1

def test_api_transitions():
    from backend.api import app,runtime
    with TestClient(app) as client:
        assert client.get('/api/health').status_code==200
        client.post('/api/simulation/reset')
        assert client.post('/api/simulation/pause').status_code==409
        assert client.post('/api/simulation/configure',json={'load_kg':-1}).status_code==422
        assert client.post('/api/simulation/configure',json={'speed_rpm':900}).status_code==200
        assert runtime.twin.config.speed_rpm==900
        assert client.post('/api/simulation/start').json()['state']=='running'
        assert client.post('/api/simulation/pause').json()['state']=='paused'
        assert client.post('/api/simulation/resume').json()['state']=='running'
        assert client.post('/api/simulation/inject-fault',json={'fault':'bad'}).status_code==422
        runtime.tick()
        assert client.get('/api/sensors/latest').json()['sensors']['power']>0
        with client.websocket_connect('/ws/telemetry') as ws: assert ws.receive_json()['sensors']
        client.post('/api/simulation/reset')
        assert client.get('/api/sensors/latest').json() is None
