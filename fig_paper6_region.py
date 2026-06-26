# -*- coding: utf-8 -*-
"""图6 (重做): 完整绕月自由返回轨道的 10km "保护区域" 管 — 3D, 无量纲坐标。
真实 10km 管在地月尺度下=线, 故管半径按示意放大显示。无标题。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D_EM = 389703.0; MU = 0.01215058; R_E = 6378.0; R_M = 1738.0
EARTH = np.array([-MU, 0, 0]); MOON = np.array([1-MU, 0, 0])

# 完整自由返回 (地->月->地 figure-8), 无量纲 DU
d = pd.read_csv('cr3bp_freereturn_full.csv')
P = d[['x_rot(km)','y_rot(km)','z_rot(km)']].values / D_EM      # (N,3) DU
P = P[::3]                                                       # 抽稀, 减小网格
ip = int(np.argmin(np.linalg.norm(P-MOON, axis=1)))             # 近月点
# 按跳变(数据里出/返程拼接的假线)切成连续段
jumps = np.where(np.linalg.norm(np.diff(P, axis=0), axis=1) > 0.1)[0] + 1
segments = np.split(P, jumps)

TUBE_TRUE = 10.0                         # 真实保护区半径 km
TUBE_R = 0.006                          # 示意显示半径 DU (调此值控制粗细)
th = np.linspace(0, 2*np.pi, 28)
cos, sin = np.cos(th)[None, :], np.sin(th)[None, :]

fig = plt.figure(figsize=(9, 7.5))
ax = fig.add_subplot(111, projection='3d')
for seg in segments:
    if len(seg) < 3:
        continue
    T = np.gradient(seg, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    N1 = np.cross(T, [0, 0, 1.0]); N1 /= np.linalg.norm(N1, axis=1, keepdims=True)
    N2 = np.cross(T, N1)
    X = seg[:, 0:1] + TUBE_R*(cos*N1[:, 0:1] + sin*N2[:, 0:1])
    Y = seg[:, 1:2] + TUBE_R*(cos*N1[:, 1:2] + sin*N2[:, 1:2])
    Z = seg[:, 2:3] + TUBE_R*(cos*N1[:, 2:3] + sin*N2[:, 2:3])
    ax.plot_surface(X, Y, Z, color='orange', alpha=0.3, linewidth=0, shade=False)
    ax.plot(seg[:, 0], seg[:, 1], seg[:, 2], color='seagreen', lw=2.5, zorder=10)
ax.plot([], [], color='seagreen', lw=2.5, label='Free-return (nominal)')
ax.scatter(*EARTH, c='royalblue', s=120, label='Earth')
ax.scatter(*MOON, c='0.5', s=80, label='Moon')
ax.scatter(*P[ip], c='red', s=110, marker='*', label='Perilune / 1st RVD')
ax.plot([], [], color='orange', lw=8, alpha=0.4,
        label=f'Protection region ({TUBE_TRUE:.0f} km, schematic)')
from matplotlib.ticker import FormatStrFormatter
ax.set_zlim(-0.065, 0.065); ax.set_zticks([-0.05, 0, 0.05])       # z 轴稀疏, 2位小数
ax.zaxis.set_major_formatter(FormatStrFormatter('%.2f'))
ax.set_xlabel('x (DU)', labelpad=14); ax.set_ylabel('y (DU)', labelpad=14); ax.set_zlabel('z (DU)', labelpad=10)
ax.set_box_aspect((1, 1, 0.5))
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=13)
ax.view_init(elev=32, azim=-60)
fig.tight_layout(); fig.savefig('fig_paper6_region.png', dpi=200, bbox_inches='tight')
print(f'[saved] fig_paper6_region.png  (3D 完整自由返回 + {TUBE_TRUE:.0f}km 保护管示意, 无量纲)')
