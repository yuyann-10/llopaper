# 保存为 extract_data.py, 在 LLO_paper 目录下运行
import numpy as np

d = np.load('figdata_cache.npz', allow_pickle=True)
WORST = 2  # 点3

# ===== 5.2 表3: 危险区统计 =====
tgrid = d['tgrid']
n_dz = d[f'pt{WORST}_n_dz']
vmean = d[f'pt{WORST}_vmean']
active = n_dz > 0
t_active = tgrid[active]
n_active = n_dz[active]
v_active = vmean[active]

peak_idx = np.argmax(n_active)
print('=== 5.2 表3: 危险区内碎片统计 (最坏点3, Δt≈7.8d) ===')
print(f'峰值碎片数: {n_active[peak_idx]:.1f}')
print(f'首/末次进入危险区时刻: {t_active[0]:.4f} d / {t_active[-1]:.4f} d (rel. perilune)')
print(f'平均相对速度 (峰值): {v_active[peak_idx]:.1f} km/s')
print(f'平均相对速度 (全窗口): {np.mean(v_active):.1f} km/s')
print(f'速度范围: {v_active.min():.1f} ~ {v_active.max():.1f} km/s')

# ===== 5.3 邻域峰值 =====
vic_days = d['vic_days']
vic_frac = d['vic_frac']

# 初始峰值 (前1天内)
early = vic_days <= 1
print(f'\n=== 5.3 100km邻域 ===')
print(f'初始峰值: {vic_frac[early].max():.3f}% @ {vic_days[early][np.argmax(vic_frac[early])]:.3f} d')

# 二次峰 (1天之后)
late = vic_days > 1
late_frac = vic_frac[late]
# 找局部峰值
from scipy.signal import find_peaks
peaks, props = find_peaks(late_frac, prominence=0.001)
late_days = vic_days[late]
if len(peaks) > 0:
    sorted_peaks = peaks[np.argsort(late_frac[peaks])[::-1]]
    for i, p in enumerate(sorted_peaks[:3]):
        print(f'二次峰{i+1}: {late_frac[p]:.3f}% @ {late_days[p]:.2f} d')
else:
    print(f'二次峰: 无显著峰值')

# ===== 5.3 侵入区边界 =====
x = d['sc_pkm_x']; y = d['sc_pkm_y']; counts = d['fig9_counts']
m = counts > 0
nz = np.where(m)[0]
print(f'\n=== 5.3 侵入区空间边界 ===')
print(f'侵入起始: ({x[nz[0]]:.0f}, {y[nz[0]]:.0f}) km')
print(f'侵入终止: ({x[nz[-1]]:.0f}, {y[nz[-1]]:.0f}) km')
print(f'侵入网格点数: {len(nz)} / {len(counts)}')