# -*- coding: utf-8 -*-
"""点3(最坏点) Δt=5.0~7.78d 细扫描(0.25d步), 修正网格(±0.12d, dt~7s), 满样本500k+CI。
断点续算: 跑过的存 sweep_server.npz, 重启自动跳过; 已预置 verify_two 的 5.0/7.78d 结果。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000
DTS = [float(x) for x in np.round(np.append(np.arange(5.0, 7.76, 0.25), 7.78), 3)]
CKPT = 'sweep_server.npz'

# 已跑过的(verify_two 服务器 500k 结果), 预置避免重复
done = {5.0:  (9.0479e-08, 8.812e-08, 9.267e-08, 6148),
        7.78: (8.6409e-08, 8.375e-08, 8.878e-08, 5903)}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())

for dt in DTS:
    if dt in done:
        print('skip Δt=%.2fd (已有 P=%.4e)' % (dt, done[dt][0]), flush=True)
        continue
    e = A.eval_point(POS[2], VEL[2], sc_t, sc_state, dt, n)
    P = 1 - np.exp(-(A.N_PHYS/n)*e.sum())
    rng = np.random.default_rng(0)
    Pb = np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0, n, n)].sum()) for _ in range(300)])
    done[dt] = (float(P), float(np.percentile(Pb, 2.5)), float(np.percentile(Pb, 97.5)), int((e > 0).sum()))
    np.savez(CKPT, done=np.array(done, dtype=object))
    print('RESULT Δt=%.2fd  P=%.4e  CI=[%.3e,%.3e]  命中=%d'
          % (dt, P, done[dt][1], done[dt][2], done[dt][3]), flush=True)

print('=== 汇总 (Δt, P) ===', flush=True)
for dt in sorted(done):
    print('  Δt=%.2fd  P=%.4e' % (dt, done[dt][0]), flush=True)
