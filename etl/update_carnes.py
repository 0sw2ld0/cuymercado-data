"""Publish a separate `carnes/` feed from MIDAGRI's daily poultry bulletin.

Every observation keeps its own series (stage, market and origin), the bulletin date, the PDF URL
and its SHA-256. Beef and pork stay unavailable: no verified official daily source was found.
"""
import argparse, datetime, hashlib, json, re
from pathlib import Path
from urllib.parse import urlparse
from carnes_sources import COLLECTION, FIRST_LAYOUT_DAY, SERIES, CarnesReader, daily_pdfs, extract_bulletin, publications
from sea_sources import lima_today

COVERAGE = ('Pollo, gallina y huevo de Lima Metropolitana y jurel y bonito de los terminales pesqueros de Villa María del Triunfo '
            'y Ventanilla, según el boletín diario de aves de MIDAGRI desde su formato de agosto de 2026. Solo días con boletín '
            'publicado; cada precio conserva su etapa (granja, mayorista o consumidor) y su mercado. Res y cerdo no tienen una '
            'fuente oficial diaria verificada.')
BEEF_PORK = ('No se encontró una serie oficial diaria y verificable de precios de res y cerdo en soles por kg: el portal SISAP '
             'presentó un certificado TLS vencido y el INEI publica variaciones porcentuales, no precios.')
PUBLIC = [{k: v for k, v in s.items() if k != 'label'} for s in SERIES]


def validate(data, today=None):
    today = today or lima_today()
    if data['schemaVersion'] != 1 or data.get('testOnly'): raise ValueError('Invalid carnes schema')
    checked = datetime.datetime.fromisoformat(data['checkedAt'])
    if checked.tzinfo is None: raise ValueError('Missing timezone')
    if data['collectionURL'] != COLLECTION: raise ValueError('Unexpected collection')
    ids = [s['id'] for s in data['series']]
    if ids != [s['id'] for s in PUBLIC] or data['series'] != PUBLIC: raise ValueError('Series catalogue changed')
    seen = set(); latest = {}
    for row in data['observations']:
        key = (row['series'], row['date'])
        if row['series'] not in ids or key in seen: raise ValueError('Unknown or duplicate observation')
        seen.add(key)
        day = datetime.date.fromisoformat(row['date'])
        if day < FIRST_LAYOUT_DAY or day > today: raise ValueError('Observation outside covered dates')
        if not isinstance(row['price'], (int, float)) or not 0 < row['price'] < 1000: raise ValueError('Invalid price')
        url = urlparse(row['url'])
        if url.scheme != 'https' or url.hostname != 'cdn.www.gob.pe' or not url.path.endswith(day.strftime('%d-%m-%Y') + '.pdf'): raise ValueError('Unexpected document')
        if not re.fullmatch('[a-f0-9]{64}', row['sha256']): raise ValueError('Missing document hash')
        latest[row['series']] = max(latest.get(row['series'], ''), row['date'])
    if set(latest) != set(ids): raise ValueError('Series without observations')
    if data['cutoff'] != max(latest.values()): raise ValueError('Cutoff mismatch')
    if not data['coverage'] or not data['beefPork']: raise ValueError('Missing coverage notes')


def prepare(root):
    data = json.loads((root / 'data-input/carnes/current-data.json').read_text()); validate(data)
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > 1_000_000: raise ValueError('Carnes package too large')
    digest = hashlib.sha256(raw).hexdigest(); path = f'releases/{digest}/pack.json'; folder = root / 'carnes'; target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    pointer = dict(schemaVersion=1, release=digest, path=path, sha256=digest, bytes=len(raw), cutoff=data['cutoff'])
    temp = folder / 'current.tmp'; temp.write_text(json.dumps(pointer, indent=2) + '\n'); temp.replace(folder / 'current.json')
    return pointer


def update(root, reader=None, months=2):
    """Reads the newest `months` publications (all from August 2026 with a larger value) and only new PDFs."""
    reader = reader or CarnesReader(); folder = root / 'data-input/carnes'; folder.mkdir(parents=True, exist_ok=True)
    provenance = folder / 'bulletins.json'; current = folder / 'current-data.json'
    bulletins = json.loads(provenance.read_text()) if provenance.exists() else []
    observations = json.loads(current.read_text())['observations'] if current.exists() else []
    known = {b['date']: b for b in bulletins}
    today = lima_today()
    pages = publications(reader.get(COLLECTION).decode('utf8'), today)[:months]
    found = {}
    for page in pages: found.update(daily_pdfs(reader.get(page).decode('utf8'), today))
    if not found: raise ValueError('No dated poultry bulletins found')
    for date, url in sorted(found.items()):
        if date < FIRST_LAYOUT_DAY or date.isoformat() in known: continue
        raw = reader.get(url)
        try:
            rows, digest = extract_bulletin(raw, date)
        except ValueError as error:
            # A bulletin whose layout or rows differ is recorded with its reason and never guessed.
            known[date.isoformat()] = dict(date=date.isoformat(), url=url, sha256=hashlib.sha256(raw).hexdigest(), status='rechazado', reason=str(error))
            print(f'Rechazado {date}: {error}')
            continue
        known[date.isoformat()] = dict(date=date.isoformat(), url=url, sha256=digest, status='importado', rows=len(rows))
        observations = [o for o in observations if o['date'] != date.isoformat()]
        observations += [dict(series=series, date=date.isoformat(), price=price, url=url, sha256=digest) for series, price in rows.items()]
    if not observations: raise ValueError('No bulletin could be imported')
    newest = max(found)
    if known[newest.isoformat()]['status'] != 'importado': raise ValueError(f'Latest bulletin {newest} rejected; review required')
    observations.sort(key=lambda o: (o['date'], o['series']))
    imported = [o for o in observations]
    cutoff = max(o['date'] for o in imported)
    data = dict(schemaVersion=1, checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), cutoff=cutoff, collectionURL=COLLECTION,
                coverage=COVERAGE, beefPork=BEEF_PORK, series=PUBLIC, observations=imported)
    validate(data)
    temp = folder / 'current-data.tmp'; temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n'); temp.replace(current)
    temp = folder / 'bulletins.tmp'; temp.write_text(json.dumps(sorted(known.values(), key=lambda b: b['date']), ensure_ascii=False, indent=2) + '\n'); temp.replace(provenance)
    pointer = prepare(root)
    print(json.dumps(dict(pointer=pointer, observations=len(imported), bulletins=len(known), requests=len(reader.receipts)), ensure_ascii=False, indent=2))
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, default=Path('.')); p.add_argument('--build-only', action='store_true')
    p.add_argument('--months', type=int, default=2, help='Monthly publications to read; use a larger value once to backfill since August 2026.')
    a = p.parse_args()
    if a.build_only: print(json.dumps(prepare(a.root), indent=2))
    else: update(a.root, months=a.months)
