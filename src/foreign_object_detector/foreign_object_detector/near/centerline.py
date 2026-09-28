"""Ограниченное продолжение вдоль рельсов и геометрия Френе низкого порядка."""
from dataclasses import dataclass
import numpy as np
from .geometry_math import robust_linear_fit,trajectory


def polynomial_fit(x,y,degree):
    # Постоянный, линейный и квадратичный базисы заданы в метрах; до 150 м обусловленность достаточна для lstsq.
    design=np.column_stack([x**i for i in range(degree+1)])
    coef=robust_linear_fit(design,y,scale_floor=.01)
    return np.pad(coef,(0,3-len(coef)))


def evaluate(coef,u):return coef[0]+coef[1]*u+coef[2]*u*u

def derivative(coef,u):return coef[1]+2*coef[2]*u


def arc_length(coef,u):
    u=np.asarray(u,dtype=float);b,c=coef[1],coef[2]
    if abs(c)<1e-10:return u*np.sqrt(1+b*b)
    def integral(t):return .5*(t*np.sqrt(1+t*t)+np.arcsinh(t))
    return (integral(b+2*c*u)-integral(b))/(2*c)

@dataclass
class Centerline:
    lateral: np.ndarray
    height: np.ndarray
    min_u: float
    max_u: float
    separation_m: float
    quality: str
    diagnostics: dict

    def project(self,points):
        u=np.asarray(points[:,0],dtype=float).copy();y=points[:,1]
        for _ in range(8):
            f=evaluate(self.lateral,u);fp=derivative(self.lateral,u)
            grad=u-points[:,0]+(f-y)*fp
            denom=1+fp*fp+(f-y)*2*self.lateral[2]
            step=grad/np.maximum(denom,.1)
            u-=np.clip(step,-10,10)
        f=evaluate(self.lateral,u);fp=derivative(self.lateral,u)
        d=(-(points[:,0]-u)*fp+(y-f))/np.sqrt(1+fp*fp)
        h=points[:,2]-evaluate(self.height,u)
        valid=(u>=self.min_u)&(u<=self.max_u)&np.isfinite(u)
        return np.column_stack([arc_length(self.lateral,u),d,h]),u,valid

    def as_dict(self):
        return {'quality':self.quality,'lateral_coefficients':self.lateral.tolist(),'height_coefficients':self.height.tolist(),
                'valid_from_m':float(arc_length(self.lateral,self.min_u)),
                'centerline_valid_until_m':float(arc_length(self.lateral,self.max_u)),
                'normalized_forward_interval_m':[self.min_u,self.max_u], 'separation_m':self.separation_m,**self.diagnostics}


def _extend_rail(points,lat,height,side,sep,lo,hi,cfg):
    part=points[(points[:,0]>=lo)&(points[:,0]<hi)]
    if not len(part):return None,'NO_POINTS'
    pred=evaluate(lat,part[:,0]);slope=derivative(lat,part[:,0])
    offset=(part[:,1]-pred)/np.sqrt(1+slope*slope)
    hz=part[:,2]-evaluate(height,part[:,0])
    target=side*sep/2
    near=(abs(offset-target)<=cfg['search_radius_m'])&(abs(hz)<=cfg['height_search_m'])
    q=part[near];offs=offset[near];hs=hz[near]
    if len(q)<cfg['min_points_per_rail']:return None,'SPARSE_RAIL'
    # Самый высокий узкий гребень с локальной поддержкой, не квантиль широкой поверхности пола.
    width=.025 if lo<50 else .05
    bins=np.floor((offs-target)/width).astype(int)
    peaks=[]
    for bi in np.unique(bins):
        idx=np.flatnonzero(bins==bi)
        if len(idx)<2:continue
        top=float(np.quantile(hs[idx],.9))
        selected=idx[hs[idx]>=top-.02]
        peers=(abs(offs-(target+(bi+.5)*width))<.08)&(hs>=top-.02)&(hs<=top+.025)
        if peers.sum()<cfg['min_points_per_rail']:continue
        peaks.append((top-.1*abs(np.median(offs[peers])-target),peers))
    if not peaks:return None,'NO_SUPPORTED_CREST'
    _,selected=max(peaks,key=lambda v:v[0]);heads=q[selected]
    innovation=float(np.median(hs[selected]))
    if abs(innovation)>cfg['max_height_innovation_m']:return None,'HEIGHT_INNOVATION'
    return {'s':float(np.median(heads[:,0])),'l':float(np.median(heads[:,1])),
            'h':float(np.median(heads[:,2])),'count':len(heads),'until':float(heads[:,0].max()),
            'lateral_innovation':float(np.median(offs[selected])-target),'height_innovation':innovation},None


def extend(points,reference,frame,config):
    cfg=config['centerline'];rail=config['rail'];plane=reference['plane']
    seed_s=np.linspace(rail['near_min_m'],rail['near_max_m'],4)
    left=trajectory(seed_s,reference['left_coefficients']);right=trajectory(seed_s,reference['right_coefficients'])
    center=(left+right)/2
    z=-plane['b']*seed_s+plane['a']*center+plane['c']
    seeds=frame.transform(np.column_stack([seed_s,center,z]))
    samples=[list(row) for row in seeds]
    lat=polynomial_fit(seeds[:,0],seeds[:,1],cfg['model_degree'])
    # h=0 является целью нормализации; ошибочное фиксированное преобразование скрыто не исправляется.
    height=np.zeros(3)
    sep=reference['separation_m'];last_supported=float(seeds[-1,0]);start=float(np.ceil(last_supported/cfg['slice_length_m'])*cfg['slice_length_m'])
    if start-last_supported>1:start=last_supported
    traces=[];support=0;gaps=0;max_gap=0;last_support_start=last_supported
    for lo in np.arange(start,cfg['max_range_m'],cfg['slice_length_m']):
        hi=min(lo+cfg['slice_length_m'],cfg['max_range_m'])
        neg,err_n=_extend_rail(points,lat,height,-1,sep,lo,hi,cfg)
        pos,err_p=_extend_rail(points,lat,height,1,sep,lo,hi,cfg)
        reason=err_n or err_p
        if neg and pos:
            middle=(neg['s']+pos['s'])/2
            # Сравнение положений при общем s с использованием предсказанной касательной.
            slope=float(derivative(lat,middle))
            left=pos['l']+slope*(middle-pos['s']);right=neg['l']+slope*(middle-neg['s'])
            width=(left-right)/np.sqrt(1+slope*slope)
            if abs(width-sep)>cfg['max_separation_error_m']:reason='SEPARATION_INCONSISTENT'
            if abs(pos['h']-neg['h'])>cfg['max_pair_height_difference_m']:reason='PAIR_HEIGHT_INCONSISTENT'
            candidate=[middle,(left+right)/2,(pos['h']+neg['h'])/2]
            trial=np.array(samples+[candidate])
            new_lat=polynomial_fit(trial[:,0],trial[:,1],cfg['model_degree'])
            new_height=polynomial_fit(trial[:,0],trial[:,2],cfg['model_degree'])
            residual=trial[:,1]-evaluate(new_lat,trial[:,0])
            if np.max(abs(residual))>cfg['max_fit_residual_m']:reason='CENTERLINE_RESIDUAL'
            if not reason:
                samples.append(candidate);lat=new_lat;height=new_height
                support+=neg['count']+pos['count'];last_supported=min(neg['until'],pos['until'])
                max_gap=max(max_gap,lo-last_support_start);last_support_start=hi
                traces.append({'interval':[float(lo),float(hi)],'accepted':True,'separation_m':float(width),'left':pos,'right':neg})
                continue
        gaps+=1
        traces.append({'interval':[float(lo),float(hi)],'accepted':False,'reason':reason})
        if hi-last_supported>=cfg['max_gap_m']:break
    max_u=min(last_supported+cfg['max_extrapolation_m'],cfg['max_range_m'])
    samples=np.array(samples)
    rms=float(np.sqrt(np.mean((samples[:,1]-evaluate(lat,samples[:,0]))**2)))
    quality='GOOD' if len(samples)>4 and max_gap<=cfg['slice_length_m'] and rms<=cfg['max_fit_residual_m']/2 else 'DEGRADED'
    return Centerline(lat,height,float(seeds[0,0]),max_u,sep,quality,
                      {'support_samples':samples.tolist(),'extended_head_support':support,'extension_slices':traces,
                       'lateral_fit_rms_m':rms,'max_supported_gap_m':float(max_gap),
                       'extrapolation_m':max_u-last_supported,'last_supported_forward_m':last_supported,
                       'rejected_slices':gaps,'range_limited':max_u<cfg['max_range_m']})
