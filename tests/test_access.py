import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from fetch_latest import allowed_by_robots,latest_pdf,update
class AccessTests(unittest.TestCase):
    def test_pagination_and_admin_are_blocked(self):
        rules='User-agent: *\nDisallow: /admin/\nDisallow: /*?sheet=\nDisallow: /*&sheet=\n'
        self.assertFalse(allowed_by_robots(rules,'https://www.gob.pe/list?sheet=2'))
        self.assertFalse(allowed_by_robots(rules,'https://www.gob.pe/list?a=1&sheet=2'))
        self.assertFalse(allowed_by_robots(rules,'https://www.gob.pe/admin/x'))
        self.assertTrue(allowed_by_robots(rules,'https://www.gob.pe/institucion/midagri'))
    def test_specific_group_and_allow(self):
        rules='User-agent: *\nAllow: /\nUser-agent: CuyMercadoData\nDisallow: /\nAllow: /public/\n'
        self.assertFalse(allowed_by_robots(rules,'https://www.gob.pe/private'))
        self.assertTrue(allowed_by_robots(rules,'https://www.gob.pe/public/x'))
    def test_access_failure_keeps_existing_data(self):
        class Blocked:
            def get(self,url):raise ValueError('HTTP 418; no bypass')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data-input/processed';folder.mkdir(parents=True)
            before=b'{"date":"2026-10-27"}'
            (folder/'gmml-sample.json').write_bytes(before);(folder/'gmml-history.json').write_text('[]')
            with self.assertRaises(ValueError):update(root,Blocked())
            self.assertEqual((folder/'gmml-sample.json').read_bytes(),before)
            self.assertEqual((folder/'gmml-history.json').read_text(),'[]')
    def test_empty_or_changed_publication_rejected(self):
        with self.assertRaises(ValueError):latest_pdf('<html>no PDF</html>')
