"""Public ARR country-wide rental-business showcase. Facts only, linked attribution.
No photos or full descriptions are republished. No contact information is collected.
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from parsers.base import PublicClient
URL='https://broker.arrpro.ru/arendniy-biznes/'
def number(text):
    m=re.search(r'\d[\d\s\xa0]*(?:[.,]\d+)?',text or '')
    return float(re.sub(r'\s','',m[0]).replace(',','.')) if m else None

def parse(html):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for node in soup.select('.net-renter__link'):
        a=node.select_one('a.net-renter__name');addr=node.select_one('.props__address')
        if not a or not addr:continue
        values={}
        for prop in node.select('.net-renter__prop'):
            k=prop.select_one('.net-renter__label');v=prop.select_one('.net-renter__value')
            if k and v:values[k.get_text(' ',strip=True).rstrip(':')]=v.get_text(' ',strip=True)
        address=addr.get_text(' ',strip=True);tenant=values.get('Арендатор')
        tenant_type='ПВЗ' if tenant and any(t in tenant.lower() for t in ['ozon','озон','wildberries','вайлдберриз','яндекс']) else 'Аптека' if tenant and 'аптек' in tenant.lower() else 'Продуктовый магазин' if tenant and any(t in tenant.lower() for t in ['пятероч','магнит','чижик','продукт','красное']) else 'Другой'
        rows.append(dict(title=a.get_text(' ',strip=True),sources=[{'name':'АРР','url':urljoin(URL,a['href']).replace('http://','https://')}],address=address,settlement=None,price=number(values.get('Стоимость')),area=number(values.get('Площадь')),monthly_rent=number(values.get('Месячный арендный поток')),tenant_name=tenant,tenant_type=tenant_type,description='Объект из публичной витрины арендного бизнеса АРР. Цена, площадь и аренда — заявления источника. Платежи и договор независимо не проверены.',active_tenant=None,payments_confirmed=None,photos=[]))
    nxt=soup.select_one('button.catalog__next[data-path]')
    return rows,urljoin(URL,nxt['data-path']) if nxt else None

def collect():
    client=PublicClient();url=URL;rows=[];seen=set()
    # The visible showcase exposes pagination through its public data-path controls.
    # Finite hourly batch: coverage is partial and explicitly reported.
    for _ in range(8):
        if not url or url in seen:break
        seen.add(url);html=client.get(url);batch,url=parse(html)
        if not batch:raise RuntimeError('ARR markup changed or empty response; existing catalog retained')
        rows.extend(batch)
    return rows
