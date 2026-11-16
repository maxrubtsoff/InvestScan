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
from parsers import avito,cian,domclick,rbn
from analyzer.photon_geo import geocode as photon_geocode
from parsers.public_source import SourceUnavailable
ROOT=Path(__file__).resolve().parents[1]
def run():
    (ROOT/'data').mkdir(exist_ok=True);db=Database(ROOT/'data/catalog.sqlite');reports=[]
    previous_path=ROOT/'data/listings.json'
    previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous_reports={s['name']:s for s in previous.get('sources',[])}
    collectors=[('АРР',collect),('Авито',avito.collect),('ЦИАН',cian.collect),('Домклик',domclick.collect),('РБН',rbn.collect)]
    enabled=os.environ.get('INVESTSCAN_SOURCES','all').split(',')
    source_ids={'АРР':'arr','Авито':'avito','ЦИАН':'cian','Домклик':'domclick','РБН':'rbn'}
    for name,collector in collectors:
        if 'all' not in enabled and source_ids[name] not in enabled:
            # A targeted check must not erase another source's known blockage,
            # successful count or snapshot date merely because it wasn't queried.
            report=dict(previous_reports.get(name,dict(name=name,status='cached',count=0,message='Источник ещё не проверялся.')))
            report['checked_this_run']=False;reports.append(report);continue
        count=0;excluded=0
        try:
            for raw in (enrich_coordinates(collector()) if name=='АРР' else collector()):
                x=normalize(raw);x=apply_geo(x);x['finance']=analyze(x);x=score(x);db.upsert(x)
                if x.get('catalog_eligible') is False:excluded+=1
                else:count+=1
            reports.append(dict(name=name,excluded_count=excluded,status=('ok' if count else 'empty') if name in ('АРР','РБН','ЦИАН') else ('imported' if count else 'empty'),count=count,message='Публичная общероссийская витрина, вся доступная пагинация (защитный предел 80 страниц). Охват ограничен этим источником. Данные продавцов требуют проверки.' if name=='АРР' else 'Публичная витрина РБН по Казани и окрестностям. Только описания с признаками аренды. Заявленная окупаемость не используется для восстановления МАП.' if name=='РБН' else 'Коммерческая выдача Татарстана; только объявления с признаками арендной модели. Аренда извлекается из явного МАП, не из прибыли бизнеса.' if name=='ЦИАН' else 'Обычный публичный доступ и импорт; без обхода ограничений.'))
        except Exception as e:
            print(f'{name}: {type(e).__name__}: {e}',file=sys.stderr);reports.append(dict(name=name,excluded_count=excluded,status='blocked' if isinstance(e,SourceUnavailable) else 'error',count=count,message=str(e)))
    # Revalidate retained records as extraction rules improve, even on source outages.
    rows=[normalize(row) for row in db.all()]
    if os.environ.get('INVESTSCAN_PHOTON','0')=='1':
        rows=photon_geocode(rows,ROOT/'data/photon-cache.json',limit=4)
    if os.environ.get('INVESTSCAN_GEOCODE','0')=='1':
        rows=geocode(rows,ROOT/'data/geocode-cache.json',limit=10)
    blocked={s['name'] for s in reports if s['status'] in ('blocked','error')}
    for row in rows:
        if row.get('sources') and all(s['name'] in blocked for s in row['sources']) and not row.get('source_fetched_at'):
            row['source_fetched_at']=row.get('last_seen')
        row=apply_geo(row);row['regional_candidate']=candidate(row);row['price_per_sqm']=row['price']/row['area'] if row.get('price') is not None and row.get('area') and not row.get('price_conflict') else None;row['finance']=analyze(row);score(row)
        db.db.execute('UPDATE listings SET payload=? WHERE id=?',(json.dumps(row,ensure_ascii=False),row['id']))
    db.db.commit();db.close();data=dict(schema_version=1,generated_at=now(),listings=[r for r in rows if r.get('catalog_eligible') is not False],sources=reports,coverage=json.loads((ROOT/'data/collection-status.json').read_text()) if (ROOT/'data/collection-status.json').exists() else {})
    destination=ROOT/'data/listings.json'
    # Preserve the published snapshot even if a fresh/missing DB meets an outage.
    if not rows and destination.exists():
        previous=json.loads(destination.read_text());data['listings']=previous.get('listings',[])
    tmp=destination.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(destination)
    print(f'Published {len(data["listings"])} records')
if __name__=='__main__':run()
