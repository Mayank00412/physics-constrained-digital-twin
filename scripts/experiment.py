"""Run independent-seed research experiments and export actual results."""
import argparse,json,os
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
os.environ.setdefault('MPLCONFIGDIR',str(Path('experiments/.matplotlib').resolve()))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from backend.datasets.synthetic import generate
from backend.ai.models import Suite

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='experiments/configs/default.yaml');a=p.parse_args()
    config=yaml.safe_load(Path(a.config).read_text());results=[]
    for seed in config['seeds']:
        df=generate(config['runs'],config['steps'],seed,f'data/synthetic/seed-{seed}')
        suite=Suite();suite.train(df,seed,config['epochs'],config['physics_lambda'],f'models/seed-{seed}')
        result=dict(seed=seed,metrics=suite.evaluate(df));results.append(result)
        Path(f'experiments/results/seed-{seed}.json').write_text(json.dumps(result,indent=2))
    summaries={}
    for split in ('test','ood'):
        summaries[split]={}
        for name in results[0]['metrics'][split]['models']:
            scores=np.array([r['metrics'][split]['models'][name]['f1'] for r in results])
            summaries[split][name]=dict(mean_f1=float(scores.mean()),std_f1=float(scores.std(ddof=1)) if len(scores)>1 else None,seeds=len(scores))
        fig,ax=plt.subplots(figsize=(10,4));names=list(summaries[split]);ax.bar(names,[summaries[split][n]['mean_f1'] for n in names],yerr=[summaries[split][n]['std_f1'] or 0 for n in names],color='#238a75');ax.set_ylim(0,1);ax.set_ylabel('F1 (mean ± sample SD)');ax.tick_params(axis='x',rotation=20);fig.tight_layout()
        Path('experiments/plots').mkdir(exist_ok=True);fig.savefig(f'experiments/plots/{split}-comparison.png',dpi=180);plt.close(fig)
    Path('experiments/results/summary.json').write_text(json.dumps(dict(config=config,summary=summaries),indent=2))
    pd.DataFrame([dict(split=split,model=name,**metrics) for split,models in summaries.items() for name,metrics in models.items()]).to_csv('experiments/results/comparison.csv',index=False)
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
