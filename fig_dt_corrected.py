# -*- coding: utf-8 -*-
"""点3 Δt 曲线: 修正(dt~7s) vs 旧粗网格(dt~230s), 展示平台 + 高估假象。"""
import os, numpy as np, matplotlib.pyplot as plt
if os.path.exists('sweep_server.npz') and 'dt' in np.load('sweep_server.npz'):
    z=np.load('sweep_server.npz'); dt_c,P_c,lo,hi=z['dt'],z['P'],z['P_lo'],z['P_hi']; src='500k'
else:
    a=np.load('sweep_5_778.npy'); dt_c,P_c=a[:,0],a[:,1]; lo=hi=None; src='100k preview'
b=np.load('analysis_base.npz'); dts=b['dts']; row=b['table'][2]
m=(dts>=5.0)&(dts<=7.78); dt_o,P_o=dts[m],row[m]
fig,ax=plt.subplots(figsize=(7.2,4.6))
ax.plot(dt_o,P_o,'--',color='0.55',marker='s',ms=5,label='Uncorrected (dt≈230 s)')
if lo is not None: ax.fill_between(dt_c,lo,hi,color='seagreen',alpha=0.2)
ax.plot(dt_c,P_c,'-',color='seagreen',marker='o',ms=4,lw=2,label=f'Corrected (dt≈7 s, {src})')
ax.set_xlabel('Warning time  Δt = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  P')
ax.set_ylim(0,2.5e-7); ax.grid(alpha=0.3); ax.legend(fontsize=11)
fig.tight_layout(); fig.savefig('fig_dt_corrected.png',dpi=200)
print('[saved] fig_dt_corrected.png  src=%s'%src)
