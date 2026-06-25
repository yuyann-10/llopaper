# -*- coding: utf-8 -*-
"""
C. 碰撞概率 vs 预警时间（Δt）曲线
================================================================
回答：对接（近月点穿越）前多久发生 LLO 解体最危险？需要多少预警时间风险才可接受？

定义：解体发生在航天器出发前 OFFSET 天。航天器沿自由返回轨道飞行，在近月点
      （t_peri）与同高度 LLO 目标交会。故碎片云在“近月点穿越”这一最危险事件
      处的演化时间（预警时间）为：
            Δt = OFFSET + t_peri
扫 OFFSET，对每个值用 BCR4BP 传播碎片子样本、与航天器轨道做通量积分，得到
整段任务的期望撞击数 E 与碰撞概率 P = 1 - exp(-E)，并由 per-fragment 贡献做
自助法 95% 置信区间。

OFFSET=0 即“航天器出发瞬间解体”，碎片云最密、与目标轨道最共址 -> 风险上界。

运行：python dt_warning_curve.py     （GPU；N_SUB / OFFSET_GRID 可调）
"""
import os
os.environ.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", ".9")
os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")

import numpy as np
import pandas as pd
import jax
import jax.numpy as jnp
from diffrax import diffeqsolve, PIDController, ODETerm, Dopri5, SaveAt
import equinox as eqx
from tqdm import tqdm
jax.config.update("jax_enable_x64", True)

# ======================================================================
#                              配置
# ======================================================================
FRAG_FILE   = "../large_data_archive/fragmentr_properties.txt"
# 对接型自由返回轨道（近月点 = LLO 高度 200 km）。预警时间曲线必须用它；
# Artemis II 飞越轨道（../artemis_bcr4bp_standard.csv）不进碎片区，仅作对照。
TRAJ_CSV    = "../astro_tools/ephemeris_free_return_full.csv"
OUT_NPZ     = "dt_warning_curve.npz"
OUT_FIG     = "fig_dt_warning_curve.png"
POS_BREAKUP_ND = np.array([1.06205353630756, 0.00119514047891347, 0.00152897141216298])

N_SUB       = 200_000      # 每个 OFFSET 参与传播的碎片子样本（GPU 够可调大）
N_PHYS      = 5_000_000    # 物理碎片总数（把 E 缩放到真实量级）
OFFSET_GRID = np.array([0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 14.0, 20.0])  # 天
N_MISSION   = 12000
BATCH_SIZE  = 1000
B_BOOT      = 400

# ---- 常量（与 runpt5.py 一致）----
mu = 0.01215058; L_km = 389703.0; L = L_km*1e3
vv = 1017.551785; vv_kms = vv/1000.0
tt = 382981.0; tt_days = tt/86400.0
M = 5.9722e24 + 7.346e22; mu3 = 1.989e30/M; R3 = 149.6e9/L; n_s = 0.9252
R_DZ_km = 100.0; R_DZ_lu = R_DZ_km/L_km
V_DZ_km3 = (4.0/3.0)*np.pi*R_DZ_km**3
AREA_SC_KM2 = np.pi*(0.01**2)


@jax.jit
def bcr4bp_rhs(t, state, args):
    x, y, z, vx, vy, vz = state
    x_moon = 1.0 - mu
    r_moon_norm = 1738.0/389703.0
    dist_to_moon_sq = (x - x_moon)**2 + y**2 + z**2

    def derivatives(_):
        mu1 = 1.0 - mu
        r1_sq = (x+mu)**2 + y**2 + z**2 + 1e-18
        r2_sq = (x-mu1)**2 + y**2 + z**2 + 1e-18
        inv_r1_3 = jax.lax.rsqrt(r1_sq)**3
        inv_r2_3 = jax.lax.rsqrt(r2_sq)**3
        psi = n_s*t
        Rsx, Rsy = R3*jnp.cos(psi), R3*jnp.sin(psi)
        r3_sq = (x-Rsx)**2 + (y-Rsy)**2 + z**2 + 1e-18
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
                      max_steps=300000, throw=False)
    return sol.ys
vmap_prop = eqx.filter_jit(jax.vmap(propagate_at, in_axes=(0, None, None)))
ARGS = {"mu": mu, "mu3": mu3, "R3": R3, "n_s": n_s}


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


def load_inputs():
    df = pd.read_csv(FRAG_FILE, sep=',', comment='#', header=None,
                     names=['ID', 'VX', 'VY', 'VZ', 'Vmag', 'Mass'])
    v = df[['VX', 'VY', 'VZ']].values[:N_SUB] / vv
    n = len(v)
    frags = np.column_stack([np.full(n, POS_BREAKUP_ND[0]), np.full(n, POS_BREAKUP_ND[1]),
                             np.full(n, POS_BREAKUP_ND[2]), v]).astype(np.float64)

    sc_t, sc_states = load_traj(TRAJ_CSV)
    T_mission = sc_t.max()
    tau = np.linspace(0.0, T_mission, N_MISSION)
    SC = np.column_stack([np.interp(tau, sc_t, sc_states[:, k]) for k in range(6)])

    # 近月点时间（用于把 OFFSET 转成预警时间 Δt = OFFSET + t_peri）
    dM = np.linalg.norm(SC[:, 0:3] - np.array([1.0-mu, 0.0, 0.0]), axis=1)
    t_peri = tau[int(np.argmin(dM))]
    return frags, tau, SC, t_peri


def eval_one_offset(frags, tau, SC, offset):
    """返回 (e_i 数组[N_SUB], 峰值危险区碎片数)。"""
    abs_days = offset + tau
    save_ts_lu = jnp.array(abs_days / tt_days)
    dt_sec = (tau[1] - tau[0]) * 86400.0
    SC_pos = jnp.array(SC[:, 0:3]); SC_vel = jnp.array(SC[:, 3:6])

    @jax.jit
    def metrics(trajs):
        rel = trajs[:, :, 0:3] - SC_pos[None]
        in_dz = jnp.sum(rel**2, axis=-1) < R_DZ_lu**2
        vrel = jnp.linalg.norm(trajs[:, :, 3:6] - SC_vel[None], axis=-1) * vv_kms
        e_i = jnp.sum(jnp.where(in_dz, vrel*AREA_SC_KM2/V_DZ_km3, 0.0), axis=1) * dt_sec
        n_in_dz_t = jnp.sum(in_dz, axis=0)          # 各时刻危险区碎片数
        return e_i, n_in_dz_t

    n = len(frags); e_all = np.zeros(n); peak = 0
    nb = int(np.ceil(n / BATCH_SIZE))
    for b in range(nb):
        s, en = b*BATCH_SIZE, min((b+1)*BATCH_SIZE, n)
        tj = vmap_prop(jnp.array(frags[s:en]), ARGS, save_ts_lu)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        e_i, n_t = metrics(tj)
        e_all[s:en] = np.array(e_i); peak = max(peak, int(jnp.max(n_t)))
    return e_all, peak


def main():
    frags, tau, SC, t_peri = load_inputs()
    rng = np.random.default_rng(0)
    rows = []
    print(f"近月点时刻 t_peri = {t_peri:.3f} d；扫描 {len(OFFSET_GRID)} 个 OFFSET，N_SUB={N_SUB}")
    for off in tqdm(OFFSET_GRID, desc="offset sweep"):
        e_all, peak = eval_one_offset(frags, tau, SC, off)
        n = len(e_all)
        E = (N_PHYS/n) * e_all.sum()
        P = 1.0 - np.exp(-E)
        # per-point 自助 95% CI
        Pb = np.empty(B_BOOT)
        for b in range(B_BOOT):
            idx = rng.integers(0, n, size=n)
            Pb[b] = 1.0 - np.exp(-(N_PHYS/n)*e_all[idx].sum())
        rows.append((off, off + t_peri, E, P,
                     np.percentile(Pb, 2.5), np.percentile(Pb, 97.5), peak))
        print(f"  OFFSET={off:5.2f}d | Δt={off+t_peri:5.2f}d | peak={peak:5d} | "
              f"E={E:.3e} | P={P:.3e}")

    arr = np.array(rows)
    np.savez(OUT_NPZ, offset=arr[:,0], dt_warning=arr[:,1], E=arr[:,2],
             P=arr[:,3], P_lo=arr[:,4], P_hi=arr[:,5], peak=arr[:,6], t_peri=t_peri)

    import matplotlib.pyplot as plt
    dt_w, P, P_lo, P_hi = arr[:,1], arr[:,3], arr[:,4], arr[:,5]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.fill_between(dt_w, P_lo, P_hi, alpha=0.25, color='C3', label='95% CI (bootstrap)')
    ax.plot(dt_w, P, '-o', color='C3', ms=5, label='collision probability')
    ax.set_yscale('log')
    ax.set_xlabel('Warning time before perilune encounter  $\\Delta t$  (days)')
    ax.set_ylabel('Collision probability  $P$')
    ax.set_title('Collision probability vs. warning time (LLO breakup, Scenario 5)')
    ax.grid(alpha=0.3, which='both'); ax.legend()
    fig.tight_layout(); fig.savefig(OUT_FIG, dpi=200)
    print(f"[saved] {OUT_FIG}  &  {OUT_NPZ}")


if __name__ == "__main__":
    main()
