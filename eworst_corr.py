# -*- coding: utf-8 -*-
"""修正网格下 点3@Δt=5.0d 的 per-fragment 贡献 e_i (供收敛图重画)。"""
import numpy as np, analysis_ldo as A
fr=np.load('fragments_ldo.npz'); POS,VEL=fr['pos_nd'],fr['vel_nd']
sc_t,sc_state=A.load_sc(); n=500_000
e=A.eval_point(POS[2],VEL[2],sc_t,sc_state,5.0,n)
np.savez('eworst_corr.npz', e_worst=e, N_PHYS=A.N_PHYS, dt_worst=5.0, worst=2)
print('RESULT eworst_corr.npz saved  P=%.4e'%(1-np.exp(-(A.N_PHYS/n)*e.sum())),flush=True)
