# -*- coding: utf-8 -*-
"""图1 (重做): 100km 逆行 LDO 与采样解体点分布 (x-y 俯视, 月球用点表示)。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D_EM = 389703.0; MU = 0.01215058; R_M = 1738.0
MOON = np.array([1-MU, 0, 0])

df = pd.read_csv('cr3bp_ldo_target.csv')
ldo = df[['x_rot(km)','y_rot(km)','z_rot(km)']].values/D_EM
Vv = df[['vx_rot(km/s)','vy_rot(km/s)','vz_rot(km/s)']].values
POS = np.load('fragments_ldo.npz')['pos_nd']        # (6,3) 等相位解体点
# 第一圈 (相位转 2π), 与解体点同一条轨道
r0 = ldo - MOON; h = np.cross(r0[0], Vv[0]); h/=np.linalg.norm(h)
e1 = r0[0]/np.linalg.norm(r0[0]); e2 = np.cross(h, e1)
ang = np.unwrap(np.arctan2(r0@e2, r0@e1))
period = int(np.argmax(np.abs(ang-ang[0]) >= 2*np.pi))

# 月心坐标 (km) — 避免 DU 下 0.98xx 需要 4 位小数的问题
ldo_km = (ldo - MOON)*D_EM
POS_km = (POS - MOON)*D_EM
fig, ax = plt.subplots(figsize=(6.2, 6))
ax.scatter(0, 0, c='k', marker='+', s=140, lw=2, zorder=2, label='Moon (center)')
ax.plot(ldo_km[:period,0], ldo_km[:period,1], color='gray', lw=1.3, alpha=0.8, label='100 km LDO')
ax.scatter(POS_km[:,0], POS_km[:,1], c='red', s=45, zorder=5, label='Breakup points')
for i,(x,y,_) in enumerate(POS_km):
    ax.annotate(str(i+1), (x,y), textcoords='offset points', xytext=(5,4),
                fontsize=12, color='darkred', fontweight='bold')
lim = 2200
ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect('equal')
ax.set_xlabel('x (km, Moon)'); ax.set_ylabel('y (km, Moon)')
ax.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=3,
          columnspacing=1.0, handletextpad=0.4); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig('fig_paper1_breakup.png', dpi=200, bbox_inches='tight')
print('[saved] fig_paper1_breakup.png  (x-y view, Moon as point, 8 equal-phase breakup points)')
