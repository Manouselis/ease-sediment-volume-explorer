"""Reproducible public-data comparison, not independent field validation."""
import json
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from ease_volume.core import AnalysisConfig, Points, analyze, make_surface
from ease_volume.kriging import KrigingSurface

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'qa'/'comparison';out.mkdir(parents=True,exist_ok=True)
xyz=np.loadtxt(ROOT/'data/demo_current.csv',delimiter=',',skiprows=1)
# An unmodified 20 by 40 subset of public measured-data-derived cell means.
mask=(xyz[:,0]<xyz[:,0].min()+20)&(xyz[:,1]<xyz[:,1].min()+40)
xyz=xyz[mask]
p=out/'rws_subset.csv';np.savetxt(p,xyz,delimiter=',',header='x,y,z',comments='',fmt='%.17g')
base=dict(reference_note='Hypothetical -6.5 m NAP design, not official',reference_elevation=-6.5,max_edge=4,filter_mode='off')
report={'dataset':'Public RWS 1 m cell means, 20 by 40 subset', 'points':len(xyz),'reference':'Hypothetical -6.5 m NAP design', 'field_validation':False,'runs':{}}
for method in ['tin','kriging']:
    c=AnalysisConfig.parse(dict(base,surface_method=method))
    start=time.perf_counter();r=analyze(p,None,None,c,out/method)
    report['runs'][method]={'seconds':time.perf_counter()-start,'summary':r['summary'],'surface_generation':r['provenance']['surface_generation']}
# Withhold a contiguous two-metre-wide strip before fitting. No test elevations
# contribute to variogram fitting. This tests this one gap, not all canal gaps.
x0=xyz[:,0].min(); withheld=(xyz[:,0]>=x0+8)&(xyz[:,0]<x0+10)
train,test=xyz[~withheld],xyz[withheld]
geometry=make_surface(Points(train,'public_rws_subset','',''),train,4)
start=time.perf_counter();tin=geometry.sample(test[:,:2]);tin_seconds=time.perf_counter()-start
start=time.perf_counter();kp=KrigingSurface(geometry,train,AnalysisConfig.parse(dict(base,surface_method='kriging')));kz,kv,reason=kp.sample(test[:,:2]);k_seconds=time.perf_counter()-start
common=np.isfinite(tin)&np.isfinite(kz)
report['holdout']={'training_points':len(train),'withheld_points':len(test),'common_predictions':int(common.sum()),'scheme':'one contiguous two-metre X strip, fitted on training only','methods':{}}
for name,values,elapsed in [('tin',tin,tin_seconds),('kriging',kz,k_seconds)]:
    error=values[common]-test[common,2]
    report['holdout']['methods'][name]={'rmse_m':float(np.sqrt(np.mean(error**2))),'bias_m':float(np.mean(error)),'seconds':elapsed}
report['holdout']['kriging_rms_standard_error_m']=float(np.sqrt(np.mean(kv[common])))
report['peak_process_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
(out/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
