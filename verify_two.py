# -*- coding: utf-8 -*-
"""服务器验证: 修正后 eval_point(近月点±0.12d, dt~7s) 下,
点3(最坏点) 在 Δt=5.0d 和 7.78d 两处的碰撞概率(满样本500k + bootstrap CI)。
只跑这两个, 不动整张表。"""
import numpy as np, analysis_ldo as A
fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000
print('=== 修正后(±0.12d, dt~7s) 点3 @ %d碎片 ==='% n, flush=True)
print('参考旧(粗网格dt230s): 5.0d=1.79e-7, 7.78d=2.34e-7', flush=True)
for dt in [5.0, 7.78]:
    e = A.eval_point(POS[2], VEL[2], sc_t, sc_state, dt, n)
    P = 1 - np.exp(-(A.N_PHYS/n)*e.sum())
    rng = np.random.default_rng(0)
    Pb = np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0, n, n)].sum()) for _ in range(300)])
    print('Δt=%.2fd  P=%.4e  95%%CI=[%.3e, %.3e]  命中=%d'
          % (dt, P, np.percentile(Pb, 2.5), np.percentile(Pb, 97.5), int((e > 0).sum())), flush=True)
