# -*- coding: utf-8 -*-
"""完整修正 Δt 曲线(0-23d): 碰撞概率随预警时间(出发时刻)变化。单平台 mesa。"""
import numpy as np, matplotlib.pyplot as plt
z=np.load('analysis_dt_corrected.npz'); dt,P=z['dt'],z['P']
m=P>0
fig,ax=plt.subplots(figsize=(7.6,4.7))
ax.semilogy(dt[m],P[m],'-o',color='seagreen',ms=5,lw=1.8)
ax.axvspan(4.5,9.0,color='orange',alpha=0.10)
ax.text(6.6,1.2e-7,'risk window\n~4.5–9 d',ha='center',fontsize=10,color='peru')
ax.axvline(2.6,ls=':',color='0.6',lw=1); ax.text(2.6,1.3e-11,' crew TLI',fontsize=9,color='0.4',rotation=90,va='bottom')
ax.set_xlabel('Warning time  Δt = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  P')
ax.set_ylim(1e-11,2e-7); ax.set_xlim(-0.5,23.5); ax.grid(alpha=0.3,which='both')
fig.tight_layout(); fig.savefig('fig_dt_full.png',dpi=200)
print('[saved] fig_dt_full.png')
print('峰: Δt=%.2f P=%.3e ; 平台>5e-8 区间: %.1f-%.1f d'%(dt[P.argmax()],P.max(),dt[P>5e-8].min(),dt[P>5e-8].max()))
