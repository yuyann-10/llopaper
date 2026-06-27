# 保存为 plot_sc_traj.py, 在 LLO_paper 目录下运行
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm

d = np.load('figdata_cache.npz', allow_pickle=True)
counts = d['fig9_counts']
x = d['sc_pkm_x']   # 月心, km
y = d['sc_pkm_y']
tgrid = d['tgrid']

# 交会窗口索引
nz = np.where(counts > 0)[0]
i_start, i_end = nz[0], nz[-1]

# 画图范围: 窗口前后各扩一点
pad = max(5, (i_end - i_start) // 2)
i0 = max(0, i_start - pad)
i1 = min(len(x) - 1, i_end + pad)

fig, ax = plt.subplots(figsize=(6, 6))
ax.set_aspect('equal')

# 全轨迹淡色
ax.plot(x[i0:i1+1], y[i0:i1+1], 'C0', lw=1.0, alpha=0.3, label='SC trajectory')

# 交会段按 count 连续着色
x_seg = x[i_start:i_end+1]; y_seg = y[i_start:i_end+1]
idx_seg = np.arange(i_start, i_end+1)
c_seg = counts[idx_seg]
points = np.array([x_seg, y_seg]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)
norm = LogNorm(vmin=1, vmax=c_seg.max())
lc = LineCollection(segments, cmap='YlOrRd', norm=norm, lw=3, zorder=4)
lc.set_array(np.clip(c_seg[:-1], 1, None))
ax.add_collection(lc)
cbar = fig.colorbar(lc, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label('fragment count', fontsize=22)

# 聚焦交会段
x_mid = (x_seg.min() + x_seg.max()) / 2
y_mid = (y_seg.min() + y_seg.max()) / 2
half = max(np.ptp(x_seg), np.ptp(y_seg)) / 2 * 1.5
ax.set_xlim(x_mid - half, x_mid + half)
ax.set_ylim(y_mid - half, y_mid + half)

# 起止标记
ax.scatter(x[i_start], y[i_start], c='C2', s=10, zorder=5, label=f'start (t={tgrid[i_start]:.4f}d)')
ax.scatter(x[i_end],   y[i_end],   c='C4', s=10, zorder=5, marker='s', label=f'end (t={tgrid[i_end]:.4f}d)')

# 月球→近月点虚线
dm = np.sqrt(x_seg**2 + y_seg**2)
i_peri = np.argmin(dm)
ax.plot([0, x_seg[i_peri]], [0, y_seg[i_peri]], 'k--', lw=1, alpha=0.5, label='Moon→perilune')

 
ax.set_xlabel('x (km, Moon-centered)'); ax.set_ylabel('y (km, Moon-centered)')
ax.legend(fontsize=12, loc='upper left')
ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig('fig_sc_traj_intersection.png', dpi=200)
print('[saved] fig_sc_traj_intersection.png')