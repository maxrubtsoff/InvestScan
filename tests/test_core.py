import pytest
from analyzer.investment import analyze,COST_KEYS
from analyzer.geo import haversine,apply_geo,KAZAN
from analyzer.validation import normalize
from analyzer.scoring import score
from storage.database import Database,duplicate

def sample(**kw):return normalize(dict(title='Test fixture',sources=[{'name':'Test','url':'https://example.org/fixture'}],price=12000000,monthly_rent=100000,area=100,**kw))
def test_finance():
 f=analyze(sample());assert f['annual_rent']==1200000;assert f['gross_yield']==10;assert f['payback_years']==10;assert f['net_yield'] is None;assert len(f['scenarios'])==3

def test_net():
 x=sample(annual_costs={k:0 for k in COST_KEYS},transaction_costs=0,vacancy_months=0);assert analyze(x)['net_yield']==10

def test_zero():
 assert analyze({'price':0,'monthly_rent':100})['gross_yield'] is None
 assert analyze({'price':10,'monthly_rent':0})['payback_years'] is None

def test_geography():
 assert haversine(KAZAN)==0;assert 30<haversine((55.846,48.501))<50
 assert apply_geo({'coordinates':None})['distance_km'] is None
 assert apply_geo({'coordinates':[999,0],'coordinate_source':'fixture','geo_accuracy':'building'})['distance_km'] is None
 assert apply_geo({'coordinates':KAZAN,'coordinate_source':'city centroid','geo_accuracy':'city'})['distance_km'] is None

def test_claims_not_confirmation():
 x=sample(active_tenant=True);assert x['verification']=='review';x=apply_geo(x);x['finance']=analyze(x);assert score(x)['score']<=39

def test_confirmed():assert sample(active_tenant=True,payments_confirmed=True,contract=True,verification_evidence='fixture documents')['verification']=='confirmed'

def test_validation():
 with pytest.raises(ValueError):sample(annual_costs={'tax':-2})
 with pytest.raises(ValueError):sample(active_tenant='yes')

def test_storage(tmp_path):
 db=Database(tmp_path/'test.db');x=sample();db.upsert(x);x=sample();x['price']=11000000;db.upsert(x);assert len(db.all())==1;assert len(db.all()[0]['history'])==2;db.close()

def test_cross_source():
 a=sample(address='Улица, 1',settlement='Казань',coordinates=KAZAN);b={**a,'sources':[{'name':'B','url':'https://example.org/b'}]};assert duplicate(a,b)
 b['area']=150;assert not duplicate(a,b)
