"""Independent source updates, durable SQLite, and atomic static JSON export."""
import json,os,sys,tempfile,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analyzer.validation import normalize
from analyzer.geo import apply_geo
from analyzer.investment import analyze
from analyzer.scoring import score
from storage.database import Database,now
from parsers.arr import collect
ROOT=Path(__file__).resolve().parents[1]
def run():
    (ROOT/'data').mkdir(exist_ok=True);db=Database(ROOT/'data/catalog.sqlite');reports=[]
    collectors=[('АРР',collect)]
    for name,collector in collectors:
        count=0
        try:
            for raw in collector():
                x=normalize(raw);x=apply_geo(x);x['finance']=analyze(x);x=score(x);db.upsert(x);count+=1
            reports.append(dict(name=name,status='ok' if count else 'empty',count=count,message='Публичная общероссийская витрина, до 8 страниц за запуск. Охват частичный. Данные продавцов требуют проверки.'))
        except Exception as e:
            print(f'{name}: {type(e).__name__}: {e}',file=sys.stderr);reports.append(dict(name=name,status='error',count=count,message=str(e)))
    rows=db.all();db.close();data=dict(schema_version=1,generated_at=now(),listings=rows,sources=reports)
    destination=ROOT/'data/listings.json'
    # Preserve the published snapshot even if a fresh/missing DB meets an outage.
    if not rows and destination.exists():
        previous=json.loads(destination.read_text());data['listings']=previous.get('listings',[])
    tmp=destination.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(destination)
    print(f'Published {len(data["listings"])} records')
if __name__=='__main__':run()
