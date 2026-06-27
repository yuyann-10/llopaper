# 保存为 check_counts.py, 跑完删掉即可
import numpy as np
d = np.load('figdata_cache.npz', allow_pickle=True)
c = d['fig9_counts']
nz = np.where(c > 0)[0]
cn = c[nz]
print('count范围:', cn.min(), cn.max())
print('均值: %.1f  中位数: %.0f' % (cn.mean(), np.median(cn)))
print('总非零点数:', len(cn))
for v in sorted(set(cn.astype(int))):
    n = int(np.sum(cn.astype(int) == v))
    print('  count=%d: %d' % (v, n))
print('<=5占比: %.0f%%' % (np.sum(cn<=5)/len(cn)*100))
print('>=100占比: %.0f%%' % (np.sum(cn>=100)/len(cn)*100))
