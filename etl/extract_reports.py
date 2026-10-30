"""Extract reviewed, locally supplied MIDAGRI PDFs. No networking or scraping."""
import argparse, datetime, hashlib, json, re
from pathlib import Path
import pdfplumber

UNITS={'Kilogramo':'kg','Atado':'atado','Atado Grande':'atado grande','Docena':'docena','Cajon':'cajón','Cajon Chico':'cajón chico','Saco Chico':'saco chico','Bolsa':'bolsa','Ciento':'ciento','Paquete':'paquete','Unidad':'unidad'}
ROW=re.compile(r'^(.*?)\s+([\d.:]+)\s+([\d.:]+)\s+([\d.:]+)\s+([\d.:]+)\s+(Kilogramo|Atado Grande|Atado|Docena|Cajon Chico|Cajon|Saco Chico|Bolsa|Ciento|Paquete|Unidad)\s+([\d.]+)\s+([\d.:]+)\s+([\d.:]+)\s+([\d.:]+)$')
MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

def parse_lines(text,page):
    rows=[]
    for line in text.splitlines():
        match=ROW.fullmatch(line)
        if not match: continue
        name,_,tonnes,_,_,unit,_,previous,price,_=match.groups()
        if ':' in (price,previous): raise ValueError('Review missing prices before importing')
        rows.append(dict(name=name,unit=UNITS[unit],previous=float(previous),price=float(price),tonnes=None if tonnes==':' else float(tonnes),page=page))
    return rows

def extract(input_dir,output):
    reports=json.loads((input_dir/'reports.json').read_text())
    if not reports: raise ValueError('Empty report list')
    snapshots=[];history=[];dates=set()
    for report in reports:
        date=datetime.date.fromisoformat(report['date'])
        if date.isoformat()!=report['date'] or date>datetime.date.today() or report['date'] in dates: raise ValueError('Invalid report date')
        dates.add(report['date'])
        name=report['file']
        if Path(name).name!=name or not name.endswith('.pdf'): raise ValueError('Invalid file path')
        path=input_dir/name
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=report['sha256']: raise ValueError('Source hash mismatch')
        if not report['url'].startswith('https://cdn.www.gob.pe/'): raise ValueError('Unexpected source')
        rows=[];texts=[]
        with pdfplumber.open(path) as pdf:
            for page_number,page in enumerate(pdf.pages,start=1):
                text=page.extract_text() or '';texts.append(text);rows.extend(parse_lines(text,page_number))
        expected=f'{date.day} de {MONTHS[date.month-1]} de {date.year}'
        if expected not in '\n'.join(texts).lower().replace('setiembre', 'septiembre'): raise ValueError('PDF date mismatch')
        if len(rows)!=report.get('expectedRows',72) or len({(r['name'],r['unit']) for r in rows})!=len(rows): raise ValueError('Unexpected coverage or duplicates')
        snapshot=dict(date=report['date'],market='Gran Mercado Mayorista de Lima',source='MIDAGRI · SISAP',url=report['url'],sha256=digest,coverage=f'{len(rows)} productos del reporte; unidades originales, sin conversiones.',products=rows)
        snapshots.append(snapshot)
        for row in rows:
            history.append({k:row[k] for k in ['name','unit','price','page']} | dict(date=report['date'],url=report['url'],sha256=digest))
    output.mkdir(parents=True,exist_ok=True)
    (output/'gmml-sample.json').write_text(json.dumps(max(snapshots,key=lambda r:r['date']),ensure_ascii=False,indent=2)+'\n')
    (output/'gmml-history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
    return len(history)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('data-input'));p.add_argument('--output',type=Path,default=Path('data-input/processed'));a=p.parse_args()
    print(f'{extract(a.input,a.output)} observations extracted')
