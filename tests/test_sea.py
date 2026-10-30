import copy, datetime, hashlib, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from sea_sources import dated_reports,norm_index,norm_details,SeaReader,parse_fish_table
from update_sea import validate,prepare,update

class SeaTests(unittest.TestCase):
    def test_table_columns_keep_today_previous_and_missing_separate(self):
        head='Precio promedio (S/ por kilo)\nEspecie Mar-20 Mié-21 Mar-27 Mié-28\n'
        table=head
        for market in ['Lima y Callao','Regiones']:
            table+=market+'\n'
            table+='\n'.join(f'TEST {i} 99.0 88.0 2.0 {"-" if i==5 else "3.0"} = -' for i in range(6))+'\n'
        rows=parse_fish_table(table,datetime.date(2026,10,28),'https://www.producempresarial.pe/test.pdf')
        self.assertEqual(rows[0]['price'],3.0)
        self.assertEqual(rows[0]['previous'],2.0)
        self.assertEqual(rows[0]['previousDate'],'2026-10-27')
        self.assertIsNone(rows[5]['price'])
        self.assertEqual(rows[6]['market'],'regiones')
        with self.assertRaises(ValueError):parse_fish_table(table.replace('S/ por kilo','USD'),datetime.date(2026,10,28),'test')

    def test_publication_sorting_uses_dates_not_listing_order(self):
        html=''.join(f'<a href="https://www.producempresarial.pe/reporte-abastecimiento-diario-de-recursos-hidrobiologicos-mercados-mayoristas-pesqueros-{d}-10-2026/">report</a>' for d in ['27','28','20'])
        with patch('sea_sources.lima_today',return_value=datetime.date(2026,10,29)):
            reports=dated_reports(html)
        self.assertEqual(max(reports),'2026-10-28')
        with self.assertRaises(ValueError):dated_reports('<a href="https://evil.test/">bad</a>')
    def test_norm_details_exclude_navigation_and_preserve_document_source(self):
        text='<div class="description rule-content"><div>TEST LEGAL SUMMARY</div></div><a href="https://cdn.www.gob.pe/test.pdf">PDF</a>'
        self.assertEqual(norm_details(text),('TEST LEGAL SUMMARY','https://cdn.www.gob.pe/test.pdf'))
        with self.assertRaises(ValueError):norm_details('<div>changed structure</div>')
    def test_failed_query_preserves_published_prices_and_feed(self):
        class Blocked:
            def get(self,url):raise ValueError('HTTP error')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data-input/sea';folder.mkdir(parents=True);(folder/'rules.json').write_text('{}');(folder/'current-data.json').write_text('existing verified data')
            with self.assertRaises(ValueError):update(root,Blocked())
            self.assertEqual((folder/'current-data.json').read_text(),'existing verified data')
            self.assertFalse((root/'sea/current.json').exists())
    def test_source_allowlist_is_separate_from_agriculture(self):
        from fetch_latest import Reader
        self.assertNotIn('www.producempresarial.pe',Reader.HOSTS)
        self.assertIn('www.producempresarial.pe',SeaReader.HOSTS)
        self.assertNotIn('consultasenlinea.produce.gob.pe',SeaReader.HOSTS)
    def test_real_package_hash_and_scope_are_valid(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'data-input/sea/current-data.json').read_text());validate(data)
        self.assertEqual({r['market'] for r in data['prices']['products']},{'lima-callao','regiones'})
        self.assertTrue(all(r['exceptions'] and r['zone'] for r in data['rules']))
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp);folder=stage/'data-input/sea';folder.mkdir(parents=True);(folder/'current-data.json').write_text(json.dumps(data))
            p=prepare(stage);raw=(stage/'sea'/p['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),p['sha256'])
    def test_wrong_unit_and_test_data_rejected(self):
        root=Path(__file__).resolve().parents[1];original=json.loads((root/'data-input/sea/current-data.json').read_text())
        for key,value in [('unit','cajón'),('source','UNKNOWN')]:
            data=copy.deepcopy(original);data['prices'][key]=value
            with self.assertRaises(ValueError):validate(data)
        data=copy.deepcopy(original);data['testOnly']=True
        with self.assertRaises(ValueError):validate(data)
