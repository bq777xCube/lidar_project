# Та же закрепленная база ROS Humble и неизменные зависимости.
FROM ros:humble-ros-base-jammy@sha256:1813d3c85d7f96ff7d3012d865204583255740182db5d0065f8f8cd029a83138
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends python3-numpy python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/detector
COPY src/foreign_object_detector src/foreign_object_detector
RUN source /opt/ros/humble/setup.bash && colcon build --packages-select foreign_object_detector \
    && source install/setup.bash && python3 -c "from foreign_object_detector.detector import Detector; Detector()" \
    && dpkg-query -W > /opt/detector/build-packages.txt
COPY transport/fastdds.xml /opt/detector/transport/fastdds.xml
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/opt/detector/transport/fastdds.xml
COPY docker/entrypoint.sh /detector_entrypoint.sh
RUN chmod +x /detector_entrypoint.sh
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["/detector_entrypoint.sh"]
CMD ["ros2", "launch", "foreign_object_detector", "detector.launch.py"]
