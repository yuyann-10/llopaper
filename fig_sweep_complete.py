# -*- coding: utf-8 -*-
"""完整 0-30d 双峰 Δt 曲线 (拼接). 峰1~5-7d, 深谷, 峰2~27d(全局最大)。"""
import numpy as np, matplotlib.pyplot as plt
z=np.load('sweep_complete.npz'); dt,P=z['dt'],z['P']; m=P>0
fig,ax=plt.subplots(figsize=(8.4,4.8))
ax.semilogy(dt[m],P[m],'-o',color='crimson',ms=4,lw=1.6)
ax.axvline(23.0,ls=':',color='purple',lw=1.2); ax.text(23.0,1.4e-11,' lander LOI (23d)',color='purple',fontsize=9,rotation=90,va='bottom')
ax.axvspan(0,23,color='green',alpha=0.05)
i1=np.argmax(P[(dt>=4)&(dt<=9)]); 
ax.annotate('peak 1\n~9.7e-8 @5.75d',(5.75,9.7e-8),xytext=(3.0,2.0e-7),fontsize=9,color='darkred',
            arrowprops=dict(arrowstyle='->',color='darkred'))
ax.annotate('peak 2 (global max)\n1.74e-7 @27d',(27,1.74e-7),xytext=(17,2.3e-7),fontsize=9,color='darkred',
            arrowprops=dict(arrowstyle='->',color='darkred'))
ax.set_xlabel('Warning time  Δt = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  P')
ax.set_ylim(1e-11,3e-7); ax.set_xlim(-0.5,30.5); ax.grid(alpha=0.3,which='both')
fig.tight_layout(); fig.savefig('sweep_complete.png',dpi=200)
print('[saved] sweep_complete.png')
