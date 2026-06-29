# 保存为 extract_peaks.py, 在 LLO_paper 目录下运行
import numpy as np

d = np.load('analysis_base.npz')
table = d['table']      # (6, N_dt) 碰撞概率
dts = d['dts']           # Δt 数组
pts = d['pts']           # [0,1,2,3,4,5]

# 找到主峰 (≈7.8d) 和次峰 (≈5.2d) 的 Δt 索引
mask_main = (dts >= 7.0) & (dts <= 9.0)
mask_sec  = (dts >= 4.5) & (dts <= 6.0)

print(f"{'Point':<8} {'Main peak (≈7.8d)':<22} {'Sec. peak (≈5.2d)':<22}")
print("-" * 52)
main_vals, sec_vals = [], []
for r, k in enumerate(pts):
    p_main = table[r][mask_main].max() if mask_main.any() else 0
    p_sec  = table[r][mask_sec].max()  if mask_sec.any()  else 0
    main_vals.append(p_main); sec_vals.append(p_sec)
    print(f"  {k+1:<6} {p_main:<22.3e} {p_sec:<22.3e}")
import numpy as np

d = np.load('analysis_base.npz')
table = d['table']      # (6, N_dt)
dts = d['dts']           # Δt 网格

# 每个点独立找主峰和次峰
for r in range(6):
    row = table[r]
    # 主峰: 在 Δt > 6.5 范围内找最大 P
    mask_hi = dts > 6.5
    i_main = mask_hi.nonzero()[0][np.argmax(row[mask_hi])]
    # 次峰: 在 Δt ∈ [3, 6.5] 范围内找最大 P
    mask_lo = (dts >= 3) & (dts <= 6.5)
    i_sec = mask_lo.nonzero()[0][np.argmax(row[mask_lo])]
    print(f"点{r+1}: 主峰 Δt={dts[i_main]:.2f}d P={row[i_main]:.3e}  |  次峰 Δt={dts[i_sec]:.2f}d P={row[i_sec]:.3e}")
print("-" * 52)
print(f"  Avg    {np.mean(main_vals):<22.3e} {np.mean(sec_vals):<22.3e}")
 
 
d = np.load('figdata_cache.npz', allow_pickle=True)
tgrid = d['tgrid']

print(f"{'解体位置':<10} {'峰值时间':<12} {'峰值数量':<10} {'开始时间':<12} {'结束时间':<12} {'平均相对速度':<14}")
print(f"{'':10} {'(d)':<12} {'(个)':<10} {'(d)':<12} {'(d)':<12} {'(km/s)':<14}")
print("-" * 72)

for k in range(6):
    n = d[f'pt{k}_n_dz']
    v = d[f'pt{k}_vmean']
    active = np.where(n > 0)[0]
    if len(active):
        i_peak = active[np.argmax(n[active])]
        t_peak  = tgrid[i_peak]
        n_peak  = n[i_peak]
        v_peak  = v[i_peak]
        t_start = tgrid[active[0]]
        t_end   = tgrid[active[-1]]
    else:
        t_peak = n_peak = v_peak = t_start = t_end = 0
    print(f"  点{k+1:<7} {t_peak:<12.4f} {n_peak:<10.0f} {t_start:<12.4f} {t_end:<12.4f} {v_peak:<14.3f}")

    import numpy as np

d = np.load('figdata_cache.npz', allow_pickle=True)
tgrid = d['tgrid']

print(f"{'解体位置':<10} {'Ė_peak (s⁻¹)':<16} {'E_final':<14} {'P_final':<14}")
print("-" * 54)

for k in range(6):
    risk = d[f'pt{k}_risk']        # Ė(t) 瞬时期望撞击率
    cumE = d[f'pt{k}_cumE']        # E(t) 累积期望撞击数
    P    = d[f'pt{k}_P']           # P(t) 碰撞概率
    print(f"  点{k+1:<7} {risk.max():<16.3e} {cumE[-1]:<14.3e} {P[-1]:<14.3e}")
import numpy as np

d = np.load('figdata_cache.npz', allow_pickle=True)
counts = d['fig9_counts']
x = d['sc_pkm_x']
y = d['sc_pkm_y']
tgrid = d['tgrid']

nz = np.where(counts > 0)[0]
i_start, i_end = nz[0], nz[-1]

print(f"交会起始:  t={tgrid[i_start]:.4f} d  |  x={x[i_start]:.1f}  y={y[i_start]:.1f} km (月心)")
print(f"交会终止:  t={tgrid[i_end]:.4f} d  |  x={x[i_end]:.1f}  y={y[i_end]:.1f} km (月心)")
print(f"交会持续:  {tgrid[i_end]-tgrid[i_start]:.4f} d ≈ {(tgrid[i_end]-tgrid[i_start])*86400:.0f} s")
print(f"峰值位置:  t={tgrid[nz[np.argmax(counts[nz])]]:.4f} d")

import numpy as np

d = np.load('figdata_cache.npz', allow_pickle=True)
counts = d['fig9_counts']
nz = np.where(counts > 0)[0]
c_nz = counts[nz]

print(f"非零count点数: {len(nz)}, 全长: {len(counts)}")
print(f"count范围: {c_nz.min():.0f} ~ {c_nz.max():.0f}")
print(f"count均值: {c_nz.mean():.1f}, 中位数: {np.median(c_nz):.0f}")
print()
for v in sorted(set(c_nz.astype(int))):
    n = int(np.sum(c_nz.astype(int) == v))
    print(f"  count={v}: {n} 个点")

# 是否集中在低值?
print(f"\n≤3的点占比: {np.sum(c_nz <= 3) / len(c_nz) * 100:.0f}%")
print(f"≥6的点占比: {np.sum(c_nz >= 6) / len(c_nz) * 100:.0f}%")
