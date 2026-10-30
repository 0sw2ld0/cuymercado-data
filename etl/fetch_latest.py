"""One daily read of MIDAGRI's latest linked PDF; fail closed on access/schema errors."""
import argparse, datetime, fnmatch, hashlib, json, re, subprocess, tempfile, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from extract_reports import extract
from build_release import validate

COLLECTION='https://www.gob.pe/institucion/midagri/colecciones/335-reporte-de-ingreso-y-precios-en-el-gran-mercado-mayorista-de-lima'
AGENT='CuyMercadoData/1.0 (+https://github.com/0sw2ld0/cuymercado-data)'
class Links(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self,tag,attrs):
        href=dict(attrs).get('href','')
        if tag=='a' and href and href not in self.urls:self.urls.append(href)

def allowed_by_robots(text,url):
    # Apply the most specific matching product-token group, then longest matching rule.
    groups=[]; agents=[]; rules=[]; started=False
    for raw in text.splitlines():
        line=raw.split('#',1)[0].strip()
        if ':' not in line:continue
        key,value=[x.strip() for x in line.split(':',1)];key=key.lower()
        if key=='user-agent':
            if started:groups.append((agents,rules));agents=[];rules=[];started=False
            agents.append(value.lower())
        elif key in ('allow','disallow') and agents:
            started=True
            if value:rules.append((key,value))
    if agents:groups.append((agents,rules))
    product=AGENT.split('/',1)[0].lower(); matches=[]
    for names,items in groups:
        score=max([len(n) if n!='*' else 0 for n in names if n=='*' or n in product],default=-1)
        if score>=0:matches.append((score,items))
    if not matches:return True
    best=max(x[0] for x in matches);path=urlparse(url).path
    if urlparse(url).query:path+='?'+urlparse(url).query
    applied=[]
    for score,items in matches:
        if score!=best:continue
        for kind,pattern in items:
            regex=re.escape(pattern.rstrip('$')).replace(r'\*','.*')
            if re.match(regex+('$' if pattern.endswith('$') else ''),path):applied.append((len(pattern.replace('*','')),kind=='allow'))
    return max(applied,default=(0,True))[1]

class Reader:
    HOSTS=('www.gob.pe','cdn.www.gob.pe')
    def __init__(self):self.robots={};self.last=0;self.receipts=[]
    def raw(self,url,robots=False):
        part=urlparse(url)
        if part.scheme!='https' or part.hostname not in self.HOSTS or part.username or part.password or 'sheet' in parse_qs(part.query):raise ValueError('URL outside approved public channel')
        time.sleep(max(0,2-(time.monotonic()-self.last)))
        result=subprocess.run(['curl','--silent','--show-error','--location','--proto','=https','--proto-redir','=https','--connect-timeout','10','--max-time','40','--max-filesize','5000000','--user-agent',AGENT,'--write-out','\n%{http_code}',url],capture_output=True,check=True)
        self.last=time.monotonic();body,status=result.stdout.rsplit(b'\n',1);status=int(status)
        self.receipts.append(dict(url=url,status=status,sha256=hashlib.sha256(body).hexdigest(),retrievedAt=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        if robots and status==404:return b''
        if status!=200:raise ValueError(f'Access unavailable (HTTP {status}); no bypass attempted: {url}')
        return body
    def get(self,url):
        origin='https://'+urlparse(url).netloc
        if origin not in self.robots:self.robots[origin]=self.raw(origin+'/robots.txt',robots=True).decode('utf8',errors='replace')
        if not allowed_by_robots(self.robots[origin],url):raise ValueError('robots.txt disallows URL')
        return self.raw(url)

def latest_pdf(page):
    parser=Links();parser.feed(page)
    candidates=[]
    for url in parser.urls:
        m=re.search(r'(\d{2})-(\d{2})-(\d{4})\.pdf(?:\?|$)',url)
        if m and urlparse(url).hostname=='cdn.www.gob.pe':candidates.append((datetime.date(int(m[3]),int(m[2]),int(m[1])),url))
    if not candidates:raise ValueError('No dated PDFs in official publication')
    return max(candidates)

def update(root,reader=None):
    reader=reader or Reader();processed=root/'data-input/processed'
    old=json.loads((processed/'gmml-sample.json').read_text());history=json.loads((processed/'gmml-history.json').read_text())
    links=Links();links.feed(reader.get(COLLECTION).decode('utf8'))
    publications=[urljoin(COLLECTION,u) for u in links.urls if '/informes-publicaciones/' in u and 'reporte-de-ingreso-y-precios-en-el-gran-mercado-mayorista-de-lima' in u]
    if not publications:raise ValueError('Publication links changed; review required')
    date,url=latest_pdf(reader.get(publications[0]).decode('utf8'))
    if date.isoformat()<old['date'] or date>datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).date():raise ValueError('Future or regressing date')
    raw=reader.get(url);digest=hashlib.sha256(raw).hexdigest()
    reports=json.loads((root/'data-input/reports.json').read_text())
    if any(r['date']==date.isoformat() and r['sha256']==digest for r in reports) and old['date']==date.isoformat():
        print(json.dumps(dict(cutoff=str(date),unchanged=True,requests=reader.receipts),ensure_ascii=False,indent=2))
        return
    report=dict(date=date.isoformat(),url=url,file=f'gmml-{date}.pdf',sha256=digest,expectedRows=72,retrievedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),extractorVersion='gmml-pdf-v2')
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);(folder/report['file']).write_bytes(raw);(folder/'reports.json').write_text(json.dumps([report]));extract(folder,folder/'processed')
        snapshot=json.loads((folder/'processed/gmml-sample.json').read_text());incoming=json.loads((folder/'processed/gmml-history.json').read_text())
    merged=[r for r in history if r['date']!=date.isoformat()]+incoming
    merged.sort(key=lambda r:(r['date'],r['name'],r['unit']))
    validate(snapshot,merged)
    # Files are not committed or published until the complete workflow succeeds.
    (processed/'gmml-sample.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
    (processed/'gmml-history.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2)+'\n')
    provenance=root/'data-input/reports.json';reports=json.loads(provenance.read_text());reports=[r for r in reports if r['date']!=date.isoformat()]+[report];reports.sort(key=lambda r:r['date'])
    provenance.write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    # Operational receipts stay in the runner logs, not in app data or daily commits.
    print(json.dumps(dict(cutoff=str(date),products=len(snapshot['products']),observations=len(merged),requests=reader.receipts),ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));a=p.parse_args();update(a.root)
