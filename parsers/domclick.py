"""Read-only data adapters; no mobile signing or private API requests.

Native fields follow the inspected Offer model and result.items schema.
HTML decoding remains unverified live while the website is blocked.
"""
import csv,json
from pathlib import Path
from bs4 import BeautifulSoup
from parsers.manual import collect_source
from parsers.public_source import PublicSource
from parsers.rental_fields import rental_candidate,rent_claim,tenant_claim
from parsers.exports import imported,number,photos,source_url,converted,next_page
SEED='https://kazan.domclick.ru/pokupka/kommercheskaya-nedvizhimost'
EXPORT_DIR=Path(__file__).resolve().parents[1]/'imports'/'domclick'
COMMERCIAL={'office','retail','commercial','free_purpose','freeAppointment','building','business','warehouse','production','shopping'}

def offers_from_payload(payload):
    if isinstance(payload,list):return payload
    if not isinstance(payload,dict):raise ValueError('Invalid Domclick payload')
    result=payload.get('result')
    if isinstance(result,dict) and isinstance(result.get('items'),list):return result['items']
    for key in ('items','offers'):
        if isinstance(payload.get(key),list):return payload[key]
    raise ValueError('Domclick offers array not found')

def convert(item):
    if not isinstance(item,dict):raise ValueError('Domclick item must be an object')
    kind=item.get('offerType') or item.get('offer_type');deal=item.get('dealType') or item.get('deal_type')
    if not deal and isinstance(item.get('type'),str):
        parts=item['type'].split(' ',1);deal=parts[0].casefold();kind=parts[1] if len(parts)>1 else kind
    if deal!='sale' or not(kind in COMMERCIAL or item.get('category')=='commercial'):return None
    text=item.get('description') or '';title=item.get('title') or ''
    if not isinstance(text,str) or not isinstance(title,str):raise ValueError('Invalid Domclick text fields')
    if not rental_candidate(title+' '+text):return None
    url=source_url(item.get('path') or item.get('listing_url') or item.get('url'),'domclick.ru')
    if not url:return None
    address=item.get('address') or {};info=item.get('objectInfo') or {}
    address_text=address.get('displayName') if isinstance(address,dict) else address if isinstance(address,str) else None
    area=info.get('area',item.get('area'));area=number(area.get('value') if isinstance(area,dict) else area)
    price=item.get('price')
    if isinstance(price,dict):
        currency=str(price.get('currency') or '').casefold()
        price=number(price.get('value')) if currency in ('rub','rur','₽','643') else None
    else:price=number(price) # Native Offer files declare ruble amounts.
    name,tenant_type=tenant_claim(text)
    return dict(title=title or ('Помещение · '+address_text if address_text else 'Помещение с заявленной арендной моделью'),sources=[{'name':'Домклик','url':url}],address=address_text,price=price,area=area,floor=info.get('floor',item.get('floor')),monthly_rent=rent_claim(text),tenant_name=name,tenant_type=tenant_type,active_tenant=None,payments_confirmed=None,coordinates=None,photos=photos(item.get('photos') or item.get('images') or []),description='Аренда заявлена продавцом. Платежи и договор не проверены.',source_fetched_at=item.get('source_fetched_at'))

def offers_from_html(page):
    soup=BeautifulSoup(page,'html.parser')
    for script in soup.select('script#__NEXT_DATA__[type="application/json"]'):
        try:
            value=json.loads(script.string or script.get_text()).get('props',{}).get('pageProps',{})
            for candidate in [value,value.get('initialState',{}) if isinstance(value,dict) else {}]:
                try:return offers_from_payload(candidate)
                except ValueError:pass
        except (ValueError,TypeError,AttributeError):continue
    raise ValueError('Domclick: public offer state not found; prior data retained')

def collect():
    yield from collect_source('Домклик');yield from native_exports()
    client=PublicSource('domclick.ru');url=SEED;seen=set()
    for _ in range(12):
        if not url or url in seen:return
        seen.add(url);page=client.get(url)
        yield from converted(offers_from_html(page),convert)
        url=next_page(page,url)
    if url:raise RuntimeError('Domclick pagination limit reached; coverage incomplete')

def native_exports():
    if not EXPORT_DIR.exists():return
    for path in sorted(EXPORT_DIR.iterdir()):
        if path.suffix=='.json':rows=offers_from_payload(json.loads(path.read_text()))
        elif path.suffix=='.csv':
            with path.open(encoding='utf-8-sig',newline='') as f:
                sample=f.read(4096);f.seek(0);rows=list(csv.DictReader(f,dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')))
        else:continue
        yield from converted(rows,convert,as_import=True)
