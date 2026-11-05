import copy, datetime, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etl'))
from carnes_sources import CarnesReader, SERIES, daily_pdfs, parse_bulletin, publications
from update_carnes import update, validate

ROOT = Path(__file__).resolve().parents[1]
DATE = datetime.date(2026, 11, 5)
TEXT = 'BOLETÍN DIARIO\njueves, 5 de noviembre de 2026\nFuente: PRODUCE.'


def word(text, x0, top):
    return dict(text=text, x0=x0, x1=x0 + 3.5 * len(text), top=top)


def table(top, label, values, days=('04', '05')):
    """A header «mié 04 jue 05 Var.» and one row, at the columns of the real bulletin."""
    header = [word('Precio', 69, top), word('mié', 353, top), word(days[0], 365, top), word('jue', 446, top), word(days[1], 457, top), word('Var.', 508, top)]
    row, x = [], 69
    for part in label.split():
        row.append(word(part, x, top + 15)); x += 3.5 * len(part) + 2
    for x, value in zip((239, 355, 448), values):
        if value is not None: row.append(word(value, x, top + 15))
    return header + row


def bulletin(overrides=None, days=('04', '05')):
    overrides = overrides or {}
    words = []
    for i, series in enumerate(SERIES):
        values = overrides.get(series['id'], ('5.10', '5.20', f'{6 + i}.00'))
        words += table(40 * i, series['label'], values, days)
    return [words]


class CarnesTests(unittest.TestCase):
    def test_reads_only_the_bulletin_day_column(self):
        rows = parse_bulletin(TEXT, bulletin(), DATE)
        self.assertEqual(rows['pollo-granja'], 6.0)
        self.assertEqual(rows['bonito'], 13.0)
        self.assertEqual(set(rows), {s['id'] for s in SERIES})

    def test_empty_day_cell_is_omitted_not_shifted(self):
        # Real case of 14/10/2026: «Jurel 9.27 8.60», average and previous day only.
        rows = parse_bulletin(TEXT, bulletin({'jurel': ('9.27', '8.60', None)}), DATE)
        self.assertNotIn('jurel', rows)
        rows = parse_bulletin(TEXT, bulletin({'jurel': ('9.27', '8.60', '-')}), DATE)
        self.assertNotIn('jurel', rows)

    def test_rejects_wrong_dates_missing_rows_and_implausible_values(self):
        with self.assertRaises(ValueError): parse_bulletin(TEXT.replace('5 de', '6 de'), bulletin(), DATE)
        with self.assertRaises(ValueError): parse_bulletin(TEXT, bulletin(days=('03', '04')), DATE)
        with self.assertRaises(ValueError): parse_bulletin(TEXT, [bulletin()[0][:-30]], DATE)
        with self.assertRaises(ValueError): parse_bulletin(TEXT, bulletin({'huevo-rosado': ('1.0', '1.0', '1500.00')}), DATE)
        with self.assertRaises(ValueError): parse_bulletin(TEXT.replace('Fuente: PRODUCE.', ''), bulletin(), DATE)
        with self.assertRaises(ValueError): parse_bulletin('jueves, 5 de noviembre de 2026', bulletin(), DATE)

    def test_listing_never_uses_paginated_collection_or_foreign_hosts(self):
        html = ''.join(f'<a href="/institucion/midagri/informes-publicaciones/{n}-boletin-de-comercializacion-y-precios-de-aves-{m}">x</a>'
                       for n, m in [(1, 'julio-2026'), (2, 'agosto-2026'), (3, 'setiembre-2026'), (4, 'diciembre-2026')])
        pages = publications(html, DATE)
        self.assertEqual([p.split('-')[-2] for p in pages], ['setiembre', 'agosto'])
        pdfs = daily_pdfs('<a href="https://cdn.www.gob.pe/uploads/document/file/1/2-boletin-de-abastecimiento-y-precios-de-aves-05-11-2026.pdf?v=1">a</a>'
                          '<a href="https://evil.test/uploads/document/file/1/2-boletin-de-abastecimiento-y-precios-de-aves-04-11-2026.pdf">b</a>'
                          '<a href="https://cdn.www.gob.pe/uploads/document/file/1/2-boletin-de-abastecimiento-y-precios-de-aves-06-11-2026.pdf">c</a>', DATE)
        self.assertEqual(list(pdfs), [DATE])
        with self.assertRaises(ValueError): CarnesReader().raw('https://www.gob.pe/institucion/midagri/colecciones/4-x?sheet=2')
        with self.assertRaises(ValueError): CarnesReader().raw('https://sistemas.midagri.gob.pe/sisap/')

    def test_failed_query_preserves_published_feed(self):
        class Blocked:
            receipts = []
            def get(self, url): raise ValueError('HTTP error')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / 'data-input/carnes'; folder.mkdir(parents=True)
            (folder / 'current-data.json').write_text('{"observations": []}')
            with self.assertRaises(ValueError): update(root, Blocked())
            self.assertEqual((folder / 'current-data.json').read_text(), '{"observations": []}')
            self.assertFalse((root / 'carnes/current.json').exists())

    def test_real_package_keeps_series_separate_and_traceable(self):
        data = json.loads((ROOT / 'data-input/carnes/current-data.json').read_text()); validate(data, DATE)
        self.assertEqual({s['group'] for s in data['series']}, {'aves', 'pescados'})
        stages = {s['id']: s['priceType'] for s in data['series']}
        self.assertNotEqual(stages['pollo-mayorista'], stages['pollo-consumidor'])
        self.assertTrue(all(o['url'].startswith('https://cdn.www.gob.pe/') for o in data['observations']))
        pointer = json.loads((ROOT / 'carnes/current.json').read_text())
        self.assertEqual(pointer['cutoff'], data['cutoff'])

    def test_validation_rejects_tampering(self):
        data = json.loads((ROOT / 'data-input/carnes/current-data.json').read_text())
        cases = [
            lambda d: d['observations'].append(dict(d['observations'][0])),
            lambda d: d['observations'][0].update(price=0),
            lambda d: d['observations'][0].update(url='https://evil.test/a.pdf'),
            lambda d: d['observations'][0].update(date='2027-01-01'),
            lambda d: d['observations'][0].update(series='res'),
            lambda d: d['series'][0].update(market='Otro mercado'),
            lambda d: d.update(cutoff='2026-01-01'),
            lambda d: d.update(beefPork=''),
        ]
        for change in cases:
            bad = copy.deepcopy(data); change(bad)
            with self.assertRaises(ValueError): validate(bad, DATE)


if __name__ == '__main__':
    unittest.main()
