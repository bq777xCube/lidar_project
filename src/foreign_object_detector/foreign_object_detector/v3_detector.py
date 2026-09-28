"""Замороженное ближнее поведение v1 и независимые дальние свидетельства без состояния."""
import time
from .config import load_config,validate_far_switch
from .v1_detector import Detector as V1Detector
from .far import FarChannel

def combine(near,far):
 result=dict(near);near_hit=bool(near['obstacle']);far_hit=bool(far['obstacle'])
 source='NEAR_NORMAL' if near.get('normal_confirmed') else 'NEAR_SPARSE' if near.get('sparse_confirmed') else None
 if far_hit:
  result['obstacle']=True
  if not near_hit:result['state']='OBSTACLE_NORMAL'
  if not near_hit or near['distance_m']<=0 or far['distance_m']<near['distance_m']:
   result['distance_m']=far['distance_m'];result['distance_definition']=far['distance_definition'];source='FAR_SYNTHETIC_BEAM'
 result['source']=source;result['far']=far
 return result
class Detector(V1Detector):
 def __init__(self,config=None):
  cfg=load_config() if config is None else config;validate_far_switch(cfg);super().__init__(cfg);self.far=FarChannel()
 def process(self,xyz,timestamp_ns,frame_index=None,debug=False):
  start=time.perf_counter();near=super().process(xyz,timestamp_ns,frame_index,debug)
  if not self.config['far_synthetic']['enabled']:return near
  far=self.far.process(xyz,debug=debug);result=combine(near,far);result['processing_ms']=(time.perf_counter()-start)*1000
  return result
