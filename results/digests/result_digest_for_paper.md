# v1.1.1 论文填数结果摘要

本文件仅汇总当前最终输出文件中的数值，不改变模型、不改变参数、不重新优化。

## 0. 数据来源与口径

| 内容 | 来源 |
|---|---|
| 问题一 JSON 汇总 | `p1_results.json` |
| 问题一表格 | `output/tables/*.csv` |
| 问题二行程与五套偏好 | `baseline_plan.json` |
| 问题三可靠度与敏感性 | `reliability_report.json` |
| 问题三补充诊断 | `output/diagnostics/diagnostic_report.json`、`output/diagnostics/diagnostic_report.md` |
| 图件 | `output/figures/*.png` |

v1.1.1 边界参数：`tau_dep_per_day=[11.5,8.5,8.5,8.5,8.5]`，`tau_back_max_per_day=[21.0,21.0,21.0,21.0,16.5]`，`T_scenic_max_per_day=[9.5,12.5,12.5,12.5,8.0]`。来源：`baseline_plan.json.boundary_v111` 与 `reliability_report.json.assumptions`。

Monte Carlo 参数：`N_simulations=10000`，`sensitivity_N_simulations=10000`，`seed=2026`，默认 `p_peak=0.6`，`p_off=0.3`，早到处理为 `wait_until_open`。来源：`reliability_report.json.assumptions`。

## 1. 问题一：景点特征与优先级

### 1.1 综合优先级排序

来源：`output/tables/p3_priority_ranking.csv`。

| rank | id | P_i | S_i | L_i | D_i_comm | 1-C_i | tier |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | A3 | 0.6879 | 0.7500 | 0.7143 | 0.8000 | 0.4000 | high |
| 2 | A7 | 0.6103 | 0.6800 | 0.5714 | 0.7333 | 0.3600 | high |
| 3 | A2 | 0.5726 | 0.9200 | 0.1429 | 0.4667 | 0.6400 | high |
| 4 | A1 | 0.5677 | 0.8600 | 0.4286 | 0.6667 | 0.1200 | high |
| 5 | A10 | 0.5377 | 0.7600 | 0.4286 | 0.6667 | 0.1200 | mid |
| 6 | A8 | 0.5187 | 0.8300 | 0.4286 | 0.5333 | 0.1200 | mid |
| 7 | A5 | 0.5057 | 0.7200 | 0.4286 | 0.6000 | 0.1200 | mid |
| 8 | A9 | 0.4563 | 0.7000 | 0.5714 | 0.3333 | 0.1600 | low |
| 9 | A6 | 0.4506 | 0.7800 | 0.1429 | 0.2000 | 0.6400 | low |
| 10 | A4 | 0.3600 | 0.8000 | 0.0000 | 0.0000 | 0.6000 | low |

高优先级景点：`A3, A7, A2, A1`。来源：`output/tables/p5_priority_pool.csv`。

### 1.2 四维评分表

来源：`output/tables/p2_four_dim_scores.csv`。

| id | S_i | L_i | D_i_comm | C_i | C_1i | C_2i | C_3i | C_4i |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | 0.8600 | 0.4286 | 0.6667 | 0.8800 | 1.0000 | 1.0000 | 1.0000 | 0.4000 |
| A2 | 0.9200 | 0.1429 | 0.4667 | 0.3600 | 0.0000 | 0.0000 | 1.0000 | 0.8000 |
| A3 | 0.7500 | 0.7143 | 0.8000 | 0.6000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| A4 | 0.8000 | 0.0000 | 0.0000 | 0.4000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| A5 | 0.7200 | 0.4286 | 0.6000 | 0.8800 | 1.0000 | 1.0000 | 1.0000 | 0.4000 |
| A6 | 0.7800 | 0.1429 | 0.2000 | 0.3600 | 0.0000 | 0.0000 | 1.0000 | 0.8000 |
| A7 | 0.6800 | 0.5714 | 0.7333 | 0.6400 | 1.0000 | 1.0000 | 0.0000 | 0.2000 |
| A8 | 0.8300 | 0.4286 | 0.5333 | 0.8800 | 1.0000 | 1.0000 | 1.0000 | 0.4000 |
| A9 | 0.7000 | 0.5714 | 0.3333 | 0.8400 | 1.0000 | 1.0000 | 1.0000 | 0.2000 |
| A10 | 0.7600 | 0.4286 | 0.6667 | 0.8800 | 1.0000 | 1.0000 | 1.0000 | 0.4000 |

### 1.3 优先级池

来源：`output/tables/p5_priority_pool.csv`。

| tier | id | P_i | recommend_role |
|---|---|---:|---|
| high | A3 | 0.6879 | 必选 |
| high | A7 | 0.6103 | 必选 |
| high | A2 | 0.5726 | 必选 |
| high | A1 | 0.5677 | 必选 |
| mid | A10 | 0.5377 | 推荐 |
| mid | A8 | 0.5187 | 推荐 |
| mid | A5 | 0.5057 | 推荐 |
| low | A9 | 0.4563 | 备选 |
| low | A6 | 0.4506 | 备选 |
| low | A4 | 0.3600 | 备选 |

### 1.4 联动组合

来源：`output/tables/p4_combo_pairs.csv`。满足 `D_ij<=0.5` 的组合共 `18` 组。

| pair | D_ij | Link_ij | feasible_one_day | combined_type |
|---|---:|---:|---|---|
| A2-A8 | 0.2 | 0.8333 | False | 主题+主题 |
| A1-A10 | 0.2 | 0.8333 | True | 人文+人文 |
| A3-A7 | 0.2 | 0.8333 | True | 休闲+自然 |
| A1-A5 | 0.3 | 0.7692 | True | 人文+人文 |
| A2-A10 | 0.3 | 0.7692 | True | 主题+人文 |
| A1-A8 | 0.3 | 0.7692 | True | 人文+主题 |
| A8-A10 | 0.3 | 0.7692 | True | 主题+人文 |
| A4-A9 | 0.3 | 0.7692 | False | 自然+自然 |
| A1-A2 | 0.4 | 0.7143 | False | 人文+主题 |
| A5-A10 | 0.4 | 0.7143 | True | 人文+人文 |

对应图件：`output/figures/fig_priority_ranking.png`。

## 2. 问题二：行程优化结果

### 2.1 可行解与归一化基准

来源：`baseline_plan.json.n_feasible_plans` 与 `baseline_plan.json.norm_basis`。

| 指标 | 数值 |
|---|---:|
| 可行解数量 | 1,066,932 |
| Z1_min | 36.1000 |
| Z1_max | 64.2000 |
| Z2_min | 4.6000 |
| Z2_max | 11.7000 |
| Z3_min | 0.0376 |
| Z3_max | 9.6616 |
| Z4_min | 0.2000 |
| Z4_max | 3.7000 |

### 2.2 五套偏好 top-1

来源：`baseline_plan.json.profiles.<profile>.top[0]`。

| profile | lambda | selected | Z1 | Z2 | Z3 | Z4 | Z4_mean | F |
|---|---|---|---:|---:|---:|---:|---:|---:|
| recommend | [0.6,0.2,0.2,0.0] | A1,A10,A2,A3,A5,A6,A7,A8 | 63.00 | 7.80 | 0.3864 | 0.60 | 3.04 | 0.8770 |
| preference | [0.8,0.1,0.1,0.0] | A1,A10,A2,A3,A5,A6,A7,A8 | 63.00 | 7.80 | 0.3864 | 0.60 | 3.04 | 0.9171 |
| low_commute | [0.4,0.4,0.2,0.0] | A1,A10,A2,A3,A5,A7,A8,A9 | 62.20 | 7.20 | 1.2904 | 0.60 | 3.46 | 0.7990 |
| balanced | [0.4,0.2,0.4,0.0] | A1,A10,A2,A3,A5,A6,A7,A8 | 63.00 | 7.80 | 0.3864 | 0.60 | 3.04 | 0.8783 |
| robust | [0.4,0.2,0.2,0.2] | A1,A10,A2,A3,A5,A7,A8,A9 | 62.20 | 7.20 | 1.2904 | 2.10 | 3.46 | 0.7808 |

对应图件：`output/figures/fig_profile_comparison.png`。

### 2.3 recommend 基准五日行程

来源：`baseline_plan.json.baseline_plan.days`。

| day | depart | route | arr | visit_st | lv | lunch | back | T_scenic / max | buffer | drive |
|---:|---:|---|---|---|---|---|---:|---:|---:|---:|
| 1 | 11.5 | A2 | 12.30 | 12.30 | 17.30 | 17.30-18.30 | 19.10 | 7.60 / 9.50 | 1.90 | 1.60 |
| 2 | 8.5 | A6 | 9.70 | 9.70 | 13.70 | 13.70-14.70 | 15.90 | 7.40 / 12.50 | 5.10 | 2.40 |
| 3 | 8.5 | A1 -> A5 | 9.00, 13.80 | 9.00, 13.80 | 12.50, 16.80 | 12.50-13.50 | 17.40 | 8.90 / 12.50 | 3.60 | 1.40 |
| 4 | 8.5 | A8 -> A10 | 9.20, 13.50 | 9.20, 13.50 | 12.20, 16.50 | 12.20-13.20 | 17.00 | 8.50 / 12.50 | 4.00 | 1.50 |
| 5 | 8.5 | A3 -> A7 | 8.80, 13.00 | 8.80, 13.00 | 11.80, 15.50 | 11.80-12.80 | 15.90 | 7.40 / 8.00 | 0.60 | 0.90 |

基准方案汇总：`selected=[A1,A10,A2,A3,A5,A6,A7,A8]`，`Z1=63.00`，`Z2=7.80`，`Z3=0.3864`，`Z4=0.6000`，`Z4_mean=3.0400`，`F=0.8770`。来源：`baseline_plan.json.baseline_plan`。

## 3. 问题三：随机扰动可靠性评估

### 3.1 主结果

来源：`reliability_report.json.main_result`。

| 指标 | 数值 |
|---|---:|
| R | 0.0005 |
| P_fail | 0.9995 |
| CI_95 半宽 | 0.0004 |
| Day1 P_fail | 0.3749 |
| Day2 P_fail | 0.2201 |
| Day3 P_fail | 0.9324 |
| Day4 P_fail | 0.4890 |
| Day5 P_fail | 0.9758 |
| phi_road | 0.5116 |
| phi_queue | 0.4884 |
| P0 | 0.0000 |
| PR | 0.9722 |
| PQ | 0.9490 |
| PF | 0.9997 |

薄弱点：`theta_per_day=0.0209`，`target_R_met=false`，薄弱日为 `1,2,3,4,5`，前三个薄弱景点为 `A3(0.9763), A7(0.9763), A1(0.9329)`。来源：`reliability_report.json.weak_points`。

对应图件：`output/figures/fig_daily_fail.png`、`output/figures/fig_contribution.png`。

### 3.2 recommend / balanced / robust 三方案对比

来源：`reliability_report.json.compared_plans.<plan>`。

| plan | selected | Z1 | Z2 | Z3 | Z4 | Z4_mean | F | R | P_fail | CI_95 | phi_road | phi_queue |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| recommend | A1,A10,A2,A3,A5,A6,A7,A8 | 63.00 | 7.80 | 0.3864 | 0.60 | 3.04 | 0.8770 | 0.0005 | 0.9995 | 0.0004 | 0.5116 | 0.4884 |
| balanced | A1,A10,A2,A3,A5,A6,A7,A8 | 63.00 | 7.80 | 0.3864 | 0.60 | 3.04 | 0.8783 | 0.0005 | 0.9995 | 0.0004 | 0.5116 | 0.4884 |
| robust | A1,A10,A2,A3,A5,A7,A8,A9 | 62.20 | 7.20 | 1.2904 | 2.10 | 3.46 | 0.7808 | 0.0011 | 0.9989 | 0.0006 | 0.5334 | 0.4666 |

结论：`plans_meeting_target=[]`，无方案达到 `R>=0.9`；默认扰动下 R 最高方案为 `robust`，`best_R=0.0011`。来源：`reliability_report.json.robust_diagnosis`。

对应图件：`output/figures/fig_robustness_comparison.png`。

### 3.3 敏感性分析 4x4 网格

来源：`reliability_report.json.sensitivity_grid`。每格 `N=10000`，来源：`reliability_report.json.assumptions.sensitivity_N_simulations`。

| p_pk | p_off | R | P_fail | phi_road | phi_queue |
|---:|---:|---:|---:|---:|---:|
| 0.4 | 0.1 | 0.0058 | 0.9942 | 0.446 | 0.554 |
| 0.4 | 0.2 | 0.0039 | 0.9961 | 0.447 | 0.553 |
| 0.4 | 0.3 | 0.0019 | 0.9981 | 0.460 | 0.540 |
| 0.4 | 0.4 | 0.0020 | 0.9980 | 0.466 | 0.534 |
| 0.5 | 0.1 | 0.0013 | 0.9987 | 0.477 | 0.523 |
| 0.5 | 0.2 | 0.0012 | 0.9988 | 0.488 | 0.512 |
| 0.5 | 0.3 | 0.0007 | 0.9993 | 0.490 | 0.510 |
| 0.5 | 0.4 | 0.0007 | 0.9993 | 0.491 | 0.509 |
| 0.6 | 0.1 | 0.0009 | 0.9991 | 0.504 | 0.496 |
| 0.6 | 0.2 | 0.0005 | 0.9995 | 0.504 | 0.496 |
| 0.6 | 0.3 | 0.0005 | 0.9995 | 0.505 | 0.495 |
| 0.6 | 0.4 | 0.0001 | 0.9999 | 0.511 | 0.489 |
| 0.7 | 0.1 | 0.0001 | 0.9999 | 0.514 | 0.486 |
| 0.7 | 0.2 | 0.0001 | 0.9999 | 0.514 | 0.486 |
| 0.7 | 0.3 | 0.0002 | 0.9998 | 0.516 | 0.484 |
| 0.7 | 0.4 | 0.0001 | 0.9999 | 0.516 | 0.484 |

敏感性结论：在 16 组扫描中，最高可靠度出现在 `p_pk=0.4, p_off=0.1`，但仍仅为 `R=0.0058`；默认参数 `p_pk=0.6, p_off=0.3` 下为 `R=0.0005`。随着高峰堵车概率上升，`phi_road` 大体从约 `0.446` 上升到约 `0.516`，说明强拥堵情形下道路扰动贡献增加；但排队贡献始终接近一半，二者共同造成全程失败概率接近 1。对应图件：`output/figures/fig_sensitivity_heatmap.png`。

## 4. 问题三补充诊断实验

来源：`output/diagnostics/diagnostic_report.json`。

### 4.1 四场景诊断结果

| plan | scenario | R | P_fail | dominant_failure_reason |
|---|---|---:|---:|---|
| recommend | deterministic | 1.0000 | 0.0000 | none |
| recommend | road_only | 0.0277 | 0.9723 | back_late |
| recommend | queue_only | 0.0501 | 0.9499 | back_late |
| recommend | road_and_queue | 0.0005 | 0.9995 | insufficient_visit_time |
| robust | deterministic | 1.0000 | 0.0000 | none |
| robust | road_only | 0.1201 | 0.8799 | back_late |
| robust | queue_only | 0.1843 | 0.8157 | back_late |
| robust | road_and_queue | 0.0011 | 0.9989 | back_late |

### 4.2 综合扰动下逐日成功率

来源：`output/diagnostics/diagnostic_report.json.plans.<plan>.scenarios.road_and_queue.per_day_success`。

| plan | day | success_rate | failure_rate | main_failure_reason |
|---|---:|---:|---:|---|
| recommend | 1 | 0.6251 | 0.3749 | insufficient_visit_time |
| recommend | 2 | 0.7799 | 0.2201 | back_late |
| recommend | 3 | 0.0676 | 0.9324 | insufficient_visit_time |
| recommend | 4 | 0.5110 | 0.4890 | insufficient_visit_time |
| recommend | 5 | 0.0242 | 0.9758 | back_late |
| robust | 1 | 0.0705 | 0.9295 | back_late_and_insufficient_visit |
| robust | 2 | 0.9107 | 0.0893 | back_late |
| robust | 3 | 0.5038 | 0.4962 | insufficient_visit_time |
| robust | 4 | 0.1268 | 0.8732 | insufficient_visit_time |
| robust | 5 | 0.3151 | 0.6849 | back_late |

### 4.3 可直接写入论文的问题三诊断解释

来源：`output/diagnostics/diagnostic_report.md`。

补充诊断显示，在关闭道路堵车与景点排队的确定性场景下，recommend 与 robust 两个方案均保持可行，说明 v1.1.1 生成的基准行程本身满足 day-specific 时间边界和最低游览时长约束。当仅开启道路堵车或仅开启排队扰动时，行程可靠度已显著下降，主要失败原因集中在返程超出当日最迟回酒店时刻以及受闭园截断导致的实际游览时长不足；当道路堵车与排队同时开启时，两类扰动叠加，使五日行程中至少一日失败的概率进一步增大。在默认强扰动参数 `p_peak=0.6`、`p_off=0.3`、`N=10000` 下，recommend 方案的综合扰动可靠度为 `R=0.0005`，`P_fail=0.9995`；robust 方案为 `R=0.0011`，`P_fail=0.9989`。robust 方案提高了确定性时间缓冲 `Z4`，但由于整次五日行程采用“任一日失败即全程失败”的判定，在五一强扰动假设下仍难以达到 `R>=0.9`。因而，该结果应解释为节假日交通与排队不确定性下的结构性脆弱点识别，而不是确定性行程安排违反约束。

## 5. 图表文件清单

| 图 | 用途 |
|---|---|
| `output/figures/fig_priority_ranking.png` | 问题一优先级排序 |
| `output/figures/fig_profile_comparison.png` | 问题二五套偏好 top-1 对比 |
| `output/figures/fig_daily_fail.png` | 问题三逐日失败概率 |
| `output/figures/fig_contribution.png` | Shapley 道路/排队贡献度 |
| `output/figures/fig_sensitivity_heatmap.png` | 敏感性扫描热力图 |
| `output/figures/fig_robustness_comparison.png` | recommend / balanced / robust 稳健性对比 |

## 6. 论文填数时的关键结论句

1. 问题一中综合优先级前四为 `A3, A7, A2, A1`，均归入高优先级池。来源：`output/tables/p3_priority_ranking.csv`、`output/tables/p5_priority_pool.csv`。
2. v1.1.1 行程枚举得到 `1,066,932` 个可行解。来源：`baseline_plan.json.n_feasible_plans`。
3. recommend 基准方案选择 `A1,A10,A2,A3,A5,A6,A7,A8`，目标值为 `Z1=63.00, Z2=7.80, Z3=0.3864, Z4=0.6000, F=0.8770`。来源：`baseline_plan.json.baseline_plan`。
4. robust 方案牺牲部分偏好得分，将最小缓冲 `Z4` 从 `0.60` 提高到 `2.10`。来源：`baseline_plan.json.profiles.robust.top[0]`。
5. 默认扰动下 recommend / balanced / robust 的可靠度分别为 `0.0005 / 0.0005 / 0.0011`，均未达到 `R>=0.9`。来源：`reliability_report.json.compared_plans` 与 `reliability_report.json.robust_diagnosis`。
6. Shapley 分解显示主基准方案中道路堵车贡献 `phi_road=0.5116`，排队贡献 `phi_queue=0.4884`，二者贡献接近。来源：`reliability_report.json.main_result`。
7. 诊断实验中确定性场景两套方案均 `R=1.0000`，说明低可靠度来自随机扰动与五日串联系统的放大效应，而非确定性排程不可行。来源：`output/diagnostics/diagnostic_report.json`。
