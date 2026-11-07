"""Download pinned public financial tables and check observed SHA256 values.
Large financial tables are intentionally not redistributed in this package.
"""
import argparse,csv,hashlib,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dest',type=Path,required=True);a=p.parse_args();a.dest.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1]
for row in csv.DictReader((root/'documentation/source_manifest.csv').open()):
    if not row['file'].startswith('hf_'):continue
    target=a.dest/row['file']
    if not target.exists():
        temp=target.with_suffix('.download')
        req=urllib.request.Request(row['url'],headers={'User-Agent':'Public-fraud-research-replication/1.0'})
        with urllib.request.urlopen(req,timeout=120) as response,temp.open('wb') as f:
            while chunk:=response.read(2**20):f.write(chunk)
        temp.replace(target)
    h=hashlib.sha256()
    with target.open('rb') as f:
        while chunk:=f.read(2**20):h.update(chunk)
    if h.hexdigest()!=row['sha256']:raise RuntimeError(f'Checksum mismatch: {target}')
    print('Verified',target.name,row['bytes'],'bytes')
