"""Необязательный точный ограниченный цикл; резервный путь NumPy."""
import ctypes
import platform
import sys
from pathlib import Path
import numpy as np
_library=None
for _name in ['_beam_selector.so',f'_beam_selector_v2_{sys.platform}_{platform.machine()}.so']:
    try:
        _candidate=ctypes.CDLL(str(Path(__file__).with_name(_name)))
        _candidate.rescue_beam_select.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_void_p]
        _candidate.rescue_beam_select.restype=None
        _library=_candidate
        break
    except (OSError,AttributeError):
        pass

def offbeam(e,beams):
    if (_library is not None and e.dtype==np.float64 and beams.dtype==np.float64
            and e.flags.c_contiguous and beams.flags.c_contiguous and e.ndim==1
            and beams.shape==(128,)):
        out=np.empty(len(e),dtype=np.bool_)
        _library.rescue_beam_select(e.ctypes.data,len(e),beams.ctypes.data,out.ctypes.data)
        return out
    j=np.clip(np.searchsorted(beams,e),1,127)
    j-=np.abs(e-beams[j-1])<=np.abs(e-beams[j])
    return np.abs(e-beams[j])>.02

if _library is not None:
    _library.rescue_beam_screen.argtypes=[ctypes.c_void_p,ctypes.c_size_t]+[ctypes.c_void_p]*7
    _library.rescue_beam_screen.restype=None

def screen(p,far):
    """Консервативный предварительный отбор. Окрестность неоднозначности 1e-6 запускает исходный расчет, а не расширяет критерий приема. Внешние границы сохраняют исходную арифметику. Для нестандартных типов, предельных величин и шагов памяти используется резервный путь; неизменные константы лучей кэшируются."""
    if (_library is None or p.dtype!=np.float64 or not p.flags.c_contiguous
            or p.ndim!=2 or p.shape[1]!=3):return None
    if not hasattr(far,'_rescue_screen_bounds'):
        b=far.beams
        if b.shape!=(128,) or not np.isfinite(b).all() or b[0]<=-89 or b[-1]>=89 or not (np.diff(b)>0).all():return None
        band=1e-6
        arrays=[np.tan(np.radians(b)),np.nextafter(np.tan(np.radians(b-.02+band)),np.inf),np.nextafter(np.tan(np.radians(b+.02-band)),-np.inf),np.nextafter(np.tan(np.radians(b-.02-band)),-np.inf),np.nextafter(np.tan(np.radians(b+.02+band)),np.inf)]
        t=arrays[0];arrays.append(np.searchsorted(t,t[0]+(np.arange(4096)+.5)*((t[-1]-t[0])/4096)).astype(np.int32))
        for a in arrays:a.flags.writeable=False
        far._rescue_screen_bounds=arrays
    out=np.empty(len(p),dtype=np.uint8)
    _library.rescue_beam_screen(p.ctypes.data,len(p),*[a.ctypes.data for a in far._rescue_screen_bounds],out.ctypes.data)
    return out
