# -*- coding: utf-8 -*-
"""
CR3BP 完整「两次交会」载人登月场景 (含两条去程)
================================================================
干净自包含。地月旋转系 CR3BP, 论文参数, 忽略历元, 时长尽量一致。

阶段1 着陆器先行奔月: 205km LEO 出发 --(~5.13d 地月转移)--> 100km 近月制动(LOI) -> LDO 驻留
阶段2 载人飞船自由返回: 205km LEO --(自由返回 figure-8)--> 100km 近月点(第一次RVD) -> 地球
两者近月点同为 100km 逆行, 近共面。
"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq, root
import matplotlib.pyplot as plt

MU = 0.01215058
D_EM = 389703.0; VU = 1.01755178; TU_S = 382981.0
R_E, R_M = 6378.0, 1738.0
H_LEO, H_LLO = 205.0, 100.0
r_LEO = (R_E+H_LEO)/D_EM
r_LLO = (R_M+H_LLO)/D_EM
EARTH = np.array([-MU, 0.0]); MOON = np.array([1-MU, 0.0])
X_PERI = 1-MU+r_LLO
TOF_LANDER = 5.129*86400/TU_S          # 论文 03-03 15:28:45 -> 03-08 18:35:00


def cr3bp(t, s):
    x, y, vx, vy = s
    r1 = np.hypot(x+MU, y); r2 = np.hypot(x-1+MU, y)
    return [vx, vy,
            2*vy + x - (1-MU)*(x+MU)/r1**3 - MU*(x-1+MU)/r2**3,
            -2*vx + y - (1-MU)*y/r1**3 - MU*y/r2**3]


def integ(s0, t_span, n=6000):
    te = np.linspace(*t_span, n)
    s = solve_ivp(cr3bp, t_span, s0, method='DOP853', t_eval=te, rtol=1e-12, atol=1e-12)
    return s.t, s.y


def depart_leo(theta, dv1):
    """205km LEO 出发 (自治旋转系): v_rot = (v_circ+dv1 - r_LEO)*切向。"""
    v_circ = np.sqrt((1-MU)/r_LEO)
    pos = EARTH + r_LEO*np.array([np.cos(theta), np.sin(theta)])
    tang = np.array([-np.sin(theta), np.cos(theta)])
    vel = (v_circ + dv1 - r_LEO)*tang
    return [pos[0], pos[1], vel[0], vel[1]]


# ---------- 阶段2: 载人自由返回 (对称打靶) ----------
def perigee_alt(vy_p, full=False):
    t, y = integ([X_PERI, 0, 0, vy_p], (0, -4.5*86400/TU_S))
    rE = np.hypot(y[0]+MU, y[1]); i = int(np.argmin(rE))
    return (rE[i]*D_EM-R_E, i, t, y) if full else rE[i]*D_EM-R_E

def solve_freereturn():
    g = np.linspace(-2.65, -2.25, 50); v = [perigee_alt(x)-H_LEO for x in g]
    idx = np.where(np.diff(np.sign(v)) != 0)[0]
    vy = brentq(lambda x: perigee_alt(x)-H_LEO, g[idx[0]], g[idx[0]+1], xtol=1e-11)
    _, ip, tb, yb = perigee_alt(vy, full=True)
    yo = yb[:, :ip+1][:, ::-1]                              # 去程: 近地点 -> 近月点
    tf, yf = integ([X_PERI, 0, 0, vy], (0, 4.5*86400/TU_S))  # 返程: 自近月点正向积分
    rEf = np.hypot(yf[0]+MU, yf[1]); jf = int(np.argmin(rEf))
    yr = yf[:, :jf+1]                                       # 近月点 -> 近地点
    full = np.concatenate([yo, yr[:, 1:]], axis=1)
    T_round = (tb[ip]*-1 + tf[jf]) * TU_S/86400            # 去程+返程总时长(天)
    return full, yo.shape[1]-1, T_round, vy


# ---------- 阶段1: 着陆器去程 (打靶到 100km 近月点, TOF≈5.13d) ----------
def lander_resid(p):
    theta, dv1 = p
    t, y = integ(depart_leo(theta, dv1), (0, 7*86400/TU_S), n=9000)
    rM = np.hypot(y[0]-MOON[0], y[1]); i = int(np.argmin(rM))
    return [(rM[i]-r_LLO)*100, (t[i]-TOF_LANDER)*5]

def lander_peri(th, dv1):
    """返回 (第一次掠月近月点高度 km, TOF d, 索引 i, t, y)。
       取 SOI 内首个最近点, 避免全局最小随 dv1 在多次掠月间跳变。"""
    t, y = integ(depart_leo(th, dv1), (0, 6.5*86400/TU_S), n=5000)
    rM = np.hypot(y[0]-MOON[0], y[1])
    mask = rM < 0.045                                # 进入月球 SOI (~17500 km)
    if not mask.any():
        return 1e6, t[-1]*TU_S/86400, len(t)-1, t, y
    idxs = np.where(mask)[0]
    brk = np.where(np.diff(idxs) > 1)[0]
    block = idxs[:brk[0]+1] if len(brk) else idxs    # 第一段连续 SOI 块
    i = int(block[np.argmin(rM[block])])
    return rM[i]*D_EM - R_M, t[i]*TU_S/86400, i, t, y

def solve_lander(alt_lo=100.0, alt_hi=200.0):
    """扫描, 挑近月点∈[100,200]km 且 TOF 最接近 5.13d 的解 (放宽窗口)。"""
    TOF_d = TOF_LANDER*TU_S/86400
    sols = []
    for th in np.radians(np.linspace(-150, -50, 40)):
        for dv1 in np.linspace(2.85, 3.30, 90)/VU:
            alt, tof, i, t, y = lander_peri(th, dv1)
            if tof > 1.5 and alt_lo <= alt <= alt_hi:
                sols.append((abs(tof-TOF_d), th, dv1))
    if not sols:
        return None
    sols.sort()
    _, th0, dv1 = sols[0]
    _, _, i, t, y = lander_peri(th0, dv1)
    return t[:i+1], y[:, :i+1], th0, dv1


def build_ldo():
    vc = np.sqrt(MU/r_LLO)
    _, y = integ([X_PERI, 0, 0, -(vc+r_LLO)], (0, 2*np.pi*np.sqrt(r_LLO**3/MU)), 3000)
    return y, vc


def main():
    print("求解载人自由返回...")
    y_fr, ip, T_round, vy = solve_freereturn()
    print("求解着陆器去程...")
    land = solve_lander()
    ldo, vc = build_ldo()

    yl = None
    if land is not None:
        tl, yl, th, dv1 = land
        loi = abs(np.hypot(yl[2,-1], yl[3,-1]) - vc)*VU
        print(f"着陆器: dv1={dv1*VU:.4f} km/s, TOF={tl[-1]*TU_S/86400:.3f} d, "
              f"近月点={np.hypot(yl[0,-1]-MOON[0],yl[1,-1])*D_EM-R_M:.1f} km, LOI≈{loi:.3f} km/s")
    else:
        print("[warn] 着陆器去程未收敛")

    # ===== 图(一): 全任务 (地月旋转系) — 独立成图, 无标题 =====
    fig, ax = plt.subplots(figsize=(8, 6.6))
    ax.add_patch(plt.Circle(EARTH, R_E/D_EM, color='steelblue', zorder=6, label='Earth'))
    ax.add_patch(plt.Circle(MOON, R_M/D_EM, color='0.6', zorder=6, label='Moon'))
    ax.plot(y_fr[0,:ip+1], y_fr[1,:ip+1], color='royalblue', lw=1.8, label='Crew free-return: outbound')
    ax.plot(y_fr[0,ip:], y_fr[1,ip:], color='crimson', lw=1.6, label='Crew free-return: return')
    if yl is not None:
        ax.plot(yl[0], yl[1], color='darkorange', lw=1.8, label='Lander outbound (Earth->LDO)')
    ax.scatter(y_fr[0,ip], y_fr[1,ip], c='red', s=90, marker='*', zorder=7, label='Perilune (1st RVD)')
    ax.set_aspect('equal'); ax.set_xlabel('x (DU)'); ax.set_ylabel('y (DU)')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=13); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig('fig_full_scenario.png', dpi=200, bbox_inches='tight')
    print("[saved] fig_full_scenario.png")

    # ===== 图(二): 近月放大 — 独立成图, 无标题 =====
    fig2, axz = plt.subplots(figsize=(7.5, 6.6))
    axz.add_patch(plt.Circle(MOON, R_M/D_EM, color='0.6', zorder=6, label='Moon'))
    axz.plot(ldo[0], ldo[1], color='seagreen', lw=2, label='Target LDO (100 km)')
    axz.plot(y_fr[0], y_fr[1], color='royalblue', lw=1.4, label='Crew free-return')
    if yl is not None:
        axz.plot(yl[0], yl[1], color='darkorange', lw=1.4, label='Lander outbound')
    axz.scatter(y_fr[0,ip], y_fr[1,ip], c='red', s=110, marker='*', zorder=7, label='Perilune / 1st RVD')
    vr = 6000/D_EM
    axz.set_xlim(MOON[0]-vr, MOON[0]+vr); axz.set_ylim(-vr, vr); axz.set_aspect('equal')
    axz.set_xlabel('x (DU)'); axz.set_ylabel('y (DU)')
    axz.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=13); axz.grid(alpha=0.3)
    fig2.tight_layout(); fig2.savefig('fig_full_scenario_zoom.png', dpi=200, bbox_inches='tight')
    print(f"载人自由返回: 往返 {T_round:.3f} d, 近月点 {np.hypot(y_fr[0,ip]-MOON[0],y_fr[1,ip])*D_EM-R_M:.1f} km")
    print("[saved] fig_full_scenario_zoom.png")


if __name__ == "__main__":
    main()
