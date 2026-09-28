"""Однопоточная оболочка ROS 2 Humble с очередью входного датчика глубиной один."""
import time
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy,HistoryPolicy
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool,Float32,String
from .config import DEFAULT_CONFIG,load_config
from .detector import Detector
from .pointcloud_adapter import xyz_from_pointcloud2,PointCloudError

class ForeignObjectDetectorNode(Node):
    def __init__(self):
        super().__init__('foreign_object_detector_node')
        self.declare_parameter('config',str(DEFAULT_CONFIG))
        self.declare_parameter('input_topic','')
        self.declare_parameter('debug',False)
        self.subscription=None;self.publishers_by_key={};self.last_state=None;self.last_error=None
        self.configure(self.get_parameter('config').value,self.get_parameter('input_topic').value,self.get_parameter('debug').value)
        self.add_on_set_parameters_callback(self.on_parameters)

    def configure(self,path,topic,debug):
        cfg=load_config(path)
        new_detector=Detector(cfg)
        selected_topic=topic or cfg['ros']['input_topic']
        qos=QoSProfile(history=HistoryPolicy.KEEP_LAST,depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,durability=DurabilityPolicy.VOLATILE)
        subscription=self.create_subscription(PointCloud2,selected_topic,self.on_cloud,qos)
        if self.subscription is not None:self.destroy_subscription(self.subscription)
        self.subscription=subscription
        for publisher in self.publishers_by_key.values():self.destroy_publisher(publisher)
        types={'obstacle':Bool,'distance':Float32,'state':String,'horizon':Float32,'processing':Float32,'quality':String}
        self.publishers_by_key={k:self.create_publisher(t,cfg['ros'][k+'_topic'],1) for k,t in types.items()}
        self.publishers_by_key['source']=self.create_publisher(String,'/foreign_object/source',1)
        self.detector=new_detector;self.debug=bool(debug or cfg['debug'])
        self.get_logger().info(f'Sparse state reset; listening on {selected_topic}, best-effort depth 1')

    def on_parameters(self,parameters):
        current={k:self.get_parameter(k).value for k in ['config','input_topic','debug']}
        changed=False
        for p in parameters:
            if p.name in current:current[p.name]=p.value;changed=True
        try:
            if changed:self.configure(current['config'],current['input_topic'],current['debug'])
        except (ValueError,OSError,TypeError,KeyError) as error:return SetParametersResult(successful=False,reason=str(error))
        return SetParametersResult(successful=True)

    def publish(self,result,elapsed):
        values={'obstacle':Bool(data=result['obstacle']),'distance':Float32(data=result['distance_m']),'state':String(data=result['state']),'horizon':Float32(data=float(result['measured_horizon_m'])),'processing':Float32(data=float(elapsed)),'quality':String(data=result['track_quality'])}
        values['source']=String(data=result.get('source') or ('NEAR_NORMAL' if result.get('normal_confirmed') else 'NEAR_SPARSE' if result.get('sparse_confirmed') else ''))
        for key,value in values.items():self.publishers_by_key[key].publish(value)
        if result['state']!=self.last_state:
            self.get_logger().info(f"{result['state']}; distance={result['distance_m']:.3f} m");self.last_state=result['state']

    def on_cloud(self,message):
        started=time.perf_counter()
        try:
            xyz=xyz_from_pointcloud2(message)
            stamp=message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
            result=self.detector.process(xyz,stamp,debug=self.debug)
            if result['sparse_reset_reason'] in ('TIMESTAMP_ROLLBACK','TIMESTAMP_GAP','FRAME_GAP'):
                self.get_logger().info('Sparse state reset: '+result['sparse_reset_reason'])
            self.last_error=None
        except (PointCloudError,ValueError,ArithmeticError) as error:
            self.detector.reset('INPUT_ERROR');description=str(error)
            if description!=self.last_error:self.get_logger().error('Point cloud rejected: '+description);self.last_error=description
            result={'obstacle':False,'distance_m':-1.0,'state':'TRACK_UNRELIABLE','measured_horizon_m':-1.0,'track_quality':'INVALID'}
        self.publish(result,(time.perf_counter()-started)*1000)

def main(args=None):
    rclpy.init(args=args);node=ForeignObjectDetectorNode()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:
        # Launch и терминал могут оба послать SIGINT группе процессов.
        # Повторное прерывание при уничтожении не должно превращать завершение в ошибку.
        try:node.destroy_node()
        except KeyboardInterrupt:pass
        try:rclpy.try_shutdown()
        except KeyboardInterrupt:pass
