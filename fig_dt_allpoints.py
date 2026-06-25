# -*- coding: utf-8 -*-
"""各解体点的 碰撞概率 vs 预警时间 Δt 曲线叠加 (验证: 每个点峰值 Δt 是否不同)。
读 analysis_base.npz 的 table[点×Δt], dts, pts。无标题。"""
import numpy as np
import matplotlib.pyplot as plt

d = np.load('analysis_base.npz')
table, dts, pts = d['table'], d['dts'], d['pts']      # table: (n点, nΔt)
markers = d['markers'] if 'markers' in d else [0.0, 2.6, 23.0]

floor = 1e-8
fig, ax = plt.subplots(figsize=(8.5, 5))
peaks = []
for r, k in enumerate(pts):
    P = table[r]
    Pp = np.where(P > 0, P, floor)
    line, = ax.plot(dts, Pp, '-o', ms=3, lw=1.3, label=f'{k+1}')
    ci = int(np.argmax(P))
    peaks.append((k+1, dts[ci], P[ci]))
    ax.scatter(dts[ci], max(P[ci], floor), s=90, marker='*',
               color=line.get_color(), zorder=6, edgecolor='k', linewidth=0.4)

# 历元节点
for x, lbl, c in [(float(markers[0]), '1st RVD', '0.4'),
                  (float(markers[1]), 'crew TLI', '0.4'),
                  (float(markers[2]), 'lander LOI', '0.4')]:
    ax.axvline(x, ls=':', color=c, lw=0.8, alpha=0.7)

ax.set_yscale('log')
ax.set_xlabel('Warning time  $\\Delta t$  = breakup → 1st RVD  (days)')
ax.set_ylabel('Collision probability  $P$')
ax.grid(alpha=0.3, which='both'); ax.legend(title='Breakup Location', fontsize=8, ncol=2, loc='lower right')
fig.tight_layout(); fig.savefig('fig_dt_allpoints.png', dpi=200)
print('[saved] fig_dt_allpoints.png')
print('各点峰值 (点, Δt_peak[d], P_peak):')
for kp, dtp, pp in peaks:
    print(f'  点{kp}: Δt={dtp:5.2f}d  P={pp:.3e}')
dtps = [p[1] for p in peaks]
print(f'峰值 Δt 范围: {min(dtps):.1f} ~ {max(dtps):.1f} d  '
      f'{"-> 各点峰值Δt不同, 相位敏感!" if max(dtps)-min(dtps) > 1 else "-> 峰值Δt相近"}')
