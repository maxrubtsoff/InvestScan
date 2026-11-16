import pytest
from analyzer.investment import analyze,COST_KEYS
from analyzer.geo import haversine,apply_geo,KAZAN
from analyzer.validation import normalize
from analyzer.scoring import score
from storage.database import Database,duplicate

def sample(**kw):return normalize(dict(title='Test fixture',sources=[{'name':'Test','url':'https://example.org/fixture'}],price=12000000,monthly_rent=100000,area=100,**kw))
def test_finance():
 f=analyze(sample());assert f['annual_rent']==1200000;assert f['gross_yield']==10;assert f['payback_years']==10;assert f['net_yield'] is None;assert len(f['scenarios'])==3

def test_net():
 x=sample(annual_costs={k:0 for k in COST_KEYS},transaction_costs=0,vacancy_months=0);assert analyze(x)['net_yield']==10

def test_zero():
 assert analyze({'price':0,'monthly_rent':100})['gross_yield'] is None
 assert analyze({'price':10,'monthly_rent':0})['payback_years'] is None

def test_geography():
 assert haversine(KAZAN)==0;assert 30<haversine((55.846,48.501))<50
 assert apply_geo({'coordinates':None})['distance_km'] is None
 assert apply_geo({'coordinates':[999,0],'coordinate_source':'fixture','geo_accuracy':'building'})['distance_km'] is None
 assert apply_geo({'coordinates':KAZAN,'coordinate_source':'city centroid','geo_accuracy':'city'})['distance_km'] is None

def test_claims_not_confirmation():
 x=sample(active_tenant=True);assert x['verification']=='review';x=apply_geo(x);x['finance']=analyze(x);assert score(x)['score']<=39

def test_confirmed():assert sample(active_tenant=True,payments_confirmed=True,contract=True,verification_evidence='fixture documents')['verification']=='confirmed'

def test_validation():
 with pytest.raises(ValueError):sample(annual_costs={'tax':-2})
 with pytest.raises(ValueError):sample(active_tenant='yes')

def test_storage(tmp_path):
 db=Database(tmp_path/'test.db');x=sample();db.upsert(x);x=sample();x['price']=11000000;db.upsert(x);assert len(db.all())==1;assert len(db.all()[0]['history'])==2;db.close()

def test_cross_source():
 a=sample(address='Улица, 1',settlement='Казань',coordinates=KAZAN);b={**a,'sources':[{'name':'B','url':'https://example.org/b'}]};assert duplicate(a,b)
 b['area']=150;assert not duplicate(a,b)

def test_negative_net():
 x=sample(annual_costs={k:300000 for k in COST_KEYS},transaction_costs=0,vacancy_months=0)
 f=analyze(x);assert f['net_yield']<0;assert f['net_payback_years'] is None

def test_arr_parser():
 from parsers.arr import parse
 html='<div class="net-renter__link"><a class="net-renter__name" href="https://example.org/fixture">Test fixture</a><span class="props__address">Test address</span><div class="net-renter__prop"><div class="net-renter__label">Стоимость:</div><div class="net-renter__value">12 000 000 руб.</div></div></div>'
 rows,_=parse(html);assert rows[0]['price']==12000000;assert rows[0]['active_tenant'] is None

def test_failed_collection_preserves_snapshot(tmp_path,monkeypatch):
 import scripts.update_catalog as runner,json
 (tmp_path/'data').mkdir();old={'listings':[{'id':'preserved-fixture'}]};(tmp_path/'data/listings.json').write_text(json.dumps(old))
 def fail():raise RuntimeError('fixture outage')
 monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner,'collect',fail);monkeypatch.setattr(runner.avito,'collect',lambda:[]);monkeypatch.setattr(runner.cian,'collect',lambda:[]);monkeypatch.setattr(runner.domclick,'collect',lambda:[]);monkeypatch.setenv('INVESTSCAN_GEOCODE','0');runner.run()
 result=json.loads((tmp_path/'data/listings.json').read_text());assert result['listings']==old['listings'];assert result['sources'][0]['status']=='error'

def test_geocode_city_not_property(tmp_path,monkeypatch):
 import analyzer.geocoding as g,json
 cache=tmp_path/'cache.json';cache.write_text(json.dumps({'fixture':{'lat':'55','lon':'49','addresstype':'city','address':{'city':'Казань'}}}))
 row=g.geocode([{'address':'fixture'}],cache,limit=0)[0];assert row.get('coordinates') is None

def test_nested_settlements():
 from parsers.arr import settlement
 assert settlement('Казань, Волжск, ул Прохорова, д. 114/1')=='Волжск'
 assert settlement('Казань, Новый Кинер ул Серп и Молот, д. 17А')=='Новый Кинер'
 assert settlement('Казань, Мирный пер, д. 6А')=='Казань'

def test_public_client_normal_redirect(monkeypatch):
 import httpx
 from parsers.base import PublicClient
 import parsers.base as base
 def response(req):
  if req.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nAllow: /')
  if req.url.path=='/start':return httpx.Response(302,headers={'location':'//arrpro.ru/end'})
  return httpx.Response(200,text='fixture property')
 c=PublicClient();c.client=httpx.Client(transport=httpx.MockTransport(response));monkeypatch.setattr(base.time,'sleep',lambda _:None)
 assert c.get('https://arrpro.ru/start')=='fixture property'

def test_price_per_sqm():assert sample()['price_per_sqm']==120000

def test_region_queue():
 from analyzer.region import candidate
 assert not candidate({'address':'Самара, пер Второй Безымянный, 4А'})
 assert candidate({'address':'Казань, Новый Кинер ул Серп и Молот, 17А'})

def test_source_photo_with_attribution():
 from parsers.arr import parse
 html='<div class="net-renter__item"><div class="props__img" style="background-image: url(http://cdn-1.arrpro.ru/test.jpg)"></div><div class="net-renter__link"><a class="net-renter__name" href="https://example.org/fixture">Fixture</a><span class="props__address">Fixture address</span></div></div>'
 rows,_=parse(html);assert rows[0]['photos']==['https://cdn-1.arrpro.ru/test.jpg'];assert rows[0]['sources'][0]['name']=='АРР'

@pytest.mark.parametrize('value', ['МАП: 16800','Арендная плата 50000','16800 ₽','Не указан'])
def test_financial_value_is_not_a_tenant(value):
 assert sample(tenant_name=value)['tenant_name'] is None

@pytest.mark.parametrize('value', ['Магнит','1000 мелочей','ООО «МАП»'])
def test_tenant_names_are_retained(value):
 assert sample(tenant_name=value)['tenant_name']==value

def test_retained_records_are_revalidated_after_source_outage(tmp_path,monkeypatch):
 import scripts.update_catalog as runner,json
 (tmp_path/'data').mkdir()
 db=Database(tmp_path/'data/catalog.sqlite');x=sample();x['tenant_name']='МАП: 16800';x['sources']=[{'name':'АРР','url':'https://example.org/fixture'}];db.upsert(x);previous=db.all()[0]['last_seen'];db.close()
 def fail():raise RuntimeError('fixture source outage')
 monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner,'collect',fail)
 for source in [runner.avito,runner.cian,runner.domclick]:monkeypatch.setattr(source,'collect',lambda:[])
 monkeypatch.setenv('INVESTSCAN_GEOCODE','0');runner.run()
 row=json.loads((tmp_path/'data/listings.json').read_text())['listings'][0]
 assert row['tenant_name'] is None
 assert row['source_fetched_at']==previous
 assert row['last_seen']==previous
