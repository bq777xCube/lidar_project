"""Собственное жесткое вращение и перенос плоскости рельсов в канонических координатах датчика."""
from dataclasses import dataclass
import numpy as np
from .geometry_math import trajectory

@dataclass
class RailFrame:
    origin: np.ndarray
    rotation: np.ndarray  # Строки: оси рельсовой системы в канонических координатах датчика.
    source: str

    def transform(self,points):
        return (np.asarray(points)-self.origin)@self.rotation.T

    def inverse(self,points):
        return np.asarray(points)@self.rotation+self.origin

    def as_dict(self):
        return {'origin_sensor_canonical':self.origin.tolist(),'rotation_sensor_to_rail':self.rotation.tolist(),'source':self.source}


def from_plane(plane,center_coefficients,source='auto'):
    # Проверенная историческая плоскость z=a*rawX+b*rawY+c => z=A*s+B*l+C.
    A,B,C=-plane['b'],plane['a'],plane['c']
    coefficients=np.asarray(center_coefficients)
    center=float(trajectory(0,coefficients));heading=coefficients[1]-25*coefficients[0]
    return _construct(A,B,C,center,heading,source)


def _construct(A,B,C,center,heading,source):
    normal=np.array([-A,-B,1.]);normal/=np.linalg.norm(normal)
    forward=np.array([1.,heading,A+B*heading]);forward/=np.linalg.norm(forward)
    left=np.cross(normal,forward);left/=np.linalg.norm(left)
    rotation=np.vstack([forward,left,normal])
    origin=np.array([0.,center,B*center+C])
    return RailFrame(origin,rotation,source)


def from_profile(profile,source='fixed'):
    A=np.tan(np.radians(profile['forward_angle_deg']));B=np.tan(np.radians(profile['lateral_angle_deg']))
    C=-profile['height_m']*np.sqrt(1+A*A+B*B)
    return _construct(A,B,C,profile['center_offset_m'],np.tan(np.radians(profile['heading_deg'])),source)
