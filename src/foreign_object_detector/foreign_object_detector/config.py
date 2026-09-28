"""Конфигурация замороженного детектора: подмножество JSON в YAML, автономная загрузка."""
import hashlib,json
from pathlib import Path
from .sparse_tracker import PARAMETERS
DEFAULT_CONFIG=Path(__file__).parent/'config/production.yaml'
NORMAL_SHA256='db908a007a5344e3412dc75001d4b33e988678a5e9cdcc372cfff25ab74023d0'
def load_config(path=DEFAULT_CONFIG):
    cfg=json.loads(Path(path).read_text())
    digest=hashlib.sha256(json.dumps(cfg['normal'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=NORMAL_SHA256:raise ValueError('Normal geometry/threshold configuration differs from frozen Phase4C baseline')
    if cfg['sparse']!=PARAMETERS or cfg['sparse_rule']!='S2':raise ValueError('Sparse configuration differs from frozen S2 parameters')
    if cfg['phase4c_payload_sha256']!='c1b1f9fdd521e76d6d31c2e22ee8697678ce89ba36842c248483aadfbaa4f016':raise ValueError('Incorrect sparse provenance digest')
    if set(cfg['ros'])!={'input_topic','obstacle_topic','distance_topic','state_topic','horizon_topic','processing_topic','quality_topic'}:raise ValueError('Invalid ROS topic keys')
    if not all(isinstance(v,str) and v for v in cfg['ros'].values()):raise ValueError('Topic names must be nonempty strings')
    if len(set(cfg['ros'].values()))!=len(cfg['ros']):raise ValueError('Topics must be distinct')
    validate_far_switch(cfg)
    validate_short_extension(cfg)
    validate_direct(cfg)
    return cfg

def normal_config():return load_config()['normal']

def validate_far_switch(cfg):
    far=cfg.get('far_synthetic')
    if not isinstance(far,dict) or set(far)!={'enabled'} or type(far['enabled']) is not bool:
        raise ValueError('far_synthetic permits only boolean enabled; all far values are frozen')

SHORT_EXTENSION_DEFAULT={'enabled':False,'model':'local_quadratic','maximum_extension_m':5.0}
def validate_short_extension(cfg):
    ext=cfg.get('short_extension',SHORT_EXTENSION_DEFAULT)
    if set(ext)!=set(SHORT_EXTENSION_DEFAULT):raise ValueError('short_extension requires enabled, model, maximum_extension_m')
    if type(ext['enabled']) is not bool:raise ValueError('short_extension.enabled must be boolean')
    if ext['model']!='local_quadratic':raise ValueError('short_extension model must be frozen local_quadratic')
    if type(ext['maximum_extension_m']) not in (int,float) or ext['maximum_extension_m']!=5.0:raise ValueError('short_extension maximum_extension_m must be exactly 5.0; greater extensions forbidden')
    return dict(ext)

DIRECT_DEFAULT={'b1':False,'b2':False,'memoize_refinement':False}
def validate_direct(cfg):
    value=cfg.get('direct',DIRECT_DEFAULT)
    if not isinstance(value,dict) or set(value)!=set(DIRECT_DEFAULT) or any(type(v) is not bool for v in value.values()):raise ValueError('direct options require exactly boolean b1,b2,memoize_refinement')
    return dict(value)
