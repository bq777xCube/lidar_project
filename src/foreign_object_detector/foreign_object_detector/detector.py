"""Один замороженный ближний канал, изолированный X1, S2, дальний канал и переходные ветви."""
import copy,time
from .config import load_config,validate_direct,validate_far_switch
from .v2_detector import Detector as V2Detector
from .v3_detector import combine
from .far import FarChannel
from .handoff import process as handoff

class Detector(V2Detector):
 def __init__(self,config=None):
  cfg=copy.deepcopy(load_config() if config is None else config);validate_far_switch(cfg);self.options=validate_direct(cfg);super().__init__(cfg);self.far=FarChannel()
 def process(self,xyz,timestamp_ns,frame_index=None,debug=False):
  started=time.perf_counter();extra=self.options['b1'] or self.options['b2']
  # Повторное использование только внутри одного кадра, без переноса геометрии между кадрами.
  from .near.geometry_math import refinement_scope
  with refinement_scope(self.options['memoize_refinement']) as memo:
   result=super().process(xyz,timestamp_ns,frame_index,debug or extra)
  if self.config['far_synthetic']['enabled']:result=combine(result,self.far.process(xyz,debug=debug))
  if extra:
   rescue=handoff(result['normal'],result['debug'],result.get('extension'),self.config['normal'],self.far,self.options['b1'],self.options['b2'],debug)
   result['handoff']=rescue
   for branch in rescue['branches'].values():
    if branch['obstacle'] and (not result['obstacle'] or result['distance_m']<=0 or branch['distance_m']<result['distance_m']):
     result.update(obstacle=True,state='OBSTACLE_NORMAL',distance_m=branch['distance_m'],source=branch['source'],distance_definition=branch['distance_definition'],selected_source_index=branch['source_index'])
  if self.short_extension['enabled'] and self.config['far_synthetic']['enabled'] and not (result.get('source') or '').startswith('SYNTHETIC_'):
   # В v2 исторический источник сохраняется, когда расширение ближе;
   # оставляем выбор ветви, связывая итоговый источник с его расстоянием.
   ext=result['extension'];base=result['production'];ds=[(c['nearest_distance_m'],'NORMAL_EXTENDED') for c in ext['candidates']]
   confirmed=set(ext['sparse']['confirmed_track_ids']['S2']);obsids={a['observation_id'] for a in ext['sparse']['assignments'] if a['track_id'] in confirmed};ds += [(o['minimum'][0],'SPARSE_EXTENDED') for o in ext['observations'] if o['observation_id'] in obsids]
   if result.get('source')!='FAR_SYNTHETIC_BEAM' and ds:
    distance,source=min(ds,key=lambda item:item[0])
    if not base['obstacle'] or distance<base['distance_m']:result['source']=source
  if self.options['memoize_refinement']:result['refinement_cache']=memo
  if not debug:result.pop('debug',None);result.pop('extraction_stats',None)
  result['processing_ms']=(time.perf_counter()-started)*1000
  return result
