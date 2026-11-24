"""Known geometry and independently solved small ordinary-Kriging systems."""
import csv
import json
import numpy as np
import pytest
import rasterio
from scipy.spatial.distance import cdist
from ease_volume.core import AnalysisConfig, AnalysisError, Points, analyze, make_surface
from ease_volume.kriging import KrigingSurface
from test_independent import config, points_file, boundary_file
from shapely.geometry import box


def kc(**kw):
    values=dict(surface_method='kriging', kriging_fit='manual', kriging_partial_sill=.2, kriging_range=4, kriging_nugget=0)
    values.update(kw)
    return config(**values)


def test_default_and_explicit_tin_identical(tmp_path):
    p=points_file(tmp_path/'a.csv',range(4),range(4),lambda x,y:x+y)
    a=analyze(p,None,None,config(),tmp_path/'a')
    b=analyze(p,None,None,config(surface_method='tin'),tmp_path/'b')
    assert a['summary']==b['summary']
    assert a['grid']==b['grid']


@pytest.mark.parametrize('model',['spherical','exponential','gaussian'])
def test_independent_small_kriging_system(model):
    xyz=np.array([[0,0,0],[1,0,.2],[0,1,.4],[1,1,.8]],float)
    c=kc(kriging_model=model)
    pred=KrigingSurface(make_surface(Points(xyz,'test','',''),xyz,2),xyz,c)
    target=np.array([[.3,.6]])
    z,v,r=pred.sample(target)
    # Independent semivariogram equations: sum(weights)=1, gamma matrix.
    def gamma(h):
        q=h/4
        if model=='spherical': return .2*np.where(q<1,1.5*q-.5*q**3,1)
        if model=='exponential': return .2*(1-np.exp(-3*q))
        return .2*(1-np.exp(-(q*7/4)**2))
    g=gamma(cdist(xyz[:,:2],xyz[:,:2])); d=gamma(cdist(xyz[:,:2],target)).ravel()
    matrix=np.block([[g,np.ones((4,1))],[np.ones((1,4)),np.zeros((1,1))]])
    w=np.linalg.solve(matrix,np.r_[d,1])
    assert z[0]==pytest.approx(w[:4]@xyz[:,2],abs=1e-10)
    assert v[0]==pytest.approx(w[:4]@d+w[4],abs=1e-10)
    assert r[0]=='accepted'
    ez,ev,_=pred.sample(xyz[:,:2])
    assert ez==pytest.approx(xyz[:,2],abs=1e-10)
    assert ev==pytest.approx(np.zeros(4),abs=1e-10)


def test_constant_partial_cells_and_exports(tmp_path):
    p=points_file(tmp_path/'a.csv',range(4),range(4),lambda x,y:2)
    boundary=boundary_file(tmp_path/'b.json',box(.2,.3,2.7,2.8))
    result=analyze(p,None,boundary,kc(),tmp_path/'out')
    assert result['summary']['positive_volume_m3']==pytest.approx(12.5)
    assert np.asarray(result['grid']['bed_variance'],float)==pytest.approx(np.asarray(result['grid']['bed_standard_error'],float)**2)
    assert result['summary']['valid_area_m2']==pytest.approx(6.25)
    rows=list(csv.DictReader((tmp_path/'out/cells.csv').open()))
    assert any(float(r['sample_x'])!=float(r['x']) for r in rows)
    assert sum(float(r['supported_area_m2'])*float(r['difference_m'] or 0) for r in rows)==pytest.approx(12.5)
    assert all(float(r['bed_kriging_variance_m2'])>=0 for r in rows if r['valid']=='1')
    with rasterio.open(tmp_path/'out/bed_kriging_variance.tif') as ds:
        assert ds.tags()['units']=='m2'
        assert ds.crs.to_epsg()==28992
    meta=json.loads((tmp_path/'out/summary.json').read_text())['provenance']
    assert meta['surface_generation']['bed']['partial_sill_m2']==.2
    assert meta['surface_generation']['reference']['method']=='constant'


def test_common_uploaded_reference(tmp_path):
    p=points_file(tmp_path/'a.csv',range(4),range(4),lambda x,y:2)
    q=points_file(tmp_path/'b.csv',range(4),range(4),lambda x,y:1.5)
    r=analyze(p,q,None,kc(reference_mode='file'),tmp_path/'out')
    assert r['summary']['positive_volume_m3']==pytest.approx(4.5)
    assert r['provenance']['surface_generation']['reference']['method']=='ordinary_kriging'
    assert (tmp_path/'out/reference_kriging_standard_error.tif').exists()


def test_auto_reproducible_and_manual_noise_exact():
    x,y=np.meshgrid(np.arange(6),np.arange(6)); xyz=np.c_[x.ravel(),y.ravel(),np.sin(x.ravel())*.2+np.cos(y.ravel())*.1]
    geom=make_surface(Points(xyz,'test','',''),xyz,2)
    c=config(surface_method='kriging')
    a,b=KrigingSurface(geom,xyz,c),KrigingSurface(geom,xyz,c)
    assert a.metadata==b.metadata
    assert a.metadata['total_sill_m2']>0
    values,var,_=a.sample(xyz[:2,:2])
    assert values==pytest.approx(xyz[:2,2],abs=1e-8)
    assert var==pytest.approx([0,0],abs=1e-8)


def test_auto_constant_fails_no_fallback(tmp_path):
    p=points_file(tmp_path/'a.csv',range(4),range(4),lambda x,y:2)
    with pytest.raises(AnalysisError,match='kriging_fit_failed'):
        analyze(p,None,None,config(surface_method='kriging'),tmp_path/'out')


def test_search_and_threshold_exclusions(tmp_path):
    p=points_file(tmp_path/'a.csv',range(5),range(5),lambda x,y:2)
    with pytest.raises(AnalysisError,match='kriging_no_predictions'):
        analyze(p,None,None,kc(kriging_radius=.01),tmp_path/'short')
    with pytest.raises(AnalysisError,match='kriging_no_predictions'):
        analyze(p,None,None,kc(kriging_max_se=0),tmp_path/'threshold')
    # A boundary creates different distances and therefore different uncertainties.
    b=boundary_file(tmp_path/'b.json',box(.05,.05,3.1,3.1))
    r=analyze(p,None,b,kc(),tmp_path/'base')
    se=np.sqrt(np.array([float(row['bed_kriging_variance_m2']) for row in csv.DictReader((tmp_path/'base/cells.csv').open()) if row['valid']=='1']))
    cutoff=float(np.median(se))
    t=analyze(p,None,b,kc(kriging_max_se=cutoff),tmp_path/'cut')
    assert t['summary']['prediction_excluded_area_m2']>0
    assert t['summary']['valid_area_m2']<r['summary']['valid_area_m2']
    assert t['summary']['positive_volume_m3']==pytest.approx(2*t['summary']['valid_area_m2'])
    assert any(row['exclusion_reason']=='uncertainty_threshold' for row in csv.DictReader((tmp_path/'cut/cells.csv').open()))


def test_disconnected_neighbors_and_gap():
    # Two separate squares at heights 0 and 100. Large radius must not mix them.
    xyz=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0],[3,0,100],[4,0,100],[3,1,100],[4,1,100]],float)
    pred=KrigingSurface(make_surface(Points(xyz,'test','',''),xyz,1.5),xyz,kc(kriging_radius=100))
    z,v,r=pred.sample(np.array([[.5,.5],[2,.5],[3.5,.5]]))
    assert z[[0,2]]==pytest.approx([0,100])
    assert np.isnan(z[1]) and r[1]=='outside_support'


@pytest.mark.parametrize('changes',[{'kriging_range':0},{'kriging_nugget':-1},{'kriging_partial_sill':0},{'kriging_neighbors':65},{'kriging_radius':0},{'kriging_max_se':-1},{'kriging_model':'invalid'},{'reference_mode':'file','reference_crs':'EPSG:32631'},{'reference_mode':'file','reference_vertical_datum':'unknown'}])
def test_configuration_checks(changes):
    with pytest.raises(AnalysisError): kc(**changes)


def test_bounded_fit_and_failure(monkeypatch):
    import ease_volume.kriging as module
    x,y=np.meshgrid(range(24),range(24));xyz=np.c_[x.ravel(),y.ravel(),np.sin(x.ravel())]
    geom=make_surface(Points(xyz,'test','',''),xyz,2)
    original=module.OrdinaryKriging; sizes=[]
    def observed(x,y,z,**kwargs):
        sizes.append(len(x));return original(x,y,z,**kwargs)
    monkeypatch.setattr(module,'OrdinaryKriging',observed)
    pred=module.KrigingSurface(geom,xyz,kc())
    pred.sample(np.array([[.5,.5],[5.5,5.5]]))
    assert sizes[0]==512 and max(sizes[1:])<=16
    monkeypatch.setattr(module,'MAX_PREDICTIONS',1)
    with pytest.raises(AnalysisError,match='kriging_limit'):pred.sample(np.array([[.5,.5],[5.5,5.5]]))
    monkeypatch.setattr(module,'MAX_PREDICTIONS',20000)
    def bad(*a,**kw):raise np.linalg.LinAlgError('singular')
    monkeypatch.setattr(module,'OrdinaryKriging',bad)
    with pytest.raises(AnalysisError,match='kriging_solve_failed'):pred.sample(np.array([[.5,.5]]))


def test_api_bundle_uncertainty_and_invalid_config(tmp_path,monkeypatch):
    import io,zipfile
    from fastapi.testclient import TestClient
    import ease_volume.server as server
    monkeypatch.setattr(server,'RUNS',tmp_path/'runs')
    server.RUNS.mkdir()
    client=TestClient(server.app)
    p=points_file(tmp_path/'a.csv',range(4),range(4),lambda x,y:2)
    r=client.post('/api/analyze',data={'config':kc().model_dump_json()},files={'survey':('a.csv',p.read_bytes(),'text/csv')})
    assert r.status_code==200,r.text
    result=r.json();bundle=client.get(result['exports']['bundle'])
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as z:
        assert 'bed_kriging_variance.tif' in z.namelist()
        assert 'reference_kriging_variance.tif' not in z.namelist()
    url=result['exports']['bundle'].replace('bundle.zip','bed_kriging_standard_error.tif')
    assert client.get(url).status_code==200
    assert client.get(url.replace('bed_kriging','reference_kriging')).status_code==404
    values=kc().model_dump();values['kriging_neighbors']=100
    bad=client.post('/api/analyze',data={'config':json.dumps(values)},files={'survey':('a.csv',p.read_bytes(),'text/csv')})
    assert bad.status_code==422 and bad.json()['error']['code']=='invalid_config'


@pytest.mark.parametrize('kind',['boundary','raster'])
def test_kriging_preserves_hole_masks(tmp_path,kind):
    from test_independent import raster_file
    values=np.full((6,6),2.)
    boundary=None
    if kind=='raster':
        values[2,2]=-9999
        p=raster_file(tmp_path/'a.tif',values)
        hole=box(2,3,3,4)
    else:
        p=points_file(tmp_path/'a.csv',range(7),range(7),lambda x,y:2)
        hole=box(2,2,3,3)
        boundary=boundary_file(tmp_path/'boundary.json',box(0,0,6,6).difference(hole))
    result=analyze(p,None,boundary,kc(max_edge=3),tmp_path/'out')
    assert result['summary']['positive_volume_m3']==pytest.approx(2*result['summary']['valid_area_m2'])
    rows=list(csv.DictReader((tmp_path/'out/cells.csv').open()))
    from shapely.geometry import Point
    assert not any(row['valid']=='1' and hole.contains(Point(float(row['sample_x']),float(row['sample_y']))) for row in rows)
