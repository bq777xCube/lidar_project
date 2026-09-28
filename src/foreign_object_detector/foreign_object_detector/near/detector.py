"""Покадровый детектор. Ядро не знает имя bag, сохраненную карту или временное состояние."""
import time
import numpy as np
from ..config import normal_config as load_config
from .point_cloud import PointCloudFrame,to_canonical
from .rail_reference import estimate
from .rail_frame import from_plane,from_profile
from .centerline import extend
from .clearance import inside_clearance,structure_masks
from .candidate import candidates


class Detector:
    def __init__(self,config=None):self.config=load_config() if config is None else config

    def process(self,frame,return_debug=False):
        if not isinstance(frame,PointCloudFrame):frame=PointCloudFrame(frame)
        started=time.perf_counter();last=started;timings={}
        def stage(name):
            nonlocal last
            now=time.perf_counter();timings[name]=(now-last)*1000;last=now
        xyz,indices,_=frame.clean(self.config['sensor']['max_input_range_m']);points=to_canonical(xyz);stage('preprocess_ms')
        reference,ref_debug=estimate(points,self.config);stage('rail_reference_ms')
        mode=self.config['sensor']['pose_mode'];profile=self.config['pose_profiles'][self.config['sensor']['fallback_profile']]
        transform=None
        if mode!='fixed' and reference['valid']:transform=from_plane(reference['plane'],reference['center_coefficients'])
        elif mode in ['fixed','auto_with_fallback']:transform=from_profile(profile,source='fixed' if mode=='fixed' else 'fallback')
        result={'detector_status':'TRACK_UNRELIABLE','obstacle_detected':None,'nearest_candidate_distance_m':None,
                'distance_definition':'horizontal estimated-centerline arc length from the local rail-frame origin',
                'input_points':len(frame.xyz),'nonzero_finite_processed_points':len(points),
                'rail_reference':reference,'pose':transform.as_dict() if transform else None,
                'centerline':{'quality':'INVALID','centerline_valid_until_m':None},
                'points_inside_gauge_before_mask':0,'points_after_mask':0,'candidate_count':0,'candidates':[],
                'reason_flags':list(reference['reason_flags'])}
        debug={'xyz':xyz,'source_indices':indices,'canonical':points,**ref_debug}
        if transform and reference['valid']:
            normalized=transform.transform(points)
            head_residual=normalized[ref_debug['head_indices'],2]
            result['normalized_head_rms_m']=float(np.sqrt(np.mean(head_residual**2)))
            result['normalized_head_mean_m']=float(np.mean(head_residual))
            result['normalized_head_min_max_m']=[float(head_residual.min()),float(head_residual.max())]
            debug['normalized']=normalized
            stage('normalization_ms')
            if result['normalized_head_rms_m']<=self.config['rail']['max_normalized_head_rms_m']:
                center=extend(normalized,reference,transform,self.config);result['centerline']=center.as_dict();stage('centerline_ms')
                frenet,u,valid=center.project(normalized)
                inside=inside_clearance(frenet,valid,self.config)
                rail,below=structure_masks(frenet,center.separation_m,self.config)
                retained=inside&~rail&~below
                result['points_inside_gauge_before_mask']=int(inside.sum());result['points_after_mask']=int(retained.sum())
                result['masked_rail_points']=int((inside&rail).sum());result['masked_below_rail_points']=int((inside&below).sum())
                stage('clearance_mask_ms')
                found=candidates(frenet[retained],xyz[retained],indices[retained],self.config,center.quality)
                result.update({'candidates':found,'candidate_count':len(found),'obstacle_detected':bool(found),
                               'nearest_candidate_distance_m':found[0]['nearest_distance_m'] if found else None,
                               'detector_status':'OBSTACLE' if found else 'CLEAR',
                               'clear_scope':'Only the reported valid track interval; beyond that interval is UNKNOWN.'})
                stage('candidates_ms')
                debug.update({'frenet':frenet,'projection_parameter':u,'valid_track':valid,'inside':inside,
                              'rail_mask':rail,'below_mask':below,'retained':retained,'centerline_object':center})
            else:result['reason_flags'].append('POSE_INCONSISTENT_WITH_RAIL_HEADS')
        elif transform:result['reason_flags'].append('FALLBACK_POSE_WITHOUT_VERIFIED_TRACK')
        result['timings_ms']=timings;result['total_processing_ms']=(time.perf_counter()-started)*1000
        return (result,debug) if return_debug else result
