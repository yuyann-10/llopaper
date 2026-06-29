# -*- coding: utf-8 -*-
"""验证 analysis_dt.npz 两端的可疑振荡点 (旧粗网格算的), 用修正细网格重算。
断点续算: 跑过的存 sweep_outer.npz, 重启自动跳过。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000

# 左端 (平台前) + 右端 (平台后振荡区) 全部重算
DTS = [0.0, 1.0, 2.0, 2.6, 3.0, 4.5,          # 左端
       8.5, 9.0, 10.0, 12.0, 14.0, 16.0, 18.0, 23.0]  # 右端振荡区

CKPT = 'sweep_outer.npz'
done = {}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())
    print(f'[恢复] 已完成 {len(done)} 个点: {sorted(done.keys())}')

for dt in DTS:
    if dt in done:
        print(f'skip Δt={dt:.2f}d (P={done[dt][0]:.4e})', flush=True)
        continue
    e = A.eval_point(POS[2], VEL[2], sc_t, sc_state, dt, n)
    P  = 1 - np.exp(-(A.N_PHYS/n)*e.sum())
    rng = np.random.default_rng(0)
    Pb = np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0,n,n)].sum()) for _ in range(300)])
    done[dt] = (float(P), float(np.percentile(Pb,2.5)), float(np.percentile(Pb,97.5)), int((e>0).sum()))
    np.savez(CKPT, done=np.array(done, dtype=object))
    print(f'RESULT Δt={dt:.2f}d  P={P:.4e}  CI=[{done[dt][1]:.3e},{done[dt][2]:.3e}]  命中={done[dt][3]}', flush=True)

print('\n=== 汇总 ===')
for dt in sorted(done):
    P,lo,hi,hits = done[dt]
    print(f'  Δt={dt:5.2f}d  P={P:.4e}  CI=[{lo:.3e},{hi:.3e}]  命中={hits}')
