"""Точные переходные ветви текущего кадра: дешевые маски и отложенный расчет дальности."""
import time
import numpy as np
from .handoff_reference import process as reference_process, _result
from .beam_selector import offbeam, screen


def process(normal,internal,extension_info,config,far,b1,b2,debug=False):
    # Сохраняем необязательное историческое поведение; в проверенной конфигурации A выключен.
    if extension_info and extension_info.get('available'):
        return reference_process(normal,internal,extension_info,config,far,b1,b2,debug)
    start=time.perf_counter();empty=np.empty((0,3));branches={}
    def emit(name,ids=np.empty(0,dtype=int),q=empty,r=np.empty(0),kind='arc'):
        branches[name]=_result(name,ids,q,r,'horizontal estimated-centerline arc length from the local rail-frame origin' if kind=='arc' else 'minimum positive N1 nominal-forward coordinate of a current accepted point; Euclidean diagnostic uses the same selected point',debug)
    if b1:emit('SYNTHETIC_MEASURED');emit('SYNTHETIC_X1_EXTRAPOLATED')
    if b2:emit('SYNTHETIC_NOMINAL_BRIDGE',kind='N1')
    if normal['centerline']['quality']!='GOOD' or 'frenet' not in internal:
        return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':False}
    center=normal['centerline'];measured=float(center['last_supported_forward_m']);minimum=float(center['normalized_forward_interval_m'][0]);effective=float(center['normalized_forward_interval_m'][1])
    if not np.isfinite([minimum,measured,effective]).all():
        return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':False}
    p=internal['canonical'];accepted={k:[] for k in branches};qs={k:[] for k in branches};rs={k:[] for k in branches};offcount=0
    # Покомпонентные предикаты равны прежним сверткам по осям. Не требуется временная матрица N x 3
    # для допустимости, преобразование типа или норма точек, согласованных с лучами.
    # Работа ограничена; каждая точка ближе 60 м участвует в диагностическом подсчете.
    for begin in range(0,len(p),8192):
        block=p[begin:begin+8192]
        codes=screen(block,far)
        if codes is None:
            x,y,z=block.T
            keep=(x<60)&np.isfinite(x)&np.isfinite(y)&np.isfinite(z)&((x!=0)|(y!=0)|(z!=0))
            local=np.flatnonzero(keep)
            if not len(local):continue
            q=block[local].astype(np.float64,copy=False)
            e=np.degrees(np.arctan2(q[:,2],np.hypot(q[:,0],q[:,1])))
            off=offbeam(e,far.beams);local=local[off];q=q[off]
        else:
            ambiguous=np.flatnonzero(codes==2)
            if len(ambiguous):
                q=block[ambiguous]
                e=np.degrees(np.arctan2(q[:,2],np.hypot(q[:,0],q[:,1])))
                codes[ambiguous]=offbeam(e,far.beams)
            local=np.flatnonzero(codes==1);q=block[local]
        if not len(local):continue
        # Та же операция нормы float64 на тех же оставшихся строках.
        ranges=np.linalg.norm(q,axis=1);within=ranges<=180.
        ix=local[within]+begin;q=q[within];ranges=ranges[within];offcount+=len(ix)
        if not len(ix):continue
        ids=internal['source_indices'][ix];u=internal['projection_parameter'][ix]
        if b1:
            f=internal['frenet'][ix]
            mask=internal['valid_track'][ix]&(u>=minimum)&(u<=measured)&internal['retained'][ix]&(abs(f[:,1])<=.95)&(f[:,2]>=.06)&(f[:,2]<=2.90)
            accepted['SYNTHETIC_MEASURED'].append(ids[mask]);qs['SYNTHETIC_MEASURED'].append(f[mask]);rs['SYNTHETIC_MEASURED'].append(ranges[mask])
        if b2:
            n=(q-far.origin)@far.rotation.T
            mask=np.isfinite(u)&(u>effective)&(u>=minimum)&(abs(n[:,1])<=.95)&(n[:,2]>=.06)&(n[:,2]<=2.90)
            accepted['SYNTHETIC_NOMINAL_BRIDGE'].append(ids[mask]);qs['SYNTHETIC_NOMINAL_BRIDGE'].append(n[mask]);rs['SYNTHETIC_NOMINAL_BRIDGE'].append(ranges[mask])
    for name in branches:
        if accepted[name]:emit(name,np.concatenate(accepted[name]),np.concatenate(qs[name]),np.concatenate(rs[name]),'N1' if name=='SYNTHETIC_NOMINAL_BRIDGE' else 'arc')
    return {'branches':branches,'processing_ms':(time.perf_counter()-start)*1000,'available':True,'offbeam_below60_points':offcount,'effective_endpoint_normalized_u_m':effective,'measured_endpoint_normalized_u_m':measured,'boundary_definition':'existing normalized centerline projection parameter > effective endpoint; N1 supplies bridge clearance, not a new track'}
