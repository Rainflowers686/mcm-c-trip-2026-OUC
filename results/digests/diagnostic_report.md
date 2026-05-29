# 问题三诊断报告

本诊断报告仅作为问题三的补充解释，不替代主可靠性报告。
模拟次数 N=10000，随机种子 seed=2026。

## 场景结果

| 方案 | 场景 | R | P_fail | 主要失败原因 |
|---|---:|---:|---:|---|
| recommend | deterministic | 1.0000 | 0.0000 | none |
| recommend | road_only | 0.0277 | 0.9723 | back_late |
| recommend | queue_only | 0.0501 | 0.9499 | back_late |
| recommend | road_and_queue | 0.0005 | 0.9995 | insufficient_visit_time |
| robust | deterministic | 1.0000 | 0.0000 | none |
| robust | road_only | 0.1201 | 0.8799 | back_late |
| robust | queue_only | 0.1843 | 0.8157 | back_late |
| robust | road_and_queue | 0.0011 | 0.9989 | back_late |

## 道路堵车与排队同时开启时的逐日成功率

| 方案 | 天数 | 成功率 | 失败率 | 主要失败原因 |
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

## 可直接写入论文的问题三诊断解释

补充诊断显示，在关闭道路堵车与景点排队的确定性场景下，recommend 与 robust 两个方案均保持可行，说明 v1.1.1 生成的基准行程本身满足 day-specific 时间边界和最低游览时长约束。当仅开启道路堵车或仅开启排队扰动时，行程可靠度已显著下降，主要失败原因集中在返程超出当日最迟回酒店时刻以及受闭园截断导致的实际游览时长不足；当道路堵车与排队同时开启时，两类扰动叠加，使五日行程中至少一日失败的概率进一步增大。在默认强扰动参数 p_peak=0.6、p_off=0.3、N=10000 下，recommend 方案的综合扰动可靠度为 R=0.0005，P_fail=0.9995；robust 方案为 R=0.0011，P_fail=0.9989。robust 方案提高了确定性时间缓冲 Z4，但由于整次五日行程采用“任一日失败即全程失败”的判定，在五一强扰动假设下仍难以达到 R>=0.9。因而，该结果应解释为节假日交通与排队不确定性下的结构性脆弱点识别，而不是确定性行程安排违反约束。
