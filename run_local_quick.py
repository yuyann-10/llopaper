import numpy as np, time
import analysis_ldo as A
A.N_SUB = 30000
fr=np.load('fragments_ldo.npz'); POS,VEL=fr['pos_nd'],fr['vel_nd']
sc_t,sc_state=A.load_sc()
PTS=list(range(POS.shape[0]))
# 覆盖 0-23d, 去掉 23d (已知≈0), 重点在峰区
DTS_ALL=[0.0, 2.0, 3.0, 5.0, 6.0, 8.0, 10.0, 14.0, 18.0]
print('N_SUB=%d | Δt=%s'%(A.N_SUB,DTS_ALL), flush=True)

def eval_fast(k, dt):
    """对大 Δt(>8d) 只取接近段窗口节省时间; 小 Δt 正常±4d。"""
    sc_t_use = sc_t
    sc_st_use = sc_state
    if dt > 8.0:
        # 只保留 t ∈ [-4d, +0.5d] (接近近月点段), 碎片已扩散对离开段无贡献
        mask = sc_t_use <= 0.5
        sc_t_use = sc_t_use[mask]; sc_st_use = sc_st_use[mask]
    return A.eval_point(POS[k], VEL[k], sc_t_use, sc_st_use, dt, A.N_SUB)

table=np.zeros((len(PTS),len(DTS_ALL))); t0=time.time()
for r,k in enumerate(PTS):
    for c,dt in enumerate(DTS_ALL):
        e=eval_fast(k, dt)
        table[r,c]=1-np.exp(-(A.N_PHYS/A.N_SUB)*e.sum())
    print('点%d [%.0fs]: '%(k+1,time.time()-t0)+' '.join('%.2e'%table[r,c] for c in range(len(DTS_ALL))),flush=True)
    np.save('quick_table.npy',table)
ri,ci=np.unravel_index(int(np.argmax(table)),table.shape)
print('\n最坏点=%d 峰Δt=%.1fd P=%.3e | 总时%.0fs'%(PTS[ri]+1,DTS_ALL[ci],table[ri,ci],time.time()-t0),flush=True)
print('DONE',flush=True)
