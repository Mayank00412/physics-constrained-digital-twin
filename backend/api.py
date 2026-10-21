import asyncio, json, logging, uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.physics.engine import Twin, Configuration, FAULTS
from backend.energy.analysis import Energy
from backend.diagnostics.localize import diagnose
from backend.datasets.synthetic import generate
from backend.ai.models import Suite, FEATURES
from backend.database.store import save, read

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
logger=logging.getLogger('twin')
class Settings(BaseModel):
    speed_rpm: float=Field(1200,ge=100,le=1800)
    load_kg: float=Field(80,ge=0,le=300)
    ambient_c: float=Field(25,ge=-10,le=60)
    dt: float=Field(.1,ge=.02,le=1)
    duration: float=Field(600,ge=1,le=86400)
    seed: int=Field(42,ge=0)
class Fault(BaseModel):
    fault: Literal['healthy','motor_efficiency','gearbox_friction','gearbox_degradation','conveyor_resistance','abnormal_load','sensor_noise','sensor_drift','sensor_failure']='healthy'
    severity: float=Field(0,ge=0,le=1)
class Training(BaseModel):
    seed:int=Field(42,ge=0)
    runs:int=Field(108,ge=108,le=600)
    steps:int=Field(180,ge=30,le=2000)
    epochs:int=Field(40,ge=1,le=1000)
    physics_lambda:float=Field(1,ge=0,le=100)

class Runtime:
    def __init__(self):
        self.twin=Twin(); self.energy=Energy(); self.state='stopped'; self.history=[]; self.alerts=[]; self.latest=None; self.persistence=0; self.suite=Suite(); self.suite.load()
    def tick(self):
        sensors=self.twin.step()['sensors']; energy=self.energy.update(sensors,self.twin.config.dt)
        scores=None; threshold=None
        if self.suite.ready:
            raw=self.suite.scores(pd.DataFrame([sensors])); scores={k:float(v[0]) for k,v in raw.items()}
            score=scores['hybrid']; threshold=self.suite.thresholds['hybrid']; abnormal=score>threshold
        else:
            score=None; abnormal=False
        self.persistence=self.persistence+1 if abnormal else 0
        detected=self.persistence>=3
        diagnostic=diagnose(sensors,detected)
        if detected and self.suite.ready:
            diagnostic['supervised_component']=str(self.suite.classifier.predict(pd.DataFrame([sensors])[FEATURES])[0])
        self.latest=dict(sensors=sensors,energy=energy,score=score,threshold=threshold,scores=scores,detected=detected,diagnostic=diagnostic,model_status='trained' if self.suite.ready else 'untrained',state=self.state)
        self.history.append(self.latest); self.history=self.history[-3600:]
        if detected and self.persistence==3:
            alert=dict(timestamp=sensors['timestamp'],**diagnostic,score=score,excess_power=energy['residual']); self.alerts.append(alert); save('alert',alert)
        if len(self.history)%10==0: save('telemetry',self.latest)
        return self.latest
runtime=Runtime(); pool=ThreadPoolExecutor(max_workers=1); jobs={}

async def loop():
    while True:
        if runtime.state=='running':
            runtime.tick()
            if runtime.twin.time>=runtime.twin.config.duration: runtime.state='stopped'
        await asyncio.sleep(runtime.twin.config.dt)
@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(loop()); yield; task.cancel()
app=FastAPI(title='Physics-Constrained Industrial Twin',version='1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])
@app.get('/api/health')
def health(): return dict(status='ok',source='synthetic')
@app.get('/api/system/status')
def status(): return dict(state=runtime.state,config=asdict(runtime.twin.config),model_status='trained' if runtime.suite.ready else 'untrained')
@app.post('/api/simulation/{action}')
def control(action:str):
    if action not in ('start','stop','pause','resume','reset'): raise HTTPException(404,'Unknown control')
    if action=='pause' and runtime.state!='running': raise HTTPException(409,'Only running simulations can pause')
    if action=='resume' and runtime.state!='paused': raise HTTPException(409,'Only paused simulations can resume')
    if action=='reset':
        runtime.twin=Twin(runtime.twin.config); runtime.energy=Energy(); runtime.history=[]; runtime.latest=None; runtime.alerts=[]; runtime.persistence=0; runtime.state='stopped'
    else: runtime.state={'start':'running','resume':'running','pause':'paused','stop':'stopped'}[action]
    return status()
# Specific configuration routes registered before dynamic POST route via explicit insert below.
def configure(settings:Settings):
    for k,v in settings.model_dump().items(): setattr(runtime.twin.config,k,v)
    return status()
def fault(settings:Fault):
    runtime.twin.config.fault=settings.fault; runtime.twin.config.severity=settings.severity
    return status()
app.router.routes.insert(0, __import__('fastapi').routing.APIRoute('/api/simulation/configure',configure,methods=['POST']))
app.router.routes.insert(0, __import__('fastapi').routing.APIRoute('/api/simulation/inject-fault',fault,methods=['POST']))
@app.get('/api/sensors/latest')
def latest(): return runtime.latest
@app.get('/api/sensors/history')
def history(limit:int=600): return runtime.history[-max(1,min(limit,3600)):]
@app.get('/api/energy/analysis')
def energy(): return runtime.latest['energy'] if runtime.latest else None
@app.get('/api/anomalies')
def anomalies(): return runtime.alerts
@app.get('/api/localization/latest')
def localization(): return runtime.latest['diagnostic'] if runtime.latest else None
@app.get('/api/models')
def models(): return dict(trained=runtime.suite.ready,metadata=getattr(runtime.suite,'metadata',None))
@app.get('/api/experiments')
def experiments(): return read('experiment',30)
@app.get('/api/jobs')
def job_list(): return jobs
def submit(kind,fn):
    if any(j['status'] in ('queued','running') for j in jobs.values()): raise HTTPException(409,'A managed job is already active')
    key=str(uuid.uuid4()); jobs[key]=dict(kind=kind,status='queued')
    def work():
        jobs[key]['status']='running'
        try: jobs[key].update(status='completed',result=fn())
        except Exception as e: logger.exception('Job failed'); jobs[key].update(status='failed',error=str(e))
    pool.submit(work); return dict(job_id=key)
@app.post('/api/models/train')
def train(config:Training):
    def work():
        df=generate(config.runs,config.steps,config.seed); suite=Suite()
        metadata=suite.train(df,config.seed,config.epochs,config.physics_lambda)
        result=dict(config=config.model_dump(),metrics=suite.evaluate(df)); save('experiment',result)
        Path('experiments/results/latest.json').write_text(json.dumps(result,indent=2)); runtime.suite=suite
        return metadata
    if any(j['status'] in ('queued','running') for j in jobs.values()): raise HTTPException(409,'A managed job is already active')
    return submit('training',work)
@app.post('/api/models/evaluate')
def evaluate():
    if not runtime.suite.ready: raise HTTPException(409,'Train a model first')
    return submit('evaluation',lambda:runtime.suite.evaluate(pd.read_csv('data/synthetic/telemetry.csv')))
@app.get('/api/datasets')
def datasets():
    from backend.datasets.public import CATALOG
    metadata=Path('data/synthetic/metadata.json')
    return dict(synthetic=json.loads(metadata.read_text()) if metadata.exists() else None,public=CATALOG)
@app.post('/api/datasets/prepare')
def prepare(config:Training): return submit('synthetic_dataset',lambda:dict(rows=len(generate(config.runs,config.steps,config.seed))))
@app.websocket('/ws/telemetry')
async def stream(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(runtime.latest); await asyncio.sleep(.25)
    except WebSocketDisconnect: pass
