# -*- coding: utf-8 -*-
"""点3 @ Δt=6.3d (旧表"深谷"处), 修正网格满样本, 验证平台 vs 深谷。"""
import numpy as np, analysis_ldo as A
fr=np.load('fragments_ldo.npz'); POS,VEL=fr['pos_nd'],fr['vel_nd']
sc_t,sc_state=A.load_sc(); n=500_000
e=A.eval_point(POS[2],VEL[2],sc_t,sc_state,6.3,n)
P=1-np.exp(-(A.N_PHYS/n)*e.sum())
rng=np.random.default_rng(0)
Pb=np.array([1-np.exp(-(A.N_PHYS/n)*e[rng.integers(0,n,n)].sum()) for _ in range(300)])
print('RESULT 点3 Δt=6.3d  P=%.4e  95%%CI=[%.3e,%.3e]  命中=%d'%(P,np.percentile(Pb,2.5),np.percentile(Pb,97.5),int((e>0).sum())),flush=True)
print('RESULT 旧表6.3d附近≈1e-11(深谷); 若~9e-8则是平台、深谷为假象',flush=True)
