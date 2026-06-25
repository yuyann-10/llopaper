# -*- coding: utf-8 -*-
"""图8 (主图): 碰撞概率 vs 预警时间 Δt。
优先读 analysis_dt.npz (服务器精确版); 回退到 coarse_dt.npy (本地粗版)。无标题。"""
import numpy as np
import matplotlib.pyplot as plt
import os

# ---- 载入数据 ----
if os.path.exists('analysis_dt.npz'):
    d = np.load('analysis_dt.npz')
    dt, P = d['dt'], d['P']
    P_lo = d.get('P_lo', None); P_hi = d.get('P_hi', None)
    mrvd  = float(d.get('marker_rvd',  0.0))
    mtli  = float(d.get('marker_tli',  2.6))
    mpark = float(d.get('marker_park', 23.0))
    src = 'analysis_dt.npz'
else:
    raw = np.load('coarse_dt.npy')   # shape (N,2): Δt, P
    dt, P = raw[:,0], raw[:,1]
    P_lo = P_hi = None
    mrvd, mtli, mpark = 0.0, 2.6, 23.0
    src = 'coarse_dt.npy (粗版)'

floor = max(P[P>0].min() * 0.3, 1e-8) if any(P>0) else 1e-8
Pp = np.where(P > 0, P, floor)
imax = int(np.argmax(P))

fig, ax = plt.subplots(figsize=(8, 4.8))
if P_lo is not None and P_hi is not None:
    Plo = np.where(P_lo > 0, P_lo, floor); Phi = np.where(P_hi > 0, P_hi, floor)
    ax.fill_between(dt, Plo, Phi, alpha=0.22, color='C3', label='95% CI (bootstrap)')
ax.plot(dt, Pp, '-o', color='C3', ms=5, lw=1.6, label='Collision probability')
zero = P == 0
if zero.any():
    ax.scatter(dt[zero], np.full(zero.sum(), floor), facecolors='none', edgecolors='C3',
               s=60, zorder=5, label='$P = 0$')

# 历元节点
for x, lbl, c in [(mrvd,'1st RVD ($\\Delta t=0$)','C0'),
                   (mtli,'crew TLI','C2'),
                   (mpark,'lander LOI','C4')]:
    ax.axvline(x, ls='--', color=c, lw=1, alpha=0.75)
    ax.text(x+0.15, ax.get_ylim()[1] if ax.get_yscale()=='linear' else Pp.max()*1.5,
            lbl, rotation=90, va='top', ha='left', fontsize=8, color=c)

# 峰标注
ax.annotate(f'peak  $\\Delta t$ = {dt[imax]:.1f} d\n$P$ = {P[imax]:.2e}',
            (dt[imax], Pp[imax]), xytext=(15, 5), textcoords='offset points',
            fontsize=9, color='C3', arrowprops=dict(arrowstyle='->', color='C3'))

ax.set_yscale('log')
ax.set_xlabel('Warning time  $\\Delta t$  = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  $P$')
ax.grid(alpha=0.3, which='both'); ax.legend(fontsize=8, loc='lower right')
fig.tight_layout()
fig.savefig('fig_paper8_dt.png', dpi=200)
print(f'[saved] fig_paper8_dt.png  (src={src})')
_p0 = '0 (碎片云未扩散, 非上界)' if P[0] == 0 else f'{P[0]:.3e}'
print(f'峰值: Δt={dt[imax]:.1f}d  P={P[imax]:.3e}  Δt=0 P={_p0}')
