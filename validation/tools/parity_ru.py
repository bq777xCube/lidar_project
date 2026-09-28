"""Точная проверка T0/T3 на 262 записях; исходный v5 против установленного RU."""
import sys,os,copy,json
from pathlib import Path
sys.path.insert(0,'/workspace/experiments/rescue_query_first')
from common import *
from foreign_object_detector.detector import Detector
from foreign_object_detector.config import load_config
original=package('original_v5',ROOT/'candidates/direct_query_first')
from original_v5.config import load_config as original_config
count=0
for flags in [(False,False),(True,True)]:
 a_cfg=original_config();b_cfg=load_config();a_cfg['direct'].update(b1=flags[0],b2=flags[1]);b_cfg['direct'].update(b1=flags[0],b2=flags[1])
 for split,rows in load(ROOT/'submission/validation/expected.json').items():
  a=original.Detector(a_cfg);b=Detector(b_cfg)
  for row in rows:
   if split=='regression':a=original.Detector(a_cfg);b=Detector(b_cfg)
   raw=regression_raw(row,split);x=a.process(raw,row['stamp'],row['frame']);y=b.process(raw,row['stamp'],row['frame'])
   # Время построения ключей и вычисления кэша не является результатом решения.
   for result in [x,y]:
    for key in ['key_ms','compute_ms']:result.get('refinement_cache',{}).pop(key,None)
   if clean(x)!=clean(y):
    def differences(a,b,path=''):
     if isinstance(a,dict):
      for k in a: differences(a[k],b[k],path+'/'+k)
     elif isinstance(a,list):
      if a!=b: print('DIFF',path,str(a)[:160],str(b)[:160],flush=True)
     elif a!=b:print('DIFF',path,a,b,flush=True)
    differences(clean(x),clean(y));raise AssertionError((flags,split,row['frame']))
   assert y.get('handoff',{}).get('offbeam_below60_points') is None
   count+=1
  print('PASS',flags,split,len(rows),flush=True)
assert count==524
save('/results/ru_parity.json',{'status':'PASS','records_per_configuration':262,'configurations':['T0','T3'],'comparisons':count,'equality':'exact_except_existing_timing_fields'})
