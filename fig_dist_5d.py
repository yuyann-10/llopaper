# -*- coding: utf-8 -*-
"""所有 6 个解体点 解体后 5d (峰值 Δt) 的碎片空间分布散点图 (像图4, 排除撞月)。
叠加 LDO 环 + 航天器近月点, 看为何 5d 是峰。无标题。"""
import numpy as np
import pandas as pd
import jax.numpy as jnp
import matplotlib.pyplot as plt
import analysis_ldo as A

N_SNAP = 20000          # 每点散点碎片数
T_SNAP = 5.0            # 解体后天数 (峰值 Δt)
LIM = 10000.0          # 视野半径 km (月心)
BATCH = 5000

D_EM = A.D_EM; MOON = np.array([1-A.MU, 0, 0]); R_M = 1738.0
fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
npts = POS.shape[0]
# LDO 环 + 航天器近月点 (上下文)
ldo = pd.read_csv('cr3bp_ldo_target.csv')[['x_rot(km)','y_rot(km)','z_rot(km)']].values - MOON*D_EM
crew = pd.read_csv('cr3bp_crew_freereturn.csv')[['x_rot(km)','y_rot(km)','z_rot(km)']].values - MOON*D_EM
peri = crew[np.argmin(np.linalg.norm(crew, axis=1))]

ts = jnp.asarray(np.array([T_SNAP])/A.tt_days)

def prop_to(pos, vel, n):
    frags = np.empty((n,6)); frags[:,:3]=pos; frags[:,3:]=vel[:n]
    fd = jnp.asarray(frags); out=[]
    for b in range(int(np.ceil(n/BATCH))):
        s,en=b*BATCH,min((b+1)*BATCH,n)
        tj = A.vprop(fd[s:en], A.ARGS, ts)
        out.append(jnp.where(jnp.isnan(tj), 1e6, tj))
    return np.asarray(jnp.concatenate(out))[:,0,:]      # (n,6) at T_SNAP, 旋转系无量纲

fig, axes = plt.subplots(2, 3, figsize=(13, 8.6))
for k, ax in enumerate(axes.ravel()):
    if k >= npts:
        ax.axis('off'); continue
    s = prop_to(POS[k], VEL[k], N_SNAP)
    P = (s[:, :3] - MOON) * D_EM                          # 月心 km
    dist = np.linalg.norm(P, axis=1)
    alive = (dist > R_M) & (dist < 5e4)                  # 排除撞月与发散
    ax.plot(ldo[:62,0], ldo[:62,1], color='0.8', lw=1, zorder=1)        # LDO 环
    ax.scatter(0, 0, c='k', marker='+', s=50, zorder=3)                 # 月心
    ax.scatter(P[alive,0], P[alive,1], s=0.5, c='C0', alpha=0.25, zorder=2)
    ax.scatter(peri[0], peri[1], c='red', marker='*', s=70, zorder=4)   # 航天器近月点
    ax.set_xlim(-LIM, LIM); ax.set_ylim(-LIM, LIM); ax.set_aspect('equal')
    ax.tick_params(labelsize=15)
    ax.text(0.03, 0.95, f'Breakup Location {k+1}', transform=ax.transAxes,
            fontsize=14, va='top', ha='left')
    ax.text(0.03, 0.04, f'{alive.sum()/N_SNAP*100:.0f}% survive', transform=ax.transAxes,
            fontsize=12, va='bottom', color='0.4')
    if k//3 == 1: ax.set_xlabel('x (km, Moon)', fontsize=17)
    if k % 3 == 0: ax.set_ylabel('y (km, Moon)', fontsize=17)
fig.tight_layout(); fig.savefig('fig_dist_5d.png', dpi=200)
print(f'[saved] fig_dist_5d.png  (6点 @ {T_SNAP}d, 红星=航天器近月点)')
