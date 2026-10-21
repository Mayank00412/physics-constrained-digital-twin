import argparse
from pathlib import Path
from backend.datasets.public import download,discover_cwru,vibration_windows,safe_extract
p=argparse.ArgumentParser(description='Official-source public vibration dataset workflow')
p.add_argument('--discover-cwru',action='store_true');p.add_argument('--url');p.add_argument('--output');p.add_argument('--accept-terms',action='store_true');p.add_argument('--approve-large',action='store_true');p.add_argument('--sha256');p.add_argument('--preprocess');p.add_argument('--channel');p.add_argument('--extract')
a=p.parse_args()
if a.discover_cwru:
    for url in discover_cwru(): print(url)
if a.url:
    if not a.output: p.error('--output is required for download')
    download(a.url,a.output,a.accept_terms,a.approve_large,a.sha256)
if a.preprocess:
    dest=Path('data/processed')/(Path(a.preprocess).stem+'.csv');dest.parent.mkdir(parents=True,exist_ok=True)
    vibration_windows(a.preprocess,a.channel).to_csv(dest,index=False);print(dest)
if a.extract: safe_extract(a.extract,'data/processed/extracted')
