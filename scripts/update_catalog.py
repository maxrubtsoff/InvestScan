"""Independent source updates, durable SQLite, and atomic static JSON export."""
import json,os,sys,tempfile,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analyzer.validation import normalize
from analyzer.geo import apply_geo
from analyzer.region import candidate
from analyzer.investment import analyze
from analyzer.scoring import score
from storage.database import Database,now
from parsers.arr import collect,enrich_coordinates
from analyzer.geocoding import geocode
from parsers import avito,cian,domclick
from parsers.public_source import SourceUnavailable
ROOT=Path(__file__).resolve().parents[1]
def run():
    (ROOT/'data').mkdir(exist_ok=True);db=Database(ROOT/'data/catalog.sqlite');reports=[]
    collectors=[('АРР',collect),('Авито',avito.collect),('ЦИАН',cian.collect),('Домклик',domclick.collect)]
    enabled=os.environ.get('INVESTSCAN_SOURCES','all').split(',')
    source_ids={'АРР':'arr','Авито':'avito','ЦИАН':'cian','Домклик':'domclick'}
    for name,collector in collectors:
        if 'all' not in enabled and source_ids[name] not in enabled:
            reports.append(dict(name=name,status='cached',count=0,message='Ранее собранные записи сохранены. Полный сбор выполняется по расписанию или вручную.'));continue
        count=0
        try:
            for raw in (enrich_coordinates(collector()) if name=='АРР' else collector()):
                x=normalize(raw);x=apply_geo(x);x['finance']=analyze(x);x=score(x);db.upsert(x);count+=1
            reports.append(dict(name=name,status=('ok' if count else 'empty') if name=='АРР' else ('ok' if name=='ЦИАН' and count else ('imported' if count else 'empty')),count=count,message='Публичная общероссийская витрина, вся доступная пагинация (защитный предел 80 страниц). Охват ограничен этим источником. Данные продавцов требуют проверки.' if name=='АРР' else 'Коммерческая выдача Татарстана; только объявления с признаками арендной модели. Аренда извлекается из явного МАП, не из прибыли бизнеса.' if name=='ЦИАН' else 'Обычный публичный доступ и импорт; без обхода ограничений.'))
        except Exception as e:
            print(f'{name}: {type(e).__name__}: {e}',file=sys.stderr);reports.append(dict(name=name,status='blocked' if isinstance(e,SourceUnavailable) else 'error',count=count,message=str(e)))
    rows=db.all()
    if os.environ.get('INVESTSCAN_GEOCODE','0')=='1':
        rows=geocode(rows,ROOT/'data/geocode-cache.json',limit=10)
    for row in rows:
        row=apply_geo(row);row['regional_candidate']=candidate(row);row['price_per_sqm']=row['price']/row['area'] if row.get('price') is not None and row.get('area') else None;row['finance']=analyze(row);score(row)
        db.db.execute('UPDATE listings SET payload=? WHERE id=?',(json.dumps(row,ensure_ascii=False),row['id']))
    db.db.commit();db.close();data=dict(schema_version=1,generated_at=now(),listings=rows,sources=reports,coverage=json.loads((ROOT/'data/collection-status.json').read_text()) if (ROOT/'data/collection-status.json').exists() else {})
    destination=ROOT/'data/listings.json'
    # Preserve the published snapshot even if a fresh/missing DB meets an outage.
    if not rows and destination.exists():
        previous=json.loads(destination.read_text());data['listings']=previous.get('listings',[])
    tmp=destination.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(destination)
    print(f'Published {len(data["listings"])} records')
if __name__=='__main__':run()
