# -*- coding: utf-8 -*-
"""完整 0-30d 双峰 Δt 曲线. 危险窗(峰1 5-9d, 峰2 25-28d) + 安全窗(谷 12-23d)。Δt>0 为唯一约束。"""
import os, numpy as np, matplotlib.pyplot as plt
f='sweep_complete.npz' if os.path.exists('sweep_complete.npz') else 'data/sweep_complete.npz'
z=np.load(f); dt,P=z['dt'],z['P']; m=P>0
fig,ax=plt.subplots(figsize=(8.6,4.8))
ax.axvspan(5,9,color='red',alpha=0.07); ax.axvspan(25,28,color='red',alpha=0.07)
ax.axvspan(12,23,color='green',alpha=0.08)
ax.semilogy(dt[m],P[m],'-o',color='crimson',ms=4,lw=1.6)
ax.annotate('peak 1\n~9.7e-8 @5.75d',(5.75,9.7e-8),xytext=(2.5,2.2e-7),fontsize=9,color='darkred',
            arrowprops=dict(arrowstyle='->',color='darkred'))
ax.annotate('peak 2 (global max)\n1.74e-7 @27d',(27,1.74e-7),xytext=(16.5,2.5e-7),fontsize=9,color='darkred',
            arrowprops=dict(arrowstyle='->',color='darkred'))
ax.text(17.5,3e-11,'safe window\n~12–23 d',ha='center',fontsize=9,color='green')
ax.set_xlabel('Warning time  Δt = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  P')
ax.set_ylim(1e-11,3.5e-7); ax.set_xlim(-0.5,30.5); ax.grid(alpha=0.3,which='both')
fig.tight_layout(); os.makedirs('figures',exist_ok=True); fig.savefig('figures/sweep_complete.png',dpi=200)
print('[saved] figures/sweep_complete.png')
