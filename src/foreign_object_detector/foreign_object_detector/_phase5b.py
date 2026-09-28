"""Рабочая граница с состоянием: неизменная основная геометрия и замороженный S2."""
import time
from .config import load_config
from .near.detector import Detector as NormalDetector
from .sparse_tracker import SparseTracker,extract,normal_regions,PARAMETERS
from .output import map_output

class Detector:
    def __init__(self,config=None):
        self.config=load_config() if config is None else config
        self.normal=NormalDetector(self.config['normal'])
        self.reset('STARTUP')

    def reset(self,reason='CONFIG_RESET'):
        self.tracker=SparseTracker(self.config['sparse']);self.last_stamp=None;self.last_frame=None;self.pending_reset=reason

    def process(self,xyz,timestamp_ns,frame_index=None,debug=False):
        start=time.perf_counter();stamp=int(timestamp_ns);reason=self.pending_reset;self.pending_reset=None
        nominal_ns=round(PARAMETERS['nominal_scan_s']*1e9)
        slots=1
        if self.last_stamp is not None:
            delta=stamp-self.last_stamp
            slots=max(1,int((delta+nominal_ns//2)//nominal_ns))
            if delta<=0:reason='TIMESTAMP_ROLLBACK';self.reset(reason)
            elif slots>PARAMETERS['max_missing_frames']+1:reason='TIMESTAMP_GAP';self.reset(reason)
        index=int(frame_index) if frame_index is not None else (self.last_frame+slots if self.last_frame is not None else 0)
        if self.last_frame is not None and not 1<=index-self.last_frame<=2:reason='FRAME_GAP';self.reset(reason)
        normal,internal=self.normal.process(xyz,return_debug=True)
        sparse_start=time.perf_counter();good=normal['centerline']['quality']=='GOOD'
        if not good:reason='TRACK_UNRELIABLE';self.reset(reason)
        if self.last_frame is not None and index-self.last_frame==2:
            # Продвигаем замороженный автомат последовательных состояний через пропущенный скан;
            # наблюдение не добавляется, препятствие при этом появиться не может.
            self.tracker.step(self.last_frame+1,(self.last_stamp+nominal_ns)/1e9,[],[],False,good=False)
        observations,stats,extraction_ms=extract(normal,internal,self.config['normal'],index,stamp/1e9)
        sparse=self.tracker.step(index,stamp/1e9,observations,normal_regions(normal,index,stamp/1e9),normal['obstacle_detected'],good)
        self.last_frame=index;self.last_stamp=stamp;self.pending_reset=None
        result=map_output(normal,observations,sparse)
        timings=dict(normal['timings_ms']);timings['sparse_extension_ms']=(time.perf_counter()-sparse_start)*1000
        result.update({'normal':normal,'observations':observations,'sparse':sparse,'sparse_reset_reason':reason,'frame_index':index,'timestamp_ns':stamp,'timings_ms':timings,'processing_ms':(time.perf_counter()-start)*1000})
        if debug:result['debug']=internal;result['extraction_stats']=stats
        return result
