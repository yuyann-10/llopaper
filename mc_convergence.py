# -*- coding: utf-8 -*-
"""
B. 蒙特卡洛收敛性与不确定性
================================================================
为论文中“70% 残留”和“碰撞概率 1e-12~5e-9”两个点估计补上：
  (1) 估计量随 MC 样本数 N 的收敛曲线
  (2) 95% 置信区间（自助法 bootstrap + 解析二项区间）

做法（避免重复积分，先传播一次拿 per-fragment 贡献，再离线重采样）：
  - 把全部碎片沿 BCR4BP 传播一次，对每个碎片记录：
        e_i        : 该碎片在整个任务窗内对“期望撞击数”的积分贡献
        retained_i : 解体后 T_REF 天时该碎片是否仍在月球附近（残留判据）
  - 收敛分析纯 numpy 重采样：从 N_POP 个碎片里抽 n 个，估计
        Ê(n) = (N_PHYS / n) * Σ_{i∈subset} e_i   ->  P = 1 - exp(-Ê)
        p̂(n) = mean(retained_{subset})
    对每个 n 做 B_BOOT 次自助抽样得到中位数与 2.5/97.5 分位。

运行：
  python mc_convergence.py --stage propagate   # 跑 GPU 传播，存 per-fragment 贡献
  python mc_convergence.py --stage analyze      # 纯 numpy 出图（可反复跑）
  python mc_convergence.py --stage all          # 一条龙
"""
import os
os.environ.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", ".9")
os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")

import argparse
import numpy as np
import pandas as pd

# ======================================================================
#                          配置（按需修改）
# ======================================================================
FRAG_FILE   = "../large_data_archive/fragmentr_properties.txt"  # point5 碎片绝对速度 (m/s)
# 航天器轨道：碰撞概率分析须用“对接型”自由返回轨道（近月点 = LLO 高度），才能对齐
# 论文中 1e-12~5e-9 的结果。Artemis II（../artemis_bcr4bp_standard.csv）近月点 ~3.5万 km，
# 不进碎片区，仅作“飞越型≈零风险”对照，切换此变量即可复现该对照。
TRAJ_CSV    = "../astro_tools/ephemeris_free_return_full.csv"   # 200 km 近月点 FRO
CACHE_NPZ   = "mc_convergence_perfrag.npz"                      # per-fragment 贡献缓存
OUT_FIG     = "fig_mc_convergence.png"

# 解体点 5 位置（与 runpt5.py 一致，旋转系无量纲）
POS_BREAKUP_ND = np.array([1.06205353630756, 0.00119514047891347, 0.00152897141216298])

N_POP        = 500_000     # 实际参与传播的碎片数（从 5M 里取前 N_POP；GPU 够可调大）
N_PHYS       = 5_000_000   # 物理上一次灾难解体 >0.1m 碎片总数（用于把 Ê 缩放到真实量级）
OFFSET_DAYS  = 7.0         # 碎片先演化天数（航天器出发前），与论文基线一致
T_REF_DAYS   = 13.0        # 残留率评估时刻（解体后）
R_RETAIN_DU  = 0.01        # “月球附近”判据：距月心 < 0.01 DU (≈3897 km)
N_MISSION    = 12000       # 任务窗时间采样点（保证危险区穿越不漏采）
BATCH_SIZE   = 1000

# 收敛分析
N_GRID  = np.unique(np.logspace(2.5, np.log10(N_POP), 18).astype(int))  # 抽样规模序列
B_BOOT  = 400              # 每个 n 的自助重采样次数

# ======================================================================
#            常量 + BCR4BP 动力学（与 runpt5.py 完全一致）
# ======================================================================
mu   = 0.01215058
L_km = 389703.0
L    = L_km * 1e3                 # m
vv   = 1017.551785                # m/s
vv_kms = vv / 1000.0
tt   = 382981.0                   # s
tt_days = tt / 86400.0
M    = 5.9722e24 + 7.346e22
mu3  = 1.989e30 / M
R3   = 149.6e9 / L
n_s  = 0.9252

R_DZ_km  = 100.0
R_DZ_lu  = R_DZ_km / L_km
V_DZ_km3 = (4.0/3.0) * np.pi * R_DZ_km**3
AREA_SC_KM2 = np.pi * (0.01**2)   # 10 m 半径球壳


def load_traj(path):
    """读取航天器轨道，自动识别单位/列名，返回 (t_days_from0, states_normalized[N,6])。"""
    d = pd.read_csv(path)
    cols = list(d.columns)
    if 't_TU' in cols:                                   # 归一化, 时间 TU (artemis_standard)
        t = d['t_TU'].values * tt_days
        S = d[['x', 'y', 'z', 'vx', 'vy', 'vz']].values
    elif 't_nd' in cols:                                 # 归一化, 时间 TU
        t = d['t_nd'].values * tt_days
        S = d[['x_nd', 'y_nd', 'z_nd', 'vx_nd', 'vy_nd', 'vz_nd']].values
    else:                                                # km / km/s, 时间天 (free_return_full)
        t = d.iloc[:, 0].values
        S = d.iloc[:, 1:7].values / np.array([L_km, L_km, L_km, vv_kms, vv_kms, vv_kms])
    return t - t.min(), S


def _propagate_perfragment():
    """GPU 传播，返回 (e_all, retained_all)：每个碎片的撞击贡献与残留标志。"""
    import jax
    import jax.numpy as jnp
    import diffrax
    from diffrax import diffeqsolve, PIDController, ODETerm, Dopri5, SaveAt
    import equinox as eqx
    from tqdm import tqdm
    jax.config.update("jax_enable_x64", True)

    @jax.jit
    def bcr4bp_rhs(t, state, args):
        x, y, z, vx, vy, vz = state
        x_moon = 1.0 - mu
        r_moon_norm = 1738.0 / 389703.0
        dist_to_moon_sq = (x - x_moon)**2 + y**2 + z**2

        def derivatives(_):
            mu1 = 1.0 - mu
            r1_sq = (x + mu)**2 + y**2 + z**2 + 1e-18
            r2_sq = (x - mu1)**2 + y**2 + z**2 + 1e-18
            inv_r1_3 = jax.lax.rsqrt(r1_sq)**3
            inv_r2_3 = jax.lax.rsqrt(r2_sq)**3
            psi = n_s * t
            Rsx, Rsy = R3 * jnp.cos(psi), R3 * jnp.sin(psi)
            r3_sq = (x - Rsx)**2 + (y - Rsy)**2 + z**2 + 1e-18
            inv_r3_3 = jax.lax.rsqrt(r3_sq)**3
            ax = x + 2.0*vy - mu1*(x+mu)*inv_r1_3 - mu*(x-mu1)*inv_r2_3 - mu3*(x-Rsx)*inv_r3_3 - mu3*jnp.cos(psi)/R3**2
            ay = y - 2.0*vx - mu1*y*inv_r1_3 - mu*y*inv_r2_3 - mu3*(y-Rsy)*inv_r3_3 - mu3*jnp.sin(psi)/R3**2
            az = -mu1*z*inv_r1_3 - mu*z*inv_r2_3 - mu3*z*inv_r3_3
            return jnp.array([vx, vy, vz, ax, ay, az])

        def frozen(_):
            return jnp.zeros(6)
        return jax.lax.cond(dist_to_moon_sq < r_moon_norm**2, frozen, derivatives, None)

    @eqx.filter_jit
    def propagate_at(X_init, args, save_ts_lu):
        sol = diffeqsolve(ODETerm(bcr4bp_rhs), Dopri5(), t0=0.0, t1=save_ts_lu[-1],
                          y0=X_init, dt0=1e-3, saveat=SaveAt(ts=save_ts_lu), args=args,
                          stepsize_controller=PIDController(rtol=1e-7, atol=1e-9),
                          max_steps=200000, throw=False)
        return sol.ys
    vmap_prop = eqx.filter_jit(jax.vmap(propagate_at, in_axes=(0, None, None)))
    args = {"mu": mu, "mu3": mu3, "R3": R3, "n_s": n_s}

    # --- 碎片初值（位置同解体点，速度 = 绝对速度 / vv）---
    df = pd.read_csv(FRAG_FILE, sep=',', comment='#', header=None,
                     names=['ID', 'VX', 'VY', 'VZ', 'Vmag', 'Mass'])
    v = df[['VX', 'VY', 'VZ']].values[:N_POP] / vv
    n = len(v)
    frags = np.column_stack([np.full(n, POS_BREAKUP_ND[0]),
                             np.full(n, POS_BREAKUP_ND[1]),
                             np.full(n, POS_BREAKUP_ND[2]), v]).astype(np.float64)

    # --- 航天器轨道：放在绝对时间 [OFFSET, OFFSET+T_mission] ---
    sc_t_days, sc_states = load_traj(TRAJ_CSV)
    T_mission = sc_t_days.max()
    tau_days  = np.linspace(0.0, T_mission, N_MISSION)            # 任务相对时间
    abs_days  = OFFSET_DAYS + tau_days                            # 绝对时间（解体后）
    SC = np.column_stack([np.interp(tau_days, sc_t_days, sc_states[:, k])
                          for k in range(6)])
    SC_pos = jnp.array(SC[:, 0:3]); SC_vel = jnp.array(SC[:, 3:6])

    save_ts_lu = jnp.array(abs_days / tt_days)
    dt_sec = (tau_days[1] - tau_days[0]) * 86400.0
    idx_ref = int(np.argmin(np.abs(abs_days - T_REF_DAYS)))       # 13d 对应的采样点

    @jax.jit
    def per_fragment_metrics(trajs):
        rel = trajs[:, :, 0:3] - SC_pos[None]
        in_dz = jnp.sum(rel**2, axis=-1) < R_DZ_lu**2             # (B, T)
        vrel = jnp.linalg.norm(trajs[:, :, 3:6] - SC_vel[None], axis=-1) * vv_kms
        e_rate = vrel * AREA_SC_KM2 / V_DZ_km3                    # (B, T)
        e_i = jnp.sum(jnp.where(in_dz, e_rate, 0.0), axis=1) * dt_sec   # (B,) 期望撞击贡献
        xm = trajs[:, idx_ref, 0:3] - jnp.array([1.0 - mu, 0.0, 0.0])
        retained_i = jnp.sum(xm**2, axis=-1) < R_RETAIN_DU**2     # (B,) 残留标志
        return e_i, retained_i

    e_all = np.zeros(n); ret_all = np.zeros(n, dtype=bool)
    nb = int(np.ceil(n / BATCH_SIZE))
    for b in tqdm(range(nb), desc="propagate"):
        s, en = b*BATCH_SIZE, min((b+1)*BATCH_SIZE, n)
        tj = vmap_prop(jnp.array(frags[s:en]), args, save_ts_lu)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        e_i, ret_i = per_fragment_metrics(tj)
        e_all[s:en] = np.array(e_i); ret_all[s:en] = np.array(ret_i)

    np.savez_compressed(CACHE_NPZ, e=e_all, retained=ret_all,
                        N_POP=n, N_PHYS=N_PHYS)
    print(f"[saved] {CACHE_NPZ}  N={n}  E_full(scaled)={N_PHYS/n*e_all.sum():.4e}  "
          f"P_full={1-np.exp(-N_PHYS/n*e_all.sum()):.4e}  retain@{T_REF_DAYS}d={ret_all.mean():.4f}")
    return e_all, ret_all


def _analyze():
    d = np.load(CACHE_NPZ)
    e = d['e']; retained = d['retained'].astype(float)
    N_pop = int(d['N_POP']); N_phys = int(d['N_PHYS'])
    rng = np.random.default_rng(0)

    P_med, P_lo, P_hi = [], [], []
    r_med, r_lo, r_hi, r_se = [], [], [], []
    for nsub in N_GRID:
        Ps = np.empty(B_BOOT); rs = np.empty(B_BOOT)
        for b in range(B_BOOT):
            idx = rng.integers(0, N_pop, size=nsub)              # 自助抽样
            E = (N_phys / nsub) * e[idx].sum()                   # 缩放到物理碎片数
            Ps[b] = 1.0 - np.exp(-E)
            rs[b] = retained[idx].mean()
        P_med.append(np.median(Ps)); P_lo.append(np.percentile(Ps, 2.5)); P_hi.append(np.percentile(Ps, 97.5))
        p = retained.mean()
        r_med.append(np.median(rs)); r_lo.append(np.percentile(rs, 2.5)); r_hi.append(np.percentile(rs, 97.5))
        r_se.append(np.sqrt(p*(1-p)/nsub))                       # 解析二项标准误

    import matplotlib.pyplot as plt
    P_med, P_lo, P_hi = map(np.array, (P_med, P_lo, P_hi))
    r_med, r_lo, r_hi, r_se = map(np.array, (r_med, r_lo, r_hi, r_se))

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].fill_between(N_GRID, P_lo, P_hi, alpha=0.25, color='C3', label='95% CI (bootstrap)')
    ax[0].plot(N_GRID, P_med, '-o', color='C3', ms=4, label='median')
    ax[0].set_xscale('log'); ax[0].set_yscale('log')
    ax[0].set_xlabel('Monte Carlo sample size $N$'); ax[0].set_ylabel('Collision probability $P$')
    ax[0].set_title('(a) Collision probability convergence'); ax[0].legend(); ax[0].grid(alpha=0.3)

    p = retained.mean()
    ax[1].fill_between(N_GRID, r_lo, r_hi, alpha=0.25, color='C0', label='95% CI (bootstrap)')
    ax[1].errorbar(N_GRID, r_med, yerr=1.96*r_se, fmt='-o', color='C0', ms=4, capsize=3,
                   label='median $\\pm$1.96·binom SE')
    ax[1].axhline(p, ls='--', color='k', lw=0.8, label=f'full-sample = {p:.3f}')
    ax[1].set_xscale('log'); ax[1].set_xlabel('Monte Carlo sample size $N$')
    ax[1].set_ylabel(f'Retained fraction @ {T_REF_DAYS:.0f} d')
    ax[1].set_title('(b) Retention fraction convergence'); ax[1].legend(); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT_FIG, dpi=200)
    print(f"[saved] {OUT_FIG}")
    print(f"  收敛值: P = {P_med[-1]:.3e}  (95% CI [{P_lo[-1]:.3e}, {P_hi[-1]:.3e}])")
    print(f"  收敛值: 残留率 = {p:.4f}  (N={N_pop} 时二项 95% CI ±{1.96*np.sqrt(p*(1-p)/N_pop):.4f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["propagate", "analyze", "all"], default="all")
    a = ap.parse_args()
    if a.stage in ("propagate", "all"):
        _propagate_perfragment()
    if a.stage in ("analyze", "all"):
        _analyze()
