# -*- coding: utf-8 -*-
"""
一次传播 -> 重做论文剩余数值模拟图 (图3/4/5/7/9)。复用 analysis_ldo 的 BCR4BP 机器。
服务器运行: python figdata_and_plots.py   (调 N_* 放大)

图3 残留率 vs 时间 (各解体点)
图4 碎片分布演化 (多时刻快照, 旋转系近月)
图5 危险区碎片数 + 平均相对速度 vs 时间
图7 瞬时风险率 / 累积期望撞击数 / 碰撞概率 vs 时间
图9 沿自由返回航线 危险区侵入碎片 空间分布
"""
import numpy as np
import jax, jax.numpy as jnp
import matplotlib.pyplot as plt
from tqdm import tqdm
import analysis_ldo as A          # 复用 vprop, 常量, load_sc

# 规模 (服务器调大, 提高碎片数以平滑图5尖峰)
N_SNAP = 15_000      # 图4 快照碎片数
N_TS   = 500_000     # 图5/7/9 时序碎片数 (核心: 增大以平滑DZ碎片数曲线)
N_RET  = 50_000      # 图3 残留率碎片数
WORST  = 2           # 最坏解体点 index (0-based; 点3, 由 analysis 确定)
DT_PEAK = 5.0        # 峰值预警时间(天) — 图5/7/9/8 用 (真实峰在 5d, 不是 2d!)
SNAP_DAYS = [1, 3, 7, 13]      # 图4 时间切片 (4)
FIG4_PTS = [0, 2, 3, 5]        # 图4 解体点 (4)
FIG4_LIM = 5000.0              # 图4 视野半径 (km, 月心) — 收紧看细节
PTS = [0,1,2,3,4,5]
# 图8 (论文原版): 碎片进入名义自由返回 10km 邻域(静态管) 的百分比 vs 时间
N_VIC = 300_000               # 邻域统计碎片数 (100km管, 20万+ 即够平滑)
VIC_TUBE_KM = 100.0           # 保护管半径 km (用 100km, 比 10km 采到多得多碎片)
# 前期密采(初始峰) + 后期覆盖二次峰
VIC_DAYS = np.unique(np.concatenate([np.linspace(0, 1, 60), np.linspace(1, 13, 80)]))
VIC_BATCH = 2000               # 矩阵距离省显存, 批可大些

D_EM=A.D_EM; VU=A.VU; tt_days=A.tt_days; MOON=np.array([1-A.MU,0,0]); R_M=1738.0
fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()


def propagate(pos, vel, n, ts_days):
    """传播 n 碎片到 ts_days(天) 各时刻, 返回轨迹 (n, T, 6) 旋转系无量纲。"""
    ts = jnp.asarray(np.asarray(ts_days)/tt_days)
    frags = np.empty((n,6)); frags[:,:3]=pos; frags[:,3:]=vel[:n]
    fd = jnp.asarray(frags); out=[]
    nb=int(np.ceil(n/A.BATCH))
    for b in range(nb):
        s,en=b*A.BATCH,min((b+1)*A.BATCH,n)
        tj=A.vprop(fd[s:en], A.ARGS, ts); out.append(jnp.where(jnp.isnan(tj),1e6,tj))
    return np.asarray(jnp.concatenate(out))


# ---------- 图3 残留率 vs 时间 (各点) ----------
def fig3():
    plt.figure(figsize=(7,4.6))
    for k in PTS:
        t, f = A.retention(POS[k], VEL[k], N_RET)
        plt.plot(t, f*100, lw=1.4, label=f'{k+1}')
    plt.axhline(70, ls='--', color='gray', lw=0.8)
    plt.xlabel('time after breakup (days)'); plt.ylabel('fraction within {:.2f} DU of Moon'.format(A.R_RETAIN_DU)+r' (%)')
    plt.legend(title='Breakup Location', fontsize=9)
    plt.grid(alpha=0.3); plt.tight_layout(); plt.savefig('fig_paper3_retention.png', dpi=200)
    print('[saved] fig_paper3_retention.png')


# ---------- 图4 碎片分布演化快照 (4 解体点 × 4 时间切片) ----------
def fig4():
    nr, nc = len(FIG4_PTS), len(SNAP_DAYS)
    fig, axes = plt.subplots(nr, nc, figsize=(3.0*nc, 3.0*nr))
    for ri, k in enumerate(FIG4_PTS):
        tj = propagate(POS[k], VEL[k], N_SNAP, SNAP_DAYS)      # (n, T, 6)
        for ci, d in enumerate(SNAP_DAYS):
            ax = axes[ri, ci]
            P = (tj[:, ci, :3]-MOON)*D_EM
            dist = np.linalg.norm(P, axis=1)
            alive = (dist > R_M) & (dist < 5e4)        # 排除撞月(冻结<R_M) 与发散(NaN→1e6)
            ax.scatter(0, 0, c='k', marker='+', s=40, zorder=3)   # 月心(不画月球盘)
            ax.scatter(P[alive,0], P[alive,1], s=0.5, c='C0', alpha=0.25)
            ax.set_xlim(-FIG4_LIM, FIG4_LIM); ax.set_ylim(-FIG4_LIM, FIG4_LIM)
            ax.set_aspect('equal'); ax.tick_params(labelsize=15)
            if ci == 0:                                    # 解体点编号: 图内标注(不写在纵轴)
                ax.text(0.04, 0.94, f'point {k+1}', transform=ax.transAxes,
                        fontsize=16, fontweight='bold', va='top')
            if ri == 0:
                ax.text(0.5, 1.02, f't = {d} d', transform=ax.transAxes, ha='center', fontsize=18)
            if ci == 0:
                ax.set_ylabel('y (km, Moon)', fontsize=17)
            if ri == nr-1:
                ax.set_xlabel('x (km, Moon)', fontsize=17)
    fig.tight_layout(); fig.savefig('fig_paper4_evolution.png', dpi=200)
    print('[saved] fig_paper4_evolution.png  (%d点 × %d切片, 视野±%.0fkm)' % (nr, nc, FIG4_LIM))


def fig579():
    # 航天器近月点对齐到 DT_PEAK
    tau = sc_t; abs_days = DT_PEAK + tau; keep = abs_days >= 0
    N_WIN_FIG7 = 10000  # 图7加密时间采样
    WIN_HALF = 0.08     # 天: 窗口聚焦近月点 ±0.08d (碰撞只发生在这~0.02d里, 不浪费点在平段)
    g0 = max(DT_PEAK - WIN_HALF, abs_days[keep].min())
    g1 = min(DT_PEAK + WIN_HALF, abs_days[keep].max())
    grid = np.linspace(g0, g1, N_WIN_FIG7)            # 1万点压在±0.08d → 渐进细节可见
    SC = np.column_stack([np.interp(grid, abs_days[keep], sc_state[keep][:,k]) for k in range(6)])
    SCp = jnp.asarray(SC[:,:3]); SCv = jnp.asarray(SC[:,3:])
    ts = jnp.asarray(grid/tt_days); dt_sec = (grid[1]-grid[0])*86400
    tgrid = grid - DT_PEAK            # 相对近月点

    @jax.jit
    def batch_ts(fb):
        tj = A.vprop(fb, A.ARGS, ts)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        rel = tj[:,:,:3] - SCp[None]
        dmoon2 = jnp.sum((tj[:,:,:3] - jnp.array([1-A.MU,0,0])[None,None])**2, -1)
        indz = (jnp.sum(rel**2, -1) < A.R_DZ_lu**2) & (dmoon2 > A.R_M_LU**2)
        vrel = jnp.linalg.norm(tj[:,:,3:] - SCv[None], axis=-1) * VU
        n = jnp.sum(indz, 0)
        fl = jnp.sum(jnp.where(indz, vrel*A.AREA_SC_KM2/A.V_DZ_km3, 0.0), 0)
        vs = jnp.sum(jnp.where(indz, vrel, 0.0), 0)
        return n, fl, vs, indz

    def compute_point(k, n_use):
        frags = np.empty((n_use, 6))
        frags[:,:3] = POS[k]
        frags[:,3:] = VEL[k][:n_use]
        fd = jnp.asarray(frags)
        n_dz = np.zeros(N_WIN_FIG7)
        flux = np.zeros(N_WIN_FIG7)
        vsum = np.zeros(N_WIN_FIG7)
        nb = int(np.ceil(n_use / A.BATCH))
        for b in range(nb):
            s, en = b*A.BATCH, min((b+1)*A.BATCH, n_use)
            n, fl, vs, _ = batch_ts(fd[s:en])
            n_dz += np.array(n)
            flux += np.array(fl)
            vsum += np.array(vs)
        scale = A.N_PHYS / n_use
        risk = flux * scale
        cumE = np.cumsum(flux * dt_sec) * scale
        P = 1 - np.exp(-cumE)
        vmean = np.where(n_dz > 0, vsum / np.maximum(n_dz, 1), np.nan)
        return n_dz * scale, vmean, risk, cumE, P

    # 预计算所有6个点
    results = {}
    for k in PTS:
        print(f'  computing point {k+1}...')
        results[k] = compute_point(k, N_TS)

    # 图5: 只用 WORST (碎片数+速度)
    n_dz, vmean, _, _, _ = results[WORST]
    fig, ax = plt.subplots(figsize=(7.5,4.6)); ax2 = ax.twinx()
    ax.plot(tgrid, n_dz, 'C0', label='fragments in DZ')
    ax2.plot(tgrid, vmean, 'C3', lw=1, label='mean rel. velocity')
    ax.set_xlabel('time rel. perilune (days)')
    ax.set_ylabel('fragments in danger zone', color='C0')
    ax2.set_ylabel('mean relative velocity (km/s)', color='C3')
    fig.tight_layout(); fig.savefig('fig_paper5_dz.png', dpi=200)
    print('[saved] fig_paper5_dz.png')

    # 图7: 6点叠加，上下子图: 累积E(对数) + P
    fig, axs = plt.subplots(2, 1, figsize=(8,7), sharex=True)
    colors = ['C%d'%i for i in range(6)]
    for k in PTS:
        _, _, risk, cumE, P = results[k]
        axs[0].semilogy(tgrid, cumE + 1e-30, colors[k], lw=1.2, label=f'point {k+1}')
        axs[1].plot(tgrid, P, colors[k], lw=1.2, label=f'point {k+1}')
    axs[0].set_ylabel('cumulative E[impacts] (log)')
    axs[1].set_ylabel('collision probability P')
    axs[1].set_xlabel('time rel. perilune (days)')
    for a in axs: a.grid(alpha=0.3); a.legend(fontsize=7, ncol=3)
    # 收紧x轴到有碎片进区的范围
    active = np.where(n_dz > 0)[0]
    if len(active):
        span = tgrid[active[-1]] - tgrid[active[0]]
        pad = max(0.002, 0.15*span)
        axs[1].set_xlim(tgrid[active[0]]-pad, tgrid[active[-1]]+pad)
    fig.tight_layout(); fig.savefig('fig_paper7_risk.png', dpi=200)
    print('[saved] fig_paper7_risk.png')

    # 图9 2D 空间热力图 (只用 WORST)
    import matplotlib.colors as mcolors
    frags = np.empty((N_TS,6))
    frags[:,:3] = POS[WORST]; frags[:,3:] = VEL[WORST][:N_TS]
    fd = jnp.asarray(frags)
    hit_idx = []
    nb = int(np.ceil(N_TS / A.BATCH))
    for b in range(nb):
        s, en = b*A.BATCH, min((b+1)*A.BATCH, N_TS)
        _, _, _, indz = batch_ts(fd[s:en])
        loc = np.array(jnp.argmax(indz, axis=1))[np.array(jnp.any(indz, axis=1))]
        hit_idx.append(loc)
    hit = np.concatenate(hit_idx) if len(hit_idx) else np.array([], int)
    counts = np.bincount(hit, minlength=N_WIN_FIG7).astype(float)
    Pkm = (np.asarray(SCp) - MOON) * D_EM
    fig, ax = plt.subplots(figsize=(7.6, 6.2))
    ax.scatter(0, 0, c='k', marker='+', s=120, zorder=2, label='Moon center')
    ax.plot(Pkm[:,0], Pkm[:,1], color='0.85', lw=0.8, zorder=1)
    m = counts > 0
    sc = ax.scatter(Pkm[m,0], Pkm[m,1], c=counts[m], cmap='hot_r', s=16, zorder=3,
                    norm=mcolors.LogNorm(vmin=1, vmax=max(counts.max(),1)))
    nz = np.where(m)[0]
    if len(nz):
        ax.scatter(*Pkm[nz[0],:2], marker='>', c='g', s=90, zorder=5, label='intrusion entry')
        ax.scatter(*Pkm[nz[-1],:2], marker='s', c='b', s=60, zorder=5, label='intrusion exit')
    fig.colorbar(sc, ax=ax, label='DZ-intrusion count (log)')
    lim = 8000
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect('equal')
    ax.set_xlabel('x (km, Moon)'); ax.set_ylabel('y (km, Moon)')
    ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout(); fig.savefig('fig_paper9_heatmap.png', dpi=200)
    print('[saved] fig_paper9_heatmap.png')
# ---------- 图8 (论文原版): 进入 10km 自由返回邻域百分比 vs 时间 ----------
def fig8_vicinity():
    sc_km = sc_state[:, :3]*D_EM
    dM = np.linalg.norm(sc_km - MOON*D_EM, axis=1)
    fro = (sc_km[dM < 25000]) / D_EM            # 近月段航迹点(无量纲), 作为静态管中心线
    fro_j = jnp.asarray(fro)
    tube_lu = VIC_TUBE_KM/D_EM
    ts = jnp.asarray(VIC_DAYS/tt_days)
    frags = np.empty((N_VIC,6)); frags[:,:3]=POS[WORST]; frags[:,3:]=VEL[WORST][:N_VIC]
    fd = jnp.asarray(frags)
    b2 = jnp.sum(fro_j**2, -1)[None, None, :]      # (1,1,M)  预算 |fro|²
    @jax.jit
    def cnt_in_tube(fb):
        tj = A.vprop(fb, A.ARGS, ts); tj = jnp.where(jnp.isnan(tj), 1e6, tj)   # (B,T,6)
        Ppos = tj[:,:,:3]
        # |P-fro|² = |P|²+|fro|²-2 P·fro  (矩阵形, 不建 (B,T,M,3) 大张量, 省显存)
        a2 = jnp.sum(Ppos**2, -1)[:,:,None]                                     # (B,T,1)
        ab = jnp.einsum('btj,mj->btm', Ppos, fro_j)                             # (B,T,M)
        dmin2 = jnp.min(a2 + b2 - 2*ab, axis=-1)                                # (B,T)
        return jnp.sum(dmin2 < tube_lu**2, axis=0)                              # (T,)
    cnt = np.zeros(len(VIC_DAYS))
    nb = int(np.ceil(N_VIC/VIC_BATCH))
    for b in tqdm(range(nb), desc='fig8 邻域'):
        s,en = b*VIC_BATCH, min((b+1)*VIC_BATCH, N_VIC)
        cnt += np.asarray(cnt_in_tube(fd[s:en]))
    frac = cnt/N_VIC*100
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(VIC_DAYS, frac, 'C2', lw=1.4)
    ax.set_xlabel('time after breakup (days)')
    ax.set_ylabel(f'fragments within {VIC_TUBE_KM:.0f} km of free-return (%)')
    ax.grid(alpha=0.3)
    early = VIC_DAYS <= 1                       # 放大前1天看初始峰
    if early.sum() > 2:
        axins = ax.inset_axes([0.48, 0.45, 0.48, 0.48])
        axins.plot(VIC_DAYS[early], frac[early], 'C2'); axins.grid(alpha=0.3)
        axins.tick_params(labelsize=7); axins.text(0.5,1.02,'first 1 day',transform=axins.transAxes,ha='center',fontsize=8)
    fig.tight_layout(); fig.savefig('fig_paper8_vicinity.png', dpi=200)
    print('[saved] fig_paper8_vicinity.png  峰值=%.3f%% @ %.2fd'%(frac.max(), VIC_DAYS[int(frac.argmax())]))


if __name__ == "__main__":
    fig3(); fig4(); fig579(); fig8_vicinity()
    print("完成: 图3/4/5/7/8(邻域)/9")
