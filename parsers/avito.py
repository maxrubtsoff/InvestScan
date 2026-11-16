"""Public MFE HTML and authorized Duff89 exports; no bypass code is imported."""
import html,json,re
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from parsers.manual import collect_source
from parsers.public_source import PublicSource
from parsers.rental_fields import rental_candidate,rent_claim,tenant_claim
from parsers.exports import imported,number,photos,source_url,converted,next_page
SEED='https://www.avito.ru/respublika_tatarstan/kommercheskaya_nedvizhimost'
EXPORT_DIR=Path(__file__).resolve().parents[1]/'imports'/'avito'

def _rub_price(item):
    price=item.get('priceDetailed')
    if not isinstance(price,dict):return number(item.get('Цена'))
    text=' '.join(str(price.get(k) or '') for k in ('fullString','string','postfix'))
    if price.get('hasValue') is False or re.search(r'[$€]|доллар|евро|usd|eur|(?:за|/)\s*(?:1\s*)?(?:м[²2]|кв(?:адратн\w*)?\.?\s*м(?:етр\w*)?\.?)|(?:в|за|/)\s*мес',text,re.I):return None
    if not re.search(r'₽|руб|\brub\b|\brur\b',text,re.I):return None
    return number(price.get('value'))

def convert(item):
    if not isinstance(item,dict):raise ValueError('Avito item must be an object')
    text=item.get('description') or item.get('Описание') or '';title=item.get('title') or item.get('Название') or ''
    if not isinstance(text,str) or not isinstance(title,str):raise ValueError('Invalid Avito text fields')
    if re.match(r'^\s*(?:сдам\b|сда[её]тся\b|аренда\b)',title,re.I):return None
    if not rental_candidate(title+' '+text):return None
    category=item.get('category') or {}
    if isinstance(category,dict) and category.get('slug') and not re.search(r'kommerchesk|gotov|biznes',category['slug'],re.I):return None
    url=source_url(item.get('urlPath') or item.get('URL'),'avito.ru')
    if not url:return None
    coords=item.get('coords') or {};geo=item.get('geo') or {};location=item.get('location') or {}
    name,kind=tenant_claim(title+' '+text)
    area=number(item.get('area') or item.get('totalArea') or item.get('Площадь'))
    if area is None:
        m=re.search(r'(\d+(?:[.,]\d+)?)\s*(?:м²|м2|кв\.?\s*м\b)',title,re.I)
        area=number(m[1]) if m else None
    return dict(title=title,sources=[{'name':'Авито','url':url}],address=coords.get('address_user') or geo.get('formattedAddress') or item.get('Адрес пользователя') or item.get('Адрес'),settlement=location.get('name') if location.get('isRegion') is False else None,price=_rub_price(item),area=area,monthly_rent=rent_claim(text),tenant_name=name,tenant_type=kind,active_tenant=None,payments_confirmed=None,photos=photos(item.get('images') or []),description='Арендная модель заявлена в источнике; документы и платежи не проверены.',source_fetched_at=item.get('source_fetched_at'))

def offers_from_html(page):
    """Decode the published MFE state with json.loads, never execute scripts."""
    soup=BeautifulSoup(page,'html.parser')
    for script in soup.select('script[type="mime/invalid"][data-mfe-state="true"]'):
        try:payload=json.loads(html.unescape(script.string or script.get_text()))
        except (ValueError,TypeError):continue
        if not isinstance(payload,dict):continue
        loader=payload.get('loaderData') or {}
        data=loader.get('data',{}) if isinstance(loader,dict) else {}
        if not isinstance(data,dict):continue
        result=data.get('result') if isinstance(data.get('result'),dict) else {}
        for value in [data.get('catalog'),result.get('catalog'),result,data]:
            if isinstance(value,dict) and isinstance(value.get('items'),list):return value['items']
    raise ValueError('Avito: public catalog state not found; prior data retained')

def collect():
    yield from collect_source('Авито');yield from native_exports()
    client=PublicSource('avito.ru');url=SEED;seen=set()
    for _ in range(12):
        if not url or url in seen:return
        seen.add(url);page=client.get(url)
        yield from converted(offers_from_html(page),convert)
        url=next_page(page,url)
    if url:raise RuntimeError('Avito pagination limit reached; coverage incomplete')

def native_exports():
    import csv
    if not EXPORT_DIR.exists():return
    for path in sorted(EXPORT_DIR.iterdir()):
        if path.suffix=='.xlsx':
            from openpyxl import load_workbook
            book=load_workbook(path,read_only=True,data_only=True);items=book.active.iter_rows(values_only=True);headers=next(items,());rows=[dict(zip(headers,row)) for row in items];book.close()
        elif path.suffix=='.csv':
            with path.open(encoding='utf-8-sig',newline='') as f:
                sample=f.read(4096);f.seek(0);rows=list(csv.DictReader(f,dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')))
        elif path.suffix=='.json':
            data=json.loads(path.read_text());rows=data.get('items',[]) if isinstance(data,dict) else data
        else:continue
        if not isinstance(rows,list):raise ValueError('Avito export must contain an items array')
        yield from converted(rows,convert,as_import=True)
