"""Вход XYZ с необязательными атрибутами. Исходная система преобразуется здесь один раз."""
from dataclasses import dataclass
import numpy as np

@dataclass
class PointCloudFrame:
    xyz: np.ndarray
    intensity: np.ndarray | None = None
    ring: np.ndarray | None = None
    timestamp: np.ndarray | None = None
    original_indices: np.ndarray | None = None

    def clean(self,max_range_m=None):
        xyz=np.asarray(self.xyz)
        if xyz.ndim!=2 or xyz.shape[1]!=3:raise ValueError('xyz must have shape (N,3)')
        valid=np.isfinite(xyz).all(axis=1)&(xyz!=0).any(axis=1)
        if max_range_m is not None:valid &= np.einsum('ij,ij->i',xyz,xyz)<=max_range_m**2
        idx=np.arange(len(xyz)) if self.original_indices is None else np.asarray(self.original_indices)
        if len(idx)!=len(xyz):raise ValueError('Point-index length mismatch')
        # В решении участвует только XYZ. Необязательные атрибуты сохраняются на входной границе.
        return xyz[valid].astype(np.float64),idx[valid],valid


def to_canonical(xyz):
    """[исходные X,Y,Z] -> [вперед s=-Y, вбок l=X, вверх z=Z]."""
    return np.column_stack([-xyz[:,1],xyz[:,0],xyz[:,2]])


def from_canonical(points):
    return np.column_stack([points[:,1],-points[:,0],points[:,2]])
