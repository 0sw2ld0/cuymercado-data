"""Fetch public PRODUCE PDFs + current norm index; publish a separate sea feed."""
import argparse,datetime,hashlib,json
from pathlib import Path
from urllib.parse import urlparse
from sea_sources import SeaReader,REPORTS,VEDAS,dated_reports,norm_index,index_signature,norm_details,extract_fish
from fetch_latest import Links

def validate(data):
    if data['schemaVersion']!=1 or data.get('testOnly'):raise ValueError('Invalid sea schema')
    datetime.date.fromisoformat(data['prices']['date']);datetime.datetime.fromisoformat(data['checkedAt'])
    if data['prices']['source']!='PRODUCE · OGEIEE' or data['prices']['unit']!='kg':raise ValueError('Unknown fish series')
    if len(data['prices']['products'])!=12 or not data['norms'] or not data['rules']:raise ValueError('Empty or changed sea data')
    for row in data['prices']['products']:
        if row['date']!=data['prices']['date'] or row['market'] not in ('lima-callao','regiones') or row['unit']!='kg':raise ValueError('Mixed fish series')
        for field in ['price','previous']:
            if row[field] is not None and not 0<row[field]<1e6:raise ValueError('Invalid price')
        if datetime.date.fromisoformat(row['previousDate'])>=datetime.date.fromisoformat(row['date']):raise ValueError('Invalid previous price date')
    for rows in [data['prices']['products'],data['norms'],data['rules']]:
        if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate sea entry')
    for norm in data['norms']:
        if not norm['url'].startswith('https://www.gob.pe/institucion/produce/normas-legales/'):raise ValueError('Unexpected norm source')
    for rule in data['rules']:
        if not rule['exceptions'] or not rule['zone'] or not rule['scientificName']:raise ValueError('Incomplete rule scope')
        if rule['kind']=='annual':
            for field in ('start','end'):datetime.date.fromisoformat('2000-'+rule[field])
        elif rule['kind']=='fixed':
            if datetime.date.fromisoformat(rule['start'])>datetime.date.fromisoformat(rule['end']):raise ValueError('Rule date order')
        else:raise ValueError('Unknown rule period')

def prepare(root):
    data=json.loads((root/'data-input/sea/current-data.json').read_text());validate(data)
    raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if len(raw)>1_000_000:raise ValueError('Sea package too large')
    digest=hashlib.sha256(raw).hexdigest();path=f'releases/{digest}/pack.json';folder=root/'sea';target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    pointer=dict(schemaVersion=1,release=digest,path=path,sha256=digest,bytes=len(raw),cutoff=data['prices']['date'])
    temp=folder/'current.tmp';temp.write_text(json.dumps(pointer,indent=2)+'\n');temp.replace(folder/'current.json')
    return pointer

def update(root,reader=None):
    reader=reader or SeaReader();folder=root/'data-input/sea';rules=json.loads((folder/'rules.json').read_text())
    reports=dated_reports(reader.get(REPORTS).decode('utf8'));cutoff=max(reports);publication=reports[cutoff]
    links=Links();links.feed(reader.get(publication).decode('utf8'));pdfs=[u for u in links.urls if urlparse(u).hostname=='www.producempresarial.pe' and u.lower().endswith('.pdf')]
    if len(pdfs)!=1:raise ValueError('Report PDF link changed')
    prices=extract_fish(reader.get(pdfs[0]),cutoff,pdfs[0]);prices['publicationURL']=publication
    previous=folder/'current-data.json'
    if previous.exists() and json.loads(previous.read_text())['prices']['date']>cutoff:raise ValueError('Fish date regressed')
    norms=norm_index(reader.get(VEDAS).decode('utf8'));signature=index_signature(norms)
    cache_path=folder/'norm-summaries.json'
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for norm in norms:
        key=hashlib.sha256(json.dumps(norm,sort_keys=True).encode()).hexdigest()
        if key not in cache:
            html=reader.get(norm['url']).decode('utf8');summary,document=norm_details(html)
            cache[key]=dict(summary=summary,documentURL=document,url=norm['url'],pageSha256=hashlib.sha256(html.encode()).hexdigest(),retrievedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
            temporary=cache_path.with_suffix('.tmp');temporary.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n');temporary.replace(cache_path)
        norm['indexSummary']=norm['summary']
        norm['summary']=cache[key]['summary'];norm['documentURL']=cache[key]['documentURL'];norm['summaryCheckedAt']=cache[key]['retrievedAt']

    changed=[]
    for source in rules['documents']:
        html=reader.get(source['publicationURL']).decode('utf8')
        summary,current_document=norm_details(html)
        for norm in norms:
            if norm['url']==source['publicationURL']:
                norm['summary']=summary;norm['documentURL']=current_document
                norm['summaryCheckedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        digest=hashlib.sha256(reader.get(current_document)).hexdigest()
        if digest!=source['sha256']:changed.append(source['id'])
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    data=dict(schemaVersion=1,checkedAt=now,prices=prices,norms=norms,rules=rules['rules'],
        reviewRequired=bool(changed) or signature!=rules['reviewedIndexSignature'],rulesReviewedAt=rules['reviewedAt'],
        coverage=f'{len(norms)} disposiciones recientes del compendio PRODUCE y periodos revisados de choro, paiche y bagre andino. Cobertura parcial; no acredita permiso de pesca o venta.',
        normsURL=VEDAS,indexSignature=signature,changedDocuments=changed)
    validate(data)
    temp=folder/'current-data.tmp';temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(previous)
    pointer=prepare(root)
    print(json.dumps(dict(pointer=pointer,prices=len(prices['products']),norms=len(norms),reviewRequired=data['reviewRequired'],requests=reader.receipts),ensure_ascii=False,indent=2))
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--build-only',action='store_true');a=p.parse_args()
    if a.build_only:print(json.dumps(prepare(a.root),indent=2))
    else:update(a.root)
