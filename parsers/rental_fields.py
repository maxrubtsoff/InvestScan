"""Extract only explicit seller claims. Operating profit is never monthly rent."""
import re
RENT=re.compile(r'(?:\bмап\b|месячн\w* арендн\w* (?:поток|плат[аёе]ж)|арендная плата|арендный поток)\s*(?:составляет|в размере|[:=—–-])?\s*(\d[\d \xa0]*(?:[.,]\d+)?)\s*(тыс(?:яч)?\.?|млн\.?)?',re.I)
def rental_candidate(text):
 t=text.casefold().replace('ё','е')
 if re.search(r'прода[её]тся\s+(?:право аренды|переуступка)|\bсубаренд\w*|\bппа\b',t):return False
 return bool(re.search(r'готов\w* арендн\w* бизнес|\bгаб\b|с (?:действующ\w* |сетев\w* |федеральн\w* )?арендатор\w*|сдан\w* в аренду',t))
def rent_claim(text):
 m=RENT.search(text)
 if not m:return None
 before=text[max(0,m.start()-35):m.start()].casefold();after=text[m.end():m.end()+35].casefold()
 if re.search(r'годов\w*\s*$',before) or re.match(r'\s*(?:₽|руб\w*\.?|р\.)?\s*(?:в год|/год)',after):return None
 if m[0].casefold().startswith('арендный поток') and not re.search(r'месяц|мес\b|/мес',after):return None
 n=float(re.sub(r'\s','',m[1]).replace(',','.'));unit=(m[2] or '').casefold()
 return n*(1000000 if 'млн' in unit else 1000 if 'тыс' in unit else 1)
def tenant_claim(text):
 brands=[('Ozon','ПВЗ'),('Озон','ПВЗ'),('Wildberries','ПВЗ'),('Вайлдберриз','ПВЗ'),('Яндекс Маркет','ПВЗ'),('Пятерочка','Продуктовый магазин'),('Пятёрочка','Продуктовый магазин'),('Магнит','Продуктовый магазин'),('Чижик','Продуктовый магазин'),('Улыбка радуги','Сервис')]
 for name,kind in brands:
  pos=text.casefold().find(name.casefold())
  if pos>=0:
   context=text[max(0,pos-90):pos].casefold()
   if re.search(r'арендатор|сдан\w* в аренду|\bгаб\b|арендн\w* бизнес',context) and not re.search(r'рядом|поблизости|соседств',context[-35:]):return name,kind
 return None,('Аптека' if 'аптек' in text.casefold() else 'Другой')
