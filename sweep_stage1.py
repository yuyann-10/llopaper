# -*- coding: utf-8 -*-
"""阶段1: 找 0-3.5d 这段(着陆器解体时载人飞船已发射)的最坏解体点。
6 个解体点 × 粗 Δt(0,0.25,...,3.5; 15点) × 500k, 只算 P+命中(不做CI, 排序够用)。
负段(返回段): 仅点3, win_half=None 真算(预计~0)。逐(点,Δt)断点续算。
跑完打印各点峰值 + 本段最坏点 -> 交给阶段2细扫(0.1d,1M)。"""
import os
import numpy as np
import analysis_ldo as A

fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()
n = 500_000
PTS = [0, 1, 2, 3, 4, 5]
DT_POS = [round(float(x), 2) for x in np.arange(0.0, 3.501, 0.25)]   # 0,0.25,...,3.5 (15点)
DT_NEG = [-3.0, -2.0, -1.0, -0.5, -0.2, -0.05]                       # 返回段(仅点3)
CKPT = 'sweep_stage1.npz'

done = {}
if os.path.exists(CKPT):
    done = dict(np.load(CKPT, allow_pickle=True)['done'].item())

def run(pt, dt, wh):
    e = A.eval_point(POS[pt], VEL[pt], sc_t, sc_state, dt, n, win_half=wh)
    return (float(1 - np.exp(-(A.N_PHYS/n)*e.sum())), int((e > 0).sum()))

def save():
    np.savez(CKPT, done=np.array(done, dtype=object))

# --- 负段: 仅点3, win=None (真算返回段) ---
for dt in DT_NEG:
    k = (2, round(dt, 2))
    if k in done:
        print('skip 点3 Δt=%.2f (P=%.3e)' % (dt, done[k][0]), flush=True); continue
    done[k] = run(2, dt, None); save()
    print('RES 点3 Δt=%6.2f  P=%.3e  命中=%d' % (dt, done[k][0], done[k][1]), flush=True)

# --- 正段: 6点 × 粗Δt, win=0.12 ---
for pt in PTS:
    for dt in DT_POS:
        k = (pt, round(dt, 2))
        if k in done:
            print('skip 点%d Δt=%.2f (P=%.3e)' % (pt+1, dt, done[k][0]), flush=True); continue
        done[k] = run(pt, dt, 0.12); save()
        print('RES 点%d Δt=%6.2f  P=%.3e  命中=%d' % (pt+1, dt, done[k][0], done[k][1]), flush=True)

# --- 汇总: 各点正段峰值 + 本段最坏点 ---
print('\n=== 各点 0-3.5d 峰值 ===', flush=True)
best = None
for pt in PTS:
    ps = [(dt, done[(pt, round(dt, 2))][0]) for dt in DT_POS if (pt, round(dt, 2)) in done]
    if not ps:
        continue
    dtm, pm = max(ps, key=lambda x: x[1])
    print('  点%d  峰值 P=%.3e @ Δt=%.2fd' % (pt+1, pm, dtm), flush=True)
    if best is None or pm > best[1]:
        best = (pt, pm, dtm)
if best:
    print('>>> 本段最坏点 = 点%d  (P=%.3e @ Δt=%.2fd)  -> 阶段2细扫此点' % (best[0]+1, best[1], best[2]), flush=True)
