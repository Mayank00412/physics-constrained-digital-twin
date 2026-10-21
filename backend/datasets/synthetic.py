from pathlib import Path
import json
import numpy as np
import pandas as pd
from backend.physics.engine import Twin, Configuration, FAULTS

def generate(runs=72, steps=180, seed=42, destination='data/synthetic'):
    rng=np.random.default_rng(seed)
    rows=[]
    for run in range(runs):
        split = ['train','train','train','validation','test','ood'][run%6]
        fault = FAULTS[(run//6)%len(FAULTS)]
        # Every split includes healthy calibration runs; run identity is the grouping unit.
        if run//6 % 4 == 0: fault='healthy'
        c=Configuration(seed=seed+run, speed_rpm=float(rng.choice([600,900,1200,1500] if split!='ood' else [450,1750])),
            load_kg=float(rng.choice([30,60,90,120] if split!='ood' else [150,180])),
            ambient_c=float(rng.uniform(18,34)), severity=float(rng.uniform(.2,.7) if split!='ood' else .9),fault=fault)
        twin=Twin(c)
        for step in range(steps):
            result=twin.step()
            rows.append(dict(run_id=f'{seed}-{run}',split=split,operating_point_rpm=c.speed_rpm,operating_load_kg=c.load_kg,**result['sensors'],**{'truth_'+k:v for k,v in result['truth'].items()}))
    frame=pd.DataFrame(rows)
    root=Path(destination); root.mkdir(parents=True,exist_ok=True)
    frame.to_csv(root/'telemetry.csv',index=False)
    (root/'metadata.json').write_text(json.dumps(dict(seed=seed,runs=runs,steps=steps,rows=len(rows),source='synthetic',splits=frame.groupby('split').run_id.nunique().to_dict()),indent=2))
    return frame

def validate(frame):
    required={'run_id','split','power','motor_speed','load','truth_anomaly'}
    if not required.issubset(frame.columns): raise ValueError(f'Missing columns: {required-set(frame.columns)}')
    if frame.groupby('run_id').split.nunique().max()!=1: raise ValueError('Run leakage across splits')
    if not np.isfinite(frame.select_dtypes('number')).all().all(): raise ValueError('Nonfinite measurements')
    return frame
