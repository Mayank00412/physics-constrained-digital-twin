import argparse
from backend.datasets.synthetic import generate
p=argparse.ArgumentParser();p.add_argument('--runs',type=int,default=108);p.add_argument('--steps',type=int,default=180);p.add_argument('--seed',type=int,default=42);a=p.parse_args()
df=generate(a.runs,a.steps,a.seed);print(f'Generated {len(df)} synthetic observations')
