# target90 合法性审计报告

本审计只检查 `target90_experiment.py` 与既有 `target90_report.json`，不修改主模型、不覆盖主结果。

## 1. 核心审计结论

- target90 是否修改堵车概率：否
- 是否修改排队分布：否
- 是否修改失败标准：否
- 是否修改五天联合可靠度定义：否
- 是否漏算午餐：否
- 是否漏算返程堵车：否
- 是否可作为论文第 6 套可靠性优先方案：可以

## 2. 逐项检查

| 检查项 | 结果 |
|---|---|
| p_peak_unchanged | True |
| p_off_unchanged | True |
| road_distribution_matches_solve_p3 | True |
| road_delay_is_additive | True |
| return_leg_jam_included | True |
| queue_distribution_matches_solve_p3 | True |
| queue_sampled_on_each_entry | True |
| no_extra_no_queue_probability_detected | True |
| trip_reliability_is_joint_five_day_success | True |
| failure_rule_unchanged | True |
| day_specific_boundaries_unchanged | True |
| selected_departures_legal | True |
| lunch_counted_for_single_spot_days | True |

## 3. N=10000, seed=2026 复核结果

- R = 0.9458
- P_fail = 0.0542
- CI_95 半宽 = 0.0044
- 逐日失败率 = [0.0086, 0.0006, 0.0009, 0.0004, 0.0442]
- 主要失败原因 = ['back_late', 'back_late', 'back_late', 'back_late', 'back_late']

## 4. 五天确定性时间轴

| day | spot | depart | arr | visit_st | actual_visit | lunch | back | back_max | buffer |
|---:|---|---:|---:|---:|---:|---|---:|---:|---:|
| 1 | A3 | 13.0 | 13.30 | 13.30 | 1.00 | 14.30-15.30 | 15.60 | 21.0 | 5.40 |
| 2 | A1 | 9.0 | 9.50 | 9.50 | 2.00 | 11.50-12.50 | 13.00 | 21.0 | 8.00 |
| 3 | A5 | 9.0 | 9.60 | 9.60 | 2.00 | 11.60-12.60 | 13.20 | 21.0 | 7.80 |
| 4 | A10 | 9.0 | 9.50 | 9.50 | 2.00 | 11.50-12.50 | 13.00 | 21.0 | 8.00 |
| 5 | A7 | 9.0 | 9.40 | 9.40 | 1.50 | 10.90-11.90 | 12.30 | 16.5 | 4.20 |

## 5. 审计解释

审计显示，target90 使用 `solve_p3.py` 中的堵车与排队采样函数，堵车概率仍为 `p_peak=0.6, p_off=0.3`，道路扰动以额外延时方式加入去程与返程，排队在每次入园后按 `visit_st` 抽样。五天可靠度仍按“任一日失败则全程失败”的联合成功概率计算，失败事件仍为 `back > back_max[k]` 或 `actual_visit_time < l_min`。单景点日仍计入 1h 午餐。因此，target90 的 R=0.9458 来自合法的可靠性优先重设计，而不是修改概率、分布、失败标准或边界。

## 6. 发现的问题

未发现违反用户约束的不一致项。