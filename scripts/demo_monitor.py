"""Ограниченное реальное ros2 bag play с наблюдением семи выходов и выборок облака."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool,Float32,String
from foreign_object_detector.pointcloud_adapter import xyz_from_pointcloud2

def stop(p):
    if p is not None and p.poll() is None:
        os.killpg(p.pid,signal.SIGINT)
        try:p.wait(timeout=12)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=5)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bag',help='Каталог bag, смонтированный только для чтения')
    ap.add_argument('--rate',type=float,default=.2,help='Фактический коэффициент воспроизведения')
    ap.add_argument('--span',type=float,default=1.2,help='Интервал времени исходных данных, с')
    ap.add_argument('--offset',type=float,default=0,help='Смещение от начала записи, с')
    ap.add_argument('--output',required=True,help='Новый каталог наблюдений')
    args=ap.parse_args();assert args.rate>0 and args.span>0
    dest=Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    info=subprocess.check_output(['ros2','bag','info',args.bag],text=True);assert '/lidar_points' in info,'В bag отсутствует /lidar_points'
    (dest/'bag_info.txt').write_text(info)
    rclpy.init();probe=Node('ru_demo_observer');events=[];inputs=[];start=time.monotonic();clouds=[]
    def receive(key):
        def cb(m):events.append({'t':time.monotonic()-start,'topic':key,'value':m.data})
        return cb
    def cloud(m):
        stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
        inputs.append({'t':time.monotonic()-start,'stamp':stamp,'point_step':m.point_step,'points':m.width*m.height})
        if len(clouds)<60:
            raw=xyz_from_pointcloud2(m);ids=np.flatnonzero(np.isfinite(raw).all(1)&(-raw[:,1]>0)&(-raw[:,1]<110)&(np.abs(raw[:,0])<8))
            ids=ids[::max(1,int(np.ceil(len(ids)/4000)))];p=raw[ids]
            clouds.append({'t':inputs[-1]['t'],'stamp':stamp,'source_indices':ids.tolist(),'xyz':p.tolist()})
    subscriptions=[probe.create_subscription(PointCloud2,'/lidar_points',cloud,qos_profile_sensor_data)]
    keys=[('obstacle',Bool),('distance',Float32),('state',String),('horizon',Float32),('processing_ms',Float32),('track_quality',String),('source',String)]
    subscriptions.extend(probe.create_subscription(typ,'/foreign_object/'+key,receive(key),100) for key,typ in keys)
    log=(dest/'detector.log').open('w');plog=(dest/'player.log').open('w');player=None
    launch=subprocess.Popen(['ros2','launch','foreign_object_detector','detector.launch.py','input_topic:=/lidar_points'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    command=['ros2','bag','play',args.bag,'--topics','/lidar_points','--read-ahead-queue-size','8','--disable-keyboard-controls','--start-offset',str(args.offset),'--rate',str(args.rate),'--delay','1']
    try:
        deadline=time.monotonic()+25
        while probe.count_publishers('/foreign_object/state')<1 or probe.count_subscribers('/lidar_points')<2:
            rclpy.spin_once(probe,timeout_sec=.05);assert launch.poll() is None;assert time.monotonic()<deadline,'Узел не готов'
        player=subprocess.Popen(command,stdout=plog,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+args.span/args.rate+40
        while not inputs or (inputs[-1]['stamp']-inputs[0]['stamp'])/1e9<args.span:
            rclpy.spin_once(probe,timeout_sec=.02)
            assert launch.poll() is None,'Узел завершился';assert time.monotonic()<deadline,'Таймаут входа'
            assert player.poll() is None,'Плеер завершился раньше интервала'
        stop(player);until=time.monotonic()+1
        while time.monotonic()<until:rclpy.spin_once(probe,timeout_sec=.02)
    finally:
        stop(player);stop(launch);log.close();plog.close();probe.destroy_node();rclpy.try_shutdown()
    assert len(inputs)>=3 and all(any(e['topic']==k for e in events) for k,_ in keys),'Не все выходы получены'
    assert launch.returncode==0,launch.returncode
    result={'status':'PASS','method':'Реальный ros2 bag play, установленный RU-узел, read-only bag; выборки фактически полученных облаков и отдельные выходы DDS','rate':args.rate,'span':args.span,'offset':args.offset,'command':command,'input_count':len(inputs),'outputs':len(events),'layouts':sorted({i['point_step'] for i in inputs}),'launch_exit':launch.returncode,'player_exit':player.returncode,'inputs':inputs,'events':events,'clouds':clouds}
    (dest/'observations.json').write_text(json.dumps(result,ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','events','clouds']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
