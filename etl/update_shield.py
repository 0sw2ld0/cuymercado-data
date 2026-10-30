"""Monitor public MINSA news; keep reviewed DIGESA advisories separate from news.

No private API, credentials, pagination, CAPTCHA bypass or registry scraping.
"""
import argparse, datetime, hashlib, json, re, unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlparse
from fetch_latest import Reader
from sea_sources import DOM

INDEXES = ['https://www.gob.pe/institucion/minsa/noticias?filter%5Bterms%5D='+q for q in ('alerta','retiro','digesa')]
MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')

def news(html):
    dom=DOM(); dom.feed(html); result={}; cards=0
    for node in dom.root.walk():
        if 'card' not in node.attrs.get('class','').split(): continue
        links=[n for n in node.walk() if n.tag=='a' and re.fullmatch(r'/institucion/minsa/noticias/\d+-[^/?]+',n.attrs.get('href','')) and n.text()!='Leer más']
        if not links:continue
        cards+=1; link=links[0]; title=link.text(); text=folded(title)
        # Conservative title filter. General disease, medicines, toys and nutrition
        # stories are not converted into product recalls. Unreviewed titles stay news.
        food=any(w in text for w in ('alimento','formula','agua de mesa','timonel','lybre','alula','guttis','byheart','nan supreme','leche','bebida','conserva'))
        concern=any(w in text for w in ('alerta','retiro','retira','no consum','contamin','suspend','levant','riesgo','prohib'))
        if not (food and concern):continue
        m=re.search(r'(\d{1,2}) de (\w+) de (\d{4})',node.text().lower().replace('setiembre','septiembre'))
        if not m or m[2] not in MONTHS:raise ValueError('MINSA date format changed')
        date=datetime.date(int(m[3]),MONTHS.index(m[2])+1,int(m[1])).isoformat()
        url=urljoin('https://www.gob.pe',link.attrs['href'])
        result[url]=dict(id=link.attrs['href'].split('/')[-1].split('-')[0],title=title,publishedDate=date,url=url)
    if cards<5:raise ValueError('MINSA news listing unavailable or format changed')
    return list(result.values())

def validate(data):
    if data['schemaVersion']!=1 or not data['alerts']:raise ValueError('Empty shield feed')
    reviewed=datetime.datetime.fromisoformat(data['reviewedAt']);checked=datetime.datetime.fromisoformat(data['checkedAt'])
    if reviewed.tzinfo is None or checked.tzinfo is None:raise ValueError('Missing timezone')
    for rows in [data['alerts'],data['news']]:
        if len(rows)>150 or len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate or oversized shield rows')
        for row in rows:
            datetime.date.fromisoformat(row['publishedDate'])
            u=urlparse(row['url'])
            if u.scheme!='https' or u.hostname not in ('www.gob.pe','www.digesa.minsa.gob.pe') or u.username or u.password:raise ValueError('Invalid official link')
            if not row['title']:raise ValueError('Missing title')
    for row in data['alerts']:
        if not all(row[k] for k in ('risk','action','scope','company','category','issuer','reviewedAt')):raise ValueError('Incomplete alert scope')
        if row['issuer']!='DIGESA · MINSA':raise ValueError('Unknown issuer')

def prepare(root):
    data=json.loads((root/'data-input/shield/current-data.json').read_text());validate(data)
    raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    if len(raw)>1_000_000:raise ValueError('Shield package too large')
    digest=hashlib.sha256(raw).hexdigest();path=f'releases/{digest}/pack.json';folder=root/'shield';target=folder/path
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    pointer=dict(schemaVersion=1,release=digest,path=path,sha256=digest,bytes=len(raw),cutoff=max(r['publishedDate'] for r in data['alerts']+data['news']))
    temp=folder/'current.tmp';temp.write_text(json.dumps(pointer,indent=2)+'\n');temp.replace(folder/'current.json');return pointer

def update(root,reader=None):
    reader=reader or Reader();folder=root/'data-input/shield'
    reviewed=json.loads((folder/'reviewed.json').read_text());old=folder/'current-data.json'
    existing=json.loads(old.read_text())['news'] if old.exists() else []
    incoming={r['url']:r for r in existing};receipts=[]
    for url in INDEXES:
        raw=reader.get(url)
        for item in news(raw.decode('utf8')):incoming[item['url']]=item
        receipts.append(dict(url=url,sha256=hashlib.sha256(raw).hexdigest()))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    data=dict(reviewed,checkedAt=now,news=sorted(incoming.values(),key=lambda r:(r['publishedDate'],r['id']),reverse=True)[:100],monitoredSources=receipts)
    validate(data)
    # Publish only after every source passed; failures retain the prior check time.
    temp=folder/'current.tmp';temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(old)
    pointer=prepare(root)
    print(json.dumps(dict(pointer=pointer,alerts=len(data['alerts']),news=len(data['news']),requests=reader.receipts),ensure_ascii=False,indent=2))
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--build-only',action='store_true');a=p.parse_args()
    if a.build_only:print(json.dumps(prepare(a.root),indent=2))
    else:update(a.root)
