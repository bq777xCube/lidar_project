"""Небольшие компоненты занятости в полосах дальности, без DBSCAN и семантического классификатора."""
from itertools import product
import numpy as np

NEIGHBORS=[d for d in product([-1,0,1],repeat=3) if d!=(0,0,0)]


def candidates(frenet,xyz,original_indices,config,track_quality):
    cfg=config['candidate'];bands=cfg['range_bands_m'];candidates=[]
    for low,high,cell in zip(bands,bands[1:],cfg['cell_sizes_m']):
        selected=np.flatnonzero((frenet[:,0]>=low)&(frenet[:,0]<high))
        if not len(selected):continue
        coordinates=np.floor(frenet[selected]/np.array(cell)).astype(int)
        cells={}
        for row,index in zip(coordinates,selected):cells.setdefault(tuple(row),[]).append(int(index))
        unseen=set(cells)
        while unseen:
            seed=min(unseen);unseen.remove(seed);stack=[seed];members=[];occupied=0
            while stack:
                node=stack.pop();members.extend(cells[node]);occupied+=1
                for delta in NEIGHBORS:
                    neighbor=tuple(node[i]+delta[i] for i in range(3))
                    if neighbor in unseen:unseen.remove(neighbor);stack.append(neighbor)
            if len(members)<cfg['min_points'] or occupied<cfg['min_occupied_cells']:continue
            idx=np.array(members);p=frenet[idx];lo=p.min(axis=0);hi=p.max(axis=0)
            # Низкие точки сохраняются для диагностики и размеров, но фрагменты на уровне рельса
            # сами по себе не доказывают наличие предмета. Верхушки высотой 0.1 м остаются выше порога.
            above=int(np.count_nonzero(p[:,2]>cfg['min_above_rail_height_m']))
            if above<cfg['min_above_rail_points']:continue
            flags=['INSIDE_GAUGE','ABOVE_EXPECTED_TRACK_STRUCTURE','SPATIAL_SUPPORT']
            boundary=bool(np.any(abs(p[:,1])>config['clearance']['width_m']/2-cfg['boundary_distance_m']) or np.any(p[:,2]>config['clearance']['height_m']-cfg['boundary_distance_m']))
            if boundary:flags.append('BOUNDARY_CASE')
            if track_quality!='GOOD':flags.append('TRACK_CONFIDENCE_LOW')
            candidates.append({'nearest_distance_m':float(lo[0]),'nearest_euclidean_range_m':float(np.linalg.norm(xyz[idx],axis=1).min()),
                               'longitudinal_min_max_m':[float(lo[0]),float(hi[0])],
                               'lateral_min_max_m':[float(lo[1]),float(hi[1])],
                               'height_min_max_m':[float(lo[2]),float(hi[2])],
                               'estimated_extent_m':(hi-lo).tolist(),'point_count':len(idx),'occupied_cells':occupied,'above_rail_point_count':above,
                               'confidence':'SUPPORTED' if not boundary and track_quality=='GOOD' else 'CAUTION',
                               'reason_flags':flags,'original_point_indices':original_indices[idx].tolist()})
    return sorted(candidates,key=lambda c:c['nearest_distance_m'])
