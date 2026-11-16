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
