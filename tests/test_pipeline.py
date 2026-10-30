"""Synthetic tests. All temporary prices are fictitious and never published."""
import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from build_release import prepare,validate
from extract_reports import parse_lines

# Only a real document URL is referenced for schema testing; no document is downloaded.
SOURCE='https://cdn.www.gob.pe/uploads/document/file/10861196/8666398-reporte-de-ingreso-y-precios-en-el-gran-mercado-mayorista-de-lima-27-10-2026.pdf?v=1793121842'
def fixture(folder):
    snapshot=dict(testOnly=True,date='2026-10-27',source='TEST FIXTURE — NOT REAL PRICES',market='TEST MARKET',url=SOURCE,products=[dict(name='TEST PRODUCT',unit='kg',previous=1.0,price=2.0,tonnes=None)])
    history=[dict(name='TEST PRODUCT',unit='kg',price=2.0,date='2026-10-27',url=SOURCE,sha256='a'*64)]
    (folder/'gmml-sample.json').write_text(json.dumps(snapshot));(folder/'gmml-history.json').write_text(json.dumps(history))
    return snapshot,history
class PipelineTests(unittest.TestCase):
    def test_reproducible_package_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);resources=root/'input';resources.mkdir();fixture(resources)
            out=root/'dist';one=prepare(out,resources,allow_test_data=True);two=prepare(out,resources,allow_test_data=True)
            self.assertEqual(one,two);raw=(out/one['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),one['sha256']);self.assertEqual(len(raw),one['bytes'])
            self.assertTrue(json.loads(raw)['testOnly'])
    def test_test_data_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root)
            with self.assertRaises(ValueError):prepare(root/'dist',root)
            self.assertFalse((root/'dist/current.json').exists())
    def test_missing_intake_and_original_unit(self):
        rows=parse_lines('TEST PRODUCT 1 : 3 4 Saco Chico 65.00 1.00 2.00 1.50',2)
        self.assertEqual(rows[0]['unit'],'saco chico');self.assertIsNone(rows[0]['tonnes']);self.assertEqual(rows[0]['price'],2)
    def test_missing_price_rejected(self):
        with self.assertRaises(ValueError):parse_lines('TEST PRODUCT 1 2 3 4 Kilogramo 1.00 1.00 : 1.50',2)
    def test_legacy_hidden_placeholders_do_not_change_price_fields(self):
        rows=parse_lines('Z:apallo Macre 144: 67: 123: 57: Kilogramo 1.00 1.53 1.65 1.E5s5table',2)
        self.assertEqual(rows[0]['name'],'Zapallo Macre')
        self.assertEqual(rows[0]['tonnes'],67)
        self.assertEqual(rows[0]['previous'],1.53)
        self.assertEqual(rows[0]['price'],1.65)
        with self.assertRaises(ValueError):
            parse_lines('Z:apallo Macre 144: 67: 123: 57: Kilogramo 1.00 1.53 : 1.E5s5table',2)

    def test_duplicate_and_mismatched_price_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,h=fixture(Path(tmp));h.append(copy.deepcopy(h[0]))
            with self.assertRaises(ValueError):validate(s,h,allow_test_data=True)
            h.pop();s['products'][0]['price']=3
            with self.assertRaises(ValueError):validate(s,h,allow_test_data=True)
