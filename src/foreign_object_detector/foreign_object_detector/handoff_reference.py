"""Переходный синтетический канал текущих отражений без состояния, независимый от обоих состояний S2."""
import time
import numpy as np
from .short_extension import Continuation,anchor_from_normal
from .near.clearance import structure_masks


def _result(source,ids,coords,ranges,definition,debug):
 positive=np.flatnonzero(coords[:,0]>0);selected=None
 if len(positive):selected=int(positive[np.lexsort((ids[positive],coords[positive,0]))[0]])
 out={'obstacle':selected is not None,'distance_m':float(coords[selected,0]) if selected is not None else -1.,'source':source if selected is not None else None,'source_index':int(ids[selected]) if selected is not None else None,'euclidean_m':float(ranges[selected]) if selected is not None else -1.,'strong_points':len(ids),'distance_definition':definition}
 if debug:out['source_indices']=ids.tolist();out['coordinates']=coords.tolist()
 return out

def process(normal,internal,extension_info,config,far,b1,b2,debug=False):
 start=time.perf_counter();empty=np.empty((0,3));branches={}
 def emit(name,ids=np.empty(0,dtype=int),q=empty,r=np.empty(0),kind='arc'):
  branches[name]=_result(name,ids,q,r,'horizontal estimated-centerline arc length from the local rail-frame origin' if kind=='arc' else 'minimum positive N1 nominal-forward coordinate of a current accepted point; Euclidean diagnostic uses the same selected point',debug)
 if b1:emit('SYNTHETIC_MEASURED');emit('SYNTHETIC_X1_EXTRAPOLATED')
 if b2:emit('SYNTHETIC_NOMINAL_BRIDGE',kind='N1')
 if normal['centerline']['quality']!='GOOD' or 'frenet' not in internal:return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':False}
 center=normal['centerline'];measured=float(center['last_supported_forward_m']);minimum=float(center['normalized_forward_interval_m'][0]);effective=float(center['normalized_forward_interval_m'][1]);curve=None
 if extension_info and extension_info['available']:
  curve=Continuation(anchor_from_normal(normal));effective=measured+extension_info['gain_m']
 if not np.isfinite([minimum,measured,effective]).all():return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':False}
 # Углы лучей вычисляются до нормализации по рельсам, с ТОЧНОЙ арифметикой дальнего канала.
 p=internal['canonical'];pre=np.flatnonzero((p[:,0]<60)&np.isfinite(p).all(1)&np.any(p!=0,axis=1))
 accepted={k:[] for k in branches};qs={k:[] for k in branches};rs={k:[] for k in branches};offcount=0
 for begin in range(0,len(pre),8192):
  ix=pre[begin:begin+8192];q=p[ix].astype(np.float64);ranges=np.linalg.norm(q,axis=1)
  e=np.degrees(np.arctan2(q[:,2],np.hypot(q[:,0],q[:,1])));j=np.clip(np.searchsorted(far.beams,e),1,127);j-=np.abs(e-far.beams[j-1])<=np.abs(e-far.beams[j]);off=(np.abs(e-far.beams[j])>.02)&(ranges<=180.)
  ix=ix[off];q=q[off];ranges=ranges[off];offcount+=len(ix)
  if not len(ix):continue
  ids=internal['source_indices'][ix];u=internal['projection_parameter'][ix]
  def add(name,mask,coord):
   accepted[name].append(ids[mask]);qs[name].append(coord[mask]);rs[name].append(ranges[mask])
  if b1:
   f=internal['frenet'][ix];mask=internal['valid_track'][ix]&(u>=minimum)&(u<=measured)&internal['retained'][ix]&(abs(f[:,1])<=.95)&(f[:,2]>=.06)&(f[:,2]<=2.90)
   add('SYNTHETIC_MEASURED',mask,f)
   if curve is not None:
    pts=internal['normalized'][ix];f,xu,valid=curve.project(pts,effective);rail,below=structure_masks(f,center['separation_m'],config)
    mask=(u>measured)&(pts[:,0]>measured-2)&(pts[:,0]<effective+2)&valid&~rail&~below&(abs(f[:,1])<=.95)&(f[:,2]>=.06)&(f[:,2]<=2.90)
    add('SYNTHETIC_X1_EXTRAPOLATED',mask,f)
  if b2:
   # u является исходным нормированным параметром горизонтальной проекции в ТОЙ ЖЕ
   # системе координат, что effective. Он проверяет только сторону относительно конца;
   # габарит за концом задается N1, без новой кривой или заявления об экстраполяции рельсов.
   n=(q-far.origin)@far.rotation.T
   mask=np.isfinite(u)&(u>effective)&(u>=minimum)&(abs(n[:,1])<=.95)&(n[:,2]>=.06)&(n[:,2]<=2.90)
   add('SYNTHETIC_NOMINAL_BRIDGE',mask,n)
 for name in branches:
  if accepted[name]:emit(name,np.concatenate(accepted[name]),np.concatenate(qs[name]),np.concatenate(rs[name]),'N1' if name=='SYNTHETIC_NOMINAL_BRIDGE' else 'arc')
 return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':True,'offbeam_below60_points':offcount,'effective_endpoint_normalized_u_m':effective,'measured_endpoint_normalized_u_m':measured,'boundary_definition':'existing normalized centerline projection parameter > effective endpoint; N1 supplies bridge clearance, not a new track'}
