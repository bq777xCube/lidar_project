"""Необязательная ветвь фиксированного +5 X1; замороженные основной канал и S2 независимы."""
import copy,time
from ._phase5b import Detector as Phase5B
from .config import load_config,validate_short_extension
from .short_extension import anchor_from_normal,Continuation,extension
from .sparse_tracker import SparseTracker,normal_regions,PARAMETERS

class Detector(Phase5B):
 def __init__(self,config=None):
  cfg=copy.deepcopy(load_config() if config is None else config)
  self.short_extension=validate_short_extension(cfg)
  super().__init__(cfg)
 def reset(self,reason='CONFIG_RESET'):
  super().reset(reason);self.extension_tracker=SparseTracker(self.config['sparse']);self.extension_last_frame=None;self.extension_last_stamp=None
 def set_extension_enabled(self,enabled):
  if type(enabled) is not bool:raise ValueError('enabled must be boolean')
  if enabled!=self.short_extension['enabled']:
   self.short_extension['enabled']=enabled;self.config['short_extension']=dict(self.short_extension);self.reset('CONFIG_RESET')
 def process(self,xyz,timestamp_ns,frame_index=None,debug=False):
  if not self.short_extension['enabled']:return super().process(xyz,timestamp_ns,frame_index,debug)
  started=time.perf_counter()
  result=super().process(xyz,timestamp_ns,frame_index,True)
  self._extend_result(result)
  if not debug:result.pop('debug',None);result.pop('extraction_stats',None)
  result['processing_ms']=(time.perf_counter()-started)*1000
  return result
 def _extend_result(self,result):
  """Та же граница интеграции, что в кэшированных префиксах проверки; без аргументов целевого объекта."""
  started=time.perf_counter();near=result['normal'];debug=result['debug'];frame=result['frame_index'];stamp=result['timestamp_ns'];ts=stamp/1e9
  production={k:v for k,v in result.items() if k not in ['debug','extraction_stats']}
  reason=result['sparse_reset_reason'];good=near['centerline']['quality']=='GOOD'
  if reason or not good:
   self.extension_tracker=SparseTracker(self.config['sparse']);self.extension_last_frame=None;self.extension_last_stamp=None
  measured=result['measured_horizon_m'];gain=0.;termination='TRACK_NOT_GOOD';added={'candidates':[],'observations':[]};curve=None
  if good:
   try:
    curve=Continuation(anchor_from_normal(near));gain,termination=curve.horizon()
   except (ValueError,KeyError,AssertionError):termination='INSUFFICIENT_CAUSAL_FIT'
   if gain>0:added=extension(near,debug,self.config['normal'],curve,gain,frame,ts)
  if gain<=0:
   self.extension_tracker=SparseTracker(self.config['sparse']);self.extension_last_frame=None;self.extension_last_stamp=None
  if self.extension_last_frame is not None and frame-self.extension_last_frame==2:
   self.extension_tracker.step(self.extension_last_frame+1,(self.extension_last_stamp+round(PARAMETERS['nominal_scan_s']*1e9))/1e9,[],[],False,False)
  # Рабочее подтверждение владеет своими физическими свидетельствами; история расширения удаляется
  # при передаче. Состояние основного трекера и массивы кандидатов никогда не изменяются.
  handoff=bool(production['obstacle'])
  if handoff:self.extension_tracker=SparseTracker(self.config['sparse'])
  state=self.extension_tracker.step(frame,ts,added['observations'],normal_regions({'candidates':added['candidates']},frame,ts),bool(added['candidates']),gain>0)
  self.extension_last_frame=frame;self.extension_last_stamp=stamp
  confirmed_ids=set(state['confirmed_track_ids']['S2']);obs_ids={a['observation_id'] for a in state['assignments'] if a['track_id'] in confirmed_ids}
  distances=[c['nearest_distance_m'] for c in added['candidates']]+[o['minimum'][0] for o in added['observations'] if o['observation_id'] in obs_ids]
  ext_normal=bool(added['candidates']);ext_sparse=bool(confirmed_ids);ext_confirmed=bool(distances)
  source='NORMAL_MEASURED' if production['normal_confirmed'] else 'SPARSE_MEASURED' if production['sparse_confirmed'] else None
  if production['obstacle']:
   if distances:result['distance_m']=min(production['distance_m'],min(distances))
  elif ext_confirmed:
   result.update(obstacle=True,distance_m=float(min(distances)),state='OBSTACLE_NORMAL' if ext_normal else 'OBSTACLE_SPARSE',normal_confirmed=ext_normal,sparse_confirmed=ext_sparse)
   source='NORMAL_EXTENDED' if ext_normal else 'SPARSE_EXTENDED'
  result.update(production=production,source=source,effective_horizon_m=measured+gain if measured>=0 else measured,extension={'available':gain>0,'gain_m':gain,'termination':termination,'candidates':added['candidates'],'observations':added['observations'],'sparse':state,'normal_confirmed':ext_normal,'sparse_confirmed':ext_sparse,'suppressed_by_production':handoff,'reset_reason':reason,'model':'local_quadratic','maximum_extension_m':5.0})
  result['timings_ms']=dict(result['timings_ms']);result['timings_ms']['short_extension_ms']=(time.perf_counter()-started)*1000
