"""Small, cached building lookups for RBN's explicit postal addresses.

Photon's public server permits reasonable project usage, with no availability
guarantee. At most four new addresses per daily run, one thread, 15s pauses.
No place names, POIs or tenant identities are inferred from a geocoder result.
"""
import json,os,re,time,sys
from pathlib import Path
import httpx
from analyzer.geo import valid_coordinates
from parsers.base import USER_AGENT

def compact(value):return re.sub(r'[^\w]','',str(value or '').casefold().replace('ё','е'))
def street_key(value):
    text=str(value or '').casefold().replace('ё','е')
    for kind,pattern in [('ул',r'\b(?:улица|ул)\b\.?'),('проспект',r'\bпроспект\b'),('пер',r'\b(?:переулок|пер)\b\.?'),('шоссе',r'\bшоссе\b')]:
        if re.search(pattern,text):return kind,compact(re.sub(pattern,' ',text))
    return None
def house_key(value):return compact(re.sub(r'\bлитера\b','',str(value or ''),flags=re.I))
def address_parts(row):
    address=row.get('address') or '';parts=[p.strip() for p in address.split(',')]
    if len(parts)<3 or not row.get('settlement') or not street_key(parts[1]):return None
    house=', '.join(parts[2:])
    if not re.match(r'^\d',house):return None
    return row['settlement'],parts[1],house

def choose_hit(row,features):
    parts=address_parts(row)
    if not parts:return None
    city,street,house=parts;hits=[]
    for f in features:
        p=f.get('properties') or {};g=f.get('geometry') or {};coords=g.get('coordinates')
        if p.get('countrycode')!='RU' or p.get('type')!='house' or g.get('type')!='Point':continue
        if compact(p.get('city'))!=compact(city) or street_key(p.get('street'))!=street_key(street) or house_key(p.get('housenumber'))!=house_key(house):continue
        if not isinstance(coords,list) or len(coords)!=2 or not valid_coordinates([coords[1],coords[0]]):continue
        hits.append(f)
    # Prefer a building footprint over a business located in the building.
    return next((f for f in hits if f['properties'].get('osm_key')=='building'),hits[0] if hits else None)

def geocode(rows,cache_path,limit=4):
    cache_path=Path(cache_path);cache=json.loads(cache_path.read_text()) if cache_path.exists() else {};count=0;blocked=False
    candidates=[r for r in rows if not r.get('coordinates') and any(s['name']=='РБН' for s in r.get('sources',[])) and address_parts(r)]
    for row in sorted(candidates,key=lambda r:(r.get('price') is None or r['price']>12000000,r.get('price') or 0)):
        key=row['address']
        if key not in cache and count<limit and not blocked:
            try:
                time.sleep(15)
                city,street,house=address_parts(row)
                r=httpx.get(os.environ.get('PHOTON_URL','https://photon.komoot.io/api/'),params={'q':f'{city}, {street}, {house}','limit':5},headers={'User-Agent':USER_AGENT},timeout=25)
                r.raise_for_status();features=r.json()['features']
                if not isinstance(features,list):raise ValueError('Invalid Photon response')
                cache[key]=features;count+=1
            except Exception as e:
                print(f'Photon: stopped after error ({type(e).__name__}); no retry',file=sys.stderr);blocked=True
        hit=choose_hit(row,cache.get(key,[]))
        if hit:
            lon,lat=hit['geometry']['coordinates'];row['coordinates']=[lat,lon];row['coordinate_source']='OpenStreetMap / Photon: совпали город, улица и номер дома';row['geo_accuracy']='building'
    cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')
    return rows
