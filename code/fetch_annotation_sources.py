"""Download separately pinned annotation inputs and exact companion code, checking hashes."""
from pathlib import Path
import argparse,csv,hashlib,urllib.request

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--dest',type=Path,required=True);a=p.parse_args()
a.dest.mkdir(parents=True,exist_ok=True)
for r in csv.DictReader((ROOT/'documentation/annotation_source_manifest.csv').open()):
    target=a.dest/r['file']
    if target.exists():
        assert hashlib.sha256(target.read_bytes()).hexdigest()==r['sha256'],f'Existing file differs: {target}'
    else:
        temporary=target.with_suffix(target.suffix+'.download')
        request=urllib.request.Request(r['url'],headers={'User-Agent':'Public-fraud-research-replication/1.0'})
        with urllib.request.urlopen(request,timeout=60) as response,temporary.open('wb') as out:
            while chunk:=response.read(2**20):out.write(chunk)
        assert hashlib.sha256(temporary.read_bytes()).hexdigest()==r['sha256'],f'Download differs: {temporary}'
        temporary.replace(target)
    assert target.stat().st_size==int(r['bytes'])
    print('Verified',target.name,r['bytes'],'bytes')
