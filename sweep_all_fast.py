# -*- coding: utf-8 -*-
"""快版全扫: 6点 × Δt(尖峰区0-0.3d加密0.0125d + 0.3-3.5d粗0.1d) + 负段6点。
正段用 eval_alldt(每点只传播一次, ~10×加速); 负段用 eval_point(win=None, 返回段~0)。逐项断点续算。"""
import os
import numpy as np
import analysis_ldo as A
from sweep_fast import eval_alldt

f = 'fragments_server.npz' if os.path.exists('fragments_server.npz') else 'fragments_ldo.npz'
fr = np.load(f); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc(); n = 500_000
PTS = [0, 1, 2, 3, 4, 5]
DT_POS = sorted(set([round(float(x), 4) for x in np.arange(0.0, 0.3001, 0.0125)] +
                    [round(float(x), 2) for x in np.arange(0.3, 3.501, 0.1)]))
DT_NEG = [-3.0, -2.0, -1.0, -0.5, -0.2, -0.05]
CKPT = 'sweep_all_fast.npz'
done = {}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())

def save():
    np.savez(CKPT, done=np.array(done, dtype=object))

# --- 正段: 每点一次传播覆盖全部 Δt ---
print('正段 Δt 点数=%d, 解体点 %d 个' % (len(DT_POS), len(PTS)), flush=True)
for pt in PTS:
    if ('pos', pt) in done:
        print('skip 正段 点%d' % (pt+1), flush=True); continue
    dts, P, HIT = eval_alldt(POS[pt], VEL[pt], sc_t, sc_state, DT_POS, n, batch=400)
    done[('pos', pt)] = (np.array(dts), np.array(P), np.array(HIT)); save()
    im = int(np.argmax(P))
    print('RES 正段 点%d 峰 P=%.3e @Δt=%.4f (命中%d)' % (pt+1, P[im], dts[im], HIT[im]), flush=True)

# --- 负段: 6点 win=None (返回段, 预计~0) ---
for pt in PTS:
    for dt in DT_NEG:
        k = ('neg', pt, round(dt, 2))
        if k in done:
            continue
        e = A.eval_point(POS[pt], VEL[pt], sc_t, sc_state, dt, n, win_half=None)
        done[k] = (float(1-np.exp(-(A.N_PHYS/n)*e.sum())), int((e > 0).sum())); save()
        print('RES 负段 点%d Δt=%.2f P=%.3e 命中=%d' % (pt+1, dt, done[k][0], done[k][1]), flush=True)

# --- 汇总: 各点正段峰值 + 本段最坏点 ---
print('\n=== 各点 0-3.5d 峰值 ===', flush=True)
best = None
for pt in PTS:
    if ('pos', pt) not in done:
        continue
    dts, P, _ = done[('pos', pt)]; im = int(np.argmax(P))
    print('  点%d 峰 P=%.3e @Δt=%.4fd' % (pt+1, P[im], dts[im]), flush=True)
    if best is None or P[im] > best[1]:
        best = (pt, P[im], dts[im])
if best:
    print('>>> 本段最坏点 = 点%d (P=%.3e @Δt=%.4fd)' % (best[0]+1, best[1], best[2]), flush=True)
