# -*- coding: utf-8 -*-
"""图6 (重做): 自由返回轨道全程 + "保护区域"管 示意图。
全程：从载人TLI到近月再到返回，全轨道展示而不是仅近月附近。
管子半径画大（示意），否则看起来像一条线。
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D_EM = 389703.0; MU = 0.01215058; R_M = 1738.0
MOON = np.array([1-MU, 0, 0])

# 全程轨道（cr3bp_crew_freereturn.csv 已经是载人自由返回全程 -4天到+4天）
crew = pd.read_csv('cr3bp_crew_freereturn.csv')[['x_rot(km)','y_rot(km)','z_rot(km)']].values
C = crew                                                  # 全程
ip = int(np.argmin(np.linalg.norm(C-MOON*D_EM, axis=1)))  # 近月点索引

# 沿全程轨迹法向偏移构造保护管 (2D 投影 x-y)
P = C[:, :2]
d = np.gradient(P, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True)
n = np.column_stack([-d[:,1], d[:,0]])                     # 法向
TUBE = 2000.0                                               # 管半径 500 km (示意，便于可视化)
up = P + TUBE*n; dn = P - TUBE*n

fig, ax = plt.subplots(figsize=(9, 7))
ax.add_patch(plt.Circle(MOON[:2]*D_EM, R_M, color='0.6', zorder=2, label='Moon'))
ax.fill(np.concatenate([up[:,0], dn[::-1,0]]), np.concatenate([up[:,1], dn[::-1,1]]),
        color='orange', alpha=0.3, zorder=3, label='Protection region (tube)')
ax.plot(P[:,0], P[:,1], color='seagreen', lw=1.5, zorder=4, label='Free-return (nominal)')
ax.scatter(*C[ip,:2], c='red', s=80, marker='*', zorder=5, label='Perilune / 1st RVD')
ax.set_aspect('equal'); ax.set_xlabel('x (km)'); ax.set_ylabel('y (km)')
ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig('fig_paper6_region.png', dpi=200)
print('[saved] fig_paper6_region.png  (全程自由返回保护管, TUBE=%.0f km, 近月点高度=%.0f km)'
      % (TUBE, np.linalg.norm(C[ip]-MOON*D_EM)-R_M))
