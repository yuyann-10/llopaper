# -*- coding: utf-8 -*-
"""本地: 0-0.2d 加密(0.025d) 锁定各点新鲜云尖峰真峰位。
用服务器同款 500k 碎片(fragments_server.npz)保证与 stage1 一致。6点 × 9个Δt, win=0.12。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_server.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc(); n = 500_000
PTS = [0, 1, 2, 3, 4, 5]
DTS = [round(float(x), 3) for x in np.arange(0.0, 0.2001, 0.025)]   # 0,0.025,...,0.2 (9点)
CKPT = 'sweep_fine02.npz'
done = {}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())
for pt in PTS:
    for dt in DTS:
        k = (pt, round(dt, 3))
        if k in done:
            print('skip 点%d Δt=%.3f' % (pt+1, dt), flush=True); continue
        e = A.eval_point(POS[pt], VEL[pt], sc_t, sc_state, dt, n, win_half=0.12)
        done[k] = (float(1-np.exp(-(A.N_PHYS/n)*e.sum())), int((e > 0).sum()))
        np.savez(CKPT, done=np.array(done, dtype=object))
        print('RES 点%d Δt=%.3f  P=%.3e  命中=%d' % (pt+1, dt, done[k][0], done[k][1]), flush=True)
print('=== 各点 0-0.2d 尖峰 ===', flush=True)
for pt in PTS:
    ps = [(dt, done[(pt, round(dt, 3))][0]) for dt in DTS if (pt, round(dt, 3)) in done]
    if ps:
        dtm, pm = max(ps, key=lambda x: x[1]); print('  点%d 尖峰 P=%.3e @ Δt=%.3fd' % (pt+1, pm, dtm), flush=True)
