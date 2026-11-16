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

@pytest.mark.parametrize('text,expected',[
 ('МАП (Арендный поток): 520 000 руб. в месяц',520000),
 ('МАП: 75 т.р.',75000),
 ('МАП (Арендный поток): 520000 руб.мес. или % от товарооборота',None),
 ('Арендная плата — 50000 рублей в месяц либо 4% от РТО',None),
 ('Прогнозируемый МАП 150000 рублей',None),
 ('Предварительная окупаемость из расчёта МАП 150000 р.',None),
 ('МАП 150000 рублей (прогноз)',None),
 ('МАП 150000 рублей, ориентировочный',None),
 ('МАП 150000 рублей в месяц при полной заполняемости',None),
 ('МАП 150000 рублей в мес. при полной заполняемости',None),
 ('МАП 150000 рублей в месяц при 100% заполняемости',None),
 ('МАП 150000 рублей. Прогноз индексации пока неизвестен.',150000),
])
def test_fixed_monthly_rent_is_not_conditional_or_estimated(text,expected):
 assert rent_claim(text)==expected

def test_bad_commercial_state_does_not_hide_another_valid_script():
 good={'key':'initialState','value':{'results':{'offers':[{'id':1}]}}}
 page='<script>"legacy-commercial-serp-frontend";[].concat(invalid);</script>'
 page+='<script>"legacy-commercial-serp-frontend";[].concat('+json.dumps([good])+');</script>'
 assert offers_from_html(page)==[{'id':1}]

def test_cian_bad_record_does_not_stop_other_offers(monkeypatch):
 import parsers.cian as module
 from parsers.exports import InvalidRecord
 good={'category':'businessSale','fullUrl':'https://kazan.cian.ru/sale/commercial/1/','description':'ГАБ. МАП 50000 рублей','bargainTerms':{'price':5000000,'currency':'rur'}}
 page='<script>"legacy-commercial-serp-frontend";[].concat('+json.dumps([{'key':'initialState','value':{'results':{'offers':[42,good]}}}])+');</script>'
 class Client:
  def get(self,url):return page
 monkeypatch.setattr(module,'collect_source',lambda name:[])
 monkeypatch.setattr(module,'PublicSource',lambda domain:Client())
 rows=list(module.collect())
 assert isinstance(rows[0],InvalidRecord) and rows[1]['price']==5000000
 assert rows[1]['acquisition_mode']=='public_html'

def test_cian_pagination_limit_reports_incomplete_coverage(monkeypatch):
 import parsers.cian as module
 from urllib.parse import urlsplit,parse_qs
 offer={'category':'businessSale','fullUrl':'https://kazan.cian.ru/sale/commercial/1/','description':'ГАБ','bargainTerms':{'price':5000000,'currency':'rur'}}
 state='<script>"legacy-commercial-serp-frontend";[].concat('+json.dumps([{'key':'initialState','value':{'results':{'offers':[offer]}}}])+');</script>'
 class Client:
  def get(self,url):
   p=int(parse_qs(urlsplit(url).query).get('p',['1'])[0])
   return state+f'<a href="/cat.php?deal_type=sale&amp;offer_type=offices&amp;office_type%5B0%5D=10&amp;region=4618&amp;p={p+1}">Далее</a>'
 monkeypatch.setattr(module,'collect_source',lambda name:[])
 monkeypatch.setattr(module,'PublicSource',lambda domain:Client())
 with pytest.raises(RuntimeError,match='охват неполный'):list(module.collect())
