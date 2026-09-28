from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from foreign_object_detector.config import DEFAULT_CONFIG

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('input_topic',default_value='/lidar_points'),
        DeclareLaunchArgument('config',default_value=str(DEFAULT_CONFIG)),
        DeclareLaunchArgument('debug',default_value='false'),
        DeclareLaunchArgument('transport_profile',default_value=str(DEFAULT_CONFIG.with_name('fastdds.xml'))),
        SetEnvironmentVariable('FASTRTPS_DEFAULT_PROFILES_FILE',LaunchConfiguration('transport_profile')),
        Node(package='foreign_object_detector',executable='foreign_object_detector_node',output='screen',
             parameters=[{'input_topic':LaunchConfiguration('input_topic'),
                          'config':LaunchConfiguration('config'),
                          'debug':ParameterValue(LaunchConfiguration('debug'),value_type=bool)}])])
