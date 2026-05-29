# v2.9 补充情景复核摘要

本实验仅作为补充情景复核，不替代已经冻结的 recommend / balanced / robust / target90 主结论。

- Monte Carlo 次数：N=10000
- 随机种子：2026
- 排队分布、道路延时分布、失败事件、Day1/Day5 边界、五天联合可靠度定义保持原问题三口径。
- target90 保留 `target90_best_plan.json` 中的单景点日程和发车时刻，仅改变拥堵概率情景。

| 情景 | p_peak | p_off | recommend R | balanced R | robust R | target90 R |
|---|---:|---:|---:|---:|---:|---:|
| low | 0.30 | 0.10 | 0.0092 | 0.0092 | 0.0254 | 0.9814 |
| mid | 0.45 | 0.20 | 0.0022 | 0.0022 | 0.0081 | 0.9665 |
| strong | 0.60 | 0.30 | 0.0005 | 0.0005 | 0.0011 | 0.9458 |

strong 情景下 target90 是否仍达到 90%：True

输出文件：
- `scenario_reliability_report.json`
- `scenario_reliability_table.csv`
- `fig_scenario_reliability.png`
