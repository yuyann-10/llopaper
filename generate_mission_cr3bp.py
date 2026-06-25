# -*- coding: utf-8 -*-
"""
按论文参数在 3D CR3BP 中复现「两次交会」载人登月场景 (近月段)
================================================================
干净自包含, 不依赖任何现有脚本/星历。把 He Boyong(2020) 的月心 J2000 根数
作为月心轨道根数, 转成 3D CR3BP 旋转系状态后在地月三体场内传播。
忽略发射窗口; 各段时长尽量与论文一致。

月心根数 (κ=近心距 km):
  对接目标 LDO   (表2): κ=1838.20 e=0.001  i=148.50 Ω=63.752 ω=112.28  近圆逆行(目标)
  载人飞船近月点 (表6): κ=1838.20 e=1.438  i=152.96 Ω=181.20 ω=302.57  双曲飞掠(单次穿越)

输出 (旋转系 km, 供后续碎片分析):
  cr3bp_ldo_target.csv      100km 逆行 LDO (驻留 ~8 d)
  cr3bp_crew_freereturn.csv 载人飞船近月段(±4d, 含趋地接近)
"""
import numpy as np
from datetime import datetime
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# ---- CR3BP 常量 (与碎片数据一致) ----
MU   = 0.01215058
D_EM = 389703.0          # km = 1 DU
VU   = 1.01755178        # km/s
TU_S = 382981.0          # s
R_M  = 1738.0
DEG  = np.pi/180.0
MOON = np.array([1-MU, 0.0, 0.0])
KAP_ND = 1838.20/D_EM    # 近心距(无量纲) = 100 km 高度
OMEGA = np.array([0, 0, 1.0])   # 旋转系角速度(无量纲)


def kep2cart(mu, kappa, e, i, Om, om, nu):
    """月心二体: 返回相对月球的 (r, v_inertial), 无量纲。"""
    i, Om, om, nu = i*DEG, Om*DEG, om*DEG, nu*DEG
    p = kappa*(1.0+e)
    r = p/(1.0+e*np.cos(nu))
    r_pf = np.array([r*np.cos(nu), r*np.sin(nu), 0.0])
    v_pf = np.sqrt(mu/p)*np.array([-np.sin(nu), e+np.cos(nu), 0.0])
    cO, sO, ci, si, co, so = np.cos(Om), np.sin(Om), np.cos(i), np.sin(i), np.cos(om), np.sin(om)
    R = np.array([[cO*co - sO*so*ci, -cO*so - sO*co*ci,  sO*si],
                  [sO*co + cO*so*ci, -sO*so + cO*co*ci, -cO*si],
                  [so*si,             co*si,             ci]])
    return R @ r_pf, R @ v_pf


def seleno_to_rotating(r_rel, v_rel_inertial):
    """月心惯性轨道状态 -> CR3BP 旋转系状态 (t=0 轴对齐)。
       v_rot = v_rel_inertial - omega x r_rel  (月球项自动抵消)。"""
    pos = MOON + r_rel
    vel = v_rel_inertial - np.cross(OMEGA, r_rel)
    return np.concatenate([pos, vel])


def cr3bp(t, s):
    x, y, z, vx, vy, vz = s
    r1 = np.sqrt((x+MU)**2 + y*y + z*z)
    r2 = np.sqrt((x-1+MU)**2 + y*y + z*z)
    ax =  2*vy + x - (1-MU)*(x+MU)/r1**3 - MU*(x-1+MU)/r2**3
    ay = -2*vx + y - (1-MU)*y/r1**3       - MU*y/r2**3
    az =            - (1-MU)*z/r1**3       - MU*z/r2**3
    return [vx, vy, vz, ax, ay, az]


def propagate(s0, t_span, n=4000):
    te = np.linspace(*t_span, n)
    sol = solve_ivp(cr3bp, t_span, s0, method='DOP853', t_eval=te, rtol=1e-12, atol=1e-12)
    return sol.t, sol.y.T


def lz_moon(S):
    rel = S[:, 0:3] - MOON
    Lz = rel[:, 0]*S[:, 4] - rel[:, 1]*S[:, 3]
    return Lz.mean()


def save(fn, t, S):
    out = np.column_stack([t*TU_S/86400, S[:, 0]*D_EM, S[:, 1]*D_EM, S[:, 2]*D_EM,
                           S[:, 3]*VU, S[:, 4]*VU, S[:, 5]*VU])
    np.savetxt(fn, out, delimiter=',', fmt='%.8f',
               header='Time(Days),x_rot(km),y_rot(km),z_rot(km),vx_rot(km/s),vy_rot(km/s),vz_rot(km/s)',
               comments='')
    print(f"[saved] {fn}")


def dur(t0, t1):
    f = "%Y-%m-%d %H:%M:%S.%f"
    return (datetime.strptime(t1, f)-datetime.strptime(t0, f)).total_seconds()/86400.0


D_PARK = dur("2025-03-31 18:35:00.0", "2025-04-08 18:35:00.0")   # LDO 驻留 (近月->下降)


def main():
    print("="*64)
    print("3D CR3BP 复现 (论文月心根数): 100km 逆行 LDO + 自由返回近月段")
    print(f"  近心距 κ = 1838.20 km (高度 {1838.20-R_M:.0f} km), LDO 驻留 {D_PARK:.2f} d")
    print("="*64)

    # ---- 1. 对接目标 LDO (近圆逆行) ----
    r, v = kep2cart(MU, KAP_ND, 0.001, 148.50, 63.752, 112.28, 0.0)
    s_ldo = seleno_to_rotating(r, v)
    t1, S_ldo = propagate(s_ldo, (0.0, D_PARK*86400/TU_S), n=6000)
    save('cr3bp_ldo_target.csv', t1, S_ldo)

    # ---- 2. 载人飞船自由返回近月段 (双曲飞掠, 近月点锚定, ±4d) ----
    # 近共面: 升交点赤经对齐 LDO(Ω=63.752°), 仅保留倾角差 152.96-148.50=4.46°
    OM_CREW = 63.752
    r, v = kep2cart(MU, KAP_ND, 1.438, 152.96, OM_CREW, 302.57, 0.0)
    s_crew = seleno_to_rotating(r, v)
    win = 4.0*86400/TU_S
    # 近月点 = t0, 向前后各积分再拼接 (对称穿越: 接近段 + 近月点 + 离开段)
    tb, Sb = propagate(s_crew, (0.0, -win), n=4000)
    tf, Sf = propagate(s_crew, (0.0,  win), n=4000)
    t2 = np.concatenate([tb[::-1], tf[1:]])
    S_crew = np.vstack([Sb[::-1], Sf[1:]])
    save('cr3bp_crew_freereturn.csv', t2, S_crew)

    # ---- 校验 ----
    altL = (np.linalg.norm(S_ldo[:, 0:3]-MOON, axis=1).mean())*D_EM - R_M
    rC = np.linalg.norm(S_crew[:, 0:3]-MOON, axis=1)
    ip = int(np.argmin(rC)); altC = rC[ip]*D_EM - R_M
    senseL, senseC = lz_moon(S_ldo), lz_moon(S_crew[max(ip-50,0):ip+50])
    # 趋地接近: 近月段两端到地球最近距离
    rE = np.linalg.norm(S_crew[:, 0:3]-np.array([-MU, 0, 0]), axis=1)
    perigee_alt = rE.min()*D_EM - 6378.0
    # 轨道面夹角
    def nrm(e, i, Om, om):
        rr, vv2 = kep2cart(MU, KAP_ND, e, i, Om, om, 0.0); h = np.cross(rr, vv2); return h/np.linalg.norm(h)
    dih = np.degrees(np.arccos(np.clip(abs(np.dot(nrm(0.001,148.5,63.752,112.28),
                                                  nrm(1.438,152.96,63.752,302.57))), 0, 1)))

    print("-"*64)
    print(f"LDO 目标:   高度 {altL:.1f} km   {'逆行' if senseL<0 else '顺行'}   周期内闭合")
    print(f"载人近月段: 近月点高度 {altC:.1f} km   {'逆行' if senseC<0 else '顺行'} (与LDO同向)" )
    print(f"  趋地端最近地距 = {perigee_alt:.0f} km (自由返回特征: 近月飞掠后趋向地球)")
    print(f"对接目标 LDO 与自由返回近月段 轨道面夹角 = {dih:.2f}°")
    print("="*64)

    # ---- 3D 图 ----
    fig = plt.figure(figsize=(9, 7)); ax = fig.add_subplot(111, projection='3d')
    u, w = np.mgrid[0:2*np.pi:30j, 0:np.pi:15j]
    Rn = R_M/D_EM
    ax.plot_surface(MOON[0]+Rn*np.cos(u)*np.sin(w), Rn*np.sin(u)*np.sin(w), Rn*np.cos(w),
                    color='lightgray', alpha=0.5, linewidth=0)
    ax.plot(S_ldo[:800,0], S_ldo[:800,1], S_ldo[:800,2], 'gray', lw=1.2, label='对接目标 LDO (逆行,i=148.5°)')
    ax.plot(S_crew[:,0], S_crew[:,1], S_crew[:,2], 'seagreen', lw=1.8, label='载人自由返回近月段(i=153°)')
    ax.scatter(S_crew[ip,0], S_crew[ip,1], S_crew[ip,2], c='red', s=80, marker='*', label='近月点(第一次RVD)')
    lim = 0.03
    ax.set_xlim(MOON[0]-lim, MOON[0]+lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_xlabel('x(DU)'); ax.set_ylabel('y(DU)'); ax.set_zlabel('z(DU)')
    ax.set_title('3D CR3BP 旋转系: 对接 LDO 与自由返回近月段'); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig('fig_cr3bp_mission.png', dpi=200)
    print("[saved] fig_cr3bp_mission.png")


if __name__ == "__main__":
    main()
