# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 15:21:16 2026

@author: ngozi
"""

import sys
sys.path.insert(0, 'src')
import config as cfg_module
cfg = cfg_module.cfg

print(f'City         : {cfg.city}')
print(f'NUM_STORES   : {cfg.NUM_STORES}')
print(f'NUM_PERIODS  : {cfg.NUM_PERIODS}')
print(f'DEMAND_RATIO : {cfg.DEMAND_RATIO}')
print(f'N_SCENARIOS  : {cfg.N_SCENARIOS}')
print('PASS: config loads correctly')

from config import ProjectConfig
try:
    ProjectConfig(city='City3')
except Exception as e:
    print(f'PASS: Invalid input caught — {e}')

exp = ProjectConfig(city='City1', demand_ratio='low_DR')
print(f'PASS: Override works — DR={exp.DEMAND_RATIO}')