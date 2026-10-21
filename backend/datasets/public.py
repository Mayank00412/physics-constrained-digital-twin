"""Conservative official-source downloader. No automatic acceptance of terms."""
from pathlib import Path
from urllib.parse import urlparse,urljoin
from urllib.request import Request,urlopen
from html.parser import HTMLParser
import hashlib,json,zipfile
import numpy as np
import pandas as pd
from scipy.io import loadmat

CATALOG={
 'CWRU':dict(source='https://engineering.case.edu/bearingdatacenter/download-data-file',status='not downloaded',note='Official MATLAB data index verified 2026-10-21. Review source terms before fetching.'),
 'NASA PHM 2009':dict(source='https://c3.ndc.nasa.gov/dashlink/resources/997/',status='source unavailable at verification',note='Official resource timed out 2026-10-21; supply an official accessible file URL after reviewing terms.'),
 'Paderborn':dict(source='https://mb.uni-paderborn.de/kat/forschung/datacenter/bearing-datacenter',status='access requires source review',note='Historical official URL returned 404. Dataset paper specifies CC BY-NC 4.0; review current access and attribution requirements.')}
ALLOWED=('case.edu','nasa.gov','uni-paderborn.de')
def official(url):
    host=urlparse(url).hostname or ''
    return url.startswith('https://') and any(host==d or host.endswith('.'+d) for d in ALLOWED)
def download(url,destination,accept_terms=False,approve_large=False,expected_sha256=None):
    if not accept_terms: raise ValueError('Review official access terms and explicitly pass --accept-terms')
    if not official(url): raise ValueError('Only HTTPS official university/NASA source URLs are supported')
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True); part=dest.with_suffix(dest.suffix+'.part')
    head=urlopen(Request(url,method='HEAD'),timeout=30)
    if not official(head.url): raise ValueError('Redirect left the official source; review manually')
    size=int(head.headers.get('Content-Length',0)); etag=head.headers.get('ETag')
    print(f'Download size: {size/1024**2:.2f} MiB' if size else 'Download size unknown')
    if (not size or size>50*1024**2) and not approve_large: raise ValueError('Unknown or large download requires explicit --approve-large')
    offset=part.stat().st_size if part.exists() else 0
    headers={'Range':f'bytes={offset}-','If-Range':etag} if offset and etag else {}
    headers={k:v for k,v in headers.items() if v}
    with urlopen(Request(url,headers=headers),timeout=60) as response:
        if not official(response.url): raise ValueError('Redirect left the official source')
        resume=offset>0 and response.status==206
        with part.open('ab' if resume else 'wb') as out:
            while chunk:=response.read(1024*1024): out.write(chunk)
    if size and part.stat().st_size!=size: raise ValueError('Incomplete file; keep partial file and retry')
    digest=hashlib.sha256(part.read_bytes()).hexdigest()
    if expected_sha256 and digest!=expected_sha256: raise ValueError('SHA256 mismatch')
    part.replace(dest)
    dest.with_suffix(dest.suffix+'.metadata.json').write_text(json.dumps(dict(source=url,sha256=digest,bytes=dest.stat().st_size,etag=etag,integrity='publisher checksum verified' if expected_sha256 else 'local SHA256 recorded; publisher checksum unavailable'),indent=2))
    return dest
def safe_extract(archive,destination):
    root=Path(destination).resolve(); root.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target=(root/member.filename).resolve()
            if not target.is_relative_to(root) or (member.external_attr>>16)&0o170000==0o120000: raise ValueError('Unsafe archive path or symlink')
        z.extractall(root)
def vibration_windows(path,channel=None,window=2048):
    """Nonoverlapping windows; retain recording identity for grouped evaluation."""
    path=Path(path)
    if path.suffix=='.mat':
        mat=loadmat(path); candidates=[k for k in mat if k.endswith('_DE_time')]
        key=channel or (candidates[0] if len(candidates)==1 else None)
        if key is None: raise ValueError('Specify the MATLAB signal channel explicitly')
        signal=np.asarray(mat[key]).ravel()
    else:
        values=np.loadtxt(path); signal=values if values.ndim==1 else values[:,int(channel or 0)]
    if not np.isfinite(signal).all(): raise ValueError('Nonfinite signal')
    rows=[]
    for start in range(0,len(signal)-window+1,window):
        x=signal[start:start+window]; rms=float(np.sqrt(np.mean(x*x)))
        rows.append(dict(recording_id=path.stem,start=start,rms=rms,peak=float(abs(x).max()),crest=float(abs(x).max()/max(rms,1e-12)),kurtosis=float(np.mean((x-x.mean())**4)/max(x.var()**2,1e-12))))
    return pd.DataFrame(rows)

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a': self.links.extend(v for k,v in attrs if k=='href')
def discover_cwru():
    index=CATALOG['CWRU']['source']; pending=[index]; seen=set(); files=[]
    while pending:
        url=pending.pop()
        if url in seen: continue
        seen.add(url)
        with urlopen(url,timeout=30) as r: html=r.read().decode(errors='replace')
        p=Links(); p.feed(html)
        for href in p.links:
            link=urljoin(url,href)
            if not official(link): continue
            if urlparse(link).path.endswith('.mat'): files.append(link)
            elif len(seen)<6 and any(s in link for s in ['normal-baseline-data','12k-drive-end-bearing-fault-data','48k-drive-end-bearing-fault-data','fan-end-bearing-fault-data']): pending.append(link)
    return sorted(set(files))
