"""Evaluate vibration features with an explicit recording-level manifest.

Manifest columns: path,label,split,channel (optional); split is train/test.
Labels must come from the publisher's documentation, never inferred here.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report,confusion_matrix
from backend.datasets.public import vibration_windows
p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--seed',type=int,default=42);a=p.parse_args()
manifest=pd.read_csv(a.manifest)
if not {'path','label','split'}.issubset(manifest):p.error('Manifest needs path,label,split')
if manifest.groupby('path').split.nunique().max()!=1:p.error('Recording leakage between train and test')
parts=[]
for row in manifest.to_dict('records'):
    channel=row.get('channel');channel=None if pd.isna(channel) else str(channel)
    frame=vibration_windows(row['path'],channel);frame['label']=row['label'];frame['split']=row['split'];parts.append(frame)
frame=pd.concat(parts);features=['rms','peak','crest','kurtosis'];train=frame[frame.split=='train'];test=frame[frame.split=='test']
if train.empty or test.empty:p.error('Both train and test recordings are required')
model=RandomForestClassifier(n_estimators=200,random_state=a.seed,class_weight='balanced').fit(train[features],train.label)
pred=model.predict(test[features]);result=dict(source_manifest=a.manifest,seed=a.seed,report=classification_report(test.label,pred,output_dict=True,zero_division=0),labels=model.classes_.tolist(),confusion_matrix=confusion_matrix(test.label,pred,labels=model.classes_).tolist(),scope='Vibration fault classification only; no energy-savings validation')
Path('experiments/results/public-vibration.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
