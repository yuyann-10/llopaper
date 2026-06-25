# -*- coding: utf-8 -*-
"""
在 100km 逆行 LDO 上生成 8 个解体点的碎片 (NASA SBM 分离速度)
================================================================
解体目标 = cr3bp_ldo_target.csv (论文表2: 100km, i=148.5°, 逆行)。
沿轨道均匀取 8 个解体点; 每点 N 个碎片:
    v_frag = v_LDO(该点) + dv_vec
    dv 大小 ~ 对数正态(论文拟合: meanlog=3.8023, sdlog=0.9617, m/s), 截到 3σ
    dv 方向 各向同性 (球面均匀采样)
输出 fragments_ldo.npz: 各点 breakup 位置(nondim) + 碎片速度(nondim, 旋转系)。
"""
import numpy as np
import pandas as pd

D_EM = 389703.0; VU = 1.01755178; MU = 0.01215058
MOON = np.array([1-MU, 0, 0])
N_PER_POINT = 500_000
N_POINTS = 6
MEANLOG, SDLOG = 3.8023, 0.9617          # 论文 dv 对数正态拟合 (m/s)
DV_MAX = np.exp(MEANLOG + 3*SDLOG)        # 3σ 截断
rng = np.random.default_rng(42)


def main():
    d = pd.read_csv('cr3bp_ldo_target.csv')
    P = d[['x_rot(km)', 'y_rot(km)', 'z_rot(km)']].values
    V = d[['vx_rot(km/s)', 'vy_rot(km/s)', 'vz_rot(km/s)']].values
    # 用相位角累计到 2π 定【第一圈】(三体进动下位置不闭合, 但相位转一圈即一周期)
    r_all = P - MOON*D_EM
    h = np.cross(r_all[0], V[0]); h = h/np.linalg.norm(h)
    e1 = r_all[0]/np.linalg.norm(r_all[0]); e2 = np.cross(h, e1)
    ang = np.unwrap(np.arctan2(r_all @ e2, r_all @ e1))
    period_idx = int(np.argmax(np.abs(ang - ang[0]) >= 2*np.pi))   # 第一圈结束
    sgn = np.sign(ang[period_idx] - ang[0])
    targets = ang[0] + sgn*np.linspace(0, 2*np.pi, N_POINTS, endpoint=False)
    idx = [int(np.argmin(np.abs(ang[:period_idx] - t))) for t in targets]
    print(f"一个周期 = {period_idx} 个采样点; 第一圈内等相位取 {N_POINTS} 点")

    pos_nd = np.zeros((N_POINTS, 3))
    vel_nd = np.zeros((N_POINTS, N_PER_POINT, 3), dtype=np.float32)
    print(f"在 100km LDO 上生成 {N_POINTS} 点 × {N_PER_POINT} 碎片 (dv~lognormal, 3σ截断 {DV_MAX:.0f} m/s)")
    for k, j in enumerate(idx):
        p_km, v_km = P[j], V[j]
        # NASA SBM dv: 大小对数正态, 方向各向同性
        dv_mag = np.exp(rng.normal(MEANLOG, SDLOG, N_PER_POINT))
        dv_mag = np.clip(dv_mag, 0, DV_MAX) / 1000.0        # m/s -> km/s
        u = rng.uniform(-1, 1, N_PER_POINT)
        phi = rng.uniform(0, 2*np.pi, N_PER_POINT)
        s = np.sqrt(1-u*u)
        dirs = np.column_stack([s*np.cos(phi), s*np.sin(phi), u])
        v_frag = v_km[None, :] + dv_mag[:, None]*dirs        # km/s, 旋转系
        pos_nd[k] = p_km / D_EM
        vel_nd[k] = (v_frag / VU).astype(np.float32)
        alt = np.linalg.norm(p_km - MOON*D_EM) - 1738.0
        print(f"  点{k+1}: 高度 {alt:.1f} km, |v_LDO|={np.linalg.norm(v_km):.3f} km/s, "
              f"碎片|v| {np.linalg.norm(v_frag,axis=1).min():.3f}~{np.linalg.norm(v_frag,axis=1).max():.3f} km/s")

    np.savez('fragments_ldo.npz', pos_nd=pos_nd, vel_nd=vel_nd,
             meanlog=MEANLOG, sdlog=SDLOG)
    print(f"[saved] fragments_ldo.npz  ({N_POINTS}×{N_PER_POINT} 碎片)")


if __name__ == "__main__":
    main()
