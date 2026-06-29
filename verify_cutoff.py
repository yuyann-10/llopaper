# -*- coding: utf-8 -*-
"""验证 9d 截断机制: 检查点3碎片在不同时刻的月心距分布与轨道面倾角散布。
用小样本(N=2000)在本地跑, 只看趋势。
"""
import numpy as np
import jax, jax.numpy as jnp
import matplotlib.pyplot as plt
import analysis_ldo as A

jax.config.update("jax_enable_x64", True)

N  = 3000                          # 小样本
TS = np.array([0.5, 1, 3, 5, 7, 9, 10, 11, 14, 20])   # 检查时刻(天)

fr = np.load('fragments_ldo.npz')
POS, VEL = fr['pos_nd'], fr['vel_nd']   # 点3 = index 2
pos0 = POS[2]; vel0 = VEL[2][:N]

frags = np.empty((N, 6))
frags[:, :3] = pos0; frags[:, 3:] = vel0
fd = jnp.asarray(frags)

ts = jnp.asarray(TS / A.tt_days)
print(f'传播 {N} 个碎片到 {len(TS)} 个时刻...')
traj = A.vprop(fd, A.ARGS, ts)   # (N, T, 6)
traj = np.array(traj)            # (N, T, 6)

MOON = np.array([1-A.MU, 0, 0])
R_M  = A.R_M_LU                  # 月球半径 DU

results = {}
for ti, t_day in enumerate(TS):
    pos = traj[:, ti, :3]        # (N, 3) 位置 DU
    vel = traj[:, ti, 3:]        # (N, 3) 速度 DU/TU
    r_moon = np.linalg.norm(pos - MOON, axis=1)          # 月心距 DU
    alive = (r_moon > R_M) & (~np.isnan(r_moon)) & (r_moon < 0.05)  # 未撞月 & 近月(<~20000km)
    r_km  = r_moon[alive] * A.D_EM - 1738.0              # 高度 km
    n_alive = alive.sum()

    # 轨道面倾角: 角动量方向
    rel = pos[alive] - MOON
    h   = np.cross(rel, vel[alive])                      # (n,3) 角动量
    h_norm = h / (np.linalg.norm(h, axis=1, keepdims=True) + 1e-30)
    inc_deg = np.degrees(np.arccos(np.clip(h_norm[:, 2], -1, 1)))   # 相对旋转系z轴

    results[t_day] = dict(
        n_alive=n_alive,
        frac_alive=n_alive/N,
        alt_mean=r_km.mean() if len(r_km)>0 else np.nan,
        alt_std =r_km.std()  if len(r_km)>0 else np.nan,
        inc_mean=inc_deg.mean() if len(inc_deg)>0 else np.nan,
        inc_std =inc_deg.std()  if len(inc_deg)>0 else np.nan,
        frac_ldo=(np.abs(r_km - 0) < 500).sum()/N,   # 高度 <500km (≈LDO带)
    )
    # 方位角相位：碎片在 LDO 轨道面内相对近月点（x方向）的相位角
    rel = pos[alive] - MOON
    phase_ang = np.degrees(np.arctan2(rel[:, 1], rel[:, 0]))  # 月心 x-y 平面方位角
    # 近月点附近（|phase| < 15°）的碎片比例
    frac_peri = (np.abs(phase_ang) < 15).sum() / N
    results[t_day]['frac_peri'] = frac_peri
    results[t_day]['phase_std'] = phase_ang.std() if len(phase_ang)>0 else np.nan

    fl = results[t_day]["frac_ldo"]
    print(f't={t_day:4.1f}d  近月={n_alive:4d}({n_alive/N*100:.0f}%)  '
          f'高度={results[t_day]["alt_mean"]:.0f}±{results[t_day]["alt_std"]:.0f}km  '
          f'倾角={results[t_day]["inc_mean"]:.1f}°±{results[t_day]["inc_std"]:.1f}°  '
          f'近月点方位碎片={frac_peri:.1%}')

# 画图
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
t_list = TS
ax1, ax2, ax3 = axes

ax1.plot(t_list, [results[t]['frac_alive'] for t in t_list], 'o-', color='steelblue')
ax1.set_xlabel('t (days after breakup)'); ax1.set_ylabel('Fraction near Moon (<0.05 DU)')
ax1.set_title('Fragment retention near Moon'); ax1.grid(alpha=0.3)

ax2.errorbar(t_list, [results[t]['alt_mean'] for t in t_list],
             yerr=[results[t]['alt_std'] for t in t_list], fmt='o-', color='darkorange', capsize=4)
ax2.axhline(100, ls='--', color='gray', lw=1, label='LDO 100km')
ax2.set_xlabel('t (days)'); ax2.set_ylabel('Altitude (km, Moon-centered)')
ax2.set_title('Mean altitude ± std of near-Moon fragments'); ax2.legend(); ax2.grid(alpha=0.3)

ax3.errorbar(t_list, [results[t]['inc_mean'] for t in t_list],
             yerr=[results[t]['inc_std'] for t in t_list], fmt='o-', color='crimson', capsize=4)
ax3.set_xlabel('t (days)'); ax3.set_ylabel('Inclination (deg, rotating frame)')
ax3.set_title('Mean inclination ± std (orbital plane scatter)'); ax3.grid(alpha=0.3)

fig.tight_layout()
fig.savefig('fig_verify_cutoff.png', dpi=160, bbox_inches='tight')
print('\n[saved] fig_verify_cutoff.png')

np.save('verify_cutoff_results.npy', results)

# 额外: 画 5d vs 10d 的方位角分布直方图
fig2, axes2 = plt.subplots(1, 2, figsize=(10, 4))
for ax, t_check in zip(axes2, [5.0, 10.0]):
    ti = list(TS).index(t_check)
    pos = traj[:, ti, :3]
    r_moon = np.linalg.norm(pos - MOON, axis=1)
    alive = (r_moon > R_M) & (~np.isnan(r_moon)) & (r_moon < 0.05)
    rel = pos[alive] - MOON
    ang = np.degrees(np.arctan2(rel[:, 1], rel[:, 0]))
    ax.hist(ang, bins=36, range=(-180, 180), color='steelblue', edgecolor='k', lw=0.3)
    ax.axvspan(-15, 15, color='red', alpha=0.2, label='Perilune zone (±15°)')
    ax.set_xlabel('Phase angle (deg, Moon-centered x-y plane)')
    ax.set_ylabel('Fragment count')
    ax.set_title(f't={t_check:.0f}d: {alive.sum()} frags near Moon')
    ax.legend(fontsize=9); ax.grid(alpha=0.3)
fig2.suptitle('Fragment azimuthal phase distribution: uniform ring or gap near perilune?')
fig2.tight_layout()
fig2.savefig('fig_verify_phase.png', dpi=160, bbox_inches='tight')
print('[saved] fig_verify_phase.png')