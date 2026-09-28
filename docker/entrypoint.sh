#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
source /opt/detector/install/setup.bash
exec "$@"
