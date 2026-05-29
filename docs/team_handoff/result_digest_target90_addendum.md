# target90 第 6 套可靠性优先方案论文填数补充

本文件仅汇总既有输出文件中的数值，不重新运行模拟、不重新优化、不覆盖任何已有 JSON 或主结果文件。

## 0. 数据来源

| 内容 | 来源 |
|---|---|
| target90 方案、搜索空间、可靠度与对比 | `output/target90/target90_report.json` |
| target90 Markdown 解释口径 | `output/target90/target90_report.md` |
| target90 合法性审计 | `output/target90/target90_audit.json`、`output/target90/target90_audit.md` |
| 问题二五套主方案 | `baseline_plan.json`、`result_digest_for_paper.md` |
| recommend / balanced / robust 主可靠度 | `reliability_report.json`、`result_digest_for_paper.md` |

## 1. target90 定位与固定条件

`target90` 是独立的第 6 套可靠性优先备用方案，不替代问题二的五套偏好方案。来源：`output/target90/target90_report.json.assumptions.experiment`、`does_not_replace_existing_profiles`。

| 指标 | 数值 | 来源字段 |
|---|---:|---|
| 粗筛模拟次数 | 1000 | `target90_report.json.assumptions.N_coarse` |
| 复核模拟次数 | 10000 | `target90_report.json.assumptions.N_final` |
| 随机种子 | 2026 | `target90_report.json.assumptions.seed` |
| 高峰堵车概率 `p_peak` | 0.6 | `target90_report.json.assumptions.p_peak` |
| 平峰堵车概率 `p_off` | 0.3 | `target90_report.json.assumptions.p_off` |
| Day1 最早出发候选下界 | 11.5 | `target90_report.json.assumptions.day_depart_candidates[0]` |
| Day5 最迟回酒店 | 16.5 | `target90_report.json.assumptions.tau_back_max_per_day[4]` |
| 可靠度定义 | `P(all five days succeed)` | `target90_report.json.assumptions.trip_reliability_definition` |
| 失败规则 | `back > back_max[k] or actual_visit_time < l_min` | `target90_report.json.assumptions.failure_rule` |
| 早到处理 | `visit_st=max(arr, open_hour)` | `target90_report.json.assumptions.early_arrival_handling` |

## 2. 搜索空间与剪枝数字

| 指标 | 数值 | 来源字段 |
|---|---:|---|
| 5 景点组合数 `C(10,5)` | 252 | `target90_report.json.search_space.spot_combinations_10_choose_5` |
| 5 个不同景点到 5 天排列数 | 30240 | `target90_report.json.search_space.spot_to_day_assignments_P_10_5` |
| 每个排列的出发时间组合数 | 34992 | `target90_report.json.search_space.raw_departure_products_per_assignment` |
| 原始候选日程数 | 1058158080 | `target90_report.json.search_space.raw_candidate_schedules` |
| 确定性日选项检查数 | 410 | `target90_report.json.search_space.deterministic_day_options_checked` |
| 确定性可行日选项数 | 367 | `target90_report.json.search_space.deterministic_day_options_feasible` |
| 优势剪枝后 day-spot 选项数 | 50 | `target90_report.json.search_space.dominance_pruned_day_spot_options` |
| 粗筛评估候选数 | 30240 | `target90_report.json.search_space.coarse_candidates_evaluated` |
| 复核保留候选数 | 20 | `target90_report.json.search_space.coarse_top_k_retained` |

剪枝规则来源：`target90_report.json.search_space.pruning_rules`。核心口径为：先排除无扰动确定性不可行的日选项；对同一 `(day, spot)` 保留粗模拟日成功率最高的出发时间；再枚举不同景点到五天的分配。

## 3. target90 最优方案数字

| 指标 | 数值 | 来源字段 |
|---|---:|---|
| 是否找到 `R>=0.9` 方案 | True | `target90_report.json.target_met` |
| 选中景点 | A3,A1,A5,A10,A7 | `target90_report.json.best_plan.selected` |
| 五天出发时间 | 13.0,9.0,9.0,9.0,9.0 | `target90_report.json.best_plan.departures` |
| 最高整体可靠度 `R` | 0.9458 | `target90_report.json.best_plan.R` |
| 失败概率 `P_fail` | 0.0542 | `target90_report.json.best_plan.P_fail` |
| 95% CI 半宽 | 0.0044 | `target90_report.json.best_plan.CI_95` |
| 95% CI 区间 | [0.9414, 0.9502] | 由 `R +/- CI_95` 计算 |
| 复核模拟次数 | 10000 | `target90_report.json.best_plan.N` |
| 复核随机种子 | 2026 | `target90_report.json.best_plan.seed` |
| 粗筛估计 `R` | 0.946329 | `target90_report.json.best_plan.coarse_R` |
| 粗筛估计 `P_fail` | 0.053671 | `target90_report.json.best_plan.coarse_P_fail` |
| 相比 recommend 的 `R` 提升 | 0.9453 | `target90_report.json.improvement_vs_recommend` |
| 相比 robust 的 `R` 提升 | 0.9447 | `target90_report.json.improvement_vs_robust` |

## 4. target90 与 recommend / balanced / robust 对比

| 方案 | R | P_fail | CI_95 半宽 | Z4 或确定性最小 buffer | 来源字段 |
|---|---:|---:|---:|---:|---|
| recommend | 0.0005 | 0.9995 | 0.0004 | 0.6000 | `target90_report.json.comparison_with_existing.recommend` |
| balanced | 0.0005 | 0.9995 | 0.0004 | 0.6000 | `target90_report.json.comparison_with_existing.balanced` |
| robust | 0.0011 | 0.9989 | 0.0006 | 2.1000 | `target90_report.json.comparison_with_existing.robust` |
| target90 | 0.9458 | 0.0542 | 0.0044 | 4.2000 | `target90_report.json.comparison_with_existing.target90`；最小 buffer 来自 `target90_report.json.best_plan.days[].buffer` |

说明：前三个方案的 `Z4` 来自问题二主模型字段；`target90` 不参与问题二五套偏好排序，因此表中 `4.2000` 仅表示其五日确定性行程的最小 buffer，不作为问题二目标函数值替换主结果。

## 5. target90 五天行程表

| day | spot | depart | arr | visit_st | actual_visit | lunch | back | back_max | buffer | drive | 来源字段 |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | A3 | 13.0 | 13.30 | 13.30 | 1.00 | 14.30-15.30 | 15.60 | 21.0 | 5.40 | 0.60 | `target90_report.json.best_plan.days[0]` |
| 2 | A1 | 9.0 | 9.50 | 9.50 | 2.00 | 11.50-12.50 | 13.00 | 21.0 | 8.00 | 1.00 | `target90_report.json.best_plan.days[1]` |
| 3 | A5 | 9.0 | 9.60 | 9.60 | 2.00 | 11.60-12.60 | 13.20 | 21.0 | 7.80 | 1.20 | `target90_report.json.best_plan.days[2]` |
| 4 | A10 | 9.0 | 9.50 | 9.50 | 2.00 | 11.50-12.50 | 13.00 | 21.0 | 8.00 | 1.00 | `target90_report.json.best_plan.days[3]` |
| 5 | A7 | 9.0 | 9.40 | 9.40 | 1.50 | 10.90-11.90 | 12.30 | 16.5 | 4.20 | 0.80 | `target90_report.json.best_plan.days[4]` |

## 6. 逐日可靠度与失败原因

| day | success_rate | fail_rate | 主要失败原因 | back_late 次数 | insufficient_visit_time 次数 | 来源字段 |
|---:|---:|---:|---|---:|---:|---|
| 1 | 0.9914 | 0.0086 | back_late | 86 | 0 | `target90_report.json.best_plan.per_day_success/fail/main_failure_reasons/failure_reason_counts[0]` |
| 2 | 0.9994 | 0.0006 | back_late | 6 | 0 | `target90_report.json.best_plan.per_day_success/fail/main_failure_reasons/failure_reason_counts[1]` |
| 3 | 0.9991 | 0.0009 | back_late | 9 | 0 | `target90_report.json.best_plan.per_day_success/fail/main_failure_reasons/failure_reason_counts[2]` |
| 4 | 0.9996 | 0.0004 | back_late | 4 | 0 | `target90_report.json.best_plan.per_day_success/fail/main_failure_reasons/failure_reason_counts[3]` |
| 5 | 0.9558 | 0.0442 | back_late | 442 | 0 | `target90_report.json.best_plan.per_day_success/fail/main_failure_reasons/failure_reason_counts[4]` |

结论：主要风险集中在 Day5，失败率为 `0.0442`。来源：`target90_report.json.best_plan.per_day_fail[4]`。

## 7. 合法性审计结论

审计文件显示 `issues=[]`，且 `target90_legal_under_current_model=true`。来源：`output/target90/target90_audit.json.issues`、`conclusion.target90_legal_under_current_model`。

| 审计问题 | 结论 | 来源字段 |
|---|---|---|
| 未修改堵车概率 | 通过 | `target90_audit.json.checks.p_peak_unchanged`、`p_off_unchanged` |
| 未修改道路堵车分布 | 通过 | `target90_audit.json.checks.road_distribution_matches_solve_p3` |
| 道路延时仍为加法扰动 | 通过 | `target90_audit.json.checks.road_delay_is_additive` |
| 未漏算返程堵车 | 通过 | `target90_audit.json.checks.return_leg_jam_included` |
| 未修改排队分布 | 通过 | `target90_audit.json.checks.queue_distribution_matches_solve_p3` |
| 每次入园均抽排队时间 | 通过 | `target90_audit.json.checks.queue_sampled_on_each_entry` |
| 未加入额外“不排队概率” | 通过 | `target90_audit.json.checks.no_extra_no_queue_probability_detected` |
| 未修改五天联合可靠度定义 | 通过 | `target90_audit.json.checks.trip_reliability_is_joint_five_day_success` |
| 未修改失败标准 | 通过 | `target90_audit.json.checks.failure_rule_unchanged` |
| 未修改 Day1 / Day5 边界 | 通过 | `target90_audit.json.checks.day_specific_boundaries_unchanged` |
| 出发时间候选合法 | 通过 | `target90_audit.json.checks.selected_departures_legal` |
| 单景点日未漏算午餐 | 通过 | `target90_audit.json.checks.lunch_counted_for_single_spot_days` |

审计复核结果与报告一致：`R=0.9458`，`P_fail=0.0542`，`CI_95=0.0044`。来源：`target90_audit.json.replay.R/P_fail/CI_95`。

## 8. 可直接写入论文的问题三新增段落

为回应“整体可靠度达到 90%以上”的要求，本文在不替代问题二五套偏好方案的基础上，进一步构造第 6 套可靠性优先备用方案 `target90`。该方案不改变高峰与平峰堵车概率、道路额外延时分布、景点排队分布、失败标准、Day1/Day5 边界及五天联合可靠度定义，仅在题目允许的行程设计层面进行重构：将总景点数收缩为 5 个，每天安排 1 个景点，并在合法出发时间候选中选择时间缓冲较大的日程。基于 `N=10000`、`seed=2026` 的 Monte Carlo 复核，`target90` 选择 `A3,A1,A5,A10,A7`，五天出发时间为 `13.0,9.0,9.0,9.0,9.0`，整体可靠度达到 `R=0.9458`，失败概率为 `P_fail=0.0542`，95% 置信区间半宽为 `0.0044`。逐日失败率分别为 `0.0086,0.0006,0.0009,0.0004,0.0442`，主要失败原因均为返程超时，其中 Day5 是主要瓶颈。审计结果表明，该结果未通过降低堵车概率、改变排队分布、放松失败标准或改写五天联合可靠度获得，而是由可靠性优先的行程重设计带来，因此可作为论文问题三中满足 `R>=0.9` 要求的备用方案。

## 9. 论文填数关键句

1. 第 6 套 `target90` 方案选中 `A3,A1,A5,A10,A7`，五天分别安排 1 个景点。来源：`target90_report.json.best_plan.selected`。
2. `target90` 的整体可靠度为 `R=0.9458`，失败概率为 `P_fail=0.0542`，95% CI 半宽为 `0.0044`。来源：`target90_report.json.best_plan.R/P_fail/CI_95`。
3. `target90` 达到 `R>=0.9`，`target_met=True`。来源：`target90_report.json.target_met`。
4. 与 recommend、balanced、robust 的 `R=0.0005/0.0005/0.0011` 相比，`target90` 明显提高整体可靠度。来源：`target90_report.json.comparison_with_existing`。
5. `target90` 相比 recommend 的可靠度提升为 `0.9453`，相比 robust 的可靠度提升为 `0.9447`。来源：`target90_report.json.improvement_vs_recommend`、`improvement_vs_robust`。
6. 审计结论为 `target90_legal_under_current_model=True`，且未发现不一致项。来源：`target90_audit.json.conclusion.target90_legal_under_current_model`、`target90_audit.json.issues`。
