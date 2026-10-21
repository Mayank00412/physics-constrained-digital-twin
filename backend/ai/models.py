"""Healthy-only detection with held-out calibration; supervised simulated localization."""
from pathlib import Path
import json, time
import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score, confusion_matrix, classification_report, roc_curve, precision_recall_curve, f1_score
from backend.datasets.synthetic import validate
from backend.diagnostics.localize import diagnose

FEATURES=['motor_speed','gearbox_output_speed','conveyor_speed','load','motor_torque','gearbox_output_torque','voltage','current','power_factor','power','mechanical_power','motor_temperature','gearbox_temperature','vibration','acceleration','ambient']
POWER=FEATURES.index('power'); CURRENT=FEATURES.index('current'); VOLTAGE=FEATURES.index('voltage'); PF=FEATURES.index('power_factor')

def network(): return nn.Sequential(nn.Linear(len(FEATURES),24),nn.SiLU(),nn.Linear(24,6),nn.SiLU(),nn.Linear(6,24),nn.SiLU(),nn.Linear(24,len(FEATURES)))

class Suite:
    def __init__(self): self.ready=False
    def residual(self,df):
        electrical=np.sqrt(3)*df.voltage*df.current*df.power_factor
        return np.maximum(abs(df.power-df.expected_power)/np.maximum(df.expected_power,100),abs(df.power-electrical)/np.maximum(electrical,100)).to_numpy()
    def train(self,frame,seed=42,epochs=40,physics_lambda=1.,root='models'):
        validate(frame); torch.set_num_threads(1); torch.manual_seed(seed)
        train=frame[(frame.split=='train')&(frame.truth_anomaly==0)]
        val=frame[(frame.split=='validation')&(frame.truth_anomaly==0)]
        if len(train)<20 or len(val)<20: raise ValueError('Need at least 20 healthy training and validation observations')
        self.scaler=StandardScaler().fit(train[FEATURES]); x=torch.tensor(self.scaler.transform(train[FEATURES]),dtype=torch.float32)
        self.forest=IsolationForest(n_estimators=100,random_state=seed).fit(x.numpy())
        mean=torch.tensor(self.scaler.mean_,dtype=torch.float32); scale=torch.tensor(self.scaler.scale_,dtype=torch.float32)
        expected=torch.tensor(train.expected_power.to_numpy(),dtype=torch.float32)
        self.nets={}; self.losses={}
        validation_x=torch.tensor(self.scaler.transform(val[FEATURES]),dtype=torch.float32)
        validation_expected=torch.tensor(val.expected_power.to_numpy(),dtype=torch.float32)
        for name,weight in [('autoencoder',0.),('hybrid',physics_lambda),('ablation_lambda0',0.)]:
            torch.manual_seed(seed); net=network(); opt=torch.optim.Adam(net.parameters(),lr=.003)
            best=float('inf');best_state=None
            for _ in range(epochs):
                opt.zero_grad(); out=net(x); raw=out*scale+mean
                data_loss=((out-x)**2).mean()
                # SI reconstruction constraints normalized by a 1000 W reference.
                electrical=np.sqrt(3)*raw[:,VOLTAGE]*raw[:,CURRENT]*raw[:,PF]
                physics_loss=(((raw[:,POWER]-electrical)/1000)**2).mean()+(((raw[:,POWER]-expected)/1000)**2).mean()
                loss=data_loss+weight*physics_loss; loss.backward(); opt.step()
                with torch.no_grad():
                    vout=net(validation_x);vraw=vout*scale+mean
                    velec=np.sqrt(3)*vraw[:,VOLTAGE]*vraw[:,CURRENT]*vraw[:,PF]
                    validation_loss=((vout-validation_x)**2).mean()+weight*((((vraw[:,POWER]-velec)/1000)**2).mean()+(((vraw[:,POWER]-validation_expected)/1000)**2).mean())
                    if float(validation_loss)<best:
                        best=float(validation_loss);best_state={k:v.clone() for k,v in net.state_dict().items()}
            net.load_state_dict(best_state)
            net.eval(); self.nets[name]=net
            self.losses[name]=dict(data=float(data_loss.detach()),physics=float(physics_loss.detach()),validation_objective=best)
        labelled=frame[(frame.split=='train')&(frame.truth_anomaly==1)]
        self.classifier=RandomForestClassifier(n_estimators=100,class_weight='balanced',random_state=seed).fit(labelled[FEATURES],labelled.truth_component)
        self.ready=True; raw=self.scores(val,calibrated=False)
        self.thresholds={k:max(float(np.quantile(v,.99)),1e-6) for k,v in raw.items()}
        self.thresholds['fusion']=max(float(np.quantile(.5*raw['physics']/self.thresholds['physics']+.5*raw['autoencoder']/self.thresholds['autoencoder'],.99)),1e-6)
        self.metadata=dict(seed=seed,epochs=epochs,physics_lambda=physics_lambda,features=FEATURES,thresholds=self.thresholds,losses=self.losses,healthy_train_rows=len(train),healthy_validation_rows=len(val))
        root=Path(root); root.mkdir(exist_ok=True,parents=True)
        joblib.dump(dict(scaler=self.scaler,forest=self.forest,classifier=self.classifier,metadata=self.metadata),root/'suite.joblib')
        torch.save({k:v.state_dict() for k,v in self.nets.items()},root/'networks.pt')
        (root/'metadata.json').write_text(json.dumps(self.metadata,indent=2))
        return self.metadata
    def load(self,root='models'):
        root=Path(root)
        if not (root/'suite.joblib').exists(): return False
        state=joblib.load(root/'suite.joblib')
        for key in ('scaler','forest','classifier','metadata'): setattr(self,key,state[key])
        self.thresholds=self.metadata['thresholds']; self.nets={}
        weights=torch.load(root/'networks.pt',map_location='cpu',weights_only=True)
        for k,v in weights.items():
            net=network(); net.load_state_dict(v); net.eval(); self.nets[k]=net
        self.ready=True; return True
    def scores(self,df,calibrated=True):
        if not self.ready: raise ValueError('Models have not been trained')
        if not np.isfinite(df[FEATURES].to_numpy()).all(): raise ValueError('Nonfinite model inputs')
        x=torch.tensor(self.scaler.transform(df[FEATURES]),dtype=torch.float32)
        timings={};start=time.perf_counter();physics=self.residual(df);timings['physics']=(time.perf_counter()-start)*1000/len(df)
        start=time.perf_counter();forest=-self.forest.score_samples(x.numpy());timings['isolation_forest']=(time.perf_counter()-start)*1000/len(df)
        scores=dict(physics=physics,isolation_forest=forest)
        with torch.no_grad():
            for name,net in self.nets.items():
                start=time.perf_counter();scores[name]=((net(x)-x)**2).mean(1).numpy();timings[name]=(time.perf_counter()-start)*1000/len(df)
        if calibrated:
            scores['fusion']=.5*scores['physics']/self.thresholds['physics']+.5*scores['autoencoder']/self.thresholds['autoencoder']
            timings['fusion']=timings['physics']+timings['autoencoder']
        self.last_timings=timings
        return scores
    def evaluate(self,frame):
        reports={}
        for split in ('test','ood'):
            df=frame[frame.split==split]; y=df.truth_anomaly.to_numpy(); start=time.perf_counter(); scores=self.scores(df)
            latency=(time.perf_counter()-start)*1000/len(df)
            models={}
            for name,score in scores.items():
                pred=score>self.thresholds[name]; p,r,f,_=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
                fpr,tpr,_=roc_curve(y,score); precision,recall,_=precision_recall_curve(y,score)
                models[name]=dict(precision=p,recall=r,f1=f,pr_auc=average_precision_score(y,score),roc_auc=roc_auc_score(y,score),false_positive_rate=float(pred[y==0].mean()),confusion_matrix=confusion_matrix(y,pred).tolist(),roc=dict(x=fpr.tolist(),y=tpr.tolist()),pr=dict(x=recall.tolist(),y=precision.tolist()),inference_ms_per_sample=self.last_timings[name])
                models[name]['scenario_detection_rate']={str(fault):float(pred[df.truth_fault.to_numpy()==fault].mean()) for fault in df.truth_fault.unique()}
            faulty=df[df.truth_anomaly==1]; predicted=self.classifier.predict(faulty[FEATURES]); rules=[diagnose(row,True)['component'] for row in faulty.to_dict('records')]
            residual=df.power-df.expected_power
            violation={}
            with torch.no_grad():
                x=torch.tensor(self.scaler.transform(df[FEATURES]),dtype=torch.float32)
                for name,net in self.nets.items():
                    raw=net(x).numpy()*self.scaler.scale_+self.scaler.mean_
                    violation[name]=float(np.mean(abs(raw[:,POWER]-np.sqrt(3)*raw[:,VOLTAGE]*raw[:,CURRENT]*raw[:,PF])))
            reports[split]=dict(models=models,suite_inference_ms_per_sample=latency,localization=dict(supervised_macro_f1=f1_score(faulty.truth_component,predicted,average='macro'),rules_macro_f1=f1_score(faulty.truth_component,rules,average='macro'),report=classification_report(faulty.truth_component,predicted,output_dict=True,zero_division=0),labels=self.classifier.classes_.tolist(),confusion_matrix=confusion_matrix(faulty.truth_component,predicted,labels=self.classifier.classes_).tolist()),energy_prediction_mae_w=float(abs(residual).mean()),energy_prediction_rmse_w=float(np.sqrt((residual**2).mean())),constraint_violation_w=violation)
        return reports
