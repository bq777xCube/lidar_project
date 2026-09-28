"""Повторная отрисовка научных графиков из приложенных данных; без выдуманных точек."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
A=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
def save(fig,name):
 fig.savefig(A/(name+'.png'),dpi=160,bbox_inches='tight');fig.savefig(A/(name+'.svg'),bbox_inches='tight');plt.close(fig)
for row in json.loads((A/'provenance.json').read_text()):
 event=row['event'];z=np.load(A/f'E{event}_points.npz');p=z['N1'];s=z['selected_N1'];fig,axs=plt.subplots(1,2,figsize=(12,5),gridspec_kw={'width_ratios':[1.8,1]},layout='constrained')
 axs[0].scatter(p[:,0],p[:,1],s=1,c='#a7a6b2',rasterized=True);axs[0].scatter(s[0],s[1],s=110,c='#e90050',marker='*',label='Выбранная точка');axs[0].set(xlim=(0,110),ylim=(-6,6),xlabel='Продольная координата N1, м',ylabel='Поперечная координата N1, м');axs[0].legend(loc='lower left')
 c=p[abs(p[:,0]-s[0])<3];axs[1].scatter(c[:,1],c[:,2],s=4,c='#635382');axs[1].scatter(s[1],s[2],s=110,c='#e90050',marker='*');axs[1].set(xlim=(-3,3),ylim=(-1,5),xlabel='Поперечная координата N1, м',ylabel='Высота N1, м',title='Срез ±3 м по продольной оси');axs[1].set_aspect('equal')
 fig.suptitle(f'E{event}, кадр {row["frame"]}: {s[0]:.6f} м по номинальной оси N1',fontsize=17);fig.supxlabel('Настоящие сохраненные точки. Иллюстрация, не запись воспроизведения.',fontsize=11);save(fig,f'E{event}')
d=json.loads((A/'chart_data.json').read_text());fig,ax=plt.subplots(1,2,figsize=(11,5),layout='constrained')
for a,vals,title,ylim in [(ax[0],d['direct'],'Прямо проверенные наблюдения DETECT',(0,21)),(ax[1],d['gaps'],'Условные пропуски на подходе',(0,175))]:
 bars=a.bar(['Базовый вариант','Итоговое решение'],vals,color=['#a9a4b7','#6d3096'],width=.55);a.set_ylim(ylim);a.set_title(title,fontsize=13);a.set_ylabel('Число наблюдений' if a==ax[0] else 'Число условных пропусков');a.bar_label(bars,labels=[f'{v}/21' if a==ax[0] else str(v) for v in vals],padding=7,fontsize=17)
fig.supxlabel('Известные предоставленные данные. Не общий recall и не независимый скрытый тест.',fontsize=11);save(fig,'quality')
fig,ax=plt.subplots(figsize=(11,5),layout='constrained');x=np.arange(4)
for delta,key,title,color in [(-.18,'baseline_age','Базовый вариант','#aaa5b8'),(.18,'candidate_age','Итоговое решение','#6d3096')]:
 vals=[p[key]['p95'] for p in d['pairs']];bars=ax.bar(x+delta,vals,.35,label=title,color=color);ax.bar_label(bars,fmt='%.3f',padding=5,fontsize=11)
ax.set_xticks(x,['16 байт, пара 1','16 байт, пара 2','26 байт, пара 1','26 байт, пара 2']);ax.set_ylim(0,100);ax.set_ylabel('p95 возраста результата, мс');ax.set_title('Возраст результата: ARM64 VM на Apple M4');ax.legend(loc='upper left',ncol=2);fig.supxlabel('В каждом запуске обоих вариантов: 500/500. i7 не измерен. Максимум итогового решения: 151.110 мс.',fontsize=11);save(fig,'latency')
def diagram(name,title,boxes,edges,note):
 fig,ax=plt.subplots(figsize=(12,6));ax.set_xlim(0,12);ax.set_ylim(0,6);ax.axis('off');ax.set_title(title,fontsize=20,pad=15)
 for x,y,text in boxes:ax.text(x,y,text,ha='center',va='center',fontsize=13,bbox=dict(boxstyle='round,pad=.6',facecolor='#f2eef7',edgecolor='#6d3096'))
 for x1,y1,x2,y2 in edges:ax.annotate('',xy=(x2,y2),xytext=(x1,y1),arrowprops=dict(arrowstyle='->',color='#6d3096',lw=1.7))
 fig.text(.5,.05,note,ha='center',fontsize=11);save(fig,name)
diagram('pipeline','Схема алгоритма',[(1.5,4.5,'PointCloud2\nXYZ по полям'),(5.7,4.5,'Геометрия рельсов\nГабарит + S2'),(5.7,2.5,'Согласованность лучей\nДальний канал + B1/B2'),(10.2,3.5,'Решение\n7 ROS-выходов')],[(2.8,4.5,4,4.5),(2.5,4,4,2.8),(7.5,4.5,9,3.8),(7.5,2.5,9,3.2),(5.7,3.9,5.7,3.1)],'A/+5 м выключен. B1 использует GOOD-геометрию. B2 сохраняет правило N1.')
diagram('deployment','Демонстрация в одном контейнере',[(1.4,4.5,'Bag\nтолько чтение'),(5.4,4.5,'Проверка topic\nГотовность узла'),(9.8,4.5,'ros2 bag play\n0.2x / 0.1x'),(9.8,2,'Установленный\nдетектор'),(4.3,2,'Наблюдатель DDS\nОблако и 7 выходов')],[(2.5,4.5,3.9,4.5),(6.9,4.5,8.4,4.5),(9.8,3.8,9.8,2.7),(8.3,2,6,2)],'linux/amd64 на M4: эмуляция, не оценка i7. --shm-size=256m, прежний Fast DDS.')
print('Готовы PNG и редактируемые SVG')
