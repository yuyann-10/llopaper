# 结果总结 / 进度（持续更新）

> 场景：China「近地一次环月两次交会」载人登月。载人飞船经自由返回抵达 **100 km 逆行 LDO**
> 做第一次环月交会对接(RVD)；评估 LDO 上航天器解体碎片对到达飞船**单次近月穿越**的碰撞风险。

最后更新：2026-06-27

---

## 🔑 最新关键结论（修正后）

| 量 | 值 | 说明 |
|---|---|---|
| 最坏点(点3)峰值碰撞概率 | **≈9.0×10⁻⁸** | 500k样本, 95%CI [8.8,9.3]×10⁻⁸ |
| 危险预警时间 Δt | **5–8 d 宽平台** | 非尖峰; 峰约在 5d |
| 残留率 @30d | **71.7%** | 不受下述修正影响 |
| 物理碎片数 N_PHYS | 655 | NASA SBM >0.1m |
| 量级定性 | ~10⁻⁸ 稀有事件 | 与原文 10⁻⁹~10⁻⁸ 一致 |

各点峰值（figdata 细网格 @7.78d）：点1=6.58、点2=7.77、**点3=8.64(峰5d:9.05)**、点4=7.53、点5=6.03、点6=5.58（×10⁻⁸）。排序 3>2>4>1>5>6。

## ⚠️ 重大修正：eval_point 时间分辨率 bug
- **问题**：危险区通量积分 E=∫(v_rel·σ/V_DZ)dt 原在整条 ±4d 轨迹均匀撒 3000 点 → dt≈230 s，
  **大于穿越遭遇时长(~234 s)**，每个碎片被赋过大 dt，导致 **P 系统性高估 ~2.5×**，并产生
  **虚假峰结构**（旧"7.78d 主峰 + 6.3d 深谷掉到 1e-11 + 双峰"全是数值假象）。
- **修复**：时间网格集中到近月点 ±0.12d、dt≈7 s（`eval_point` 里 WIN_HALF=0.12）。
- **验证**：点3@7.78d 2.34e-7→8.64e-8；@5.0d 1.79e-7→9.05e-8。细扫描 5–7.78d 全在 8.2–10.0e-8，
  无深谷无尖峰 → 平台。见 `fig_dt_corrected.png`（修正 vs 旧对比）。

## 图件状态
| 图 | 文件 | 状态 |
|---|---|---|
| 图1 LDO+解体点 | fig_paper1_breakup.png | ✅ 正确 |
| 图6 保护管 3D | fig_paper6_region.png | ✅ 正确 |
| 全任务/近月放大 | fig_full_scenario(_zoom).png | ✅ 正确 |
| 5d碎片环 | fig_dist_5d.png | ✅ 正确 |
| 残留率/分布/危险区/邻域/热力图 | figdata 出的 fig3/4/5/7/8/9 | ✅ 正确（figdata 本就用细网格 dt~7s） |
| Δt 平台曲线 | fig_dt_corrected.png | ⏳ 100k预览; 待服务器500k重画 |
| 收敛图 | fig_convergence.png | ⏳ 待用修正 e_worst 重画 |
| 旧 Δt 全点图 | fig_dt_allpoints.png | ❌ 作废(旧粗网格), 待删/替换 |

## ⏳ 待办（远程）
1. 服务器跑 `python sweep_server.py`（点3 Δt=5.0~7.78d 细网格 500k，断点续算，已预置 5.0/7.78d）→
   生成 `sweep_server.npz`(dt,P,P_lo,P_hi,hits) → 发我精确平台曲线。
2. 我据此：重画 `fig_dt_corrected`(500k) + `fig_convergence`(修正 e_worst) + 删/替 `fig_dt_allpoints`。
3. 定稿 `paper_section5_revision.md` 5.2 剩余 prose（旧双峰/物理含义/收敛段已部分改、待清干净）。

## 关键文件
- `analysis_ldo.py` — 主分析（base/dt stage，已含时间分辨率修复 + 断点续算）
- `sweep_server.py` / `verify_two.py` — 服务器细网格/两点验证（断点续算）
- `figdata_and_plots.py` — fig3/4/5/7/8/9
- `paper_section5_revision.md` — 5.1/5.2/5.3 对照修改稿
- 数据 `*.npz/*.npy` 已 gitignore（含 344MB fragments_ldo.npz，不入库）
