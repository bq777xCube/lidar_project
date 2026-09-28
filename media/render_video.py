"""Рендер фактически записанного воспроизведения bag и выходов DDS, не синтетическая анимация."""
import json,sys,subprocess,textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
real,synth,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True);frames=out/'frames';frames.mkdir(exist_ok=True);index=0
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12})
def store(fig):
 global index
 fig.savefig(frames/f'{index:05d}.png',dpi=100);plt.close(fig);index+=1
sources=[]
for label,path in [('Реальная запись',real),('Предоставленная синтетическая запись',synth)]:
 r=json.loads(path.read_text());assert r['status']=='PASS';sources.append({'label':label,'input_count':r['input_count'],'outputs':r['outputs'],'layouts':r['layouts'],'rate':r['rate'],'span':r['span'],'launch_exit':r['launch_exit']})
 fig=plt.figure(figsize=(12.8,7.2),facecolor='#191322');fig.text(.06,.82,label,color='white',fontsize=25);fig.text(.06,.67,'Реальный запуск установленного узла и ros2 bag play',color='white',fontsize=17)
 lines=['lidar-near:v5-query-first-ru','linux/amd64, эмуляция на Apple M4',f'Коэффициент bag: {r["rate"]}x; layout: {r["layouts"]}', 'Данные только для чтения; --network none; --shm-size=256m','После проверки topic и готовности подписчика:', ' '.join(r['command'])]
 fig.text(.06,.53,'\n'.join('\n'.join(textwrap.wrap(x,91)) for x in lines),color='#e7d9f5',fontsize=14,va='top',linespacing=1.55);fig.text(.06,.08,'Далее: визуализация записанного потока DDS. Не запись экрана и не тест 10 Гц на i7.',color='white',fontsize=12)
 store(fig)
 first=Image.open(frames/f'{index-1:05d}.png')
 for _ in range(11):first.save(frames/f'{index:05d}.png');index+=1
 lo=r['clouds'][0]['t'];hi=max(r['inputs'][-1]['t'],max(e['t'] for e in r['events']))+.5
 for t in np.arange(lo,hi,.25):
  cloud=max((x for x in r['clouds'] if x['t']<=t),key=lambda x:x['t']);p=np.asarray(cloud['xyz']);latest={}
  for e in r['events']:
   if e['t']<=t:latest[e['topic']]=e
  fig=plt.figure(figsize=(12.8,7.2),facecolor='white');ax=fig.add_axes([.07,.26,.57,.52]);ax.scatter(-p[:,1],p[:,0],c=p[:,2],s=2,cmap='viridis',vmin=-2,vmax=4);ax.set(xlim=(0,110),ylim=(-8,8),xlabel='Продольная координата s=-Y, м',ylabel='Поперечная координата X, м');ax.grid(alpha=.2)
  fig.text(.06,.91,label,fontsize=22,color='#38104e');fig.text(.06,.84,f'Итоговое решение; amd64/M4; bag {r["rate"]}x; время наблюдения {t-lo:.2f} с',fontsize=13)
  labels={'obstacle':'Препятствие','distance':'Расстояние, м','state':'Состояние','horizon':'Горизонт, м','processing_ms':'Обработка, мс','track_quality':'Качество','source':'Источник'}
  y=.76
  for key,name in labels.items():
   e=latest.get(key);v='еще не получено' if e is None else e['value'];v=f'{v:.3f}' if isinstance(v,float) else str(v)
   fig.text(.68,y,name,fontsize=12,color='#6c6072');fig.text(.68,y-.035,v,fontsize=12,color='#191322');y-=.085
  state=latest.get('state');age='нет результата' if state is None else f'{(t-state["t"])*1000:.0f} мс после получения state'
  fig.text(.06,.115,'Точки реально принятого облака, ограниченная выборка для показа.',fontsize=12)
  fig.text(.06,.075,'Выходы независимы и без общей метки кадра. '+age,fontsize=11)
  fig.text(.06,.035,'Не измерение полной задержки датчика. При остановке входа старое сообщение не становится свежим.',fontsize=11)
  store(fig)
video=out/'Демонстрация_RU.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','4','-i',str(frames/'%05d.png'),'-c:v','libx264','-threads','2','-preset','fast','-crf','21','-pix_fmt','yuv420p','-r','24','-movflags','+faststart',str(video)],check=True)
(out/'video_provenance.json').write_text(json.dumps({'method':'Рендер записанного реального ros2 bag play и фактически полученных DDS-сообщений. Не скринкаст и не заранее нарисованные доказательные кадры.','image':'lidar-near:v5-query-first-ru','image_id':'sha256:a709d2566c0c33362c24325d3137c1f983f38b22571cff5aa26dfda131b08b4f','platform':'linux/amd64 emulation on Apple M4','render_fps':4,'encoded_fps':24,'duration_s':index/4,'runs':sources,'no_throughput_claim':True},ensure_ascii=False,indent=2)+'\n')
print(video,'длительность',index/4)
