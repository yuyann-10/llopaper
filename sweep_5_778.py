# -*- coding: utf-8 -*-
"""点3(最坏点) Δt=5.0~7.78d 细扫描(0.25d), 修正网格, 看曲线是平台还是有结构(深谷)。
100k样本(够看形状); 每点即时打印。"""
import numpy as np, analysis_ldo as A
fr=np.load('fragments_ldo.npz'); POS,VEL=fr['pos_nd'],fr['vel_nd']
sc_t,sc_state=A.load_sc(); n=100_000
DTS=np.round(np.append(np.arange(5.0,7.76,0.25),7.78),3)
print('=== 点3 Δt=5.0~7.78d 细扫描 (修正网格dt~7s, %dk) ==='%(n//1000),flush=True)
out=[]
for dt in DTS:
    e=A.eval_point(POS[2],VEL[2],sc_t,sc_state,float(dt),n)
    P=1-np.exp(-(A.N_PHYS/n)*e.sum())
    out.append((float(dt),float(P),int((e>0).sum())))
    np.save('sweep_5_778.npy',np.array(out))
    print('RESULT Δt=%.2fd  P=%.4e  命中=%d'%(dt,P,int((e>0).sum())),flush=True)
print('RESULT done',flush=True)
