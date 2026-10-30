"""Update latest prices and recover intervening reports before changing local inputs."""
import argparse, datetime, json, os, shutil, tempfile
from pathlib import Path
from urllib.parse import urljoin
from fetch_latest import Reader, Links, COLLECTION, latest_pdf, update
from backfill import backfill
from build_release import validate


def run(root):
    since=json.loads((root/'data-input/processed/gmml-sample.json').read_text())['date']
    # Stage the whole update: a failed recovery never changes the publishable inputs.
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)
        shutil.copytree(root/'data-input',stage/'data-input')
        reader=Reader()
        update(stage,reader)
        links=Links(); links.feed(reader.get(COLLECTION).decode('utf8'))
        publications=list(dict.fromkeys(urljoin(COLLECTION,u) for u in links.urls
            if '/informes-publicaciones/' in u and '-gmml-' in u))
        if not publications:raise ValueError('Monthly publications missing')
        for index,url in enumerate(publications):
            date,_=latest_pdf(reader.get(url).decode('utf8'))
            if date.isoformat()<since:break
            if index>=3:raise ValueError('Recovery exceeds three months; explicit backfill required')
            backfill(stage,url,since)
        folder=stage/'data-input/processed'
        snapshot=json.loads((folder/'gmml-sample.json').read_text())
        history=json.loads((folder/'gmml-history.json').read_text())
        validate(snapshot,history)
        reports=json.loads((stage/'data-input/reports.json').read_text())
        for path in ('processed/gmml-sample.json','processed/gmml-history.json','reports.json'):
            shutil.copyfile(stage/'data-input'/path,root/'data-input'/path)
        result=dict(checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    cutoff=snapshot['date'],products=len(snapshot['products']),
                    reportDates=len(reports),observations=len(history),
                    newReportDates=sum(r['date']>since for r in reports))
        print(json.dumps(result,indent=2))
        summary=os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            age=(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).date()-datetime.date.fromisoformat(snapshot['date'])).days
            with open(summary,'a') as out:
                out.write(f"## Precios MIDAGRI verificados\n\nCorte: **{snapshot['date']}** · {len(snapshot['products'])} productos · {len(reports)} fechas · {len(history)} observaciones.\n\nFechas nuevas recuperadas: {result['newReportDates']}. Antigüedad calendario: {age} días.\n")
                if age>3:out.write('\n⚠️ La fuente no ofrece un reporte reciente; se conserva el corte real. Revisar la publicación oficial.\n')
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'))
    run(p.parse_args().root)
