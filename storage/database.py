import json,sqlite3,re
from datetime import datetime,timezone,timedelta
from analyzer.geo import haversine

def now():return datetime.now(timezone.utc).isoformat()
def observed(value):
    if not isinstance(value,str):return None
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt if dt.tzinfo is not None and dt<=datetime.now(timezone.utc)+timedelta(minutes=10) else None
    except ValueError:return None
def norm(s):return re.sub(r'[^\w]','',str(s or '').casefold().replace('ё','е'))
def duplicate(a,b):
    if {s['url'] for s in a['sources']} & {s['url'] for s in b['sources']}:return True
    # Conservative cross-source identity: full non-empty address, municipality and near-identical size.
    if not(a.get('address') and b.get('address') and a.get('settlement') and b.get('settlement') and a.get('area') and b.get('area')):return False
    same=norm(a['address'])==norm(b['address']) and norm(a['settlement'])==norm(b['settlement']) and abs(a['area']-b['area'])<=.1
    if same and a.get('coordinates') and b.get('coordinates'):return haversine(a['coordinates'],b['coordinates'])<=.03
    # Unspecified units at same address can be different properties: do not merge without coordinates.
    return False
class Database:
    def __init__(self,path):
        self.db=sqlite3.connect(path);self.db.execute('CREATE TABLE IF NOT EXISTS listings(id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    def all(self):return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM listings ORDER BY id')]
    def upsert(self,x):
        old=next((r for r in self.all() if duplicate(r,x)),None);ingested_at=now()
        is_import=x.get('acquisition_mode') in ('import','snapshot')
        stamp=x.get('source_fetched_at') or (None if is_import else ingested_at)
        primary_url=old['sources'][0]['url'] if old else x['sources'][0]['url']
        primary=not old or primary_url in {s['url'] for s in x['sources']}
        history=list(old.get('history',[])) if old else []
        observations=list(old.get('source_observations',[])) if old else []
        prior_record=old if primary else next((o for o in reversed(observations) if {s['url'] for s in o.get('sources',[])} & {s['url'] for s in x['sources']}),None)
        if prior_record:
            prior=observed(prior_record.get('last_seen') if primary else prior_record.get('observed_at',prior_record.get('last_seen')));incoming=observed(stamp)
            if prior and ((incoming is not None and incoming<prior) or (is_import and incoming is None)):return old
            if is_import and x.get('import_fingerprint') and x['import_fingerprint']==prior_record.get('import_fingerprint'):return old
        if old:
            sources=list({s['url']:s for s in old['sources']+x['sources']}.values())
            if primary:
                changed=any(old.get(k)!=x.get(k) for k in ['price','monthly_rent','contract_months','indexation'])
                x.update(id=old['id'],first_seen=old['first_seen'],sources=sources)
            else:
                observation={k:x.get(k) for k in ['sources','price','monthly_rent','price_claims','acquisition_mode','import_fingerprint']}
                observation['observed_at']=stamp
                incoming_urls={s['url'] for s in x['sources']}
                observation['price_claims']=[c for c in observation.get('price_claims') or [] if not c.get('source_url') or c.get('source_url') in incoming_urls]
                observations=[o for o in observations if not incoming_urls & {s['url'] for s in o.get('sources',[])}]+[observation]
                changed=prior_record is None or any(prior_record.get(k)!=x.get(k) for k in ['price','monthly_rent'])
            if changed:
                history.append(dict(at=stamp or ingested_at,event='import' if is_import else 'observed',source=x['sources'][0]['name'],**{k:x.get(k) for k in ['price','monthly_rent','contract_months','indexation']}))
            if not primary:
                # Canonical facts always belong to the first source. A repeated
                # secondary URL never becomes the primary just by being linked.
                x={**old,'sources':sources};stamp=old.get('last_seen')
        else:
            x['first_seen']=stamp or ingested_at
            history=[dict(at=stamp or ingested_at,event='import' if is_import else 'observed',source=x['sources'][0]['name'],**{k:x.get(k) for k in ['price','monthly_rent','contract_months','indexation']})]
        if primary:
            x['primary_price_claims']=[c for c in x.get('price_claims',[]) if not c.get('source_url') or c.get('source_url')==primary_url]
            if is_import:x['last_imported_at']=ingested_at
        primary_claims=x.get('primary_price_claims',[])
        claims=[{**c,'source_url':primary_url} for c in primary_claims]
        if x.get('price') is not None:claims.append(dict(location=x['sources'][0]['name'],source_url=primary_url,value=x['price']))
        for o in observations:
            source=(o.get('sources') or [{}])[0]
            observation_urls={s['url'] for s in o.get('sources',[])}
            if o.get('price') is not None:claims.append(dict(location=source.get('name','Другой источник'),source_url=source.get('url'),value=o['price']))
            claims.extend({**c,'source_url':c.get('source_url') or source.get('url')} for c in o.get('price_claims') or [] if not c.get('source_url') or c.get('source_url') in observation_urls)
        x['price_claims']=list({(c.get('source_url'),c.get('location'),c['value']):c for c in claims}.values())
        x['price_conflict']=len({c['value'] for c in claims})>1
        x.update(history=history,source_observations=observations,last_seen=stamp)
        if 'finance' in x:
            from analyzer.investment import analyze
            from analyzer.scoring import score
            x['finance']=analyze(x)
            if 'score' in x:score(x)
        x['price_per_sqm']=x['price']/x['area'] if x.get('price') is not None and x.get('area') and not x['price_conflict'] else None
        self.db.execute('INSERT OR REPLACE INTO listings VALUES(?,?)',(x['id'],json.dumps(x,ensure_ascii=False,allow_nan=False)));self.db.commit();return x
    def close(self):self.db.close()
