"""Optional free OSM Nominatim: bounded, single-threaded and persistent cache.
Never substitutes a settlement centroid for a property coordinate.
"""
import json,time,os
from pathlib import Path
import httpx
from parsers.base import USER_AGENT
URL=os.environ.get('GEOCODER_URL','https://nominatim.openstreetmap.org/search')
def geocode(rows,cache_path,limit=10):
    cache_path=Path(cache_path);cache=json.loads(cache_path.read_text()) if cache_path.exists() else {};count=0
    for row in rows:
        if row.get('coordinates'):continue
        address=row.get('address')
        if not address:continue
        if address not in cache and count<limit:
            try:
                time.sleep(15.1)
                r=httpx.get(URL,params={'q':address,'format':'jsonv2','addressdetails':1,'limit':1,'countrycodes':'ru'},headers={'User-Agent':USER_AGENT},timeout=20)
                r.raise_for_status();data=r.json();cache[address]=data[0] if data else None;count+=1
            except Exception:break # no retry or block evasion
        hit=cache.get(address)
        if not hit:continue
        a=hit.get('address',{});row['settlement']=a.get('city') or a.get('town') or a.get('village') or a.get('hamlet')
        row['district']=a.get('municipality') or a.get('county') or a.get('city_district')
        # Require a house number in both the input and result. Street/centroid matches remain unresolved.
        import re
        house=a.get('house_number');has_number=house and re.search(r'(?<!\d)'+re.escape(house.lower())+r'(?!\d)',address.lower())
        if has_number and hit.get('addresstype') in ('building','house','amenity','shop','office','leisure','tourism'):
            row['coordinates']=[float(hit['lat']),float(hit['lon'])];row['coordinate_source']='OpenStreetMap / Nominatim';row['geo_accuracy']='building'
    cache_path.write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n')
    return rows
