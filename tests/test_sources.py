import pytest,httpx,json
from parsers.rental_fields import rent_claim,rental_candidate
from parsers.cian import convert,offers_from_html
from parsers.public_source import PublicSource,SourceUnavailable

def test_rent_vs_profit_and_annual():
 assert rent_claim('Чистая прибыль салона 150000 рублей в месяц') is None
 assert rent_claim('Годовой арендный поток — 7 880 000 ₽.') is None
 assert rent_claim('МАП 150 тыс. рублей')==150000
 assert rent_claim('Арендный поток 4195000 рублей в месяц')==4195000
 assert rent_claim('Арендный поток 1200000 ₽ в год') is None

def test_filter_non_rental_business():
 assert not rental_candidate('Продается салон красоты с прибылью 100000')
 assert rental_candidate('Готовый арендный бизнес с арендатором')
 assert not rental_candidate('Субарендный бизнес с арендатором')

def test_public_commercial_state_and_currency():
 offer={'category':'businessSale','fullUrl':'https://kazan.cian.ru/sale/commercial/1/?context=secret','description':'ГАБ с арендатором. МАП 50 000 рублей','totalArea':'50','monthlyIncome':{'income':900000},'bargainTerms':{'price':5000000,'currency':'rur'},'geo':{'coordinates':{'lat':55.8,'lng':49.1},'userInput':'Fixture street, 1','address':[{'geoType':'house','name':'1'}]},'isNeedHideExactAddress':False}
 html='<script>window._cianConfig["legacy-commercial-serp-frontend"]=[].concat('+json.dumps([{'key':'initialState','value':{'results':{'offers':[offer]}}}])+');</script>'
 result=convert(offers_from_html(html)[0]);assert result['monthly_rent']==50000;assert result['sources'][0]['url'].endswith('/1/');assert result['coordinates']==[55.8,49.1]
 offer['isNeedHideExactAddress']=True;assert convert(offer)['coordinates'] is None
 offer['description']='Салон красоты';assert convert(offer) is None

def test_block_stops_without_retry():
 calls=[]
 def handler(req):calls.append(req);return httpx.Response(401,text='challenge')
 c=PublicSource('example.org',delay=0);c.client=httpx.Client(transport=httpx.MockTransport(handler))
 with pytest.raises(SourceUnavailable):c.get('https://example.org/search')
 assert len(calls)==1

def test_nearby_brand_is_not_tenant():
 from parsers.rental_fields import tenant_claim
 assert tenant_claim('Готовый арендный бизнес. Рядом Магнит')[0] is None
 assert tenant_claim('Действующий арендатор — Ozon')[0]=='Ozon'
