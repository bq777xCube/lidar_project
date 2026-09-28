"""Операторский наблюдатель свежести. Топики и поведение детектора не меняются."""
import argparse,json,time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool,Float32,String

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--timeout',type=float,default=5,help='Таймаут свежести, с');ap.add_argument('--duration',type=float,default=0,help='Длительность наблюдения, с; 0 без ограничения');args=ap.parse_args()
    rclpy.init();node=Node('foreign_object_output_probe');start=time.monotonic();last={};values={};exit_code=0
    def cb(key):
        def receive(m):
            last[key]=time.monotonic();values[key]=m.data
            if key=='state':print(json.dumps({'received_state':m.data,'latest_separate_topics':values}),flush=True)
        return receive
    subs=[node.create_subscription(t,'/foreign_object/'+k,cb(k),10) for k,t in [('obstacle',Bool),('distance',Float32),('state',String)]]
    try:
        while rclpy.ok():
            rclpy.spin_once(node,timeout_sec=.1);now=time.monotonic()
            if any(now-last.get(k,start)>args.timeout for k in ['obstacle','distance','state']):
                print('NO_FRESH_OUTPUT: результат UNKNOWN. Не используйте прежний признак препятствия или расстояние. Проверьте topic, bag, ROS_DOMAIN_ID и сеть Docker.',flush=True);exit_code=2;break
            if args.duration and now-start>=args.duration:break
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()
    raise SystemExit(exit_code)
if __name__=='__main__':main()
