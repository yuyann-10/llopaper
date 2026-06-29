# -*- coding: utf-8 -*-
"""快速扫描: 每个解体点只把碎片传播一次, 所有 Δt 复用(对Δt向量化危险区积分)。
比逐Δt重新传播快~10×。先验证与 eval_point 一致再用于正式扫描。"""
import numpy as np, jax, jax.numpy as jnp
import analysis_ldo as A

def eval_alldt(pt_pos, pt_vel, sc_t, sc_state, DTS, n_sub, win=0.02, nw=600, batch=200):
    DTS = np.asarray(sorted(float(d) for d in DTS))
    tau = np.linspace(-win, win, nw)                       # 近月点窗口内相对时间(天)
    SCp = np.column_stack([np.interp(tau, sc_t, sc_state[:, k]) for k in range(3)])    # (nw,3) 飞船位置
    SCv = np.column_stack([np.interp(tau, sc_t, sc_state[:, k]) for k in range(3, 6)]) # (nw,3) 飞船速度
    dt_sec = (tau[1]-tau[0])*86400
    # 各Δt窗口绝对时间(>=0), 拼全局升序唯一 save 网格 + 每个Δt的gather索引/有效掩码
    absmat = DTS[:, None] + tau[None, :]                   # (n_dt, nw)
    vmask = absmat >= 0
    save_abs = np.unique(np.round(absmat[vmask], 9))       # 升序唯一
    gidx = np.searchsorted(save_abs, np.round(np.clip(absmat, 0, None), 9))
    gidx = np.clip(gidx, 0, len(save_abs)-1)
    save_ts = jnp.asarray(save_abs / A.tt_days)
    GIDX = jnp.asarray(gidx); VM = jnp.asarray(vmask)
    SCp_j, SCv_j = jnp.asarray(SCp), jnp.asarray(SCv)
    R2, RM2 = A.R_DZ_lu**2, A.R_M_LU**2; coef = A.AREA_SC_KM2/A.V_DZ_km3

    @jax.jit
    def batch_e(fb):
        tj = A.vprop(fb, A.ARGS, save_ts)                  # (nb, NSAVE, 6)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        sub = tj[:, GIDX, :]                               # (nb, n_dt, nw, 6)
        rel = sub[..., :3] - SCp_j[None, None]
        dmoon2 = jnp.sum((sub[..., :3] - A.MOON[None, None])**2, -1)
        indz = (jnp.sum(rel**2, -1) < R2) & (dmoon2 > RM2) & VM[None]
        vrel = jnp.linalg.norm(sub[..., 3:] - SCv_j[None, None], axis=-1)*A.VU
        e = jnp.sum(jnp.where(indz, vrel*coef, 0.0), axis=2)*dt_sec     # (nb, n_dt)
        hit = jnp.sum(jnp.any(indz, axis=2), axis=0)                    # (n_dt,)
        return jnp.sum(e, axis=0), hit
    frags = np.empty((n_sub, 6)); frags[:, :3] = pt_pos; frags[:, 3:] = pt_vel[:n_sub]
    fd = jnp.asarray(frags)
    E = np.zeros(len(DTS)); HIT = np.zeros(len(DTS), dtype=np.int64)
    from tqdm import tqdm
    for b in tqdm(range(0, n_sub, batch), desc='1次传播·全Δt', leave=False):
        e, hit = batch_e(fd[b:b+batch]); E += np.array(e); HIT += np.array(hit)
    P = 1 - np.exp(-(A.N_PHYS/n_sub)*E)
    return DTS, P, HIT


if __name__ == '__main__':       # 验证: 与 eval_point 对几个点
    fr = np.load('fragments_server.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
    sc_t, sc_state = A.load_sc(); n = 50_000
    test = [0.05, 0.5, 2.5]
    DTS, P, HIT = eval_alldt(POS[0], VEL[0], sc_t, sc_state, test, n)
    print('=== sweep_fast (一次传播) ===', flush=True)
    for d, p, h in zip(DTS, P, HIT): print('  Δt=%.3f P=%.4e 命中=%d' % (d, p, h), flush=True)
    print('=== eval_point (逐Δt, 对照) ===', flush=True)
    for d in test:
        e = A.eval_point(POS[0], VEL[0], sc_t, sc_state, d, n)
        print('  Δt=%.3f P=%.4e 命中=%d' % (d, 1-np.exp(-(A.N_PHYS/n)*e.sum()), int((e > 0).sum())), flush=True)
