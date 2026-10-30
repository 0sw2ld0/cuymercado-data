"""Public PRODUCE reports and norms; no Datero internal services or paid infrastructure."""
import datetime, hashlib, io, json, re, tempfile, subprocess, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlparse
import pdfplumber
from fetch_latest import Reader, Links

REPORTS='https://www.producempresarial.pe/category/pesca-acuicultura/artesanal-om/artesanal-reportes/'
VEDAS='https://www.gob.pe/institucion/produce/colecciones/1918-vedas'
class SeaReader(Reader):
    HOSTS=('www.gob.pe','cdn.www.gob.pe','www.producempresarial.pe')
    def raw(self,url,robots=False):
        try:return super().raw(url,robots)
        except subprocess.CalledProcessError as error:
            if error.returncode not in (7,28,56):raise
            time.sleep(3)
            return super().raw(url,robots)


class Node:
    def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.children=[];self.parent=parent
    def text(self):return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split())
    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c,Node):yield from c.walk()
class DOM(HTMLParser):
    def __init__(self):super().__init__();self.root=Node();self.current=self.root
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.current);self.current.children.append(node)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):self.current=node
    def handle_startendtag(self,tag,attrs):self.current.children.append(Node(tag,attrs,self.current))
    def handle_endtag(self,tag):
        node=self.current
        while node.parent:
            if node.tag==tag:self.current=node.parent;break
            node=node.parent
    def handle_data(self,data):self.current.children.append(data)

def lima_today():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).date()

def dated_reports(html):
    links=Links();links.feed(html);result={}
    for url in links.urls:
        m=re.search(r'mercados-mayoristas-pesqueros-(\d{2})-(\d{2})-(\d{4})/?$',url)
        if m and urlparse(url).hostname=='www.producempresarial.pe':
            date=datetime.date(int(m[3]),int(m[2]),int(m[1]))
            if date<=lima_today():result[date.isoformat()]=url
    if not result:raise ValueError('No dated fishing reports in public listing')
    return result

def norm_index(html):
    dom=DOM();dom.feed(html);result=[];seen=set()
    months=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    for node in dom.root.walk():
        url=node.attrs.get('href','')
        if node.tag!='a' or not re.fullmatch(r'/institucion/produce/normas-legales/\d+-[^/?]+',url):continue
        card=node.parent
        if 'shadow-campaign-card' not in card.attrs.get('class',''):continue
        url=urljoin(VEDAS,url)
        if url in seen:continue
        seen.add(url)
        date_text=next((c.text() for c in card.children if isinstance(c,Node) and c.tag=='div'),'')
        m=re.fullmatch(r'(\d{1,2}) de (\w+) de (\d{4})',date_text.replace('setiembre','septiembre').strip())
        if not m or m[2] not in months:raise ValueError('Unknown norm publication date')
        published=datetime.date(int(m[3]),months.index(m[2])+1,int(m[1])).isoformat()
        summary=' '.join(' '.join(c for c in card.children if isinstance(c,str)).split())
        if not summary or not node.text().startswith('Resolución'):raise ValueError('Norm summary format changed')
        result.append(dict(id=url.rsplit('/',1)[-1],title=node.text(),publishedDate=published,summary=summary,url=url))
    if not 10<=len(result)<=100:raise ValueError('Unexpected norm index coverage')
    return result

def index_signature(norms):
    return hashlib.sha256(json.dumps(norms,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def extract_fish(raw,date,url):
    cutoff=datetime.date.fromisoformat(date)
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages)!=1:raise ValueError('Fish report page count changed')
        page=pdf.pages[0];full=page.extract_text() or ''
        months=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
        expected=f'{cutoff.day} de {months[cutoff.month-1]} de {cutoff.year}'
        if expected not in full.lower().replace('setiembre','septiembre'):raise ValueError('Fish PDF date mismatch')
        headers=[w for w in page.extract_words() if w['text']=='Especie' and w['x0']>page.width/2]
        if len(headers)!=1:raise ValueError('Price table header changed')
        text=page.crop((page.width/2,headers[0]['top']-80,page.width,page.height-20)).extract_text() or ''
    rows=parse_fish_table(text,cutoff,url)
    return dict(date=date,source='PRODUCE · OGEIEE',priceType='Promedio mayorista',unit='kg',url=url,sha256=hashlib.sha256(raw).hexdigest(),products=rows)

def norm_details(html):
    dom=DOM();dom.feed(html)
    descriptions=[n.text() for n in dom.root.walk() if 'description' in n.attrs.get('class','').split() and 'rule-content' in n.attrs.get('class','').split()]
    links=Links();links.feed(html);documents=list(dict.fromkeys(u for u in links.urls if u.startswith('https://cdn.www.gob.pe/') and '.pdf' in u.lower()))
    if len(descriptions)!=1 or not descriptions[0] or not documents:raise ValueError('Norm detail structure changed')
    return descriptions[0],documents[0]


def parse_fish_table(text,cutoff,url):
    text=text[text.find('Precio promedio'):] if 'Precio promedio' in text else ''
    if 'S/ por kilo' not in text or 'Precio promedio' not in text:raise ValueError('Unknown fish price type or unit')
    days=re.findall(r'(?:Lun|Mar|Mié|Mie|Jue|Vie|Sáb|Sab|Dom)-(\d{1,2})',text)
    if len(days)!=4 or int(days[-1])!=cutoff.day:raise ValueError('Price columns changed')
    previous=cutoff-datetime.timedelta(days=1)
    for _ in range(31):
        if previous.day==int(days[-2]):break
        previous-=datetime.timedelta(days=1)
    else:raise ValueError('Previous observation date missing')
    number=r'(\d+(?:\.\d+)?|-)'
    pattern=re.compile(r'^(.*?)\s+'+r'\s+'.join([number]*4)+r'\s+(?:[↑↓=]\s*)?(?:-?\d+(?:\.\d+)?%|-)$')
    market=None;rows=[]
    for line in text.splitlines():
        if line.strip()=='Lima y Callao':market='lima-callao';continue
        if line.strip()=='Regiones':market='regiones';continue
        m=pattern.fullmatch(line)
        if m and market:
            name,_,_,before,price=m.groups()
            rows.append(dict(id=market+'|'+name,name=name,market=market,unit='kg',price=None if price=='-' else float(price),previous=None if before=='-' else float(before),date=cutoff.isoformat(),previousDate=previous.isoformat(),url=url,page=1))
    if len(rows)!=12 or len({r['id'] for r in rows})!=12 or any(sum(r['market']==m for r in rows)!=6 for m in ['lima-callao','regiones']):raise ValueError('Unexpected fish catalog coverage')
    if any(r['price'] is not None and not 0<r['price']<1e6 for r in rows):raise ValueError('Invalid fish price')
    return rows
