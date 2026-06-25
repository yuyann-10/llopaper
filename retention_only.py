# -*- coding: utf-8 -*-
"""单独计算残留率: 各解体点碎片在月球附近的留存比例 vs 时间 (图3)"""
import numpy as np, pandas as pd
import jax, jax.numpy as jnp
from diffrax import diffeqsolve, PIDController, ODETerm, Dopri5, SaveAt
import equinox as eqx
from tqdm import tqdm
jax.config.update("jax_enable_x64", True)

# ---- 常量 (复用 analysis_ldo) ----
MU = 0.01215058; D_EM = 389703.0
VU = 1.01755178; TU_S = 382981.0; tt_days = TU_S/86400.0
M = 5.9722e24 + 7.346e22; mu3 = 1.989e30/M; R3 = 149.6e9/(D_EM*1e3); n_s = 0.9252
R_M_LU = 1738.0/D_EM
R_RETAIN_DU = 0.01          # 月球附近阈值 (~3897 km)
T_RETAIN = 13.0             # 评估13天
MOON = jnp.array([1-MU, 0.0, 0.0])
N_RET = 500000               # 残留率碎片数 (不必太多, 5万够)
BATCH = 10000                # 可以开大点

@jax.jit
def bcr4bp_rhs(t, s, args):
    x, y, z, vx, vy, vz = s
    r_moon = 1738.0/D_EM
    d2 = (x-(1-MU))**2 + y*y + z*z
    def deriv(_):
        mu1 = 1-MU
        r1 = jax.lax.rsqrt((x+MU)**2+y*y+z*z+1e-18)**3
        r2 = jax.lax.rsqrt((x-mu1)**2+y*y+z*z+1e-18)**3
        psi = n_s*t; Rx, Ry = R3*jnp.cos(psi), R3*jnp.sin(psi)
        r3 = jax.lax.rsqrt((x-Rx)**2+(y-Ry)**2+z*z+1e-18)**3
        ax = x+2*vy-mu1*(x+MU)*r1-MU*(x-mu1)*r2-mu3*(x-Rx)*r3-mu3*jnp.cos(psi)/R3**2
        ay = y-2*vx-mu1*y*r1-MU*y*r2-mu3*(y-Ry)*r3-mu3*jnp.sin(psi)/R3**2
        az = -mu1*z*r1-MU*z*r2-mu3*z*r3
        return jnp.array([vx,vy,vz,ax,ay,az])
    return jax.lax.cond(d2 < r_moon**2, lambda _: jnp.zeros(6), deriv, None)

@eqx.filter_jit
def prop(X, args, ts):
    return diffeqsolve(ODETerm(bcr4bp_rhs), Dopri5(), t0=0.0, t1=ts[-1], y0=X, dt0=1e-3,
                       saveat=SaveAt(ts=ts), args=args,
                       stepsize_controller=PIDController(rtol=1e-6, atol=1e-8),
                       max_steps=300000, throw=False).ys
vprop = eqx.filter_jit(jax.vmap(prop, in_axes=(0, None, None)))
ARGS = {}

def retention_one_point(pt_pos, pt_vel, n_sub):
    """传播 n_sub 碎片，返回 (时间数组, 留存比例数组)"""
    ts = jnp.array(np.linspace(0, T_RETAIN, 60) / tt_days)
    frags = np.empty((n_sub, 6), np.float64)
    frags[:, :3] = pt_pos; frags[:, 3:] = pt_vel[:n_sub]
    fd = jnp.asarray(frags)

    @jax.jit
    def batch_frac(fb):
        tj = vprop(fb, ARGS, ts)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        d = jnp.linalg.norm(tj[:, :, :3] - MOON[None, None], axis=-1)
        return jnp.sum((d > R_M_LU) & (d < R_RETAIN_DU), axis=0)  # 排除撞月

    nb = int(np.ceil(n_sub / BATCH))
    acc = np.zeros(60, dtype=np.int64)                # 60个时间点
    for b in tqdm(range(nb), desc=f'  batches ({n_sub} frags)'):
        s, en = b*BATCH, min((b+1)*BATCH, n_sub)
        cnt = np.asarray(batch_frac(fd[s:en]))
        acc = acc + cnt                                # 不原地修改
    return np.linspace(0, T_RETAIN, 60), acc / n_sub
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    fr = np.load('fragments_ldo.npz')
    POS, VEL = fr['pos_nd'], fr['vel_nd']
    PTS = range(len(POS))

    plt.figure(figsize=(7, 5))
    for k in PTS:
        print(f"Point {k+1}/{len(POS)} ...", end=' ', flush=True)
        t, f = retention_one_point(POS[k], VEL[k], N_RET)
        plt.plot(t, f * 100, lw=1.5, label=f'point {k+1}')
        print(f"retention@13d = {f[-1]*100:.1f}%")

    plt.axhline(70, ls='--', color='gray', lw=0.8)
    plt.xlabel('time after breakup (days)')
    plt.ylabel(f'fraction within {R_RETAIN_DU} DU of Moon (%)')
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig('fig_paper3_retention.png', dpi=200)
    print("[saved] fig_paper3_retention.png")