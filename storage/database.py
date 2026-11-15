import json,sqlite3,re
from datetime import datetime,timezone
from analyzer.geo import haversine

def now():return datetime.now(timezone.utc).isoformat()
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
        old=next((r for r in self.all() if duplicate(r,x)),None);stamp=x.get('source_fetched_at') or now()
        if old:
            primary=bool({s['url'] for s in old['sources']} & {s['url'] for s in x['sources']})
            x['id']=old['id'];x['first_seen']=old['first_seen'];history=old.get('history',[])
            if not primary:
                # Conflicting cross-source facts are retained for review, never overwritten silently.
                old.setdefault('source_observations',[]).append({k:x.get(k) for k in ['sources','price','monthly_rent','last_seen']})
                merged={**old};merged['sources']=list({s['url']:s for s in old['sources']+x['sources']}.values());merged['last_seen']=stamp
                x=merged
            else:
                x['sources']=list({s['url']:s for s in old['sources']+x['sources']}.values())
            if any(old.get(k)!=x.get(k) for k in ['price','monthly_rent','contract_months','indexation']):history.append(dict(at=stamp,**{k:x.get(k) for k in ['price','monthly_rent','contract_months','indexation']}))
            x['history']=history
        else:x['first_seen']=stamp;x['history']=[dict(at=stamp,**{k:x.get(k) for k in ['price','monthly_rent','contract_months','indexation']})]
        x['last_seen']=stamp
        self.db.execute('INSERT OR REPLACE INTO listings VALUES(?,?)',(x['id'],json.dumps(x,ensure_ascii=False,allow_nan=False)));self.db.commit();return x
    def close(self):self.db.close()
