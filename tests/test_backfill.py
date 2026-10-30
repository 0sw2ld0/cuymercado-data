import datetime, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from backfill import backfill

class FakeReader:
    receipts=[]
    def get(self,url):
        if url.endswith('/publication'):
            return b'<a href="https://cdn.www.gob.pe/26-10-2026.pdf">bad</a><a href="https://cdn.www.gob.pe/27-10-2026.pdf">good</a>'
        return b'SYNTHETIC TEST PDF PLACEHOLDER'

class BackfillTests(unittest.TestCase):
    def setup_root(self,root):
        folder=root/'data-input/processed';folder.mkdir(parents=True)
        (folder/'gmml-sample.json').write_text('{"date":"2026-10-29"}')
        (folder/'gmml-history.json').write_text('[]')
        (root/'data-input/reports.json').write_text('[]')
    def extract(self,folder,output):
        report=json.loads((folder/'reports.json').read_text())[0]
        if report['date']=='2026-10-26':raise ValueError('PDF date mismatch')
        output.mkdir();(output/'gmml-history.json').write_text('[{"date":"2026-10-27","name":"TEST","unit":"kg"}]')
    @patch('backfill.Reader',FakeReader)
    @patch('backfill.validate')
    def test_explicit_historical_mode_records_rejections_without_importing_them(self,validate):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_root(root)
            with patch('backfill.extract',side_effect=self.extract):
                backfill(root,'https://www.gob.pe/publication','2026-10-01',skip_invalid=True)
            self.assertEqual(len(json.loads((root/'data-input/processed/gmml-history.json').read_text())),1)
            self.assertEqual(json.loads((root/'data-input/rejected-reports.json').read_text())[0]['date'],'2026-10-26')
            self.assertEqual(json.loads((root/'data-input/reports.json').read_text())[0]['date'],'2026-10-27')
    @patch('backfill.Reader',FakeReader)
    def test_daily_default_fails_without_mutating_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_root(root)
            before={p:p.read_bytes() for p in (root/'data-input').rglob('*.json')}
            with patch('backfill.extract',side_effect=self.extract):
                with self.assertRaises(ValueError):backfill(root,'https://www.gob.pe/publication','2026-10-01')
            self.assertEqual(before,{p:p.read_bytes() for p in (root/'data-input').rglob('*.json')})
