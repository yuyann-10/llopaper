# -*- coding: utf-8 -*-
"""密集 Δt 扫描 0→3.1d (步长0.1d)。
场景: 着陆器在 LDO 解体, 而载人飞船【已发射/在自由返回途中】→ 无法取消, 研究单次近月穿越碰撞。
"飞船已发射" 等价 Δt ≤ 自由返回奔月段 2.911 d (Δt=0 解体在到达时, =2.911d 解体在发射时);
Δt 超过奔月段则飞船尚未发射、直接不发射 → 无碰撞。故物理相关区间为 Δt∈[0, ~2.9 d]。
点3最坏点, 修正网格(±0.12d, dt~7s), 500k+bootstrap CI, 断点续算。
预置 sweep_complete 已有点(0/1/2/2.6/3)直接跳过。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000
DTS = [round(float(x), 2) for x in np.arange(0.0, 3.101, 0.1)]   # 0.0,0.1,...,3.0,3.1
CKPT = 'sweep_dense.npz'

done = {}
# 预置: sweep_complete 已算过的同 Δt 点 (避免重复)
if os.path.exists('sweep_complete.npz'):
    z = np.load('sweep_complete.npz')
    have = {round(float(a), 2): float(b) for a, b in zip(z['dt'], z['P'])}
    for d in DTS:
        if d in have:
            done[d] = (have[d], np.nan, np.nan, -1)     # hits=-1 标记"预置/沿用"
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())

for dt in DTS:
    if dt in done:
        print('skip Δt=%.2fd (已有 P=%.4e)' % (dt, done[dt][0]), flush=True); continue
    e = A.eval_point(POS[2], VEL[2], sc_t, sc_state, dt, n)
    P = 1 - np.exp(-(A.N_PHYS/n)*e.sum())
    rng = np.random.default_rng(0)
    Pb = np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0, n, n)].sum()) for _ in range(300)])
    done[dt] = (float(P), float(np.percentile(Pb, 2.5)), float(np.percentile(Pb, 97.5)), int((e > 0).sum()))
    np.savez(CKPT, done=np.array(done, dtype=object))
    print('RESULT Δt=%.2fd  P=%.4e  CI=[%.3e,%.3e]  命中=%d'
          % (dt, P, done[dt][1], done[dt][2], done[dt][3]), flush=True)

# 完成: 存干净数组
ds = sorted(done); arr = np.array([[d]+list(done[d][:3]) for d in ds])
np.savez(CKPT, done=np.array(done, dtype=object),
         dt=arr[:, 0], P=arr[:, 1], P_lo=arr[:, 2], P_hi=arr[:, 3])
print('=== 0-3.1d 汇总 ===', flush=True)
for d in ds: print('  Δt=%.2fd  P=%.4e' % (d, done[d][0]), flush=True)
