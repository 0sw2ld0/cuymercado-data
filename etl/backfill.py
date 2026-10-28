"""Explicit, bounded backfill of a directly linked monthly publication. No pagination."""
import argparse,datetime,hashlib,json,re,tempfile
from pathlib import Path
from fetch_latest import Reader,Links
from extract_reports import extract
from build_release import validate

def backfill(root,publication,since):
    reader=Reader();page=Links();page.feed(reader.get(publication).decode('utf8'))
    provenance=root/'data-input/reports.json';reports=json.loads(provenance.read_text());known={r['date'] for r in reports}
    resources=root/'data-input/processed';snapshot=json.loads((resources/'gmml-sample.json').read_text());history=json.loads((resources/'gmml-history.json').read_text());candidates={}
    for url in page.urls:
        m=re.search(r'(\d{2})-(\d{2})-(\d{4})\.pdf(?:\?|$)',url)
        if m:
            date=datetime.date(int(m[3]),int(m[2]),int(m[1])).isoformat()
            if since<=date<=snapshot['date'] and date not in known:candidates[date]=url
    if len(candidates)>31:raise ValueError('Backfill limited to one month / 31 reports per run')
    for date,url in sorted(candidates.items()):
        raw=reader.get(url);report=dict(date=date,url=url,file=f'gmml-{date}.pdf',sha256=hashlib.sha256(raw).hexdigest(),expectedRows=72,retrievedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/report['file']).write_bytes(raw);(folder/'reports.json').write_text(json.dumps([report]));extract(folder,folder/'processed');incoming=json.loads((folder/'processed/gmml-history.json').read_text())
        history.extend(incoming);reports.append(report)
    history.sort(key=lambda r:(r['date'],r['name'],r['unit']));reports.sort(key=lambda r:r['date']);validate(snapshot,history)
    (resources/'gmml-history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n');provenance.write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(addedReports=len(candidates),totalReports=len(reports),observations=len(history),requests=reader.receipts),ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--publication',required=True);p.add_argument('--since',required=True);p.add_argument('--root',type=Path,default=Path('.'));a=p.parse_args();datetime.date.fromisoformat(a.since);backfill(a.root,a.publication,a.since)
