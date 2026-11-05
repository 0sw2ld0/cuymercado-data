"""MIDAGRI daily poultry bulletin (gob.pe): chicken, hen, egg and the PRODUCE jurel/bonito table.

Only the public collection, its monthly publication pages and their PDFs are read. The paginated
collection (`?sheet=`) is disallowed by robots.txt and is never requested. No private SISAP service.
"""
import datetime, hashlib, io, re
from urllib.parse import urljoin, urlparse
import pdfplumber
from fetch_latest import Links, Reader

COLLECTION = 'https://www.gob.pe/institucion/midagri/colecciones/4-boletin-diario-de-comercializacion-y-precio-de-aves'
# The current layout ("BOLETÍN DIARIO", three pages, with the fish table) appears in August 2026.
FIRST_LAYOUT_DAY = datetime.date(2026, 8, 1)
MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
SPANISH_MONTHS = {m: i + 1 for i, m in enumerate(MONTHS)}
SPANISH_MONTHS['setiembre'] = 9

AVES = 'MIDAGRI · DGESEP (SISAP)'
LIMA_CD = 'Centros de distribución de Lima Metropolitana'
SANTA_ANITA = 'Mercado de Productores de Santa Anita'
TERMINALS = 'Terminales pesqueros de Villa María del Triunfo y Ventanilla'

# Fixed catalogue: each row of the bulletin is its own series. Prices of different stages are never merged.
SERIES = [
    dict(id='pollo-granja', name='Pollo vivo', group='aves', priceType='Precio en granja', market='Granjas avícolas que abastecen Lima Metropolitana', origin=AVES, label='Granja'),
    dict(id='pollo-mayorista', name='Pollo vivo', group='aves', priceType='Precio mayorista', market=LIMA_CD, origin=AVES, label='Mayorista (centros de distribucion)'),
    dict(id='pollo-consumidor', name='Pollo eviscerado', group='aves', priceType='Precio al consumidor', market='Mercados minoristas de Lima Metropolitana', origin=AVES, label='Consumidor (mercados minoristas)'),
    dict(id='gallina-colorada', name='Gallina de postura (colorada)', group='aves', priceType='Precio mayorista', market=SANTA_ANITA, origin=SANTA_ANITA, label='De postura (colorada)'),
    dict(id='gallina-reproductora', name='Gallina reproductora', group='aves', priceType='Precio mayorista', market=SANTA_ANITA, origin=SANTA_ANITA, label='Reproductora'),
    dict(id='huevo-rosado', name='Huevo rosado', group='aves', priceType='Precio mayorista', market=SANTA_ANITA, origin=SANTA_ANITA, label='Huevo rosado'),
    dict(id='jurel', name='Jurel', group='pescados', priceType='Precio promedio', market=TERMINALS, origin='PRODUCE', label='Jurel'),
    dict(id='bonito', name='Bonito', group='pescados', priceType='Precio promedio', market=TERMINALS, origin='PRODUCE', label='Bonito'),
]
NUMBER = r'(-|\d{1,4}(?:,\d{3})*\.\d{1,3})'


class CarnesReader(Reader):
    HOSTS = ('www.gob.pe', 'cdn.www.gob.pe')


def publications(html, until):
    """Monthly publication pages of the collection, newest first, from the first month of the current layout."""
    links = Links(); links.feed(html); result = {}
    for url in links.urls:
        m = re.fullmatch(r'/institucion/midagri/informes-publicaciones/\d+-boletin-de-comercializacion-y-precios-de-aves-([a-z]+)-(\d{4})', url)
        if not m or m[1] not in SPANISH_MONTHS: continue
        month = datetime.date(int(m[2]), SPANISH_MONTHS[m[1]], 1)
        if FIRST_LAYOUT_DAY.replace(day=1) <= month <= until.replace(day=1): result[month] = urljoin(COLLECTION, url)
    if not result: raise ValueError('Poultry collection links changed; review required')
    return [result[k] for k in sorted(result, reverse=True)]


def daily_pdfs(html, until):
    """Dated daily PDFs on a monthly publication page; the date comes from the official file name."""
    links = Links(); links.feed(html); result = {}
    for url in links.urls:
        part = urlparse(url)
        m = re.fullmatch(r'/uploads/document/file/\d+/\d+-boletin-de-abastecimiento-y-precios-de-aves-(\d{2})-(\d{2})-(\d{4})\.pdf', part.path)
        if part.scheme != 'https' or part.hostname != 'cdn.www.gob.pe' or not m: continue
        date = datetime.date(int(m[3]), int(m[2]), int(m[1]))
        if date <= until: result[date] = url
    return result


def lines_of(words):
    """Groups pdfplumber words into visual lines, left to right."""
    rows = []
    for word in sorted(words, key=lambda w: (round(w['top']), w['x0'])):
        if rows and abs(rows[-1][0]['top'] - word['top']) < 3: rows[-1].append(word)
        else: rows.append([word])
    return [sorted(r, key=lambda w: w['x0']) for r in rows]


def _center(word):
    return (word['x0'] + word['x1']) / 2


def parse_bulletin(text, pages, date):
    """Values of the bulletin's own day, located by column position under each table header.

    An empty cell in that column means the source published no value for the day: it is omitted,
    never filled with the previous day or the seven-day average.
    """
    lower = text.lower().replace('setiembre', 'septiembre')
    expected = f'{date.day} de {MONTHS[date.month - 1]} de {date.year}'
    if expected not in lower: raise ValueError('Poultry PDF date mismatch')
    if 'boletín diario' not in lower and 'boletin diario' not in lower: raise ValueError('Poultry layout changed')
    if 'Fuente: PRODUCE' not in text: raise ValueError('Fish source changed')
    rows = {}
    labels = {s['label']: s['id'] for s in SERIES}
    found_labels = set()
    for words in pages:
        header = None
        for line in lines_of(words):
            tokens = [w['text'] for w in line]
            if 'Var.' in tokens:
                days = [w for w in line if re.fullmatch(r'\d{2}', w['text'])]
                if len(days) == 2: header = (days[1], int(days[1]['text']))
                continue
            label = ' '.join(w['text'] for w in line if w['x1'] < 200)
            if label not in labels or header is None: continue
            # Arequipa reuses «Al mayorista» with the previous day; only the Lima tables are listed in SERIES.
            if label in found_labels: raise ValueError(f'Row repeated: {label}')
            found_labels.add(label)
            if header[1] != date.day: raise ValueError(f'Column date changed: {label}')
            column = _center(header[0])
            cells = [w for w in line if w['x0'] > 200 and abs(_center(w) - column) < 22]
            if len(cells) > 1: raise ValueError(f'Ambiguous cell: {label}')
            if not cells: continue
            value = cells[0]['text']
            if not re.fullmatch(NUMBER, value): raise ValueError(f'Cell changed: {label}')
            number = _number(value)
            if number is None: continue
            if not 0 < number < 1000: raise ValueError(f'Implausible price: {label}')
            rows[labels[label]] = number
    missing = set(labels) - found_labels
    if missing: raise ValueError('Rows changed: ' + ', '.join(sorted(missing)))
    return rows


def _number(text):
    return None if text == '-' else float(text.replace(',', ''))


def extract_bulletin(raw, date):
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages) != 3: raise ValueError('Poultry page count changed')
        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        pages = [page.extract_words() for page in pdf.pages[1:]]
    return parse_bulletin(text, pages, date), hashlib.sha256(raw).hexdigest()
