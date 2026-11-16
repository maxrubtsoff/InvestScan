import pytest
from parsers.rbn import catalog_links,parse_detail
from analyzer.photon_geo import choose_hit,geocode
from parsers.rental_fields import rental_candidate,tenant_claim

def detail(description):
    return f'''<div class="container content"><div><h1>Тестовое помещение</h1><p class="bold fs28">2 300 000 руб.</p></div>
    <div><div class="col-md-8"><div class="catalog-slider-block"><ul class="catalog-slider"><li><img src="/dir_images/test.jpg"></li></ul></div>
    <p>Площадь: 17.8 м²</p><p>Окупаемость, лет: 11</p>{description}</div><input name="address" value="Казань г., Лукина ул., 50"></div></div>
    <footer>Готовый арендный бизнес. Арендатор Ozon. МАП 100000 рублей</footer>'''

def test_rbn_reads_public_links_without_leaving_catalog():
    html='<a class="item-one2" href="/rents/show/1">1</a><a class="item-one2" href="https://example.org/rents/show/2">2</a><a class="item-one2" href="/rents/show/1">1</a>'
    assert catalog_links(html)==(['https://kazan.rbnpro.ru/rents/show/1'],[])
    with pytest.raises(ValueError):catalog_links('<h1>Unavailable</h1>')

def test_rbn_does_not_use_template_rent_or_reverse_calculate_payback():
    url='https://kazan.rbnpro.ru/rents/show/1'
    assert parse_detail(detail('Пустое помещение, дизайнерский ремонт.'),url) is None
    assert parse_detail(detail('Готовый арендный бизнес: можно сразу сдавать.'),url) is None
    assert parse_detail(detail('Готовый арендный бизнес: при заполнении 1-го этажа окупаемость 10 лет.'),url) is None
    x=parse_detail(detail('Помещение с арендатором. Арендатор — ателье.'),url)
    assert x['price']==2300000 and x['area']==17.8
    assert x['monthly_rent'] is None and x['coordinates'] is None
    assert x['tenant_name']=='ателье' and x['photos']==['https://kazan.rbnpro.ru/dir_images/test.jpg']

def test_present_tenant_and_long_term_lease_are_candidates():
    assert rental_candidate('Есть арендатор — проведение квестов.')
    assert rental_candidate('Помещение с долгосрочным арендатором — салон красоты.')
    assert tenant_claim('Рядом ателье, возможный арендатор — кофейня')==(None,None)

def hit(**overrides):
    p=dict(countrycode='RU',type='house',city='Казань',street='улица Лукина',housenumber='50',osm_key='building');p.update(overrides)
    return dict(properties=p,geometry=dict(type='Point',coordinates=[49.0965,55.8685]))
ROW=dict(address='Казань г., Лукина ул., 50',settlement='Казань',price=2300000,sources=[{'name':'РБН'}])

@pytest.mark.parametrize('props',[dict(city='Самара'),dict(street='улица Ленина'),dict(housenumber='5'),dict(type='city'),dict(countrycode='DE'),dict(housenumber=None)])
def test_geocoder_rejects_wrong_building_or_centroid(props):
    assert choose_hit(ROW,[hit(**props)]) is None

def test_geocoder_uses_cached_building_without_inventing_tenant(tmp_path,monkeypatch):
    import analyzer.photon_geo as module,json
    path=tmp_path/'cache.json';path.write_text(json.dumps({ROW['address']:[hit(osm_key='shop',name='Соседний магазин'),hit()]}))
    monkeypatch.setattr(module.httpx,'get',lambda *a,**k:pytest.fail('cached address must not hit network'))
    row=geocode([dict(ROW)],path,limit=4)[0]
    assert row['coordinates']==[55.8685,49.0965] and row['geo_accuracy']=='building'
    assert row.get('tenant_name') is None

def test_targeted_run_preserves_other_source_health(tmp_path,monkeypatch):
    import scripts.update_catalog as runner,json
    (tmp_path/'data').mkdir();path=tmp_path/'data/listings.json'
    path.write_text(json.dumps(dict(listings=[],sources=[dict(name='ЦИАН',status='blocked',count=11,message='fixture challenge')])))
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner.rbn,'collect',lambda:[])
    monkeypatch.setenv('INVESTSCAN_SOURCES','rbn');monkeypatch.setenv('INVESTSCAN_PHOTON','0')
    runner.run();report=next(s for s in json.loads(path.read_text())['sources'] if s['name']=='ЦИАН')
    assert report['status']=='blocked' and report['count']==11 and report['checked_this_run'] is False

def test_conflicting_source_prices_are_retained_without_financial_estimates():
    from analyzer.validation import normalize
    from analyzer.investment import analyze
    row=normalize(parse_detail(detail('Помещение с арендатором. МАП 50000 рублей. Стоимость объекта: 2 800 000 руб.'),'https://kazan.rbnpro.ru/rents/show/1'))
    assert row['price']==2300000 and {c['value'] for c in row['price_claims']}=={2300000,2800000}
    assert row['price_conflict'] is True and row['price_per_sqm'] is None
    f=analyze(row)
    assert f['annual_rent']==600000 and f['gross_yield'] is None and f['payback_years'] is None and not f['scenarios']

def test_newly_rejected_offer_stays_in_database_but_leaves_public_catalog(tmp_path,monkeypatch):
    import scripts.update_catalog as runner,json
    from storage.database import Database
    from analyzer.validation import normalize
    (tmp_path/'data').mkdir();db=Database(tmp_path/'data/catalog.sqlite')
    url='https://kazan.rbnpro.ru/rents/show/1';previous=normalize(parse_detail(detail('Помещение с арендатором.'),url));db.upsert(previous);db.close()
    rejected=parse_detail(detail('Готовый арендный бизнес: при заполнении окупаемость 10 лет.'),url,include_excluded=True)
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner.rbn,'collect',lambda:[rejected]);monkeypatch.setenv('INVESTSCAN_SOURCES','rbn');monkeypatch.setenv('INVESTSCAN_PHOTON','0');monkeypatch.setenv('INVESTSCAN_GEOCODE','0')
    runner.run();data=json.loads((tmp_path/'data/listings.json').read_text())
    assert data['listings']==[]
    assert next(s for s in data['sources'] if s['name']=='РБН')['excluded_count']==1
    db=Database(tmp_path/'data/catalog.sqlite');assert len(db.all())==1 and db.all()[0]['catalog_eligible'] is False;db.close()
