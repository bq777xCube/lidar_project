"""Общий разреженный БЛИЖНИЙ канал. Без меток, bag, целевых объектов или дальних входов."""
import time
import numpy as np
from .near.candidate import NEIGHBORS
PARAMETERS={'nominal_scan_s':.1,'max_delta_d_m':.20,'max_delta_h_m':.20,'approach_per_scan_min_m':-.5,'approach_per_scan_max_m':3.,'max_approach_innovation_m':1.,'history_positions':5,'max_missing_frames':1,'rules':['S0','S1','S2','S3'],'emit_on_missing':False,'require_above_existing_height_evidence':True}

def extract(result,debug,config,frame,timestamp):
 start=time.perf_counter();obs=[];stats={'no_above_rail_evidence':0,'not_count_sparse':0,'excluded_normal_points':0}
 if result['centerline']['quality']!='GOOD' or 'frenet' not in debug:return obs,stats,(time.perf_counter()-start)*1000
 center=result['centerline'];eligible=debug['retained'].copy();eligible&=(debug['projection_parameter']>=center['normalized_forward_interval_m'][0])&(debug['projection_parameter']<=center['last_supported_forward_m'])
 normal_ids=[i for c in result['candidates'] for i in c['original_point_indices']]
 if normal_ids:
  normal=np.isin(debug['source_indices'],normal_ids);stats['excluded_normal_points']=int((eligible&normal).sum());eligible&=~normal
 p=debug['frenet'][eligible];xyz=debug['xyz'][eligible];ids=debug['source_indices'][eligible];cfg=config['candidate']
 for lo,hi,cell in zip(cfg['range_bands_m'],cfg['range_bands_m'][1:],cfg['cell_sizes_m']):
  selected=np.flatnonzero((p[:,0]>=lo)&(p[:,0]<hi));cells={}
  for row,i in zip(np.floor(p[selected]/cell).astype(int),selected):cells.setdefault(tuple(row),[]).append(int(i))
  unseen=set(cells)
  while unseen:
   seed=min(unseen);unseen.remove(seed);stack=[seed];members=[];occupied=0
   while stack:
    node=stack.pop();members.extend(cells[node]);occupied+=1
    for delta in NEIGHBORS:
     nxt=tuple(node[k]+delta[k] for k in range(3))
     if nxt in unseen:unseen.remove(nxt);stack.append(nxt)
   if len(members)>=cfg['min_points'] and occupied>=cfg['min_occupied_cells']:stats['not_count_sparse']+=1;continue
   q=p[members];above=int((q[:,2]>cfg['min_above_rail_height_m']).sum())
   if above==0:stats['no_above_rail_evidence']+=1;continue
   boundary=np.minimum.reduce([config['clearance']['width_m']/2-abs(q[:,1]),config['clearance']['height_m']-q[:,2],q[:,2]-config['structure_mask']['below_rail_ceiling_m']])
   obs.append({'observation_id':len(obs),'frame':int(frame),'timestamp':float(timestamp),'point_count':len(members),'occupied_voxels':occupied,'above_rail_points':above,'centroid':q.mean(axis=0).tolist(),'minimum':q.min(axis=0).tolist(),'maximum':q.max(axis=0).tolist(),'nearest_euclidean_m':float(np.linalg.norm(xyz[members],axis=1).min()),'minimum_gauge_boundary_distance_m':float(boundary.min()),'original_point_indices':ids[members].tolist(),'mask_state':'INSIDE_MEASURED_GOOD_SURVIVES_RAIL_AND_BELOW','status':'SPARSE_OBSERVATION'})
 return obs,stats,(time.perf_counter()-start)*1000

def normal_regions(result,frame,ts):
 out=[]
 for i,c in enumerate(result['candidates']):
  bounds=np.array([c['longitudinal_min_max_m'],c['lateral_min_max_m'],c['height_min_max_m']]);out.append({'observation_id':i,'frame':frame,'timestamp':ts,'centroid':bounds.mean(axis=1).tolist(),'point_count':c['point_count']})
 return out

def link_cost(history,observation,p=PARAMETERS):
 last=history[-1];gap=observation['frame']-last['frame'];dt=(observation['timestamp']-last['timestamp'])/p['nominal_scan_s']
 if not 1<=gap<=p['max_missing_frames']+1 or dt<=0:return None,'GAP'
 old=np.array(last['centroid']);new=np.array(observation['centroid']);delta=old-new;approach=delta[0]/dt
 if abs(delta[1])>p['max_delta_d_m'] or abs(delta[2])>p['max_delta_h_m']:return None,'DH_GATE'
 if not p['approach_per_scan_min_m']<=approach<=p['approach_per_scan_max_m']:return None,'S_GATE'
 recent=[h for h in history if h['frame']>=observation['frame']-4];xy=np.array([h['centroid'][1:] for h in recent]+[new[1:]])
 if np.ptp(xy[:,0])>p['max_delta_d_m'] or np.ptp(xy[:,1])>p['max_delta_h_m']:return None,'DH_HISTORY'
 velocity=None
 if len(recent)>=2:
  rates=[(a['centroid'][0]-b['centroid'][0])/((b['timestamp']-a['timestamp'])/p['nominal_scan_s']) for a,b in zip(recent,recent[1:])];velocity=float(np.median(rates))
  if abs(approach-velocity)>p['max_approach_innovation_m']:return None,'S_INNOVATION'
 score=abs(delta[1])/p['max_delta_d_m']+abs(delta[2])/p['max_delta_h_m']+abs(approach-(velocity if velocity is not None else 0))/p['approach_per_scan_max_m']
 return float(score),'OK'

def rule_states(history,current_frame):
 states={'S0':False}
 for rule,window,minimum in [('S1',3,2),('S2',5,3),('S3',5,2)]:
  h=[o for o in history if current_frame-window+1<=o['frame']<=current_frame];gaps=h[-1]['frame']-h[0]['frame']+1-len(h) if h else 0
  states[rule]=bool(h and h[-1]['frame']==current_frame and len(h)>=minimum and gaps<=1 and (rule!='S3' or sum(o['point_count'] for o in h)>=3))
 return states

class SparseTracker:
 def __init__(self,parameters=None):self.p=dict(PARAMETERS if parameters is None else parameters);self.tracks={};self.next_id=0;self.last_frame=None;self.last_ts=None
 def step(self,frame,ts,observations,normal_candidates,normal_obstacle,good=True):
  started=time.perf_counter()
  if self.last_frame is not None:assert frame==self.last_frame+1 and ts>self.last_ts,'Causal consecutive input required'
  self.last_frame=frame;self.last_ts=ts
  for tid in list(self.tracks):
   track=self.tracks[tid];track['history']=[h for h in track['history'] if h['frame']>=frame-4]
   if not track['history'] or frame-track['history'][-1]['frame']>2:del self.tracks[tid]
  transitions=[];reject={};normal_links=[]
  if good:
   for tid,tr in self.tracks.items():
    for n in normal_candidates:
     cost,why=link_cost(tr['history'],n,self.p)
     if cost is not None:normal_links.append((cost,tid,n['observation_id']))
  used_normal=set()
  for cost,tid,nid in sorted(normal_links):
   if tid not in self.tracks or nid in used_normal:continue
   transitions.append({'track_id':tid,'normal_candidate_id':nid,'status':'NORMAL_CONFIRMED'});used_normal.add(nid);del self.tracks[tid]
  links=[]
  if good:
   for tid,tr in self.tracks.items():
    for o in observations:
     cost,why=link_cost(tr['history'],o,self.p)
     if cost is not None:links.append((cost,tid,o['observation_id']))
     else:reject[why]=reject.get(why,0)+1
  assignment={};used_tracks=set()
  for cost,tid,oid in sorted(links):
   if tid in used_tracks or oid in assignment:continue
   assignment[oid]=(tid,cost);used_tracks.add(tid)
  association_ms=(time.perf_counter()-started)*1000;updated=time.perf_counter();emitted=[]
  for o in observations if good else []:
   oid=o['observation_id'];existing=oid in assignment
   if existing:tid,cost=assignment[oid];tr=self.tracks[tid]
   else:tid=self.next_id;self.next_id+=1;cost=None;tr={'history':[],'first_confirmed':{},'birth_frame':frame};self.tracks[tid]=tr
   before=[h['frame'] for h in tr['history']];tr['history'].append({k:o[k] for k in ['frame','timestamp','centroid','point_count','observation_id']})
   emitted.append({'observation_id':oid,'track_id':tid,'matched_prior':existing,'prior_frames':before,'association_cost':cost,'history_frames':[h['frame'] for h in tr['history']],'history_points':sum(h['point_count'] for h in tr['history']),'birth_frame':tr['birth_frame']})
  update_ms=(time.perf_counter()-updated)*1000;confirmed_start=time.perf_counter();flags={r:[] for r in self.p['rules']};new={r:[] for r in self.p['rules']}
  for e in emitted:
   tr=self.tracks[e['track_id']];states=rule_states(tr['history'],frame);e['rules']=states
   for rule,passes in states.items():
    if passes:
     flags[rule].append(e['track_id'])
     if rule not in tr['first_confirmed']:tr['first_confirmed'][rule]={'frame':frame,'timestamp':ts};new[rule].append(e['track_id'])
   e['first_confirmed']=dict(tr['first_confirmed'])
  confirmation_ms=(time.perf_counter()-confirmed_start)*1000
  final={rule:(True if flags[rule] else normal_obstacle) for rule in self.p['rules']}
  return {'assignments':emitted,'normal_transitions':transitions,'active_tracklets':len(self.tracks),'confirmed_track_ids':flags,'new_confirmations':new,'normal_obstacle':normal_obstacle,'experimental_obstacle':final,'link_rejections':reject,'timings_ms':{'association_ms':association_ms,'track_update_ms':update_ms,'confirmation_ms':confirmation_ms,'temporal_total_ms':(time.perf_counter()-started)*1000}}
