"""Дальний канал без состояния для предоставленной синтетики; используются только XYZ."""
import hashlib,json,time
from pathlib import Path
import numpy as np
ASSET_SHA256='e1300ecdaa788ab663fd982b0438ca5be7282017714f8da6c2d92bca114ac156'
BEAM_SOURCE_SHA256='da0f6ec664cc2b5451819a4a55e2ad2d78fdc36032722d269b2c03c28055f690'
CONSTANTS={'beam_error_strict_gt_deg':.02,'canonical_forward_min_m':60.,'range_max_m':180.,'strong_half_width_m':.95,'strong_lower_m':.06,'strong_upper_m':2.9}
def load_assets():
 data=(Path(__file__).parent/'config/frozen_far.json').read_bytes()
 if hashlib.sha256(data).hexdigest()!=ASSET_SHA256:raise ValueError('Frozen far asset digest mismatch')
 asset=json.loads(data)
 if asset['constants']!=CONSTANTS or asset['beam_source_sha256']!=BEAM_SOURCE_SHA256:raise ValueError('Frozen far constants differ')
 return asset
class FarChannel:
 def __init__(self):
  a=load_assets();beams=np.asarray(a['beam_elevations_deg'],dtype=np.float64);self.order=np.argsort(beams);self.beams=beams[self.order];self.origin=np.asarray(a['origin']);self.rotation=np.asarray(a['rotation'])
  for x in [self.order,self.beams,self.origin,self.rotation]:x.flags.writeable=False
 def process(self,xyz,canonical=False,source_indices=None,debug=False):
  start=time.perf_counter_ns();a=np.asarray(xyz)
  if a.ndim!=2 or a.shape[1]!=3:raise ValueError('xyz must have shape (N,3)')
  if source_indices is not None and len(source_indices)!=len(a):raise ValueError('Point-index length mismatch')
  # Сначала отбор впереди, затем копирование float64, проверка допустимости, дальности и луча.
  forward=a[:,0] if canonical else -a[:,1];idx=np.flatnonzero(forward>=60.)
  p=a[idx].astype(np.float64);valid=np.isfinite(p).all(1)&np.any(p!=0,axis=1);p=p[valid];idx=idx[valid]
  if not canonical:p=np.column_stack((-p[:,1],p[:,0],p[:,2]))
  ranges=np.linalg.norm(p,axis=1);within=ranges<=180.;p=p[within];idx=idx[within];ranges=ranges[within]
  src=idx if source_indices is None else np.asarray(source_indices)[idx];t1=time.perf_counter_ns()
  elevation=np.degrees(np.arctan2(p[:,2],np.hypot(p[:,0],p[:,1])));j=np.clip(np.searchsorted(self.beams,elevation),1,127);j-=np.abs(elevation-self.beams[j-1])<=np.abs(elevation-self.beams[j]);mismatch=np.abs(elevation-self.beams[j]);beam_ids=self.order[j];t2=time.perf_counter_ns()
  off=mismatch>.02;offp=p[off];offsrc=src[off];offranges=ranges[off];t3=time.perf_counter_ns()
  q=(offp-self.origin)@self.rotation.T;t4=time.perf_counter_ns()
  strong=(np.abs(q[:,1])<=.95)&(q[:,2]>=.06)&(q[:,2]<=2.90);t5=time.perf_counter_ns()
  accepted=np.flatnonzero(strong);positive=accepted[q[accepted,0]>0];selected=None
  if len(positive):
   # Устойчивый выбор ближайшей точки по номинальной оси; равенство решается индексом источника.
   selected=int(positive[np.lexsort((offsrc[positive],q[positive,0]))[0]])
  result={'obstacle':bool(len(accepted)),'distance_m':float(q[selected,0]) if selected is not None else -1.,'euclidean_m':float(offranges[selected]) if selected is not None else -1.,'source_index':int(offsrc[selected]) if selected is not None else None,'far_input_points':len(p),'offbeam_points':len(q),'strong_points':len(accepted),'source':'FAR_SYNTHETIC_BEAM' if len(accepted) else None,'distance_definition':'minimum positive N1 nominal-forward coordinate of a current accepted point; Euclidean diagnostic uses the same selected point'}
  if result['obstacle'] and selected is None:raise ArithmeticError('Accepted far point has no valid forward distance')
  end=time.perf_counter_ns();stages=['far_filter','elevation_and_beam_lookup','offbeam_mask','N1_transform','strong_interior','distance_selection'];times=[start,t1,t2,t3,t4,t5,end];result['timings_ms']={k:(b-a)/1e6 for k,a,b in zip(stages,times,times[1:])};result['timings_ms']['total_far']=(end-start)/1e6
  if debug:result['debug']={'far_source_indices':src,'canonical_far':p,'far_ranges':ranges,'elevation':elevation,'nearest_beam':beam_ids,'beam_mismatch':mismatch,'offbeam_mask':off,'offbeam_source_indices':offsrc,'N1_coordinates':q,'strong_mask':strong,'strong_source_indices':offsrc[strong]}
  return result
