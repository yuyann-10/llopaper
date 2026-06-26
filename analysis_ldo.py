# -*- coding: utf-8 -*-
"""
新场景碎片碰撞分析 (100km 逆行 LDO 解体 + 载人自由返回单次穿越)
================================================================
解体目标: 100km LDO (8 点, fragments_ldo.npz);  航天器: cr3bp_crew_freereturn.csv
碎片 BCR4BP 传播; 危险区通量模型 -> 期望撞击数 E -> 碰撞概率 P=1-exp(-E)。

Δt = 解体 -> 载人飞船近月点(1st RVD) 的预警时间。航天器近月点对齐到绝对时间 Δt。

stage:
  base : 8 点碰撞概率(Δt_ref) + 残留率(t) + 存最坏点 per-fragment 贡献(供收敛)
  dt   : 最坏点 碰撞概率 vs 预警时间 Δt 曲线
"""
import os
os.environ.setdefault("XLA_PYTHON_CLIENT_MEM_FRACTION", ".9")
os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")
os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")
import argparse
from datetime import datetime
import numpy as np
import pandas as pd
import jax, jax.numpy as jnp
from diffrax import diffeqsolve, PIDController, ODETerm, Dopri5, SaveAt
import equinox as eqx
from tqdm import tqdm
jax.config.update("jax_enable_x64", True)

# ---- 常量 ----
MU = 0.01215058; D_EM = 389703.0; L_km = D_EM
VU = 1.01755178; TU_S = 382981.0; tt_days = TU_S/86400.0
M = 5.9722e24 + 7.346e22; mu3 = 1.989e30/M; R3 = 149.6e9/(D_EM*1e3); n_s = 0.9252
R_M_LU = 1738.0/D_EM                 # 月球半径(无量纲), 排除撞月冻结碎片
R_DZ_km = 100.0                      # 危险区半径 (同论文)
R_DZ_lu = R_DZ_km/L_km; V_DZ_km3 = (4/3)*np.pi*R_DZ_km**3
AREA_SC_KM2 = np.pi*(0.01**2)        # 10m 半径球壳 (物理截面)
R_RETAIN_DU = 0.01                   # "月球附近": <0.01 DU (~3897 km, 同论文)
N_PHYS = 655                       # 真实物理碎片数 = NASA SBM 预测的 >0.1m 碎片数 (按航天器算)
N_SUB = 500_000                    # 蒙特卡洛样本数 (仅为平滑 dv 分布; E 缩放=N_PHYS/N_SUB)
N_WIN = 3000                         # 穿越窗采样
BATCH = 5000                          # batch size (减小以防GPU显存不足)
T_RETAIN = 30.0                      # 残留率评估时刻(天)
MOON = jnp.array([1-MU, 0.0, 0.0])

# ---- 预警时间 Δt = 解体 -> 载人飞船近月点(1st RVD) ----
def _dt(a, b):
    f = "%Y-%m-%d %H:%M:%S.%f"
    return (datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds()/86400
DT_RVD  = 0.0                                                          # 解体恰在 RVD (上界)
DT_TLI  = _dt("2025-03-29 04:14:18.75", "2025-03-31 18:35:00.0")      # ≈2.60d 解体在载人TLI
DT_PARK = _dt("2025-03-08 18:35:00.0",  "2025-03-31 18:35:00.0")      # ≈23d  解体在着陆器入轨
DT_MARKERS = [("RVD", DT_RVD), ("crew-TLI", DT_TLI), ("lander-LOI", DT_PARK)]


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


def load_sc():
    d = pd.read_csv('cr3bp_crew_freereturn.csv')
    t = d['Time(Days)'].values
    S = d[['x_rot(km)','y_rot(km)','z_rot(km)']].values/D_EM
    Vv = d[['vx_rot(km/s)','vy_rot(km/s)','vz_rot(km/s)']].values/VU
    rM = np.linalg.norm(S-np.array([1-MU,0,0]), axis=1)
    ip = int(np.argmin(rM)); t = t - t[ip]            # 近月点 = t0
    return t, np.hstack([S, Vv])


def eval_point(pt_pos, pt_vel, sc_t, sc_state, dt_warning, n_sub):
    """返回 per-fragment 期望撞击贡献 e_i[n_sub]。"""
    # 航天器: 近月点对齐到绝对时间 dt_warning
    tau = sc_t                                         # 相对近月点 (天)
    abs_days = dt_warning + tau
    keep = abs_days >= 0
    tau, abs_days = tau[keep], abs_days[keep]
    # 重采样到 N_WIN 均匀
    grid = np.linspace(abs_days.min(), abs_days.max(), N_WIN)
    SC = np.column_stack([np.interp(grid, abs_days, sc_state[keep][:,k]) for k in range(6)])
    SCp, SCv = jnp.array(SC[:,:3]), jnp.array(SC[:,3:])
    save_ts = jnp.array(grid/tt_days)
    dt_sec = (grid[1]-grid[0])*86400

    frags = np.empty((n_sub,6), np.float64)
    frags[:,:3] = pt_pos; frags[:,3:] = pt_vel[:n_sub]
    frags_d = jnp.asarray(frags)                       # 一次性上设备

    @jax.jit
    def batch_e(fb):
        tj = vprop(fb, ARGS, save_ts)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        rel = tj[:,:,:3]-SCp[None]
        dmoon2 = jnp.sum((tj[:,:,:3]-MOON[None,None])**2, -1)
        indz = (jnp.sum(rel**2,-1) < R_DZ_lu**2) & (dmoon2 > R_M_LU**2)
        vrel = jnp.linalg.norm(tj[:,:,3:]-SCv[None],axis=-1)*VU
        return jnp.sum(jnp.where(indz, vrel*AREA_SC_KM2/V_DZ_km3, 0.0),axis=1)*dt_sec

    parts = []
    nb = int(np.ceil(n_sub/BATCH))
    for b in tqdm(range(nb), desc='  eval batches', leave=False):
        s, en = b*BATCH, min((b+1)*BATCH, n_sub)
        parts.append(batch_e(frags_d[s:en]))
    return np.asarray(jnp.concatenate(parts))


def retention(pt_pos, pt_vel, n_sub):
    ts = jnp.array(np.linspace(0, T_RETAIN, 120)/tt_days)
    frags = np.empty((n_sub,6)); frags[:,:3]=pt_pos; frags[:,3:]=pt_vel[:n_sub]
    frags_d = jnp.asarray(frags)
    @jax.jit
    def batch_frac(fb):
        tj = vprop(fb, ARGS, ts); tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        d = jnp.linalg.norm(tj[:,:,:3]-MOON[None,None], axis=-1)
        return jnp.sum((d > R_M_LU) & (d < R_RETAIN_DU), axis=0)   # 在轨碎片, 排除撞月
    nb = int(np.ceil(n_sub/BATCH))
    acc = np.zeros(120, dtype=np.int64)
    for b in tqdm(range(nb), desc='  retention batches', leave=False):
        s, en = b*BATCH, min((b+1)*BATCH, n_sub)
        cnt = np.asarray(batch_frac(frags_d[s:en]))
        acc = acc + cnt
    return np.linspace(0, T_RETAIN, 120), acc / n_sub

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', default='base')
    a = ap.parse_args()
    fr = np.load('fragments_ldo.npz')
    POS, VEL = fr['pos_nd'], fr['vel_nd']        # (8,3), (8,N,3)
    sc_t, sc_state = load_sc()
    print(f"航天器近月段: {sc_t.min():.2f}~{sc_t.max():.2f} d (近月点=0)")

    if a.stage == 'base':
        PTS = [0,1,2,3,4,5]
        # Δt 网格(linspace 第三参=点数): 稀疏0-5 + 密集5-10抓峰 + 稀疏尾部
        DTS = np.unique(np.round(np.concatenate([
            np.linspace(0, 5.0, 3),       # [0, 2.5, 5]
            np.linspace(5.0, 10.0, 10),   # 5~10d 峰区
            np.linspace(10.0, 23.0, 5),   # [10, 13.25, 16.5, 19.75, 23]
            [DT_TLI, DT_PARK]             # 两个历元节点
        ]), 3))
        print(f"\n=== 各点碰撞概率 P[点 × Δt] + 残留率  ({len(DTS)} 个 Δt) ===")
        print("Δt(d): " + " ".join(f"{d:.2f}" for d in DTS))
        # ---- 逐点存档 + 自动恢复 ----
        CKPT = 'analysis_base_ckpt.npz'
        if os.path.exists(CKPT) and np.array_equal(np.load(CKPT)['dts'], DTS):
            c = np.load(CKPT); table = c['table'].copy(); done = list(c['done'])
            print(f"[恢复] 已完成点 {[d+1 for d in done]}, 续算剩余")
        else:
            table = np.zeros((len(PTS), len(DTS))); done = []
        for r, k in enumerate(PTS):
            if k in done:
                continue
            for c, dt in enumerate(DTS):
                e = eval_point(POS[k], VEL[k], sc_t, sc_state, dt, N_SUB)
                table[r, c] = 1-np.exp(-(N_PHYS/N_SUB)*e.sum())
            print(f"  点{k+1}: " + " ".join(f"{table[r,c]:.2e}" for c in range(len(DTS))))
            done.append(k)
            np.savez(CKPT, table=table, done=np.array(done), dts=DTS, pts=np.array(PTS))  # 每点存一次
        # 最坏点 + 峰值 Δt = 全表最大 (不会落在 Δt=0, 那里 P≈0)
        ridx, cidx = np.unravel_index(int(np.argmax(table)), table.shape)
        worst = PTS[ridx]; dt_worst = float(DTS[cidx])
        print(f"最坏点: {worst+1}  峰值 Δt={dt_worst:.2f}d  P={table[ridx,cidx]:.3e}")
        tret, fret = retention(POS[worst], VEL[worst], N_SUB)
        print(f"残留率@{T_RETAIN}d (点{worst+1}, <{R_RETAIN_DU}DU): {fret[-1]*100:.1f}%")
        # 存最坏点 per-fragment, 在【峰值 Δt】算 (有信号, 供 2a 收敛分析)
        e_worst = eval_point(POS[worst], VEL[worst], sc_t, sc_state, dt_worst, N_SUB)
        np.savez('analysis_base.npz', table=table, pts=np.array(PTS), dts=DTS,
                 markers=np.array([DT_RVD, DT_TLI, DT_PARK]), worst=worst, dt_worst=dt_worst,
                 tret=tret, fret=fret, e_worst=e_worst, N_PHYS=N_PHYS)
        if os.path.exists(CKPT): os.remove(CKPT)          # 全部完成, 清理存档
        print("[saved] analysis_base.npz")

    elif a.stage == 'dt':
        worst = int(np.load('analysis_base.npz')['worst']) if os.path.exists('analysis_base.npz') else 4
        # 峰区 4.5-8.5d 密采(0.25d): base 显示双峰(~5d & ~7.78d)+谷(~6.3d); 两端稀疏
        DTS = np.unique(np.round(np.concatenate([
            [0.0, 1.0, 2.0, DT_TLI, 3.0], np.arange(4.5, 8.51, 0.25),
            [9.0, 10.0, 12.0, 14.0, 16.0, 18.0, DT_PARK]]), 3))
        CKPT = 'analysis_dt_ckpt.npz'                      # 逐 Δt 存档 + 恢复
        if os.path.exists(CKPT) and np.array_equal(np.load(CKPT)['dts'], DTS):
            out = list(map(tuple, np.load(CKPT)['out']))
            print(f"[恢复] 已完成 {len(out)}/{len(DTS)} 个 Δt")
        else:
            out = []
        for i, dt in enumerate(tqdm(DTS, desc='Δt sweep')):
            if i < len(out):
                continue
            e = eval_point(POS[worst], VEL[worst], sc_t, sc_state, dt, N_SUB)
            E = (N_PHYS/N_SUB)*e.sum(); P=1-np.exp(-E)
            rng=np.random.default_rng(0); Pb=np.array([1-np.exp(-(N_PHYS/N_SUB)*e[rng.integers(0,N_SUB,N_SUB)].sum()) for _ in range(300)])
            out.append((float(dt), float(E), float(P), float(np.percentile(Pb,2.5)), float(np.percentile(Pb,97.5))))
            np.savez(CKPT, out=np.array(out), dts=DTS)    # 每个 Δt 存一次
            print(f"  Δt={dt:5.1f}d  P={P:.3e}")
        out = np.array(out)
        np.savez('analysis_dt.npz', dt=out[:,0], P=out[:,2], P_lo=out[:,3], P_hi=out[:,4],
                 worst=worst, marker_rvd=DT_RVD, marker_tli=DT_TLI, marker_park=DT_PARK)
        if os.path.exists(CKPT): os.remove(CKPT)
        print("[saved] analysis_dt.npz")


if __name__ == "__main__":
    main()