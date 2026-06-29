# -*- coding: utf-8 -*-
"""10–23d 密扫(0.5d步长), 确认有无真实次峰。断点续算。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000

DTS = list(np.round(np.arange(10.0, 23.1, 0.5), 2))  # 10~23d, 0.5d步, 27点

CKPT = 'sweep_tail.npz'
done = {}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())
    print(f'[恢复] 已完成 {len(done)} 个点: {sorted(done.keys())}')

for dt in DTS:
    if dt in done:
        print(f'skip Δt={dt:.1f}d (P={done[dt][0]:.4e})', flush=True)
        continue
    e = A.eval_point(POS[2], VEL[2], sc_t, sc_state, dt, n)
    P = 1 - np.exp(-(A.N_PHYS/n)*e.sum())
    rng = np.random.default_rng(0)
    Pb = np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0,n,n)].sum()) for _ in range(300)])
    done[dt] = (float(P), float(np.percentile(Pb,2.5)), float(np.percentile(Pb,97.5)), int((e>0).sum()))
    np.savez(CKPT, done=np.array(done, dtype=object))
    print(f'RESULT Δt={dt:.1f}d  P={P:.4e}  CI=[{done[dt][1]:.3e},{done[dt][2]:.3e}]  命中={done[dt][3]}', flush=True)

print('\n=== 汇总 ===')
for dt in sorted(done):
    P,lo,hi,hits = done[dt]
    flag = ' <-- 峰?' if P > 1e-9 else ''
    print(f'  Δt={dt:5.1f}d  P={P:.4e}  命中={hits}{flag}')
