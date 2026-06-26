# -*- coding: utf-8 -*-
"""图8-扩展: 6个解体点的碰撞概率 vs 预警时间 Δt (多线 + 全局最坏高亮)。无标题。"""
import numpy as np, matplotlib.pyplot as plt

t   = np.load('quick_table.npy')
DTS = [0.0,2.0,3.0,5.0,6.0,8.0,10.0,14.0,18.0,23.0]
N_PTS = t.shape[0]
t = np.column_stack([t, np.zeros(N_PTS)])
floor = 1e-8
ri, ci = divmod(int(t.argmax()), t.shape[1])

fig, ax = plt.subplots(figsize=(8.5, 4.8))
colors = plt.cm.tab10(np.linspace(0, 0.6, N_PTS))
for r in range(N_PTS):
    Pp = np.where(t[r]>0, t[r], floor)
    lw = 2.2 if r == ri else 1.0
    zo = 5 if r == ri else 2
    ls = '-' if r == ri else '--'
    
    ax.plot(DTS, Pp, ls, lw=lw, color=colors[r], zorder=zo,
            label=f' {r+1}' + (' (worst)' if r==ri else ''))
    zero = t[r] == 0
    ax.scatter(np.array(DTS)[zero], np.full(zero.sum(), floor),
               marker='v', s=18, color=colors[r], zorder=zo)

ax.axvline(0.0,  ls=':', color='0.5', lw=0.8); ax.text(0.1, 5e-5, '$\\Delta t=0$\n(RVD)',    fontsize=10, color='0.5')
ax.axvline(2.60, ls=':', color='0.5', lw=0.8); ax.text(2.7, 5e-5, 'crew TLI\n(2.6d)', fontsize=10, color='0.5')
ax.axvline(23.0, ls=':', color='0.5', lw=0.8); ax.text(20, 5e-5, 'lander\nLOI (23d)', fontsize=10, color='0.5')


ax.set_yscale('log'); ax.set_ylim(floor*0.5, 5e-4)
ax.set_xlabel('$\\Delta t$  (breakup to 1st RVD, days)')
ax.set_ylabel('Collision probability  $P$')
ax.legend(fontsize=8, ncol=2, loc='upper right'); ax.grid(alpha=0.3, which='both')
fig.tight_layout(); fig.savefig('fig_paper8_allpts.png', dpi=200)
print('[saved] fig_paper8_allpts.png')