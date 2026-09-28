from setuptools import find_packages,setup
from setuptools.command.build_py import build_py
from pathlib import Path
import subprocess,shutil
class BuildWithBeamSelector(build_py):
    def run(self):
        super().run()
        compiler=shutil.which('c++')
        if compiler is None:
            self.announce('C++17 unavailable; retaining exact NumPy rescue fallback',level=2)
            return
        source=Path(__file__).parent/'foreign_object_detector/beam_selector.cpp'
        target=Path(self.build_lib)/'foreign_object_detector/_beam_selector.so'
        subprocess.run([compiler,'-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-shared','-fPIC',str(source),'-o',str(target)],check=True)
setup(name='foreign_object_detector',version='0.6.0',packages=find_packages(),
      cmdclass={'build_py':BuildWithBeamSelector},
      package_data={'foreign_object_detector':['config/*.yaml','config/frozen_far.json','config/fastdds.xml','beam_selector.cpp']},
      data_files=[('share/ament_index/resource_index/packages',['resource/foreign_object_detector']),
                  ('share/foreign_object_detector',['package.xml']),
                  ('share/foreign_object_detector/launch',['launch/detector.launch.py'])],
      install_requires=['setuptools','numpy'],zip_safe=False,
      maintainer='Detector team',maintainer_email='maintainer@example.invalid',
      description='Ближний и дальний детектор с точным ускорением переходных ветвей текущего кадра',license='Proprietary',
      entry_points={'console_scripts':['foreign_object_detector_node = foreign_object_detector.node:main']})
