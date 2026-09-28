"""Общая подгонка гребня и головки POSE-01; канонические столбцы [s,l,z]. Это проверенный диагностический алгоритм. Словарь плоскости сохраняет исходные a,b,c для совместимости отчетов POSE-01."""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from .geometry_math import robust_linear_fit, fit_plane, trajectory, rail_separation, point_plane_signed_distance

@dataclass
class RailSettings:
    near_min_m: float = 5.
    near_max_m: float = 20.
    slice_m: float = .5
    ransac_trials: int = 1500
    separation_min_m: float = 1.35
    separation_max_m: float = 1.85
    max_plane_rms_m: float = .025
    @property
    def slice_count(self):
        return int(round((self.near_max_m-self.near_min_m)/self.slice_m))

def as_raw(points):
    return np.column_stack([points[:,1],-points[:,0],points[:,2]])

def fit_rail_plane(points):
    return fit_plane(as_raw(points))

def rail_plane_signed_distance(points,coef):
    return point_plane_signed_distance(as_raw(points),coef)

def _small_median(values):
    ordered=sorted(values);n=len(ordered);middle=n//2
    return ordered[middle] if n%2 else (ordered[middle-1]+ordered[middle])/2

def ridges(points, settings=None):
    """Те же поперечные профили с групповыми линейными процентилями по ячейкам. Сортированные группы заменяют многочисленные вызовы np.quantile. Ячейки, срезы, арифметика интерполяции, порядок итераций и выбор головки сохраняются точно."""
    settings = settings or RailSettings()
    s=points[:,0];x=points[:,1];z=points[:,2]
    edges=settings.near_min_m+np.arange(settings.slice_count+1)*settings.slice_m
    slices=np.searchsorted(edges,s,side='right')-1
    valid=(slices>=0)&(slices<settings.slice_count)
    ids=np.flatnonzero(valid)
    if not len(ids):return np.empty((0,5))
    bins=np.floor((x[ids]+3)/.025).astype(int)
    order=np.lexsort((z[ids],bins,slices[ids]));ids=ids[order];bins=bins[order];sl=slices[ids]
    starts=np.r_[0,np.flatnonzero((np.diff(bins)!=0)|(np.diff(sl)!=0))+1]
    ends=np.r_[starts[1:],len(ids)];counts=ends-starts
    keep=counts>=2;starts=starts[keep];ends=ends[keep];counts=counts[keep]
    virtual=(counts-1)*.9;low=np.floor(virtual).astype(int);fraction=virtual-low
    a=z[ids[starts+low]];b=z[ids[starts+np.ceil(virtual).astype(int)]];diff=b-a
    # Линейная интерполяция np.quantile меняет арифметику при fraction>=.5.
    top=a+diff*fraction;upper=fraction>=.5;top[upper]=b[upper]-diff[upper]*(1-fraction[upper])
    grid=[]
    for si in range(settings.slice_count):
        groups=np.flatnonzero(sl[starts]==si)
        profiles={int(bins[starts[g]]):(float(top[g]),ids[starts[g]:ends[g]]) for g in groups}
        for bi,(height,idx) in profiles.items():
            neighbors=[profiles[j][0] for j in range(bi-2,bi+3) if j in profiles]
            if height<max(neighbors)-.006:continue
            lower=[profiles[j][0] for j in range(bi-10,bi-4) if j in profiles]
            upper=[profiles[j][0] for j in range(bi+5,bi+11) if j in profiles]
            if len(lower)<2 or len(upper)<2:continue
            contrast=height-max(_small_median(lower),_small_median(upper))
            if .045<=contrast<=.4:
                head=idx[z[idx]>=height-.015]
                grid.append([float(np.median(s[head])),float(np.median(x[head])),float(np.median(z[head])),float(contrast),si])
    return np.array(grid,dtype=float).reshape(-1,5)


# Предварительный отбор групповой; дорогое уточнение сохраняет исходный порядок проб.
HYPOTHESIS_CHUNK_SIZE=128

@lru_cache(maxsize=64)
def _trial_pairs(count,trials):
    """Кэшируется только та же последовательность индексов с заданным seed, никогда наблюдения или подгонки."""
    rng=np.random.default_rng(20260926)
    pairs=np.asarray([rng.choice(count,2,replace=False) for _ in range(trials)])
    pairs.flags.writeable=False
    return pairs

def _screen_trials(ridge,design,t,trials,chunk_size=HYPOTHESIS_CHUNK_SIZE,trace=None):
    pairs=_trial_pairs(len(ridge),trials)
    order=np.argsort(ridge[:,4],kind='stable')
    starts=np.r_[0,np.flatnonzero(np.diff(ridge[order,4])!=0)+1]
    if trace is not None:trace.update({'pairs':pairs.tolist(),'reasons':['UNVISITED']*trials,'screened':[],'refined':[],'accepted':[]})
    for start in range(0,trials,chunk_size):
        ids=np.arange(start,min(start+chunk_size,trials));ij=pairs[ids]
        delta=t[ij[:,0]]-t[ij[:,1]];passes=abs(delta)>=5
        if trace is not None:
            for idx in ids[~passes]:trace['reasons'][int(idx)]='SEPARATION'
        ids=ids[passes];ij=ij[passes];delta=delta[passes]
        slope=(ridge[ij[:,0],1]-ridge[ij[:,1],1])/delta;passes=abs(slope)<=.15
        if trace is not None:
            for idx in ids[~passes]:trace['reasons'][int(idx)]='SLOPE'
        ids=ids[passes];ij=ij[passes];slope=slope[passes]
        if not len(ids):continue
        coefficients=np.column_stack([np.zeros(len(ids)),slope,ridge[ij[:,0],1]-slope*t[ij[:,0]]])
        # Независимые произведения матрицы на вектор, без перестановки сумм в матричном произведении.
        residuals=ridge[None,:,1]-np.matmul(design,coefficients[:,:,None])[:,:,0]
        masks=abs(residuals)<.07
        covered=np.logical_or.reduceat(masks[:,order],starts,axis=1).sum(axis=1)
        if trace is not None:
            for idx in ids[covered<12]:trace['reasons'][int(idx)]='COVERAGE'
        for index in np.flatnonzero(covered>=12):
            trial_id=int(ids[index]);coef=coefficients[index];mask=masks[index]
            if trace is not None:
                trace['reasons'][trial_id]='SCREENED'
                trace['screened'].append([trial_id,coef.tolist(),mask.tobytes().hex()])
            yield trial_id,coef,mask


def candidate_tracks(ridge, settings=None, *, trace=None, chunk_size=HYPOTHESIS_CHUNK_SIZE):
    settings = settings or RailSettings()
    """Deterministic RANSAC lines followed by small quadratic refinement."""
    if len(ridge)<10:return []
    t=ridge[:,0]-12.5
    design=np.column_stack([t*t,t,np.ones(len(t))])
    models=[];evaluated_masks=set()
    for trial_id,coef,mask in _screen_trials(ridge,design,t,settings.ransac_trials,chunk_size,trace):
        # Одинаковая начальная поддержка дает одинаковое детерминированное уточнение.
        # Избегаем повторного решения, сохраняя исходные пробы и первый результат.
        signature=mask.tobytes()
        if signature in evaluated_masks:
            if trace is not None:trace['reasons'][trial_id]='DUPLICATE_MASK'
            continue
        evaluated_masks.add(signature)
        if trace is not None:trace['refined'].append(trial_id)
        for repeat in range(3):
            coef=robust_linear_fit(design[mask],ridge[mask,1],scale_floor=.01)
            mask=abs(ridge[:,1]-design@coef)<.065
            if mask.sum()<6:break
        if mask.sum()<6:continue
        span=float(np.ptp(ridge[mask,0])); coverage=len(np.unique(ridge[mask,4]))
        if span<8 or coverage<14 or abs(coef[0])>.008:continue
        if any(np.max(np.abs(design[[0,-1]]@(coef-c['coef'])))<.08 for c in models):continue
        residual=ridge[mask,1]-design[mask]@coef
        if trace is not None:trace['accepted'].append(trial_id)
        models.append({'coef':coef,'mask':mask,'span':span,'coverage':coverage,
                       'lateral_rms':float(np.sqrt(np.mean(residual**2))),
                       'score':coverage+min(span,15)+10*float(np.median(ridge[mask,3]))})
    return sorted(models,key=lambda m:m['score'],reverse=True)[:12]


def choose_pair(ridge,models, settings=None):
    settings = settings or RailSettings()
    pairs=[];s=np.linspace(settings.near_min_m,settings.near_max_m,31)
    for i,first in enumerate(models):
        for second in models[i+1:]:
            neg,pos=sorted([first,second],key=lambda model:model['coef'][2])
            sep=rail_separation(neg['coef'],pos['coef'],s)
            if not 1.2<sep['median_m']<2.0 or sep['variation_m']>.22:continue
            dz=abs(np.median(ridge[neg['mask'],2])-np.median(ridge[pos['mask'],2]))
            if dz>.25:continue
            center=(neg['coef'][2]+pos['coef'][2])/2
            score=neg['score']+pos['score']-8*abs(sep['median_m']-1.52)-8*sep['variation_m']-4*abs(center)
            pairs.append((score,neg,pos))
    return sorted(pairs,key=lambda row:row[0],reverse=True)


def head_points(points,model, settings=None):
    settings = settings or RailSettings()
    """Select the upper 15 mm near the fitted ridge in each 0.5 m slice."""
    s=points[:,0]
    near=abs(points[:,1]-trajectory(s,model['coef']))<.055
    chosen=[];summaries=[]
    for si in range(settings.slice_count):
        idx=np.flatnonzero(near&(s>=settings.near_min_m+settings.slice_m*si)&(s<settings.near_min_m+settings.slice_m*(si+1)))
        if len(idx)<4:continue
        top=np.quantile(points[idx,2],.9)
        idx=idx[(points[idx,2]>=top-.015)&(points[idx,2]<=top+.025)]
        if len(idx)<2:continue
        chosen.extend(idx.tolist());summaries.append(np.median(points[idx],axis=0))
    return np.array(chosen,dtype=int),np.array(summaries).reshape(-1,3)


def fit_frame(points, settings=None, bootstrap=200):
    settings = settings or RailSettings()
    ridge=ridges(points,settings);models=candidate_tracks(ridge,settings);pairs=choose_pair(ridge,models,settings)
    result={'ridge_candidate_count':len(ridge),'trajectory_hypothesis_count':len(models),
            'pair_hypothesis_count':len(pairs),'quality_flags':[],
            'visual_verification_status':'pending','status':'POSE_UNRELIABLE','plane':None,
            'numerical_quality_pass':False}
    if not pairs:
        result['quality_flags']=['NO_SUPPORTED_RAIL_PAIR'];return result,{'ridge':ridge}
    _,negative,positive=pairs[0]
    idxneg,repneg=head_points(points,negative,settings);idxpos,reppos=head_points(points,positive,settings)
    debug={'ridge':ridge,'negative_idx':idxneg,'positive_idx':idxpos,'repneg':repneg,'reppos':reppos}
    reps=np.vstack([repneg,reppos])
    if len(reps)<6:
        result['quality_flags']=['INSUFFICIENT_HEAD_SUPPORT'];return result,debug
    # Равный вес рельсов и продольных срезов устраняет смещение из-за плотности вблизи.
    initial_plane=fit_rail_plane(reps)
    # Измеренный отказ: редкие срезы могут содержать шейку вместо головки рельса.
    # Отбрасываем несогласованные срезы без изменения ROI и получения новых кадров.
    initial_coef=[initial_plane[k] for k in ['a','b','c']]
    original_counts=[len(idxneg),len(idxpos)]
    original_slices=[len(repneg),len(reppos)]
    kept=[]
    for indices,rep in [(idxneg,repneg),(idxpos,reppos)]:
        good=abs(rail_plane_signed_distance(rep,initial_coef))<=.030
        good_slices=np.floor((rep[good,0]-settings.near_min_m)/settings.slice_m).astype(int)
        point_slices=np.floor((points[indices,0]-settings.near_min_m)/settings.slice_m).astype(int)
        indices=indices[np.isin(point_slices,good_slices)]
        # Удаляем отдельные отражения кромки и шейки, слишком далекие от той же предварительной плоскости головки.
        indices=indices[abs(rail_plane_signed_distance(points[indices],initial_coef))<=.035]
        representatives=[]
        for si in np.unique(np.floor((points[indices,0]-settings.near_min_m)/settings.slice_m).astype(int)):
            subset=indices[np.floor((points[indices,0]-settings.near_min_m)/settings.slice_m).astype(int)==si]
            if len(subset)>=2:representatives.append(np.median(points[subset],axis=0))
        kept.append((indices,np.asarray(representatives).reshape(-1,3)))
    (idxneg,repneg),(idxpos,reppos)=kept
    reps=np.vstack([repneg,reppos])
    if len(reps)<6:
        result['quality_flags']=['INSUFFICIENT_ROBUST_HEAD_SUPPORT'];return result,debug
    plane=fit_rail_plane(reps)
    coef=[plane[k] for k in ['a','b','c']]
    raw_residual=rail_plane_signed_distance(points[np.concatenate([idxneg,idxpos])],coef)
    plane.update({'rail_head_point_count':len(raw_residual),
                  'head_point_residual_rms_m':float(np.sqrt(np.mean(raw_residual**2))),
                  'head_point_residual_median_abs_m':float(np.median(abs(raw_residual))),
                  'head_point_residual_p95_abs_m':float(np.quantile(abs(raw_residual),.95)),
                  'initial_slice_residual_rms_m':initial_plane['residual_rms_m'],
                  'rejected_head_candidate_points':sum(original_counts)-len(raw_residual),
                  'rejected_slices':sum(original_slices)-len(reps)})
    if bootstrap:
        # Продольный блочный bootstrap оценивает условную неопределенность подгонки,
        # но не систематическую ошибку калибровки или распознавания рельсов.
        blocks=np.floor((reps[:,0]-5)/1.5).astype(int)
        unique=np.unique(blocks);rng=np.random.default_rng(20260926)
        heights=[];rolls=[];pitches=[]
        for _ in range(bootstrap):
            chosen=rng.choice(unique,len(unique),replace=True)
            sample=np.concatenate([reps[blocks==block] for block in chosen])
            try:trial=fit_rail_plane(sample)
            except ValueError:continue
            heights.append(trial['height_to_plane_m']);rolls.append(trial['roll_slope_angle_deg']);pitches.append(trial['pitch_slope_angle_deg'])
        plane['uncertainty']={'method':'200 deterministic 1.5 m longitudinal block bootstrap resamples of slice representatives',
                              'height_conditional_95_interval_m':np.quantile(heights,[.025,.975]).tolist(),
                              'roll_conditional_95_interval_deg':np.quantile(rolls,[.025,.975]).tolist(),
                              'pitch_conditional_95_interval_deg':np.quantile(pitches,[.025,.975]).tolist(),
                              'excludes':'head selection, calibration, correlated measurement bias, track nonplanarity; not total accuracy'}
    debug.update({'negative_idx':idxneg,'positive_idx':idxpos,'repneg':repneg,'reppos':reppos})
    s=np.linspace(settings.near_min_m,settings.near_max_m,31)
    separation=rail_separation(negative['coef'],positive['coef'],s)
    for label,model,indices,rep in [('right_negative_x',negative,idxneg,repneg),('left_positive_x',positive,idxpos,reppos)]:
        result[label]={'trajectory_coefficients_q_m_x0':model['coef'].tolist(),
                       'candidate_count':len(indices),'slice_support':len(rep),'ridge_slice_support':model['coverage'],
                       'longitudinal_span_m':float(np.ptp(rep[:,0])) if len(rep) else 0,
                       'ridge_lateral_rms_m':model['lateral_rms']}
    result['separation']=separation
    result['candidate_plane']=plane
    result['raw_head_candidate_counts']={'right_negative_x':original_counts[0],'left_positive_x':original_counts[1]}
    if min(len(idxneg),len(idxpos))<40:result['quality_flags'].append('LOW_POINT_SUPPORT')
    if min(len(repneg),len(reppos))<18:result['quality_flags'].append('LOW_SLICE_SUPPORT')
    if min(np.ptp(repneg[:,0]),np.ptp(reppos[:,0]))<10:result['quality_flags'].append('SHORT_SPAN')
    if not settings.separation_min_m<=separation['median_m']<=settings.separation_max_m:result['quality_flags'].append('IMPLAUSIBLE_SEPARATION')
    if separation['variation_m']>.12:result['quality_flags'].append('NONPARALLEL_RAILS')
    if plane['residual_rms_m']>settings.max_plane_rms_m or plane['residual_p95_abs_m']>.04:result['quality_flags'].append('HIGH_PLANE_RESIDUAL')
    if max(negative['lateral_rms'],positive['lateral_rms'])>.045:result['quality_flags'].append('HIGH_TRAJECTORY_RESIDUAL')
    if plane['rejected_head_candidate_points']/max(1,sum(original_counts))>.2:result['quality_flags'].append('EXCESSIVE_HEAD_REJECTION')
    if bootstrap and np.ptp(plane['uncertainty']['height_conditional_95_interval_m'])>.06:result['quality_flags'].append('HIGH_HEIGHT_UNCERTAINTY')
    result['numerical_quality_pass']=not result['quality_flags']
    return result,debug
