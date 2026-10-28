"""Prepare a static, content-addressed release without networking or publishing."""
import argparse, datetime, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def validate(snapshot, history, allow_test_data=False):
    if snapshot.get("testOnly") and not allow_test_data: raise ValueError("Test data cannot be published")
    def date(value): return datetime.date.fromisoformat(value)
    cutoff = date(snapshot['date'])
    if not snapshot['products'] or not history: raise ValueError('Empty dataset')
    keys = [(r['name'], r['unit']) for r in snapshot['products']]
    if len(keys) != len(set(keys)): raise ValueError('Duplicate catalog entry')
    seen = set()
    for r in history:
        key = (r['name'], r['unit'], r['date'])
        if key in seen or date(r['date']) > cutoff: raise ValueError('Duplicate or future observation')
        seen.add(key)
        if not isinstance(r['price'], (float, int)) or not 0 < r['price'] < 1e7: raise ValueError('Invalid price')
        if not re.fullmatch('[a-f0-9]{64}', r['sha256']): raise ValueError('Missing source hash')
        if not r['url'].startswith('https://cdn.www.gob.pe/'): raise ValueError('Unexpected source')
    latest = {(r['name'],r['unit']):r['price'] for r in history if r['date']==snapshot['date']}
    for r in snapshot['products']:
        if latest.get((r['name'],r['unit'])) != r['price']: raise ValueError('Snapshot/history mismatch')
        if not 0 < r['previous'] < 1e7: raise ValueError('Invalid previous price')

def prepare(output, resources=None, allow_test_data=False):
    resources = resources or ROOT/'data-input/processed'
    snapshot=json.loads((resources/'gmml-sample.json').read_text())
    history=json.loads((resources/'gmml-history.json').read_text())
    validate(snapshot,history,allow_test_data)
    package=dict(schemaVersion=1,snapshot=snapshot,history=history)
    if snapshot.get("testOnly"): package["testOnly"]=True
    raw=(json.dumps(package,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    digest=hashlib.sha256(raw).hexdigest()
    path=f'releases/{digest}/pack.json'
    target=output/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    pointer=dict(schemaVersion=1,release=digest,path=path,sha256=digest,bytes=len(raw),cutoff=snapshot['date'])
    # Pointer written only after all content has been validated and written.
    temporary=output/'current.tmp';temporary.write_text(json.dumps(pointer,indent=2)+'\n');temporary.replace(output/'current.json')
    (output/'_headers').write_text('/current.json\n  Cache-Control: no-cache\n/releases/*\n  Cache-Control: public, max-age=31536000, immutable\n/*\n  X-Content-Type-Options: nosniff\n')
    return pointer

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--resources',type=Path,default=ROOT/'data-input/processed')
    args=parser.parse_args()
    print(json.dumps(prepare(args.output,args.resources),indent=2))
