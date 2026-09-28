"""Перенос только X1 из Phase7C. Фиксированное продолжение на пять метров; компоненты изолированы."""
from dataclasses import dataclass
import time
import numpy as np
from .near.centerline import arc_length
from .near.clearance import inside_clearance,structure_masks
from .near.candidate import candidates
from .sparse_tracker import extract
MAXIMUM_EXTENSION_M=5.0

@dataclass(frozen=True)
class Anchor:
 end: float
 lateral: tuple
 height: tuple
 samples: tuple

def anchor_from_normal(near):
 c=near['centerline']
 if c.get('quality')!='GOOD' or not near['rail_reference']['valid']:
  raise ValueError('TRACK_NOT_GOOD')
 a=Anchor(float(c['last_supported_forward_m']),tuple(c['lateral_coefficients']),tuple(c['height_coefficients']),tuple(map(tuple,c['support_samples'])))
 q=np.asarray(a.samples)
 if len(q)<3 or q.ndim!=2 or q.shape[1]!=3 or not np.isfinite(q).all() or not np.isfinite([a.end,*a.lateral,*a.height]).all() or len(a.lateral)!=3 or len(a.height)!=3:
  raise ValueError('INSUFFICIENT_CAUSAL_FIT')
 return a

class Continuation:
 def __init__(self,anchor):
  self.anchor=anchor;self.coefs=np.array([anchor.lateral,anchor.height])
 def at(self,u):
  u=np.asarray(u,dtype=float);vals=[];slopes=[];second=[]
  for c in self.coefs:
   v=c[0]+c[1]*u+c[2]*u*u;dv=c[1]+2*c[2]*u;dd=np.full_like(u,2*c[2])
   vals.append(v);slopes.append(dv);second.append(dd)
  return (*vals,*slopes,*second)
 def arc(self,u):
  u=np.asarray(u,dtype=float);return arc_length(self.anchor.lateral,u)
 def horizon(self):
  # Только численная допустимость. Некалиброванная неопределенность НЕ является критерием приема.
  ds=np.arange(0,MAXIMUM_EXTENSION_M+1e-8,0.1)
  finite=np.all(np.isfinite(np.array(self.at(self.anchor.end+ds))),axis=0)
  bad=np.flatnonzero(~finite)
  if len(bad):return float(ds[max(0,bad[0]-1)]),'INSUFFICIENT_CAUSAL_FIT'
  return MAXIMUM_EXTENSION_M,'MAX_EXTENSION'
 def project(self,points,end):
  u=points[:,0].astype(float).copy()
  for _ in range(8):
   y,h,dy,dh,ddy,ddh=self.at(u);step=(u-points[:,0]+(y-points[:,1])*dy)/np.maximum(1+dy*dy+(y-points[:,1])*ddy,.1);u-=np.clip(step,-10,10)
  y,h,dy,*_=self.at(u);d=(-(points[:,0]-u)*dy+points[:,1]-y)/np.sqrt(1+dy*dy)
  valid=(u>self.anchor.end)&(u<=end)&np.isfinite(u)
  return np.column_stack([self.arc(u),d,points[:,2]-h]),u,valid

def extension(near,debug,config,continuation,gain,frame=0,ts=0.):
 """Возвращает ТОЛЬКО добавленную диагностику. Входы, измеренные массивы и основное состояние не меняются."""
 started=time.perf_counter();end=continuation.anchor.end+gain
 # Замороженная исходная измеренная проекция задает одностороннюю границу владения.
 choose=(debug['projection_parameter']>continuation.anchor.end)&(debug['normalized'][:,0]>continuation.anchor.end-2)&(debug['normalized'][:,0]<end+2)
 old_ids=[i for c in near['candidates'] for i in c['original_point_indices']]
 if old_ids:choose&=~np.isin(debug['source_indices'],old_ids)
 idx=np.flatnonzero(choose);points=debug['normalized'][idx];f,u,valid=continuation.project(points,end)
 inside=inside_clearance(f,valid,config);rail,below=structure_masks(f,near['centerline']['separation_m'],config);keep=inside&~rail&~below
 found=candidates(f[keep],debug['xyz'][idx][keep],debug['source_indices'][idx][keep],config,'GOOD')
 stub={'centerline':{'quality':'GOOD','normalized_forward_interval_m':[continuation.anchor.end,end],'last_supported_forward_m':end},'candidates':found}
 extdebug={'frenet':f,'retained':keep,'projection_parameter':u,'source_indices':debug['source_indices'][idx],'xyz':debug['xyz'][idx]}
 obs,stats,_=extract(stub,extdebug,config,frame,ts)
 for o in obs:o['mask_state']='DIAGNOSTIC_EXTRAPOLATED_GOOD_SURVIVES_FROZEN_MASKS'
 return {'candidates':found,'observations':obs,'stats':stats,'incremental_clearance_ms':(time.perf_counter()-started)*1000,'source_indices':debug['source_indices'][idx],'frenet':f,'projection_parameter':u,'valid':valid,'retained':keep}
