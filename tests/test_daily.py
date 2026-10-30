"""Recovery orchestration tests; synthetic data lives only in temporary folders."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from update_daily import run

class DailyTests(unittest.TestCase):
    def stage(self,root):
        folder=root/'data-input/processed';folder.mkdir(parents=True)
        (folder/'gmml-sample.json').write_text(json.dumps(dict(testOnly=True,date='2026-10-27',products=[])))
        (folder/'gmml-history.json').write_text('[]')
        (root/'data-input/reports.json').write_text('[{"date":"2026-10-27"}]')

    @patch('update_daily.validate')
    @patch('update_daily.latest_pdf',return_value=(__import__('datetime').date(2026,10,29),'unused'))
    @patch('update_daily.Reader')
    def test_failed_recovery_preserves_all_inputs(self,reader,latest,validate):
        reader.return_value.get.return_value=b'<a href="/informes-publicaciones/123-gmml-octubre-2026">month</a>'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.stage(root)
            before={p.relative_to(root):p.read_bytes() for p in (root/'data-input').rglob('*.json')}
            def update(stage,reader):
                (stage/'data-input/processed/gmml-history.json').write_text('["modified staging"]')
            with patch('update_daily.update',side_effect=update),patch('update_daily.backfill',side_effect=ValueError('bad PDF')):
                with self.assertRaises(ValueError):run(root)
            self.assertEqual(before,{p.relative_to(root):p.read_bytes() for p in (root/'data-input').rglob('*.json')})

    @patch('update_daily.validate')
    @patch('update_daily.latest_pdf',return_value=(__import__('datetime').date(2026,10,29),'unused'))
    @patch('update_daily.Reader')
    def test_recovery_uses_previous_cutoff_and_commits_after_validation(self,reader,latest,validate):
        reader.return_value.get.return_value=b'<a href="/informes-publicaciones/123-gmml-octubre-2026">month</a>'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.stage(root)
            def update(stage,reader):
                path=stage/'data-input/processed/gmml-sample.json'
                data=json.loads(path.read_text());data['date']='2026-10-29';path.write_text(json.dumps(data))
            def recover(stage,url,since):
                self.assertEqual(since,'2026-10-27')
                (stage/'data-input/reports.json').write_text(json.dumps([dict(date=d) for d in ['2026-10-27','2026-10-28','2026-10-29']]))
            with patch('update_daily.update',side_effect=update),patch('update_daily.backfill',side_effect=recover):
                result=run(root)
            self.assertEqual(result['newReportDates'],2)
            self.assertEqual(result['cutoff'],'2026-10-29')
            validate.assert_called_once()
