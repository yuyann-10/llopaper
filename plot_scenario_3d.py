# -*- coding: utf-8 -*-
"""3D 视图: 当前 full scenario (旋转系) — 自由返回 + 100km 逆行 LDO + 近月单次穿越。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D_EM = 389703.0; MU = 0.01215058; R_M = 1738.0; R_E = 6378.0
EARTH = np.array([-MU, 0, 0]); MOON = np.array([1-MU, 0, 0])


def load(fn):
    d = pd.read_csv(fn)
    return d[['x_rot(km)', 'y_rot(km)', 'z_rot(km)']].values/D_EM


frt = load('cr3bp_freereturn_full.csv')      # 平面完整自由返回 (去程+返程)
ldo = load('cr3bp_ldo_target.csv')           # 3D 100km 逆行 LDO
crew = load('cr3bp_crew_freereturn.csv')     # 3D 近月单次穿越
ipf = int(np.argmin(np.linalg.norm(frt-MOON, axis=1)))
ipc = int(np.argmin(np.linalg.norm(crew-MOON, axis=1)))


def sphere(ax, c, r, color):
    u, w = np.mgrid[0:2*np.pi:24j, 0:np.pi:12j]
    ax.plot_surface(c[0]+r*np.cos(u)*np.sin(w), c[1]+r*np.sin(u)*np.sin(w),
                    c[2]+r*np.cos(w), color=color, alpha=0.6, linewidth=0)


fig = plt.figure(figsize=(15, 6.6))

# ---------- (a) 全局 3D ----------
ax = fig.add_subplot(121, projection='3d')
sphere(ax, EARTH, R_E/D_EM, 'royalblue')
sphere(ax, MOON, R_M/D_EM, '0.6')
ax.plot(frt[:ipf+1, 0], frt[:ipf+1, 1], frt[:ipf+1, 2], color='royalblue', lw=1.6,
        label='Crew free-return: outbound')
ax.plot(frt[ipf:, 0], frt[ipf:, 1], frt[ipf:, 2], color='crimson', lw=1.4,
        label='Crew free-return: return')
ax.plot(ldo[:600, 0], ldo[:600, 1], ldo[:600, 2], color='seagreen', lw=2.5,
        label='Target LDO (100 km)')
ax.scatter(*frt[ipf], c='red', s=80, marker='*', label='Perilune / 1st RVD')
ax.set_box_aspect((1, 1, 0.5))
ax.set_xlabel('x (DU)'); ax.set_ylabel('y (DU)'); ax.set_zlabel('z (DU)')
ax.set_title('(a) Full mission (rotating frame)')
ax.legend(fontsize=8, loc='upper left'); ax.view_init(elev=26, azim=-58)

# ---------- (b) 近月 3D 放大 (LDO + 单次穿越, 3D 平面倾角) ----------
ax2 = fig.add_subplot(122, projection='3d')
sphere(ax2, MOON, R_M/D_EM, '0.6')
ax2.plot(ldo[:600, 0], ldo[:600, 1], ldo[:600, 2], color='seagreen', lw=2.5,
         label='Target LDO (i=148.5°, retrograde)')
near = np.linalg.norm(crew-MOON, axis=1) < 0.03
ax2.plot(crew[near, 0], crew[near, 1], crew[near, 2], color='darkorange', lw=2,
         label='Crew single pass (i=153°)')
ax2.scatter(*crew[ipc], c='red', s=110, marker='*', label='Perilune / 1st RVD')
R = 0.018
ax2.set_xlim(MOON[0]-R, MOON[0]+R); ax2.set_ylim(-R, R); ax2.set_zlim(-R, R)
ax2.set_box_aspect((1, 1, 1))
ax2.set_xlabel('x (DU)'); ax2.set_ylabel('y (DU)'); ax2.set_zlabel('z (DU)')
ax2.set_title('(b) Zoom at Moon: LDO + single pass (3D, 4.46$^\\circ$ tilt)')
ax2.legend(fontsize=8, loc='upper left'); ax2.view_init(elev=18, azim=-50)

fig.suptitle('Two-RVD manned lunar mission — current full scenario (3D CR3BP)', fontsize=13)
fig.tight_layout(); fig.savefig('fig_scenario_3d.png', dpi=200)
print('[saved] fig_scenario_3d.png')
print(f'free-return perilune alt={np.linalg.norm(frt[ipf]-MOON)*D_EM-R_M:.1f} km; '
      f'crew pass perilune alt={np.linalg.norm(crew[ipc]-MOON)*D_EM-R_M:.1f} km')
