# -*- coding: utf-8 -*-
"""图3: 残留率 vs 时间 — 计算与绘图分离。

用法:
  python retention_only.py --compute    # 仅计算, 保存到 retention_cache.npz
  python retention_only.py --plot       # 仅绘图, 从缓存读取 (默认)
  python retention_only.py              # 若无缓存则计算+绘图, 有则仅绘图
"""
import os, sys, argparse
os.environ.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", ".5")
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")
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
T_RETAIN = 22.0             # 评估22天
MOON = jnp.array([1-MU, 0.0, 0.0])
N_RET = 50000               # 5万就够画图了，比50万快很多
BATCH = 10000                # 可以开大点
CACHE = 'retention_cache.npz'

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
def compute_all():
    """计算所有点的残留率, 保存到 CACHE"""
    fr = np.load('fragments_ldo.npz')
    POS, VEL = fr['pos_nd'], fr['vel_nd']
    PTS = range(len(POS))
    data = {}
    for k in PTS:
        print(f"Point {k+1}/{len(POS)} ...", end=' ', flush=True)
        t, f = retention_one_point(POS[k], VEL[k], N_RET)
        data[f't{k}'] = t; data[f'f{k}'] = f
        print(f"retention@22d = {f[-1]*100:.1f}%")
    np.savez(CACHE, **data)
    print(f'[saved] {CACHE}')

def plot_all():
    """从缓存读取并绘图"""
    if not os.path.exists(CACHE):
        print(f'错误: {CACHE} 不存在, 请先运行 --compute')
        sys.exit(1)
    import matplotlib.pyplot as plt
    d = np.load(CACHE)
    PTS = [k for k in range(6) if f't{k}' in d]
    print(f'加载缓存: {CACHE}  ({len(PTS)} 个点)')

    plt.figure(figsize=(7, 5.5))
    colors = plt.cm.viridis(np.linspace(0, 1, len(PTS)))
    for k in PTS:
        plt.plot(d[f't{k}'], d[f'f{k}'] * 100, lw=1.5, color=colors[k], label=f'{k+1}')
    plt.axhline(70, ls='--', color='gray', lw=0.8)
    plt.xlabel('time after breakup (days)', fontsize=14)
    plt.ylabel('Fraction of debris within 0.01 DU of Moon (%)', fontsize=14)
    plt.ylim(70, 77)
    plt.legend(title='Breakup location', fontsize=9); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig('fig_paper3_retention.png', dpi=200)
    print('[saved] fig_paper3_retention.png')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--compute', action='store_true', help='仅计算并保存缓存')
    p.add_argument('--plot', action='store_true', help='仅从缓存绘图')
    args = p.parse_args()
    if args.compute:
        compute_all()
    elif args.plot:
        plot_all()
    else:
        if os.path.exists(CACHE):
            plot_all()
        else:
            print(f'未找到 {CACHE}, 自动计算...')
            compute_all()
            plot_all()