import argparse,json
from pathlib import Path
from backend.datasets.synthetic import generate
from backend.ai.models import Suite
from backend.database.store import save
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=42);p.add_argument('--epochs',type=int,default=40);p.add_argument('--runs',type=int,default=108);p.add_argument('--steps',type=int,default=180);p.add_argument('--physics-lambda',type=float,default=1.0);a=p.parse_args()
df=generate(a.runs,a.steps,a.seed);suite=Suite();suite.train(df,a.seed,a.epochs,a.physics_lambda)
result=dict(config=vars(a),metrics=suite.evaluate(df));Path('experiments/results/latest.json').write_text(json.dumps(result,indent=2));save('experiment',result)
print(json.dumps({split:{name:round(v['f1'],4) for name,v in report['models'].items()} for split,report in result['metrics'].items()},indent=2))
