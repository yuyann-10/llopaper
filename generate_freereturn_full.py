# -*- coding: utf-8 -*-
"""
CR3BP 完整绕月自由返回轨道 (地球 205km -> 100km 近月点 -> 地球) + LDO
================================================================
干净自包含。对称打靶: 近月点取在月球远端 x 轴上、速度垂直 x 轴 (0,vy_p),
逆行 (vy_p<0)。单参数调 vy_p 使反向积分的近地点高度 = 205 km。
由对称性自动得到去程(地->月)与返程(月->地)。
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
import matplotlib.pyplot as plt

MU = 0.01215058
D_EM = 389703.0
VU = 1.01755178
TU_S = 382981.0
R_E, R_M = 6378.0, 1738.0
H_LEO, H_LLO = 205.0, 100.0
r_LEO = (R_E + H_LEO)/D_EM
r_LLO = (R_M + H_LLO)/D_EM
EARTH = np.array([-MU, 0.0])
MOON = np.array([1-MU, 0.0])
X_PERI = 1 - MU + r_LLO            # 近月点: 月球远端 x 轴


def cr3bp(t, s):
    x, y, vx, vy = s
    r1 = np.hypot(x+MU, y); r2 = np.hypot(x-1+MU, y)
    ax = 2*vy + x - (1-MU)*(x+MU)/r1**3 - MU*(x-1+MU)/r2**3
    ay = -2*vx + y - (1-MU)*y/r1**3 - MU*y/r2**3
    return [vx, vy, ax, ay]


def integ(s0, t_span, n=5000):
    te = np.linspace(*t_span, n)
    sol = solve_ivp(cr3bp, t_span, s0, method='DOP853', t_eval=te, rtol=1e-12, atol=1e-12)
    return sol.t, sol.y


def perigee_alt(vy_p, t_back=4.5*86400/TU_S, full=False):
    t, y = integ([X_PERI, 0, 0, vy_p], (0, -t_back), n=6000)
    rE = np.hypot(y[0]+MU, y[1]); i = int(np.argmin(rE))
    if full:
        return rE[i]*D_EM - R_E, i, t, y
    return rE[i]*D_EM - R_E


def solve_frt():
    grid = np.linspace(-2.65, -2.25, 50)
    vals = [perigee_alt(v) - H_LEO for v in grid]
    s = np.sign(vals); idx = np.where(np.diff(s) != 0)[0]
    if len(idx) == 0:
        j = int(np.argmin(np.abs(vals)))
        print(f"[warn] 无精确零点, 最接近 vy_p={grid[j]:.4f}, 残差 {vals[j]:.1f} km")
        return grid[j]
    return brentq(lambda v: perigee_alt(v)-H_LEO, grid[idx[0]], grid[idx[0]+1], xtol=1e-11)


def build_full(vy_p):
    alt, ip, tb, yb = perigee_alt(vy_p, full=True)
    # 去程: 近地点 -> 近月点 (时间正序)
    yo = yb[:, :ip+1][:, ::-1]; to = (-tb[:ip+1][::-1]); to -= to[0]
    # 返程: 镜像 (y,vx 取负)
    yr = np.vstack([yo[0,1:], -yo[1,1:], -yo[2,1:], yo[3,1:]])
    tr = to[1:] + to[-1]
    return np.concatenate([to, tr]), np.concatenate([yo, yr], axis=1), to[-1]


def build_ldo():
    v_circ = np.sqrt(MU/r_LLO)
    t, y = integ([X_PERI, 0, 0, -(v_circ+r_LLO)], (0, 2*np.pi*np.sqrt(r_LLO**3/MU)), 3000)
    return y


def main():
    vy_p = solve_frt()
    t, y, T_half = build_full(vy_p)
    ip = int(np.argmin(np.hypot(y[0]-MOON[0], y[1])))
    peri_alt = np.hypot(y[0,ip]-MOON[0], y[1,ip])*D_EM - R_M
    perig = perigee_alt(vy_p)
    ldo = build_ldo()

    # 导出
    out = np.column_stack([t*TU_S/86400, y[0]*D_EM, y[1]*D_EM, np.zeros_like(t),
                           y[2]*VU, y[3]*VU, np.zeros_like(t)])
    np.savetxt('cr3bp_freereturn_full.csv', out, delimiter=',', fmt='%.8f',
               header='Time(Days),x_rot(km),y_rot(km),z_rot(km),vx_rot(km/s),vy_rot(km/s),vz_rot(km/s)',
               comments='')
    print(f"自由返回: 往返 {t[-1]*TU_S/86400:.3f} d (单向 {T_half*TU_S/86400:.3f} d)")
    print(f"近月点高度 {peri_alt:.1f} km | 近地点高度 {perig:.1f} km | vy_p={vy_p:.4f} ({vy_p*VU:.3f} km/s)")
    print("[saved] cr3bp_freereturn_full.csv")

    # ---- 图: 全局 (地月旋转系) + 近月放大 ----
    fig, ax = plt.subplots(figsize=(9, 6))
    half = ip+1
    ax.plot(y[0,:half], y[1,:half], color='royalblue', lw=1.8, label='Outbound (Earth->Moon)')
    ax.plot(y[0,half:], y[1,half:], color='crimson', lw=1.8, label='Return (Moon->Earth)')
    ax.add_patch(plt.Circle(EARTH, R_E/D_EM, color='steelblue', zorder=5, label='Earth'))
    ax.add_patch(plt.Circle(MOON, R_M/D_EM, color='0.6', zorder=5, label='Moon'))
    ax.scatter(y[0,ip], y[1,ip], c='red', s=80, marker='*', zorder=6, label='Perilune (100 km, 1st RVD)')
    ax.set_aspect('equal'); ax.set_xlabel('x (DU)'); ax.set_ylabel('y (DU)')
    ax.set_title('Circumlunar free-return trajectory (CR3BP): outbound + return')
    ax.legend(loc='upper right', fontsize=9); ax.grid(alpha=0.3)

    axins = ax.inset_axes([0.06, 0.06, 0.36, 0.36])
    axins.add_patch(plt.Circle(MOON, R_M/D_EM, color='0.6', zorder=5))
    axins.plot(ldo[0], ldo[1], color='seagreen', lw=1.4, label='Target LDO 100km')
    axins.plot(y[0], y[1], color='royalblue', lw=1.2)
    axins.scatter(y[0,ip], y[1,ip], c='red', s=60, marker='*', zorder=6)
    vr = 5500/D_EM
    axins.set_xlim(MOON[0]-vr, MOON[0]+vr); axins.set_ylim(-vr, vr); axins.set_aspect('equal')
    axins.set_xticks([]); axins.set_yticks([]); axins.set_title('Zoom at Moon', fontsize=8)
    axins.legend(fontsize=6, loc='upper right')
    ax.indicate_inset_zoom(axins, edgecolor='black')
    fig.tight_layout(); fig.savefig('fig_freereturn_full.png', dpi=200)
    print("[saved] fig_freereturn_full.png")


if __name__ == "__main__":
    main()
