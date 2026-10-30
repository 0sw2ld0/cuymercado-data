import copy, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from update_shield import news, validate, update, prepare
ROOT=Path(__file__).resolve().parents[1]

def card(title,date='16 de setiembre de 2026',identifier='123'):
    return f'<div class="card"><h3><a href="/institucion/minsa/noticias/{identifier}-titulo">{title}</a></h3><p>{date}</p></div>'
def page(title='Minsa ordena el retiro de agua de mesa contaminada'):
    return card(title)+''.join(card('Campaña contra el dengue',identifier=str(i)) for i in range(4))

class ShieldTests(unittest.TestCase):
    def test_dates_and_food_scope(self):
        rows=news(page());self.assertEqual(len(rows),1);self.assertEqual(rows[0]['publishedDate'],'2026-09-16')
        self.assertEqual(news(page('Alerta epidemiológica de sarampión')),[])
        self.assertEqual(news(page('Minsa recomienda consumir alimentos nutritivos')),[])
        self.assertEqual(news(page('Se levanta retiro de fórmula infantil'))[0]['id'],'123')
    def test_unavailable_is_not_empty_success(self):
        with self.assertRaises(ValueError):news('<h1>Access denied</h1>')
        with self.assertRaises(ValueError):news(page().replace('setiembre','unknown'))
    def test_real_lots_are_searchable_and_specific(self):
        data=json.loads((ROOT/'data-input/shield/reviewed.json').read_text())
        nan=next(r for r in data['alerts'] if r['id']=='digesa-01-2026')
        self.assertEqual(nan['lots'],['52840742F2']);self.assertIn('800 g',nan['scope'])
        self.assertEqual(next(r for r in data['alerts'] if r['id']=='digesa-09-2026')['registrations'],['P0652824N/NAINYY'])
    def test_integrity_and_failed_refresh_preserves_copy(self):
        class Fake:
            receipts=[]
            def get(self,url):return page().encode()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data-input/shield';folder.mkdir(parents=True)
            (folder/'reviewed.json').write_bytes((ROOT/'data-input/shield/reviewed.json').read_bytes())
            first=update(root,Fake());saved=(folder/'current-data.json').read_bytes();pointer=prepare(root)
            import hashlib
            self.assertEqual(hashlib.sha256((root/'shield'/pointer['path']).read_bytes()).hexdigest(),pointer['sha256'])
            self.assertEqual(first['reviewedAt'],json.loads((folder/'reviewed.json').read_text())['reviewedAt'])
            class Bad(Fake):
                def get(self,url):return b'Unavailable'
            with self.assertRaises(ValueError):update(root,Bad())
            self.assertEqual((folder/'current-data.json').read_bytes(),saved)
            invalid=copy.deepcopy(first);invalid['alerts'][0]['url']='https://fake.example/alert'
            with self.assertRaises(ValueError):validate(invalid)
            invalid=copy.deepcopy(first);invalid['alerts'][0]['scope']=''
            with self.assertRaises(ValueError):validate(invalid)
