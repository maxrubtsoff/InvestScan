"""Distances are straight-line km. No coordinates are guessed from a city name."""
from math import radians, sin, cos, asin, sqrt
KAZAN = (55.796127, 49.106414)
def valid_coordinates(c):
    return isinstance(c,(list,tuple)) and len(c)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in c) and -90<=c[0]<=90 and -180<=c[1]<=180
def haversine(a,b=KAZAN):
    if not valid_coordinates(a) or not valid_coordinates(b): return None
    lat1,lon1,lat2,lon2=map(radians,(*a,*b))
    q=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return round(6371.0088*2*asin(sqrt(min(1,q))),2)
def apply_geo(x):
    c=x.get('coordinates')
    if not valid_coordinates(c) or not x.get('coordinate_source') or x.get('geo_accuracy') not in ('building','parcel','street'):
        x['coordinates']=None;x['distance_km']=None;x['geo_status']='unknown'
    else:x['distance_km']=haversine(c);x['geo_status']='located'
    return x
