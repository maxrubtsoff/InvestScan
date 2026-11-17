"""Synthetic schema fixtures only; no test records are published as real ads."""
import json,html
import pytest
from parsers import avito,domclick
from parsers.exports import imported,InvalidRecord,converted,next_page
from analyzer.validation import normalize
from storage.database import Database

def avito_item():return dict(title='ГАБ, 50 м²',description='Действующий арендатор — Ozon. МАП 50000 рублей',urlPath='/kazan/kommercheskaya_nedvizhimost/fixture_1?context=tracking',priceDetailed=dict(value=5000000,fullString='5 000 000 ₽',hasValue=True),coords=dict(address_user='Казань, тестовый адрес, 1',lat=55.8,lon=49.1),location=dict(name='Казань',isRegion=False),isVerifiedItem=True)
def domclick_item():return dict(dealType='sale',category='commercial',offerType='office',path='/card/sale__commercial__fixture',description='ГАБ. Действующий арендатор — Ozon. МАП 50000 рублей',objectInfo=dict(area={'value':50},floor=1),address=dict(displayName='Казань, тестовый адрес, 1',coordinates=[55.8,49.1]),price=dict(value=5000000,currency='RUB'))

def test_avito_public_mfe_json_without_executing_code():
    item=avito_item();payload={'loaderData':{'data':{'catalog':{'items':[item]}}}}
    page='<script type="mime/invalid" data-mfe-state="true">'+html.escape(json.dumps(payload))+'</script>'
    row=normalize(avito.convert(avito.offers_from_html(page)[0]))
    assert row['price']==5000000 and row['monthly_rent']==50000 and row['area']==50
    assert row['settlement']=='Казань' and row['tenant_name']=='Ozon'
    assert row['coordinates'] is None and row['active_tenant'] is None and row['verification']=='review'
    assert '?' not in row['sources'][0]['url']
    with pytest.raises(ValueError):avito.offers_from_html('<script type="mime/invalid" data-mfe-state="true">__import__("os")</script>')
    with pytest.raises(ValueError):avito.offers_from_html('<title>Unavailable</title>')

@pytest.mark.parametrize('text',['50000 $','50000 евро','50000 ₽/м²','50000 ₽ за м²','100000 ₽ за кв. м','100000 ₽ за 1 м²','100000 ₽/кв.м','100000 ₽ за квадратный метр','50000 ₽/мес'])
def test_avito_foreign_or_per_sqm_price_is_not_total_rubles(text):
    item=avito_item();item['priceDetailed']['fullString']=text
    assert avito.convert(item)['price'] is None

def test_avito_rental_offer_is_not_property_for_sale():
    item=avito_item();item['title']='Сдается помещение с арендатором, 50 м²'
    assert avito.convert(item) is None

def test_domclick_native_payload_and_strict_rent_fields():
    item=domclick_item();payload={'result':{'items':[item]}}
    row=normalize(domclick.convert(domclick.offers_from_payload(payload)[0]))
    assert row['price']==5000000 and row['monthly_rent']==50000 and row['area']==50
    assert row['coordinates'] is None and row['verification']=='review'
    assert row['sources'][0]['url']=='https://domclick.ru/card/sale__commercial__fixture'
    item['dealType']='rent';assert domclick.convert(item) is None
    item=domclick_item();item['description']='ГАБ. Чистая прибыль 50000 рублей в месяц'
    assert domclick.convert(item)['monthly_rent'] is None
    item['price']['currency']='USD';assert domclick.convert(item)['price'] is None

def test_domclick_html_only_reads_recognized_json_state():
    item=domclick_item();page='<script id="__NEXT_DATA__" type="application/json">'+json.dumps({'props':{'pageProps':{'result':{'items':[item]}}}})+'</script>'
    assert domclick.offers_from_html(page)==[item]
    with pytest.raises(ValueError):domclick.offers_from_html('<h1>Protective check</h1>')

def test_native_domclick_export_and_unknown_date(tmp_path,monkeypatch):
    path=tmp_path/'authorized.json';path.write_text(json.dumps({'result':{'items':[domclick_item()]}}))
    monkeypatch.setattr(domclick,'EXPORT_DIR',tmp_path)
    rows=list(domclick.native_exports());assert len(rows)==1 and rows[0]['acquisition_mode']=='import'
    assert not rows[0].get('source_fetched_at') and rows[0]['import_fingerprint']

def test_import_whitelist_and_record_isolation():
    row=imported({**avito.convert(avito_item()),'cookies':'SECRET','api_key':'SECRET','phone':'PRIVATE'})
    assert all(k not in row for k in ('cookies','api_key','phone'))
    rows=list(converted([42,avito_item()],avito.convert,as_import=True))
    assert isinstance(rows[0],InvalidRecord) and rows[1]['title']=='ГАБ, 50 м²'

def test_pagination_uses_only_same_public_path():
    base='https://www.avito.ru/region/commercial'
    assert next_page('<a rel="next" href="?p=2">next</a>',base)==base+'?p=2'
    assert next_page('<a rel="next" href="https://example.org/steal">next</a>',base) is None
    assert next_page('<a rel="next" href="/login">next</a>',base) is None

def test_old_or_undated_import_cannot_regress_newer_observation(tmp_path):
    db=Database(tmp_path/'db.sqlite')
    fresh=normalize(avito.convert(avito_item()));fresh['source_fetched_at']='2026-01-10T12:00:00+00:00';db.upsert(fresh)
    older=imported({**fresh,'price':1000000,'source_fetched_at':'2026-01-01T12:00:00+00:00'})
    result=db.upsert(normalize(older));assert result['price']==5000000 and result['last_seen']==fresh['source_fetched_at']
    undated=imported({**fresh,'price':2000000,'source_fetched_at':None})
    result=db.upsert(normalize(undated));assert result['price']==5000000 and len(result['history'])==1
    db.close()

def test_identical_undated_import_never_gains_source_freshness(tmp_path):
    db=Database(tmp_path/'db.sqlite');row=normalize(imported(avito.convert(avito_item())))
    first=db.upsert(row);second=db.upsert(normalize(imported(avito.convert(avito_item()))))
    assert first['last_seen'] is None and second['last_seen'] is None
    assert first['first_seen']==second['first_seen'] and first['last_imported_at']==second['last_imported_at']
    assert len(second['history'])==1 and second['history'][0]['event']=='import';db.close()

def test_secondary_undated_import_does_not_erase_primary_observation(tmp_path):
    db=Database(tmp_path/'db.sqlite');row=normalize(avito.convert(avito_item()))
    row.update(settlement='Казань',coordinates=[55.8,49.1],source_fetched_at='2026-01-10T12:00:00+00:00');db.upsert(row)
    secondary=imported({**row,'sources':[{'name':'Домклик','url':'https://domclick.ru/card/fixture'}],'price':1000000,'source_fetched_at':None})
    result=db.upsert(normalize(secondary))
    assert result['price']==5000000 and result['last_seen']==row['source_fetched_at'] and len(result['sources'])==2
    assert result['source_observations'][-1]['observed_at'] is None;db.close()

def test_secondary_repeated_updates_preserve_primary_facts_and_show_price_conflicts(tmp_path):
    db=Database(tmp_path/'db.sqlite');row=normalize(avito.convert(avito_item()));row.update(settlement='Казань',coordinates=[55.8,49.1]);db.upsert(row)
    other=normalize({**row,'sources':[{'name':'Домклик','url':'https://domclick.ru/card/fixture'}],'price':6000000})
    first=db.upsert(other);second=db.upsert(normalize({**other,'price':1000000}))
    assert second['price']==5000000 and second['sources'][0]['name']=='Авито'
    assert second['price_conflict'] is True and {c['value'] for c in second['price_claims']}=={5000000,1000000}
    assert len(second['source_observations'])==1 and second['source_observations'][0]['price']==1000000
    updated=db.upsert(normalize({**row,'price':5500000}))
    assert updated['price']==5500000 and updated['price_conflict'] and len(updated['source_observations'])==1
    assert any(h.get('source')=='Домклик' and h['price']==1000000 for h in updated['history']);db.close()

def test_matching_current_prices_clear_conflict_without_relabeling_foreign_claim(tmp_path):
    db=Database(tmp_path/'db.sqlite');a=normalize(avito.convert(avito_item()));a.update(settlement='Казань',coordinates=[55.8,49.1]);db.upsert(a)
    b=normalize({**a,'sources':[{'name':'Домклик','url':'https://domclick.ru/card/fixture'}],'price':6000000});db.upsert(b)
    current=normalize(avito.convert(avito_item()));current.update(settlement='Казань',coordinates=[55.8,49.1],price=6000000)
    resolved=db.upsert(current)
    assert resolved['price']==6000000 and resolved['price_conflict'] is False
    assert {c['value'] for c in resolved['price_claims']}=={6000000} and resolved['price_per_sqm']==120000
    assert not any(c.get('location')=='Авито' for c in resolved['source_observations'][0]['price_claims']);db.close()

def test_invalid_rows_do_not_stop_good_rows_and_import_is_not_live(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','avito');monkeypatch.setenv('INVESTSCAN_PHOTON','0')
    good=imported(avito.convert(avito_item()));bad={**good,'price':-1}
    monkeypatch.setattr(runner.avito,'collect',lambda:[bad,InvalidRecord('fixture invalid'),good]);runner.run()
    data=json.loads((tmp_path/'data/listings.json').read_text());report=next(s for s in data['sources'] if s['name']=='Авито')
    assert len(data['listings'])==1 and data['listings'][0]['last_seen'] is None
    assert report['invalid_count']==2 and report['live_count']==0 and report['imported_count']==1 and report['status']=='partial'

def test_missing_sqlite_recovers_whole_snapshot_before_partial_collection(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    (tmp_path/'data').mkdir();path=tmp_path/'data/listings.json'
    retained=normalize(avito.convert(avito_item()));retained.update(first_seen='2026-01-01T12:00:00+00:00',last_seen='2026-01-10T12:00:00+00:00',history=[])
    path.write_text(json.dumps(dict(listings=[retained],coverage={'pages':32,'records':472,'complete':True})))
    new=normalize(domclick.convert(domclick_item()))
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','domclick');monkeypatch.setenv('INVESTSCAN_PHOTON','0');monkeypatch.setattr(runner.domclick,'collect',lambda:[new]);runner.run()
    data=json.loads(path.read_text());assert len(data['listings'])==2 and data['coverage']['pages']==32
    previous=next(r for r in data['listings'] if r['sources'][0]['name']=='Авито');assert previous['last_seen']==retained['last_seen']

@pytest.mark.parametrize('stamp',['2026-01-01','2026-01-01T10:00:00','invalid',42])
def test_source_observation_requires_known_timezone(stamp):
    row=avito.convert(avito_item());row['source_fetched_at']=stamp
    with pytest.raises(ValueError):normalize(row)

def test_future_source_observation_cannot_poison_chronology():
    row=avito.convert(avito_item());row['source_fetched_at']='2999-01-01T00:00:00+00:00'
    with pytest.raises(ValueError):normalize(row)

def test_import_only_never_requests_sources_or_geocoding_and_preserves_health(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    (tmp_path/'data').mkdir();path=tmp_path/'data/listings.json'
    path.write_text(json.dumps({'listings':[],'sources':[{'name':'ЦИАН','status':'blocked','count':0,'message':'Previously observed challenge'}]}))
    good=imported(avito.convert(avito_item()));good['sources']=[{'name':'ЦИАН','url':'https://kazan.cian.ru/sale/commercial/1/'}]
    def forbidden(*args,**kwargs):raise AssertionError('Import-only mode must not access network collectors or geocoding')
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','all');monkeypatch.setenv('INVESTSCAN_IMPORTS_ONLY','1');monkeypatch.setenv('INVESTSCAN_PHOTON','1');monkeypatch.setenv('INVESTSCAN_GEOCODE','1')
    monkeypatch.setattr(runner,'imports_for',lambda name:[good] if name=='ЦИАН' else [])
    monkeypatch.setattr(runner,'collect',forbidden);monkeypatch.setattr(runner,'geocode',forbidden);monkeypatch.setattr(runner,'photon_geocode',forbidden)
    for m in (runner.avito,runner.cian,runner.domclick,runner.rbn):monkeypatch.setattr(m,'collect',forbidden)
    runner.run();data=json.loads(path.read_text());report=next(s for s in data['sources'] if s['name']=='ЦИАН')
    assert len(data['listings'])==1 and data['listings'][0]['last_seen'] is None
    assert report['status']=='blocked' and report['live_count']==0 and report['imported_count']==1 and report['checked_this_run'] is False
    assert report['message']=='Previously observed challenge'

def test_live_and_imported_copy_of_same_url_are_not_counted_twice(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    item=avito.convert(avito_item());items=[imported(item),item,item]
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','avito');monkeypatch.setenv('INVESTSCAN_IMPORTS_ONLY','0');monkeypatch.setenv('INVESTSCAN_PHOTON','0');monkeypatch.setattr(runner.avito,'collect',lambda:items)
    runner.run();data=json.loads((tmp_path/'data/listings.json').read_text());report=next(s for s in data['sources'] if s['name']=='Авито')
    assert len(data['listings'])==1 and report['count']==1 and report['live_count']==1 and report['imported_count']==0

def test_partial_live_run_counts_only_imports_not_refreshed_by_live_rows(tmp_path,monkeypatch):
    import scripts.update_catalog as runner
    from parsers.public_source import SourceUnavailable
    a=avito.convert(avito_item());b={**a,'sources':[{'name':'Авито','url':'https://www.avito.ru/kazan/fixture_2'}]}
    def collect():
        yield imported(a);yield imported(b);yield a
        raise SourceUnavailable('Fixture challenge')
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setenv('INVESTSCAN_SOURCES','avito');monkeypatch.setenv('INVESTSCAN_IMPORTS_ONLY','0');monkeypatch.setenv('INVESTSCAN_PHOTON','0');monkeypatch.setattr(runner.avito,'collect',collect)
    runner.run();data=json.loads((tmp_path/'data/listings.json').read_text());report=next(s for s in data['sources'] if s['name']=='Авито')
    assert len(data['listings'])==2 and report['status']=='blocked' and report['count']==2
    assert report['live_count']==1 and report['imported_count']==1
