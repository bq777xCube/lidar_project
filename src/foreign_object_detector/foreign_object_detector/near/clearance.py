"""Принадлежность криволинейному габариту в координатах осевой линии [arc_s,d,h]."""
import numpy as np


def inside_clearance(frenet,track_valid,config):
    cfg=config['clearance']
    return track_valid&(abs(frenet[:,1])<=cfg['width_m']/2+cfg['lateral_margin_m'])&(frenet[:,2]<=cfg['height_m']+cfg['vertical_margin_m'])


def structure_masks(frenet,separation,config):
    cfg=config['structure_mask'];d=frenet[:,1];h=frenet[:,2]
    rail=np.zeros(len(d),dtype=bool);below=rail.copy()
    if cfg['rail_enabled']:
        rail=((abs(d)-separation/2)/cfg['rail_lateral_radius_m'])**2+(h/cfg['rail_vertical_radius_m'])**2<=1
    if cfg['below_rail_enabled']:below=h<cfg['below_rail_ceiling_m']
    return rail,below
