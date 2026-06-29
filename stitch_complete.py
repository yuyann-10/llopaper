# -*- coding: utf-8 -*-
"""拼接所有 sweep npz -> 完整 0-30d Δt 曲线 (点3最坏点, 修正网格)。
优先级低->高(高覆盖): analysis_dt_corrected < sweep_outer < sweep_tail < sweep_extend < sweep_server"""
import numpy as np
master={}
def add(f):
    z=np.load(f,allow_pickle=True)
    if 'done' in z:
        for k,v in z['done'].item().items(): master[round(float(k),3)]=(float(v[0]),float(v[1]),float(v[2]))
    elif 'dt' in z:
        lo=z['P_lo'] if 'P_lo' in z else np.full(len(z['dt']),np.nan)
        hi=z['P_hi'] if 'P_hi' in z else np.full(len(z['dt']),np.nan)
        for d,p,l,h in zip(z['dt'],z['P'],lo,hi): master[round(float(d),3)]=(float(p),float(l),float(h))
for f in ['analysis_dt_corrected.npz','sweep_outer.npz','sweep_tail.npz','sweep_extend.npz','sweep_server.npz']:
    try: add(f)
    except Exception as e: print('skip',f,e)
dt=np.array(sorted(master)); P=np.array([master[d][0] for d in dt])
lo=np.array([master[d][1] for d in dt]); hi=np.array([master[d][2] for d in dt])
np.savez('sweep_complete.npz',dt=dt,P=P,P_lo=lo,P_hi=hi)
print('完整 0-%.0fd, %d 点:'%(dt.max(),len(dt)))
for d,p in zip(dt,P): print('  Δt=%5.2f  P=%.4e'%(d,p))
# 找两个峰
from scipy.signal import argrelmax
print('全局最大: Δt=%.2f P=%.3e'%(dt[P.argmax()],P.max()))
