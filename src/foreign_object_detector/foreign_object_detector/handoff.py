"""Точная геометрия запросов с необязательным аудитом всего облака. В рабочем режиме отсутствует только глобальный счетчик (None); debug включает полный аудит. audit=False сохраняет состав точек без общего подсчета. Геометрия всей сцены вычисляется до этой функции."""
import time
import numpy as np
from .handoff_audit import process as audit_process
from .handoff_reference import _result
from .beam_selector import screen, offbeam


def process(normal, internal, extension_info, config, far, b1, b2, debug=False, *, audit=None):
    if audit is None:
        audit = debug
    if audit:
        return audit_process(normal, internal, extension_info, config, far, b1, b2, debug)
    start = time.perf_counter()
    def fallback():
        out = audit_process(normal, internal, extension_info, config, far, b1, b2, debug)
        if 'offbeam_below60_points' in out:
            out['offbeam_below60_points'] = None
        out['processing_ms'] = (time.perf_counter()-start)*1000
        return out
    # Сохраняем необязательное историческое поведение A на полном входе.
    if extension_info and extension_info.get('available'):
        return fallback()
    empty = np.empty((0, 3)); branches = {}
    def emit(name, ids=np.empty(0, dtype=int), coords=empty, ranges=np.empty(0)):
        definition = ('minimum positive N1 nominal-forward coordinate of a current accepted point; Euclidean diagnostic uses the same selected point'
                      if name == 'SYNTHETIC_NOMINAL_BRIDGE' else
                      'horizontal estimated-centerline arc length from the local rail-frame origin')
        branches[name] = _result(name, ids, coords, ranges, definition, debug)
    if b1:
        emit('SYNTHETIC_MEASURED'); emit('SYNTHETIC_X1_EXTRAPOLATED')
    if b2:
        emit('SYNTHETIC_NOMINAL_BRIDGE')
    if normal['centerline']['quality'] != 'GOOD' or 'frenet' not in internal:
        return {'branches':branches, 'processing_ms':(time.perf_counter()-start)*1000, 'available':False}
    center = normal['centerline']
    measured = float(center['last_supported_forward_m'])
    minimum, effective = map(float, center['normalized_forward_interval_m'])
    if not np.isfinite([minimum, measured, effective]).all():
        return {'branches':branches, 'processing_ms':(time.perf_counter()-start)*1000, 'available':False}
    p = internal['canonical']; u = internal['projection_parameter']
    one = np.empty(0, dtype=int); two = one
    if b1:
        one = np.flatnonzero(internal['retained'] & internal['valid_track'] & (u >= minimum) & (u <= measured) & (p[:,0] < 60))
        f = internal['frenet'][one]
        one = one[(abs(f[:,1]) <= .95) & (f[:,2] >= .06) & (f[:,2] <= 2.90)]
    if b2:
        two = np.flatnonzero(np.isfinite(u) & (u > effective) & (u >= minimum) & (p[:,0] < 60))
        q = p[two].astype(np.float64, copy=False)
        n = (q-far.origin) @ far.rotation.T
        # Численный резервный путь N1 не расширяет критерий приема.
        # Сохраняем прежнюю защиту компактного пути;
        # на границе используется исходная групповая матрица.
        if np.any((abs(abs(n[:,1])-.95) < 1e-10) | (abs(n[:,2]-.06) < 1e-10) | (abs(n[:,2]-2.90) < 1e-10)):
            return fallback()
        two = two[(abs(n[:,1]) <= .95) & (n[:,2] >= .06) & (n[:,2] <= 2.90)]
    union = np.union1d(one, two)
    pieces=[]
    for begin in range(0, len(union), 8192):
        ix=union[begin:begin+8192]; q=p[ix].astype(np.float64, copy=False)
        codes=screen(q, far)
        if codes is None:
            valid=np.isfinite(q).all(1) & np.any(q != 0, axis=1)
            ix=ix[valid];q=q[valid]
            e=np.degrees(np.arctan2(q[:,2], np.hypot(q[:,0], q[:,1])))
            keep=offbeam(e, far.beams)
        else:
            ambiguous=np.flatnonzero(codes == 2)
            if len(ambiguous):
                a=q[ambiguous];e=np.degrees(np.arctan2(a[:,2], np.hypot(a[:,0], a[:,1])))
                codes[ambiguous]=offbeam(e, far.beams)
            keep=codes == 1
        ix=ix[keep];q=q[keep]
        ranges=np.linalg.norm(q, axis=1)
        pieces.append(ix[ranges <= 180.])
    accepted=np.concatenate(pieces) if pieces else np.empty(0, dtype=int)
    for name, candidates in [('SYNTHETIC_MEASURED',one), ('SYNTHETIC_NOMINAL_BRIDGE',two)]:
        if name not in branches:
            continue
        ix=np.intersect1d(accepted,candidates,assume_unique=True)
        q=p[ix].astype(np.float64,copy=False)
        if name == 'SYNTHETIC_NOMINAL_BRIDGE' and len(ix):
            # BLAS может округлять одну строку иначе при изменении размера группы.
            # Восстанавливаем исходные блоки по 8192 строки лишь при наличии свидетельств B2.
            # Вызовы сохраняют полный состав точек и координаты,
            # не запрашивая и не восстанавливая общий счетчик.
            rows=[]; coords=[]; ranges=[]
            for block_id in np.unique(ix // 8192):
                sl=slice(int(block_id)*8192, min((int(block_id)+1)*8192,len(p)))
                subset={k:internal[k][sl] for k in ['canonical','source_indices','projection_parameter','frenet','valid_track','retained']}
                exact=audit_process(normal,subset,None,config,far,False,True,True)['branches'][name]
                rows.extend(exact['source_indices']);coords.extend(exact['coordinates'])
                # Сохраняем выражение дальности и соответствие исходным индексам, включая
                # повторяющиеся индексы: восстановление идет по позициям принятых строк.
                original=np.arange(sl.start,sl.stop)
                selected=original[np.isin(internal['source_indices'][sl],exact['source_indices'])]
                ranges.extend(np.linalg.norm(p[selected].astype(np.float64,copy=False),axis=1).tolist())
            emit(name,np.asarray(rows,dtype=int),np.asarray(coords).reshape(-1,3),np.asarray(ranges))
        else:
            emit(name,internal['source_indices'][ix],internal['frenet'][ix] if name == 'SYNTHETIC_MEASURED' else np.empty((0,3)),np.linalg.norm(q,axis=1))
    return {'branches':branches, 'processing_ms':(time.perf_counter()-start)*1000,
            'available':True, 'offbeam_below60_points':None,
            'effective_endpoint_normalized_u_m':effective,
            'measured_endpoint_normalized_u_m':measured,
            'boundary_definition':'existing normalized centerline projection parameter > effective endpoint; N1 supplies bridge clearance, not a new track'}
