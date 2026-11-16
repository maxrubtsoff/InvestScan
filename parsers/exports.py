"""Normalizers for authorized files and public HTML, without executable state."""
import hashlib,json,math,re
from urllib.parse import urljoin,urlsplit,urlunsplit
from bs4 import BeautifulSoup
from analyzer.validation import FIELDS

IMPORT_FIELDS=set(FIELDS)|{'id','title','sources','photos','annual_costs','source_fetched_at','price_claims','catalog_eligible','exclusion_reason'}
class InvalidRecord(ValueError):pass

def converted(items,converter,as_import=False):
    for item in items:
        try:
            row=converter(item)
            if row:yield imported(row) if as_import else {**row,'acquisition_mode':'public_html'}
        except (ValueError,TypeError,AttributeError,KeyError):
            # Report the bad record without logging raw payloads or secrets.
            yield InvalidRecord('Malformed source record')

def imported(row):
    # Only listing facts enter the public catalog; cookies, headers, contact
    # fields and arbitrary upstream metadata never propagate from an export.
    result={k:v for k,v in row.items() if k in IMPORT_FIELDS}
    result['acquisition_mode']='snapshot' if result.get('source_fetched_at') else 'import'
    result['import_fingerprint']=hashlib.sha256(json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result

def source_url(value,domain):
    if not isinstance(value,str) or not value:return None
    origin='https://www.avito.ru' if domain=='avito.ru' else 'https://'+domain
    p=urlsplit(urljoin(origin,value))
    if p.scheme!='https' or p.username or p.password or not(p.hostname==domain or (p.hostname or '').endswith('.'+domain)) or p.path in ('','/'):return None
    return urlunsplit((p.scheme,p.netloc,p.path,'',''))

def number(value):
    if isinstance(value,bool):return None
    if isinstance(value,(int,float)):return value if math.isfinite(value) and value>=0 else None
    if isinstance(value,str):
        s=re.sub(r'\s','',value).replace(',','.')
        if re.fullmatch(r'\d+(?:\.\d+)?',s):return float(s)
    return None

def photos(values):
    out=[]
    for item in values or []:
        value=item if isinstance(item,str) else next((item.get(k) for k in ('url','src','thumbnailUrl','640x480','480x360') if item.get(k)),None) if isinstance(item,dict) else None
        if not isinstance(value,str):continue
        p=urlsplit(value)
        if p.scheme=='https' and p.hostname and not p.username and not p.password:
            url=urlunsplit((p.scheme,p.netloc,p.path,'',''))
            if url not in out:out.append(url)
    return out[:3]

def next_page(page,current):
    soup=BeautifulSoup(page,'html.parser')
    for a in soup.select('a[rel~="next"][href],a[data-marker="pagination-button/nextPage"][href]'):
        url=urljoin(current,a['href']);p=urlsplit(url);base=urlsplit(current)
        if p.scheme=='https' and p.hostname==base.hostname and not p.username and not p.password and p.path==base.path:return url
    return None
