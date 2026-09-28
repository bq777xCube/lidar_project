"""Редакционные иллюстрации из сохранённых точек и результатов. Детектор не запускается."""
from pathlib import Path
import json,hashlib,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
A=Path(__file__).resolve().parent;H=A.parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none','svg.hashsalt':'presentation02','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
PURPLE='#693397';PINK='#ce2871';GREY='#bac0cd';DARK='#282b3f'
def save(fig,n):
 fig.savefig(A/(n+'.png'),dpi=180,bbox_inches='tight');fig.savefig(A/(n+'.svg'),bbox_inches='tight',metadata={'Date':None});plt.close(fig)
annotations=json.loads((H/'sources/object_annotations.json').read_text());original=json.loads((H/'technical/comparison_assets/provenance.json').read_text());provenance=[]
names={1:'Крупное препятствие',9:'Низкое препятствие поперёк пути',10:'Тонкий подвешенный предмет'}
for r in annotations:
 e=r['event'];z=np.load(A/f'E{e}_points.npz');q=z['N1'];ids=z['source_indices'];s=z['selected_N1'];mask=np.isin(ids,r['reference_indices']);obj=q[mask]
 assert mask.sum()==len(r['reference_indices']) and int(z['selected_source_index']) in r['reference_indices']
 fig,axs=plt.subplots(2,1,figsize=(5.1,6.8),gridspec_kw={'height_ratios':[.9,1.15]},layout='constrained')
 ax=axs[0];ax.scatter(q[:,0],q[:,1],s=1.3,c=GREY,alpha=.8,rasterized=True);ax.scatter(obj[:,0],obj[:,1],s=17,c=PINK,zorder=3);ax.scatter(s[0],s[1],s=115,marker='*',c='#f8b940',edgecolors=DARK,linewidths=.75,zorder=4)
 ax.set(xlim=(0,110),ylim=(-6,6),xlabel='Продольная координата, м',ylabel='Поперечная координата, м',title='Общий вид облака')
 ax.set_xticks([0,25,50,75,100]);ax.set_yticks([-5,0,5]);ax.grid(alpha=.13)
 ax=axs[1];local=q[np.abs(q[:,0]-s[0])<3]
 ax.scatter(local[:,1],local[:,2],s=8,c=GREY,alpha=.8,rasterized=True);ax.scatter(obj[:,1],obj[:,2],s=25,c=PINK,zorder=3);ax.scatter(s[1],s[2],s=160,marker='*',c='#f8b940',edgecolors=DARK,linewidths=.8,zorder=4)
 center=(obj.min(0)+obj.max(0))/2;span=max(np.ptp(obj[:,1]),np.ptp(obj[:,2]),.7)+.8
 ax.set(xlim=(center[1]-span/2,center[1]+span/2),ylim=(center[2]-span/2,center[2]+span/2),xlabel='Поперечная координата, м',ylabel='Высота над номинальной\nплоскостью, м',title='Увеличенный фрагмент')
 ax.set_aspect('equal');ax.grid(alpha=.15);ax.tick_params(labelsize=10)
 save(fig,f'E{e}')
 p=next(x for x in original if x['event']==e);provenance.append({**p,'scenario_name':names[e],'scenario_source':'sources/scenarios.json','plotted_reference_point_count':len(obj),'object_annotation_source':r,'annotation_is_runtime_segmentation':False,'selected_marker':'Золотая звезда с тёмным контуром','object_marker':'Малиновые точки из сохранённой поясняющей разметки','height_axis':'Высота над калиброванной номинальной плоскостью; не высота над измеренными рельсами на дальности объекта','zoom_limits':{'lateral':[float(center[1]-span/2),float(center[1]+span/2)],'height':[float(center[2]-span/2),float(center[2]+span/2)]},'npz_sha256':hashlib.sha256((A/f'E{e}_points.npz').read_bytes()).hexdigest(),'generator':'assets/render_assets.py'})
(A/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
def flow(name,labels):
 fig,ax=plt.subplots(figsize=(13,2.0));ax.set(xlim=(0,13),ylim=(0,2));ax.axis('off');w=11.7/len(labels);gap=.3
 for i,t in enumerate(labels):
  x=.2+i*(w+gap);ax.add_patch(FancyBboxPatch((x,.37),w-.13,1.2,boxstyle='round,pad=.03,rounding_size=.12',facecolor='#f2edf8',edgecolor='#aa8ac6',linewidth=1.3));ax.text(x+(w-.13)/2,.97,t,ha='center',va='center',fontsize=14,color=DARK)
  if i<len(labels)-1:ax.annotate('',(x+w+gap-.09,.97),(x+w-.02,.97),arrowprops={'arrowstyle':'->','color':PURPLE,'lw':1.8})
 save(fig,name)
flow('product_flow',['Лидар','Обработка\nоблака','Проверка зоны\nдвижения','Обнаружение\nи расстояние'])
flow('integration',['Docker\nс ROS 2 Humble','Запись ROS 2 bag\nили поток лидара','Признак препятствия,\nрасстояние и состояние'])
# Схема отражает два параллельных пути к общему результату, а не фиктивную последовательность.
fig,ax=plt.subplots(figsize=(13,4));ax.set(xlim=(0,13),ylim=(0,4));ax.axis('off')
def box(x,y,w,h,t):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04,rounding_size=.1',facecolor='#f2edf8',edgecolor='#aa8ac6'));ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=13,color=DARK)
def arrow(a,b):ax.annotate('',b,a,arrowprops={'arrowstyle':'->','color':PURPLE,'lw':1.8})
box(.15,1.5,1.5,1,'Текущее\nоблако');box(2.3,2.5,2.6,1.1,'Геометрия рельсов\nи зона движения');box(5.6,2.5,3.0,1.1,'Проверка точек\nи подтверждение\nво времени');box(2.3,.2,3.0,1.25,'Сопоставление точек\nсо структурой лучей');box(6,.2,2.6,1.25,'Дальние примеры\nи поддержка\nпри приближении');box(10.1,1.4,2.5,1.2,'Результат\nи состояние')
for a,b in [((1.65,2.1),(2.3,3.05)),((1.65,1.8),(2.3,.8)),((4.9,3.05),(5.6,3.05)),((5.3,.8),(6,.8)),((8.6,3.05),(10.1,2.2)),((8.6,.8),(10.1,1.8)),((4.9,2.6),(6,1.45))]:arrow(a,b)
save(fig,'algorithm')
d=json.loads((H/'sources/delivery_evaluation.json').read_text())['query_T3']['pairs'];rows=[]
for i,x in enumerate(d,1):rows.append({'run':i,'point_step_bytes':x['layout'],'input_hz':10,'offered':500,'completed':x['candidate_completed'],'p95_ms':x['candidate_age']['p95'],'max_ms':x['candidate_age']['max'],'over_100ms':x['deadline_misses']['candidate']})
metrics={'platform':'Linux ARM64 VM на Apple M4','latency_definition':'От публикации входа до завершения callback установленного узла; не до получения всеми потребителями','runs':rows,'max_ms':max(x['max_ms'] for x in rows),'reviewed_detect':{'hits':13,'observations':21},'reviewed_ignore':{'alarms':2,'observations':12},'background':{'positive':4,'inputs':702},'real_controls':{'positive':0,'inputs':193},'unknown_frames':[775,776,777,778,792,793],'sources':['sources/delivery_evaluation.json','sources/evaluation.json','sources/v3_competition_integration.json','sources/summary.json']}
(A/'final_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
with (A/'performance.csv').open('w') as f:
 out=csv.DictWriter(f,fieldnames=list(rows[0]));out.writeheader();out.writerows(rows)
print('Готовы реальные облака, схемы, метрики и происхождение данных')
