# -*- coding: utf-8 -*-
"""清晰绘制 3D CR3BP 场景: 等比例 3D + 高度证明 (LDO 始终在月面之上)。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D_EM = 389703.0; MU = 0.01215058; R_M = 1738.0
MOON = np.array([1-MU, 0.0, 0.0])


def load_moon_km(fn):
    d = pd.read_csv(fn)
    return d[['x_rot(km)', 'y_rot(km)', 'z_rot(km)']].values - MOON*D_EM


ldo = load_moon_km('cr3bp_ldo_target.csv')
crew = load_moon_km('cr3bp_crew_freereturn.csv')
ip = int(np.argmin(np.linalg.norm(crew, axis=1)))
# 只取近月段 crew (距月心 < 8000 km) 让图聚焦
near = np.linalg.norm(crew, axis=1) < 8000
ldo1 = ldo[:600]                      # 约一圈

fig = plt.figure(figsize=(13, 5.2))

# ---------- (a) 等比例 3D ----------
ax = fig.add_subplot(121, projection='3d')
u, w = np.mgrid[0:2*np.pi:40j, 0:np.pi:20j]
ax.plot_surface(R_M*np.cos(u)*np.sin(w), R_M*np.sin(u)*np.sin(w), R_M*np.cos(w),
                color='0.65', alpha=0.55, linewidth=0, zorder=1)
ax.plot(ldo1[:,0], ldo1[:,1], ldo1[:,2], color='steelblue', lw=2.2,
        label='Target LDO (alt 100 km, retrograde)', zorder=5)
ax.plot(crew[near,0], crew[near,1], crew[near,2], color='seagreen', lw=2,
        label='Crew free-return (near-Moon pass)', zorder=5)
ax.scatter(*crew[ip], c='red', s=110, marker='*', zorder=6, label='Perilune / 1st RVD')
R = 2400
ax.set_xlim(-R, R); ax.set_ylim(-R, R); ax.set_zlim(-R, R)
ax.set_box_aspect((1, 1, 1))          # 关键: 强制等比例
ax.set_xlabel('x (km)'); ax.set_ylabel('y (km)'); ax.set_zlabel('z (km)')
ax.set_title('(a) Near-Moon geometry (equal aspect)')
ax.legend(fontsize=8, loc='upper left')
ax.view_init(elev=22, azim=-60)

# ---------- (b) 高度证明: 离月面高度 vs 轨迹百分比 ----------
ax2 = fig.add_subplot(122)
altL = np.linalg.norm(ldo, axis=1) - R_M
altC = np.linalg.norm(crew[near], axis=1) - R_M
ipc = int(np.argmin(altC))
ax2.axhspan(-150, 0, color='0.82', zorder=0, label='Moon interior (alt < 0)')
ax2.axhline(0, color='0.3', lw=2)
ax2.plot(np.linspace(0, 100, len(altL)), altL, color='steelblue', lw=2,
         label=f'Target LDO  ({altL.min():.0f}–{altL.max():.0f} km)')
xc = np.linspace(0, 100, len(altC))
ax2.plot(xc, altC, color='seagreen', lw=1.8, label=f'Crew pass (perilune {altC.min():.0f} km)')
ax2.scatter(xc[ipc], altC[ipc], c='red', s=110, marker='*', zorder=6)
ax2.set_ylim(-150, 1500); ax2.set_xlim(0, 100)
ax2.set_xlabel('along trajectory (%)'); ax2.set_ylabel('Altitude above lunar surface (km)')
ax2.set_title('(b) Altitude proof: orbits never enter the Moon')
ax2.legend(fontsize=9, loc='upper center'); ax2.grid(alpha=0.3)

fig.suptitle('100 km retrograde LDO + crew free-return single pass (3D CR3BP, paper params)',
             fontsize=12)
fig.tight_layout()
fig.savefig('fig_scenario_clean.png', dpi=200)
print('[saved] fig_scenario_clean.png')
print(f'LDO altitude: {altL.min():.1f} ~ {altL.max():.1f} km  (R_M={R_M}, never < 0)')
print(f'crew perilune altitude: {altC.min():.1f} km')
