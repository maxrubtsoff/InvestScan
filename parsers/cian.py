"""Commercial Cian pages: parse public server-rendered JSON, not cianparser's residential API.
Reference inspected: https://github.com/lenarsaitov/cianparser (no upstream code copied).
"""
import json,re
from urllib.parse import urlsplit,urlunsplit,urljoin,parse_qs
from bs4 import BeautifulSoup
from parsers.public_source import PublicSource
from parsers.rental_fields import rental_candidate,rent_claim,tenant_claim
from parsers.manual import collect_source
from parsers.exports import converted
SEED='https://kazan.cian.ru/kupit-gotoviy-biznes-tatarstan/'
def offers_from_html(html):
 soup=BeautifulSoup(html,'html.parser');found=[]
 for script in soup.select('script'):
  text=script.string or script.get_text()
  if 'legacy-commercial-serp-frontend' not in text or '.concat(' not in text:continue
  try:data=json.JSONDecoder().raw_decode(text.split('.concat(',1)[1])[0]
  except (ValueError,TypeError):continue
  if not isinstance(data,list):continue
  for entry in data:
   if not isinstance(entry,dict) or entry.get('key')!='initialState':continue
   state=entry.get('value');results=state.get('results') if isinstance(state,dict) else None
   if isinstance(results,dict) and isinstance(results.get('offers'),list):found.extend(results['offers'])
 return found

def convert(o):
 if o.get('category') not in ('businessSale','freeAppointmentObjectSale','shoppingAreaSale','buildingSale','officeSale'):return None
 text=o.get('description') or ''
 if not rental_candidate(text):return None
 terms=o.get('bargainTerms') or {};geo=o.get('geo') or {};parts=geo.get('address') or []
 currency=terms.get('currency');price=terms.get('priceRur')
 if price is None and currency=='rur':price=terms.get('price')
 coords=geo.get('coordinates') or {};hidden=o.get('isNeedHideExactAddress')
 precise=hidden is False and bool(geo.get('userInput')) and not re.search(r'не указан|скрыт|нет адрес',geo.get('userInput',''),re.I) and any(p.get('geoType')=='house' and re.search(r'\d',p.get('name') or p.get('title') or '') and not re.search(r'не указан|скрыт|нет',p.get('name') or p.get('title') or '',re.I) for p in parts) and all(isinstance(coords.get(k),(int,float)) for k in ['lat','lng'])
 u=urlsplit(o.get('fullUrl') or '');url=urlunsplit((u.scheme,u.netloc,u.path,'',''))
 if u.scheme!='https' or not (u.hostname or '').endswith('.cian.ru'):return None
 name,kind=tenant_claim(text)
 local=[p.get('name') for p in parts if p.get('geoType')=='location' and p.get('locationTypeId')!=140]
 district=next((p.get('name') for p in parts if p.get('geoType')=='district'),None)
 title=o.get('formattedFullInfo') or 'Помещение с заявленной арендной моделью'
 return dict(title=title,sources=[{'name':'ЦИАН','url':url}],address=geo.get('userInput') or ', '.join(p.get('title','') for p in parts if p.get('isFormingAddress')),settlement=local[-1] if local else None,district=district,price=price,area=float(o['totalArea']) if o.get('totalArea') else None,monthly_rent=rent_claim(text),tenant_name=name,tenant_type=kind,coordinates=[coords['lat'],coords['lng']] if precise else None,coordinate_source='ЦИАН: координаты объекта в публичной странице' if precise else None,geo_accuracy='building' if precise else None,floor=o.get('floorNumber'),photos=[p.get('thumbnail2Url') or p.get('thumbnailUrl') for p in o.get('photos',[]) if p.get('thumbnailUrl')][:3],description='В объявлении заявлена арендная модель. Платежи и договор независимо не проверены. Доход от операционного бизнеса не используется как аренда.',active_tenant=None,payments_confirmed=None,contract=None,published_at=o.get('creationDate') if isinstance(o.get('creationDate'),str) else None)

def collect():
 yield from collect_source('ЦИАН');client=PublicSource('cian.ru');url=SEED;seen=set()
 for _ in range(12):
  if not url or url in seen:break
  seen.add(url);html=client.get(url);offers=offers_from_html(html)
  if not offers:raise RuntimeError('ЦИАН: не найдена структура коммерческой выдачи; прежние записи сохранены')
  yield from converted(offers,convert)
  page=int(parse_qs(urlsplit(url).query).get('p',['1'])[0]);url=None
  for a in BeautifulSoup(html,'html.parser').select('a[href]'):
   candidate=urljoin(SEED,a['href']);q=parse_qs(urlsplit(candidate).query)
   if q.get('p')==[str(page+1)] and urlsplit(candidate).hostname==urlsplit(SEED).hostname and q.get('deal_type')==['sale'] and q.get('offer_type')==['offices'] and q.get('office_type[0]')==['10'] and q.get('region')==['4618']:url=candidate;break
 if url and url not in seen:raise RuntimeError('ЦИАН: достигнут предел 12 страниц; охват неполный')
