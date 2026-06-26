# -*- coding: utf-8 -*-
"""
论文数值模拟图 (图3/4/5/7/8/9) — 计算与绘图分离。

用法:
  python figdata_and_plots.py --compute    # 仅计算, 保存到 figdata_cache.npz
  python figdata_and_plots.py --plot       # 仅绘图, 从缓存读取 (默认)
  python figdata_and_plots.py              # 若无缓存则计算+绘图, 有则仅绘图
"""
import os, sys, argparse
import numpy as np
import jax, jax.numpy as jnp
import matplotlib.pyplot as plt
from tqdm import tqdm
import analysis_ldo as A

CACHE = 'figdata_cache.npz'

# ==================== 参数 ====================
N_SNAP    = 15_000
N_TS      = 100_000
N_RET     = 50_000
N_VIC     = 100_000
N_WIN_FIG7 = 2000
WORST     = 2
DT_PEAK   = 7.8
SNAP_DAYS = [1, 7, 13, 22]
FIG4_PTS  = [0, 2, 3, 5]
FIG4_LIM  = 5000.0
PTS       = [0, 1, 2, 3, 4, 5]
VIC_TUBE_KM = 100.0
VIC_DAYS = np.unique(np.concatenate([np.linspace(0, 1, 60), np.linspace(1, 23, 120)]))
VIC_BATCH = 2000

D_EM = A.D_EM; VU = A.VU; tt_days = A.tt_days
MOON = np.array([1 - A.MU, 0, 0]); R_M = 1738.0
fr = np.load('fragments_ldo.npz'); POS, VEL = fr['pos_nd'], fr['vel_nd']
sc_t, sc_state = A.load_sc()

# ==================== 传播工具 ====================
def propagate(pos, vel, n, ts_days):
    ts = jnp.asarray(np.asarray(ts_days) / tt_days)
    frags = np.empty((n, 6)); frags[:, :3] = pos; frags[:, 3:] = vel[:n]
    fd = jnp.asarray(frags); out = []
    nb = int(np.ceil(n / A.BATCH))
    for b in range(nb):
        s, en = b * A.BATCH, min((b + 1) * A.BATCH, n)
        tj = A.vprop(fd[s:en], A.ARGS, ts)
        out.append(jnp.where(jnp.isnan(tj), 1e6, tj))
    return np.asarray(jnp.concatenate(out))

# ==================== 计算引擎 ====================
def _make_grid():
    tau = sc_t; abs_days = DT_PEAK + tau; keep = abs_days >= 0
    WIN_HALF = 0.08
    g0 = max(DT_PEAK - WIN_HALF, abs_days[keep].min())
    g1 = min(DT_PEAK + WIN_HALF, abs_days[keep].max())
    grid = np.linspace(g0, g1, N_WIN_FIG7)
    SC = np.column_stack([np.interp(grid, abs_days[keep], sc_state[keep][:, k]) for k in range(6)])
    return grid, SC

def compute_all():
    d = {}
    if os.path.exists(CACHE):
        d = dict(np.load(CACHE, allow_pickle=True))
        print(f'加载已有缓存 ({len(d)} 个键), 将跳过已完成部分')

    def save():
        np.savez(CACHE, **d)

    grid, SC = _make_grid()
    SCp = jnp.asarray(SC[:, :3]); SCv = jnp.asarray(SC[:, 3:])
    ts = jnp.asarray(grid / tt_days)
    dt_sec = (grid[1] - grid[0]) * 86400
    tgrid = grid - DT_PEAK

    @jax.jit
    def batch_ts(fb):
        tj = A.vprop(fb, A.ARGS, ts)
        tj = jnp.where(jnp.isnan(tj), 1e6, tj)
        rel = tj[:, :, :3] - SCp[None]
        dmoon2 = jnp.sum((tj[:, :, :3] - jnp.array([1 - A.MU, 0, 0])[None, None])**2, -1)
        indz = (jnp.sum(rel**2, -1) < A.R_DZ_lu**2) & (dmoon2 > A.R_M_LU**2)
        vrel = jnp.linalg.norm(tj[:, :, 3:] - SCv[None], axis=-1) * VU
        n = jnp.sum(indz, 0)
        fl = jnp.sum(jnp.where(indz, vrel * A.AREA_SC_KM2 / A.V_DZ_km3, 0.0), 0)
        vs = jnp.sum(jnp.where(indz, vrel, 0.0), 0)
        return n, fl, vs, indz

    d.setdefault('tgrid', tgrid)
    d.setdefault('sc_pkm_x', (SC[:, :3] - MOON)[:, 0] * D_EM)
    d.setdefault('sc_pkm_y', (SC[:, :3] - MOON)[:, 1] * D_EM)
    save()

    for k in PTS:
        key = f'pt{k}_P'
        if key in d:
            print(f'  点 {k+1} 已缓存, 跳过')
            continue
        print(f'  computing point {k+1}...')
        frags = np.empty((N_TS, 6))
        frags[:, :3] = POS[k]; frags[:, 3:] = VEL[k][:N_TS]
        fd = jnp.asarray(frags)
        n_dz = np.zeros(N_WIN_FIG7); flux = np.zeros(N_WIN_FIG7); vsum = np.zeros(N_WIN_FIG7)
        nb = int(np.ceil(N_TS / A.BATCH))
        for b in range(nb):
            s, en = b * A.BATCH, min((b + 1) * A.BATCH, N_TS)
            n, fl, vs, _ = batch_ts(fd[s:en])
            n_dz += np.array(n); flux += np.array(fl); vsum += np.array(vs)
        scale = A.N_PHYS / N_TS
        cumE_raw = np.cumsum(flux * dt_sec) * scale
        d[f'pt{k}_n_dz'] = n_dz * scale
        d[f'pt{k}_vmean'] = np.where(n_dz > 0, vsum / np.maximum(n_dz, 1), np.nan)
        d[f'pt{k}_risk'] = flux * scale
        d[f'pt{k}_cumE'] = cumE_raw
        d[f'pt{k}_P'] = 1 - np.exp(-cumE_raw)
        save()
        print(f'    已保存 (P={d[f"pt{k}_P"][-1]:.3e})')

    if 'fig9_counts' not in d:
        print('  computing fig9 counts...')
        frags = np.empty((N_TS, 6))
        frags[:, :3] = POS[WORST]; frags[:, 3:] = VEL[WORST][:N_TS]
        fd = jnp.asarray(frags)
        hit_idx = []
        nb = int(np.ceil(N_TS / A.BATCH))
        for b in range(nb):
            s, en = b * A.BATCH, min((b + 1) * A.BATCH, N_TS)
            _, _, _, indz = batch_ts(fd[s:en])
            loc = np.array(jnp.argmax(indz, axis=1))[np.array(jnp.any(indz, axis=1))]
            hit_idx.append(loc)
        hit = np.concatenate(hit_idx) if len(hit_idx) else np.array([], int)
        d['fig9_counts'] = np.bincount(hit, minlength=N_WIN_FIG7).astype(float)
        save()

    if 'vic_frac' not in d:
        print('=== 计算图8 邻域数据 ===')
        sc_km = sc_state[:, :3] * D_EM
        dM_vic = np.linalg.norm(sc_km - MOON * D_EM, axis=1)
        fro = (sc_km[dM_vic < 25000]) / D_EM
        fro_j = jnp.asarray(fro)
        tube_lu = VIC_TUBE_KM / D_EM
        ts_vic = jnp.asarray(VIC_DAYS / tt_days)
        frags = np.empty((N_VIC, 6))
        frags[:, :3] = POS[WORST]; frags[:, 3:] = VEL[WORST][:N_VIC]
        fd_vic = jnp.asarray(frags)
        b2 = jnp.sum(fro_j**2, -1)[None, None, :]

        @jax.jit
        def cnt_in_tube(fb):
            tj = A.vprop(fb, A.ARGS, ts_vic)
            tj = jnp.where(jnp.isnan(tj), 1e6, tj)
            Ppos = tj[:, :, :3]
            a2 = jnp.sum(Ppos**2, -1)[:, :, None]
            ab = jnp.einsum('btj,mj->btm', Ppos, fro_j)
            dmin2 = jnp.min(a2 + b2 - 2 * ab, axis=-1)
            return jnp.sum(dmin2 < tube_lu**2, axis=0)

        cnt = np.zeros(len(VIC_DAYS))
        nb = int(np.ceil(N_VIC / VIC_BATCH))
        for b in tqdm(range(nb), desc='fig8 邻域'):
            s, en = b * VIC_BATCH, min((b + 1) * VIC_BATCH, N_VIC)
            cnt += np.asarray(cnt_in_tube(fd_vic[s:en]))
        d['vic_days'] = VIC_DAYS
        d['vic_frac'] = cnt / N_VIC * 100
        d['vic_tube_km'] = VIC_TUBE_KM
        save()

    d['DT_PEAK'] = DT_PEAK; d['FIG4_LIM'] = FIG4_LIM
    d['SNAP_DAYS'] = np.array(SNAP_DAYS); d['FIG4_PTS'] = np.array(FIG4_PTS)
    save()
    print(f'[saved] {CACHE}  ({os.path.getsize(CACHE)/1e6:.1f} MB)')

# ==================== 绘图函数 ====================
def plot_fig3(d):
    plt.figure(figsize=(8, 5.5))
    plt.subplots_adjust(left=0.15, bottom=0.12)
    colors = plt.cm.viridis(np.linspace(0, 1, len(PTS)))
    for k in PTS:
        plt.plot(d[f'ret_t{k}'], d[f'ret_f{k}'] * 100, lw=1.5, color=colors[k], label=f'{k+1}')
    plt.axhline(70, ls='--', color='gray', lw=0.8)
    plt.xlabel('time after breakup (days)', fontsize=20)
    plt.ylabel('Fraction of debris within 0.01 DU\nof Moon (%)', fontsize=20)
    plt.ylim(70, 77)
    plt.legend(title='Breakup location', fontsize=9); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig('fig_paper3_retention.png', dpi=200)
    print('[saved] fig_paper3_retention.png')

def plot_fig4(d):
    nr, nc = len(FIG4_PTS), len(SNAP_DAYS)
    lim_lu = FIG4_LIM / D_EM; r_m_lu = R_M / D_EM
    fig, axes = plt.subplots(nr, nc, figsize=(3.0 * nc, 3.0 * nr))
    for ri, k in enumerate(FIG4_PTS):
        tj = d[f'fig4_tj{k}']
        bp = POS[k] - MOON
        for ci, day in enumerate(SNAP_DAYS):
            ax = axes[ri, ci]
            P = tj[:, ci] - MOON
            dist = np.linalg.norm(P, axis=1)
            alive = (dist > r_m_lu) & (dist < 5e4 / D_EM)
            ax.scatter(0, 0, c='k', marker='+', s=40, zorder=3)
            ax.scatter(P[alive, 0], P[alive, 1], s=0.5, c='C0', alpha=0.25)
            ax.scatter(bp[0], bp[1], c='red', marker='x', s=60, zorder=4)
            ax.set_xlim(-lim_lu, lim_lu); ax.set_ylim(-lim_lu, lim_lu)
            ax.set_aspect('equal'); ax.tick_params(labelsize=15)
            if ri == 0: ax.set_title(f't = {day} d', fontsize=20, pad=6)
            if ci == 0: ax.set_ylabel('y (DU)', fontsize=17)
            else: ax.set_yticklabels([])
            if ri == nr - 1: ax.set_xlabel('x (DU)', fontsize=17)
            else: ax.set_xticklabels([])
    fig.tight_layout(); fig.savefig('fig_paper4_evolution.png', dpi=200)
    print('[saved] fig_paper4_evolution.png')

def plot_fig5(d):
    tgrid = d['tgrid']; n_dz = d[f'pt{WORST}_n_dz']; vmean = d[f'pt{WORST}_vmean']
    P = d[f'pt{WORST}_P']
    t_sec = tgrid * 86400
    fig, ax = plt.subplots(figsize=(7.5, 4.6)); ax2 = ax.twinx()

    ax.fill_between(t_sec, P * 1e7, alpha=0.2, color='C0')
    ax.plot(t_sec, P * 1e7, 'C0', lw=1.5, label='collision probability')
    mask = n_dz > 0
    ax2.plot(t_sec[mask], vmean[mask], 'C3o-', lw=1.8, ms=4, label='mean rel. velocity')

    ax.set_xlabel('time relative to perilune (seconds)')
    ax.set_ylabel('collision probability (×10⁻⁷)', color='C0')
    ax2.set_ylabel('mean relative velocity (km/s)', color='C3')

    active = np.where(n_dz > 0)[0]
    if len(active):
        pad = (t_sec[active[-1]] - t_sec[active[0]]) * 0.15
        ax.set_xlim(t_sec[active[0]] - pad, t_sec[active[-1]] + pad)
    v_ok = vmean[~np.isnan(vmean)]
    if len(v_ok):
        ax2.set_ylim(0, np.ceil(v_ok.max()))
        ax2.set_yticks(np.arange(0, np.ceil(v_ok.max()) + 0.5, 0.5))
    ax.set_ylim(0, P.max() * 1e7 * 1.15)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout(); fig.savefig('fig_paper5_dz.png', dpi=200)
    print('[saved] fig_paper5_dz.png')

def plot_fig7(d):
    tgrid = d['tgrid']
    fig, axs = plt.subplots(3, 1, figsize=(8, 10), sharex=True)
    colors = plt.cm.viridis(np.linspace(0, 1, len(PTS)))
    for k in PTS:
        axs[0].plot(tgrid, d[f'pt{k}_risk'], color=colors[k], lw=1.2)
        axs[1].semilogy(tgrid, d[f'pt{k}_cumE'] + 1e-30, color=colors[k], lw=1.2)
        axs[2].plot(tgrid, d[f'pt{k}_P'], color=colors[k], lw=1.2)
    axs[0].set_ylabel(r'$\dot{E}(t)$')
    axs[1].set_ylabel(r'$E(t)$')
    axs[2].set_ylabel(r'$P(t)$')
    axs[2].set_xlabel('time rel. perilune (days)')
    for a in axs:
        a.grid(alpha=0.3)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=colors[k], lw=2) for k in PTS]
    fig.legend(handles, [f'{k+1}' for k in PTS], title='Breakup location',
               ncol=6, fontsize=10, title_fontsize=8, loc='upper center', bbox_to_anchor=(0.5, 0.995))
    n_dz = d[f'pt{WORST}_n_dz']
    active = np.where(n_dz > 0)[0]
    if len(active):
        span = tgrid[active[-1]] - tgrid[active[0]]
        pad = max(0.002, 0.15 * span)
        axs[2].set_xlim(tgrid[active[0]] - pad, tgrid[active[-1]] + pad)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig('fig_paper7_risk.png', dpi=200)
    print('[saved] fig_paper7_risk.png')
def plot_fig8_vicinity(d):
    vic_days = d['vic_days']; frac = d['vic_frac']; tube = d['vic_tube_km']
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(vic_days, frac, 'C2', lw=1.4)
    ax.set_xlabel('time after breakup (days)')
    ax.set_ylabel(f'Percentage of fragments')
    early = vic_days <= 1
    if early.sum() > 2:
        axins = ax.inset_axes([0.48, 0.45, 0.48, 0.48])
        axins.plot(vic_days[early], frac[early], 'C2'); axins.grid(alpha=0.3)
        axins.tick_params(labelsize=7)
        axins.text(0.5, 1.02, 'first 1 day', transform=axins.transAxes, ha='center', fontsize=8)
    fig.tight_layout(); fig.savefig('fig_paper8_vicinity.png', dpi=200)
    print('[saved] fig_paper8_vicinity.png  峰值=%.3f%% @ %.2fd' % (frac.max(), vic_days[int(frac.argmax())]))

def plot_fig9(d):
    tgrid = d['tgrid']; counts = d['fig9_counts']
    t_sec = tgrid * 86400
    m = counts > 1
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.bar(t_sec[m], counts[m], width=(t_sec[1]-t_sec[0])*0.9, color='C3', alpha=0.7, edgecolor='C3')
    ax.set_xlabel('time relative to perilune (seconds)')
    ax.set_ylabel('Number of fragments \n per second')
    ax.grid(True, alpha=0.3, axis='y')
    if m.sum():
        pad = (t_sec[m][-1] - t_sec[m][0]) * 0.15
        ax.set_xlim(t_sec[m][0] - pad, t_sec[m][-1] + pad)
        ax.set_ylim(0, counts[m].max() * 1.2)
    fig.tight_layout(); fig.savefig('fig_paper9_heatmap.png', dpi=200)
    print('[saved] fig_paper9_heatmap.png')

def plot_all():
    if not os.path.exists(CACHE):
        print(f'错误: {CACHE} 不存在, 请先运行 --compute')
        sys.exit(1)
    d = np.load(CACHE, allow_pickle=True)
    needed = {'vic_frac', 'fig9_counts', 'pt0_P'}
    if needed - set(d.keys()):
        print('缓存数据不完整, 自动补算...')
        d.close()
        compute_all()
        d = np.load(CACHE, allow_pickle=True)
    needed = {'vic_frac', 'fig9_counts', 'pt0_P'}
    if needed - set(d.keys()):
        print('缓存数据不完整, 自动补算...')
        d.close()
        compute_all()
        d = np.load(CACHE, allow_pickle=True)
    print(f'加载缓存: {CACHE}  (DT_PEAK={d.get("DT_PEAK","?")}d)')
    # plot_fig3(d); plot_fig4(d);  # 已单独出图, 这里跳过
    plot_fig5(d); plot_fig7(d)
    plot_fig8_vicinity(d); plot_fig9(d)
    print('完成: 图5/7/8(邻域)/9')

# ==================== 入口 ====================
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