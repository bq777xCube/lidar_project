"""Подтвержденные ближние результаты; расстояния в метрах горизонтальной дуги осевой линии."""
def map_output(normal,observations,sparse):
    normal_confirmed=bool(normal['obstacle_detected'])
    selected=set(sparse['confirmed_track_ids']['S2'])
    obs_ids={a['observation_id'] for a in sparse['assignments'] if a['track_id'] in selected}
    distances=[c['nearest_distance_m'] for c in normal['candidates']] if normal_confirmed else []
    distances.extend(o['minimum'][0] for o in observations if o['observation_id'] in obs_ids)
    confirmed=normal_confirmed or bool(selected)
    quality=normal['centerline']['quality']
    state='OBSTACLE_NORMAL' if normal_confirmed else 'OBSTACLE_SPARSE' if selected else 'TRACK_UNRELIABLE' if quality!='GOOD' else 'CLEAR'
    return {'obstacle':confirmed,'distance_m':float(min(distances)) if confirmed else -1.0,'state':state,'normal_confirmed':normal_confirmed,'sparse_confirmed':bool(selected),'track_quality':quality,'measured_horizon_m':normal['centerline'].get('last_supported_forward_m',-1.0),'distance_definition':normal['distance_definition']}
