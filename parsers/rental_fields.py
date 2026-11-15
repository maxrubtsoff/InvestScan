"""Conservative extraction of explicit present-tense seller claims, not business profit."""
import re
AMOUNT=r'(\d[\d \xa0\u202f]*(?:[.,]\d+)?)\s*(тыс(?:яч)?\.?|млн\.?)?'
RENT=re.compile(r'(?:\bмап\b|месячн\w* арендн\w* (?:поток|плат[аёе]ж)|арендная плата|арендный поток)\s*(?:составляет|в размере|[:=—–-])?\s*'+AMOUNT,re.I)
NEGATIVE=re.compile(r'бывш\w*\s+арендатор|планиру\w*[^.!?\n]{0,70}сдать|без\s+арендатора|нет\s+арендатора|помещение\s+свободно|арендатор[^.!?\n]{0,70}(?:съехал|съезжает|расторг)|(?:возможн\w*|потенциальн\w*|будущ\w*)\s+арендатор|договор\s+(?:ещ[её]\s+)?не\s+(?:подписан|заключ[её]н)|арендатор\s+(?:подбирается|в поиске)',re.I)
def rental_candidate(text):
 t=text.casefold().replace('ё','е')
 if NEGATIVE.search(t):return False
 if re.search(r'прода[её]тся\s+(?:право аренды|переуступка)|субарендн\w*\s+бизнес|\bппа\b|продаж\w*\s+субаренд',t):return False
 return bool(re.search(r'готов\w* арендн\w* бизнес|\bгаб\b|с (?:действующ\w* |сетев\w* |федеральн\w* )?арендатор\w*|сдан\w* в аренду',t))
def rent_claim(text):
 if NEGATIVE.search(text):return None
 for m in RENT.finditer(text):
  before=text[max(0,m.start()-60):m.start()].casefold();after=text[m.end():m.end()+90].casefold()
  if re.search(r'годов\w*\s*$|квартальн\w*\s*$|потенциальн\w*[^.!?]*$|планируем\w*[^.!?]*$|предполагаем\w*[^.!?]*$',before):continue
  if re.search(r'(?:в|за|/)\s*(?:год|квартал|недел|сутк|день)|годовых|доллар|евро|\busd\b|\beur\b|[$€]',after):continue
  if re.search(r'потенциальн|планируем|пустует',after):continue
  currency=re.match(r'\s*(?:₽|руб(?:лей|ля|ль)?\.?|р\.)',after)
  if not currency:continue
  after=re.split(r'[.!?;\n]',after[currency.end():],maxsplit=1)[0]
  monthly=bool(re.search(r'\bмап\b|месячн',m[0].casefold()) or re.search(r'ежемесячн\w*\s*$',before) or re.match(r'\s*(?:без ндс\s*)?(?:(?:в|за|/)\s*(?:месяц|мес\b)|ежемесячно)',after))
  if not monthly:continue
  n=float(re.sub(r'\s','',m[1]).replace(',','.'));unit=(m[2] or '').casefold()
  return n*(1000000 if 'млн' in unit else 1000 if 'тыс' in unit else 1)
 return None

def tenant_claim(text):
 if NEGATIVE.search(text):return None,None
 brands=[('Ozon','ПВЗ'),('Озон','ПВЗ'),('Wildberries','ПВЗ'),('Вайлдберриз','ПВЗ'),('Яндекс Маркет','ПВЗ'),('Пятерочка','Продуктовый магазин'),('Пятёрочка','Продуктовый магазин'),('Магнит','Продуктовый магазин'),('Чижик','Продуктовый магазин'),('Улыбка радуги','Сервис')]
 for name,kind in brands:
  for match in re.finditer(re.escape(name),text,re.I):
   before=text[max(0,match.start()-90):match.start()].casefold();around=text[max(0,match.start()-45):match.end()+70].casefold()
   if re.search(r'рядом|поблизости|соседств|соседн|через дорогу|напротив|в окружении',around):continue
   clause=re.split(r'[.!?;\n]',before)[-1]
   if re.search(r'\bне\b|возможн|потенциальн|бывш',clause):continue
   if re.search(r'(?:арендатор(?:ом)?(?:\s+(?:является|выступает))?|сдан\w*(?:\s+в аренду)?)\s*(?:[:—–-]\s*)?(?:(?:федеральн\w*|сетев\w*|магазин|сеть|компании)\s+)*[«\"\']?\s*$',clause):return name,kind
 if re.search(r'арендатор\s*(?:[:—–-]\s*)?аптек\w*|сдан\w* в аренду\s+аптек\w*',text,re.I):return None,'Аптека'
 return None,None
