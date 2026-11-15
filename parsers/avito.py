"""Public access probe plus native Duff89 export normalization; bypass functions are not imported."""
from parsers.manual import collect_source
from parsers.public_source import PublicSource
from parsers.rental_fields import rental_candidate,rent_claim,tenant_claim
from urllib.parse import urljoin,urlsplit,urlunsplit
SEED='https://www.avito.ru/respublika_tatarstan/kommercheskaya_nedvizhimost'
def convert(item):
 text=item.get('description') or item.get('Описание') or '';title=item.get('title') or item.get('Название') or ''
 if not rental_candidate(title+' '+text):return None
 url=urljoin('https://www.avito.ru',item.get('urlPath') or item.get('URL') or '');p=urlsplit(url)
 if p.scheme!='https' or not (p.hostname=='avito.ru' or (p.hostname or '').endswith('.avito.ru')) or not p.path:return None
 coords=item.get('coords') or {};name,kind=tenant_claim(title+' '+text);price=(item.get('priceDetailed') or {}).get('value',item.get('Цена'))
 # Export coords are not evidence of geocoding precision: retained only if explicitly documented by an upstream adapter.
 return dict(title=title,sources=[{'name':'Авито','url':urlunsplit((p.scheme,p.netloc,p.path,'',''))}],address=coords.get('address_user') or item.get('Адрес пользователя') or item.get('Адрес'),price=price,monthly_rent=rent_claim(text),tenant_name=name,tenant_type=kind,active_tenant=None,payments_confirmed=None,photos=[],description='Арендная модель заявлена в источнике; документы и платежи не проверены.')
def collect():
 yield from collect_source('Авито')
 yield from native_exports()
 # An unavailable/challenge page raises SourceUnavailable and stops this source immediately.
 html=PublicSource('avito.ru').get(SEED)
 raise RuntimeError('Авито: публичный ответ получен, но структура выдачи не подтверждена; результаты не имитируются')


def native_exports():
 from pathlib import Path
 import csv,json
 root=Path(__file__).resolve().parents[1]/'imports'/'avito'
 if not root.exists():return
 for path in sorted(root.iterdir()):
  if path.suffix=='.xlsx':
   from openpyxl import load_workbook
   book=load_workbook(path,read_only=True,data_only=True);sheet=book.active;items=sheet.iter_rows(values_only=True);headers=next(items,());rows=[dict(zip(headers,row)) for row in items];book.close()
  elif path.suffix=='.csv':
   with path.open(encoding='utf-8-sig',newline='') as f:
    sample=f.read(4096);f.seek(0);rows=list(csv.DictReader(f,dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')))
  elif path.suffix=='.json':
   data=json.loads(path.read_text());rows=data.get('items',[]) if isinstance(data,dict) else data
  else:continue
  for item in rows:
   for key in ['Цена']:
    if isinstance(item.get(key),str):
     try:item[key]=float(item[key].replace(' ','').replace('\xa0','').replace(',','.'))
     except ValueError:item[key]=None
   row=convert(item)
   if row:yield row
