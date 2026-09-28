"""Небольшие независимо проверяемые функции геометрии для ограниченной проверки положения. Координаты исходные X,Y,Z; продольная s=-Y. Соответствие REP-103 не заявляется."""
import numpy as np


def _finite_median(values):
    # Входы и невязки подгонки: конечные векторы float64; то же среднее центральных значений.
    n=len(values);middle=n//2
    if n%2:return np.partition(values,middle)[middle]
    part=np.partition(values,[middle-1,middle])
    return (part[middle-1]+part[middle])/2

def robust_linear_fit(design, values, iterations=15, scale_floor=.002):
    design=np.asarray(design,dtype=float)
    values=np.asarray(values,dtype=float)
    if len(values)<design.shape[1]+1 or not np.isfinite(design).all() or not np.isfinite(values).all():
        raise ValueError('Insufficient/nonfinite fit data')
    if np.linalg.matrix_rank(design)<design.shape[1]:
        raise ValueError('Rank-deficient geometry')
    coef=np.linalg.lstsq(design,values,rcond=None)[0]
    for _ in range(iterations):
        residual=values-design@coef
        scale=max(scale_floor,1.4826*_finite_median(np.abs(residual-_finite_median(residual))))
        weights=np.minimum(1,1.5*scale/np.maximum(np.abs(residual),1e-12))
        new=np.linalg.lstsq(design*np.sqrt(weights[:,None]),values*np.sqrt(weights),rcond=None)[0]
        if np.linalg.norm(new-coef)<1e-10:break
        coef=new
    return coef


def fit_plane(points):
    points=np.asarray(points,dtype=float)
    design=np.column_stack([points[:,:2],np.ones(len(points))])
    coef=robust_linear_fit(design,points[:,2])
    residual=point_plane_signed_distance(points,coef)
    return {'a':float(coef[0]),'b':float(coef[1]),'c':float(coef[2]),
            'normal_up':(np.array([-coef[0],-coef[1],1])/np.sqrt(1+sum(coef[:2]**2))).tolist(),
            'support_count':len(points),'residual_rms_m':float(np.sqrt(np.mean(residual**2))),
            'residual_median_abs_m':float(np.median(np.abs(residual))),
            'residual_p95_abs_m':float(np.quantile(np.abs(residual),.95)),
            **plane_pose(coef)}


def point_plane_signed_distance(points,coef):
    a,b,c=coef
    points=np.asarray(points,dtype=float)
    return (points[:,2]-a*points[:,0]-b*points[:,1]-c)/np.sqrt(a*a+b*b+1)


def plane_pose(coef):
    a,b,c=map(float,coef)
    return {'height_to_plane_m':abs(c)/np.sqrt(a*a+b*b+1),
            'lateral_slope_dz_dx':a,'longitudinal_slope_dz_ds':-b,
            'roll_slope_angle_deg':float(np.degrees(np.arctan(a))),
            'pitch_slope_angle_deg':float(np.degrees(np.arctan(-b))),
            'roll_magnitude_deg':float(abs(np.degrees(np.arctan(a)))),
            'pitch_magnitude_deg':float(abs(np.degrees(np.arctan(-b))))}


def trajectory(s,coef):
    """Формула: x(s)=q*(s-12.5)^2 + m*(s-12.5) + x0."""
    t=np.asarray(s)-12.5
    return coef[0]*t*t+coef[1]*t+coef[2]


def rail_separation(negative,positive,s):
    """Горизонтальное расстояние по нормали к средней траектории, не ширина колеи по внутренним граням."""
    s=np.asarray(s,dtype=float)
    left,right=trajectory(s,positive),trajectory(s,negative)
    slope=((2*positive[0]*(s-12.5)+positive[1])+(2*negative[0]*(s-12.5)+negative[1]))/2
    widths=(left-right)/np.sqrt(1+slope*slope)
    return {'median_m':float(np.median(widths)),'min_m':float(widths.min()),
            'max_m':float(widths.max()),'variation_m':float(np.ptp(widths)),
            'std_m':float(widths.std()),'delta_to_1_520_m':float(np.median(widths)-1.520),
            'definition':'horizontal head-trajectory separation normal to centerline; not inner-face gauge'}

# DIRECT-01: точное повторное использование чистого вызова. Исходная функция выше не изменена.
from contextvars import ContextVar
from contextlib import contextmanager
import time as _time
_refinement_context=ContextVar('refinement_frame',default=None)
_original_robust_linear_fit=robust_linear_fit
@contextmanager
def refinement_scope(enabled):
    state={'hits':0,'misses':0,'bypasses':0,'key_ms':0.,'compute_ms':0.,'entries':0,'limit':256}
    token=_refinement_context.set(({},state) if enabled else None)
    try:yield state
    finally:_refinement_context.reset(token)
def robust_linear_fit(design,values,iterations=15,scale_floor=.002):
    context=_refinement_context.get()
    if context is None:return _original_robust_linear_fit(design,values,iterations,scale_floor)
    cache,state=context
    # Отсутствие побочных эффектов доказано только для обычных числовых массивов и точных скалярных типов
    # ближнего ядра. Подклассы, объекты и необычные скалярные типы обходят кэш:
    # например, iterations=2.0 равен 2 как ключ словаря,
    # но исходный range() обязан вызвать TypeError. Преобразование массива и
    # предупреждения о неподдерживаемых типах должны выполняться исходной функцией.
    if (type(design) is not np.ndarray or type(values) is not np.ndarray
            or design.dtype.kind not in 'biuf' or values.dtype.kind not in 'biuf'
            or type(iterations) is not int or type(scale_floor) is not float):
        state['bypasses']+=1
        return _original_robust_linear_fit(design,values,iterations,scale_floor)
    start=_time.perf_counter()
    # Упорядоченное содержимое, dtype, форма, размещение и ВСЕ скалярные аргументы.
    # Чистая функция не принимает веса или начальную итерацию. Исключения
    # никогда не кэшируются. Свежие копии сохраняют независимую изменяемость результатов.
    a=np.asarray(design);b=np.asarray(values)
    key=(a.shape,a.dtype.str,a.strides,a.tobytes(),b.shape,b.dtype.str,b.strides,b.tobytes(),iterations,scale_floor)
    state['key_ms']+=(_time.perf_counter()-start)*1000
    if key in cache:state['hits']+=1;return cache[key].copy()
    state['misses']+=1;start=_time.perf_counter();out=_original_robust_linear_fit(design,values,iterations,scale_floor);state['compute_ms']+=(_time.perf_counter()-start)*1000
    if len(cache)<256:cache[key]=out.copy()
    state['entries']=len(cache);return out
