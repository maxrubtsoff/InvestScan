"""Independent public RBN showcase. No rent inferred from advertised payback.

The Kazan office's catalog also contains surrounding municipalities. Read every
visible offer, including prices above budget, then apply the normal geo filters.
"""
import re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from parsers.base import PublicClient
from parsers.arr import number
from parsers.rental_fields import rental_candidate,rent_claim,tenant_claim

ROOT='https://kazan.rbnpro.ru'
SEED=ROOT+'/rents/show_all'

def catalog_links(html):
    soup=BeautifulSoup(html,'html.parser')
    urls=[]
    for a in soup.select('a.item-one2[href]'):
        url=urljoin(ROOT,a['href']);p=urlsplit(url)
        if p.scheme=='https' and p.hostname=='kazan.rbnpro.ru' and re.fullmatch(r'/rents/show/\d+',p.path) and url not in urls:urls.append(url)
    if not urls:raise ValueError('RBN catalog markup missing; prior records retained')
    # Follow only explicit public pagination links, never generated query grids.
    pages=[]
    for a in soup.select('.pagination a[href],.paginator a[href]'):
        url=urljoin(ROOT,a['href']);p=urlsplit(url)
        if p.scheme=='https' and p.hostname=='kazan.rbnpro.ru' and p.path.startswith('/rents/show_all') and url not in pages:pages.append(url)
    return urls,pages

def parse_detail(html,url,include_excluded=False):
    soup=BeautifulSoup(html,'html.parser');content=soup.select_one('.container.content')
    heading=content.select_one('h1') if content else None
    if not heading:raise ValueError('RBN property markup missing')
    # Use only the property description column, excluding breadcrumbs, nearby
    # listings, site-wide tenant names, contact forms and sales-agent contacts.
    slider=content.select_one('.catalog-slider-block')
    column=slider.parent if slider else None
    if not column:raise ValueError('RBN description markup missing')
    description=BeautifulSoup(str(column),'html.parser')
    for node in description.select('.catalog-slider-block,script,style,form'):node.decompose()
    text=description.get_text(' ',strip=True)
    # This misspelling appears in the public RBN field; correcting the missing
    # letter is deterministic and does not assert independent tenant verification.
    text=re.sub(r'\bарендаор\b','арендатор',text,flags=re.I)
    reason=None
    if re.search(r'можно\s+(?:сразу\s+)?сдавать|готов\w*\s+к сдаче|при заполнении',text,re.I):reason='В описании указана будущая сдача или доходность при заполнении.'
    elif not rental_candidate(text):reason='В описании нет признаков действующей арендной модели.'
    if reason and not include_excluded:return None
    address_node=content.select_one('input[name="address"]')
    address=address_node.get('value') if address_node else None
    town=re.match(r'^(.+?)\s+г\.',address or '')
    area=next((number(p.get_text(' ',strip=True)) for p in column.select('p') if p.get_text(' ',strip=True).startswith('Площадь:')),None)
    price=content.select_one('p.bold.fs28')
    amount=number(price.get_text(' ',strip=True)) if price else None
    claims=[dict(location='Шапка объявления',value=amount)] if amount else []
    for m in re.finditer(r'стоимость объекта\s*[:—–-]?\s*(\d[\d\s\xa0]*(?:[.,]\d+)?)\s*руб',text,re.I):
        value=number(m[1])
        if value and value not in [p['value'] for p in claims]:claims.append(dict(location='Описание объявления',value=value))
    name,kind=tenant_claim(text)
    # The public detail pages inspected expose no property coordinates.
    # A municipal/office contact address is never used as a location substitute.
    image=column.select_one('.catalog-slider img[src]')
    photo=urljoin(ROOT,image['src']) if image else None
    photos=[photo] if photo and urlsplit(photo).scheme=='https' and urlsplit(photo).hostname=='kazan.rbnpro.ru' else []
    return dict(title=heading.get_text(' ',strip=True),sources=[{'name':'РБН','url':url}],address=address,settlement=town[1] if town else None,price=amount,price_claims=claims,catalog_eligible=not bool(reason),exclusion_reason=reason,area=area,monthly_rent=rent_claim(text),tenant_name=name,tenant_type=kind,active_tenant=None,payments_confirmed=None,coordinates=None,photos=photos,description='Описание не подтверждает действующую арендную модель.' if reason else 'Арендная модель заявлена в карточке РБН. Платежи и договор не проверены.')

def collect():
    client=PublicClient(allowed_hosts={'kazan.rbnpro.ru'});pages=[SEED];seen_pages=set();seen_offers=set()
    while pages and len(seen_pages)<20:
        page=pages.pop(0)
        if page in seen_pages:continue
        seen_pages.add(page);offers,more=catalog_links(client.get(page))
        pages.extend(p for p in more if p not in seen_pages and p not in pages)
        for url in offers:
            if url in seen_offers:continue
            seen_offers.add(url);row=parse_detail(client.get(url),url,include_excluded=True)
            if row:yield row
    if pages:raise RuntimeError('RBN pagination safety limit reached; coverage incomplete')
