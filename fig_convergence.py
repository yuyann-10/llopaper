# -*- coding: utf-8 -*-
"""任务2a: 碰撞概率随 MC 样本数收敛曲线 + 95% 置信区间 (无标题)。
读 analysis_base.npz['e_worst'] (最坏点 per-fragment 期望撞击贡献), 自助重采样。
前提: e_worst 须在【有信号的 Δt(≈峰值2d 或 crew-TLI 2.6d)】算, 否则全 0。"""
import numpy as np
import matplotlib.pyplot as plt

d = np.load('analysis_base.npz')
e = np.asarray(d['e_worst']); N_PHYS = int(d['N_PHYS']); N = len(e)
print(f"e_worst: N={N}, 非零贡献={np.count_nonzero(e)}, 全量 P={1-np.exp(-(N_PHYS/N)*e.sum()):.3e}")

grid = np.unique(np.logspace(2.5, np.log10(N), 20).astype(int))
B = 400; rng = np.random.default_rng(0)
med, lo, hi = [], [], []
for n in grid:
    Ps = np.empty(B)
    for b in range(B):
        idx = rng.integers(0, N, n)
        Ps[b] = 1 - np.exp(-(N_PHYS/n)*e[idx].sum())     # 缩放到物理碎片数
    med.append(np.median(Ps)); lo.append(np.percentile(Ps,2.5)); hi.append(np.percentile(Ps,97.5))
med, lo, hi = map(np.asarray, (med, lo, hi))

fig, ax = plt.subplots(figsize=(7.2, 4.6))
ax.fill_between(grid, lo, hi, alpha=0.25, color='C3', label='95% CI (bootstrap)')
ax.plot(grid, med, '-o', color='C3', ms=4, label='median')
ax.axhline(med[-1], ls='--', color='k', lw=0.8, label=f'converged P = {med[-1]:.2e}')
ax.set_xscale('log'); ax.set_yscale('log')
ax.set_xlabel('Monte Carlo sample size  $N$')
ax.set_ylabel('Collision probability  $P$')
ax.legend(fontsize=9); ax.grid(alpha=0.3, which='both')
fig.tight_layout(); fig.savefig('fig_convergence.png', dpi=200)
print(f"[saved] fig_convergence.png  收敛 P={med[-1]:.3e}, 95%CI@maxN=[{lo[-1]:.3e},{hi[-1]:.3e}]")
