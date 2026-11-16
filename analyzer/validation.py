import hashlib, math, re
from urllib.parse import urlparse
FIELDS=['district','settlement','address','price','area','monthly_rent','tenant_name','tenant_type','active_tenant','payments_confirmed','contract','contract_months','indexation','condition','floor','separate_entrance','wet_point','ventilation','power','repair','communications','legal_clear','traffic','tenant_tenure_months','termination_terms','closure_risk','location_dependency','coordinates','coordinate_source','geo_accuracy','published_at','transaction_costs','vacancy_months','verification_evidence']
def clean_tenant_name(value):
    """A mislabeled rent amount is not evidence identifying an occupant."""
    if not isinstance(value,str):return None
    value=value.strip()
    if not value or re.match(r'^(?:мап|месячный арендный поток|арендная плата|стоимость|цена)\b',value,re.I):return None
    if re.fullmatch(r'(?:не указан|нет информации|нет данных|—|-)',value,re.I):return None
    if re.fullmatch(r'[\d\s.,]+(?:\s*(?:₽|руб\.?|рублей))?',value,re.I):return None
    return value
def normalize(raw):
    x={k:None for k in FIELDS};x.update(raw)
    x['tenant_name']=clean_tenant_name(x.get('tenant_name'))
    x.setdefault('photos',[]);x.setdefault('description','');x.setdefault('annual_costs',{})
    sources=x.get('sources',[])
    if not sources or any(urlparse(s.get('url','')).scheme!='https' or not s.get('name') for s in sources):raise ValueError('At least one named HTTPS source is required')
    if not x.get('title'):raise ValueError('Title required')
    for key in ['price','area','monthly_rent','contract_months','transaction_costs','vacancy_months']:
        v=x.get(key)
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0):raise ValueError(f'Invalid {key}')
    for key in ['active_tenant','payments_confirmed','contract','indexation','separate_entrance','wet_point','ventilation','repair','communications','legal_clear','traffic']:
        if x.get(key) is not None and type(x[key]) is not bool:raise ValueError(f'{key} must be boolean or null')
    if x.get('vacancy_months') is not None and x['vacancy_months']>12:raise ValueError('Vacancy exceeds 12 months')
    if not isinstance(x['annual_costs'],dict):raise ValueError('annual_costs must be object')
    for v in x['annual_costs'].values():
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0):raise ValueError('Invalid annual cost')
    x['price_per_sqm']=x['price']/x['area'] if x.get('price') is not None and x.get('area') else None
    x['id']=x.get('id') or hashlib.sha256(sources[0]['url'].encode()).hexdigest()[:20]
    # Source claims alone never confirm the lease/payment history.
    x['verification']='confirmed' if x.get('active_tenant') is True and x.get('payments_confirmed') is True and x.get('contract') is True and x.get('monthly_rent',0) and x.get('verification_evidence') else 'review'
    return x
