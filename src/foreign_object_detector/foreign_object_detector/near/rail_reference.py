"""Рельсовая опора текущего облака, общая с успешной диагностикой POSE-01."""
import numpy as np
from .rail_geometry import RailSettings,fit_frame


def estimate(points,config):
    cfg=config['rail']
    settings=RailSettings(**{k:cfg[k] for k in RailSettings.__dataclass_fields__})
    mask=(points[:,0]>=cfg['near_min_m'])&(points[:,0]<=cfg['near_max_m'])&(abs(points[:,1])<=cfg['search_half_width_m'])&(points[:,2]>=cfg['height_search_m'][0])&(points[:,2]<=cfg['height_search_m'][1])
    indices=np.flatnonzero(mask);roi=points[indices]
    try:fit,debug=fit_frame(roi,settings,bootstrap=0)
    except (ValueError,np.linalg.LinAlgError) as error:
        return {'valid':False,'quality':'INVALID','reason_flags':['RAIL_FIT_FAILED'],'error':str(error)},{}
    reference={'valid':fit['numerical_quality_pass'],'quality':'GOOD' if fit['numerical_quality_pass'] else 'INVALID',
               'reason_flags':fit['quality_flags'],'roi_points':len(roi)}
    if 'candidate_plane' not in fit:return reference,{}
    reference.update({'plane':fit['candidate_plane'],'separation_m':fit['separation']['median_m'],
                      'separation_variation_m':fit['separation']['variation_m'],
                      'right_coefficients':fit['right_negative_x']['trajectory_coefficients_q_m_x0'],
                      'left_coefficients':fit['left_positive_x']['trajectory_coefficients_q_m_x0'],
                      'center_coefficients':((np.array(fit['right_negative_x']['trajectory_coefficients_q_m_x0'])+np.array(fit['left_positive_x']['trajectory_coefficients_q_m_x0']))/2).tolist(),
                      'right_support':fit['right_negative_x']['candidate_count'],'left_support':fit['left_positive_x']['candidate_count']})
    head=np.concatenate([debug['negative_idx'],debug['positive_idx']])
    return reference,{'head_indices':indices[head], 'right_head_indices':indices[debug['negative_idx']],
                      'left_head_indices':indices[debug['positive_idx']], 'roi_indices':indices}
