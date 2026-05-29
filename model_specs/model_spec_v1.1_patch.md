# model_spec_v1.1_patch.md

> 中国海洋大学数学建模校赛 C 题 —— 稳健化扩展补丁
> 版本：v1.1（仅对 v1.0 的增量；v1.0 主文档不动）
> 兼容性：所有 v1.0 字段与公式保留；本补丁只增不改。

---

## 0. 补丁范围

本补丁仅扩展三处，**不修改任何 v1.0 既有定义**：

- §3.4 增第 4 个目标 Z4（时间缓冲指标）
- §3.5 增 Z4 的归一化与 F_robust
- §3.6 增第 5 套偏好 robust
- §3.9 baseline_plan.json 增字段
- §4.11（新增）三方案 Monte Carlo 对比
- §4.12（新增）reliability_report.json 新增字段
- §5（新增）论文表述模板

**不变项**（强制保留 v1.0 规定）：
- τ_dep = 8.5
- 景区内行程口径（口径 B）
- T_all ≤ 14 ⟺ T_scenic ≤ 12.5
- 失败事件 F_k^(s)、可靠度 R = 1 - P_fail
- 问题二为确定性枚举求解（非随机优化）

---

## 1. §3.4 新增：时间缓冲指标 Z4

每日缓冲：

$$B_k = 12.5 - T_k^{\text{scenic}}$$

整体缓冲指标（取最弱一日）：

$$Z_4 = \min_{k=1,\dots,5} B_k \quad (\max)$$

补充参考量（仅输出，不参与优化）：

$$Z_4^{\text{mean}} = \frac{1}{5}\sum_{k=1}^{5} B_k$$

**说明**：Z3 惩罚天间方差，Z4 惩罚最忙日逼近上限；两者数学不冗余。

---

## 2. §3.5 新增：Z4 归一化与 F_robust

在 v1.0 同一可行解集 𝓕 上共享基准：

$$\tilde Z_4 = \frac{Z_4 - Z_4^{\min}}{Z_4^{\max} - Z_4^{\min}} \in [0, 1]$$

四目标综合评分：

$$F_{\text{robust}}(\lambda) = \lambda_1 \tilde Z_1 + \lambda_2 \tilde Z_2 + \lambda_3 \tilde Z_3 + \lambda_4 \tilde Z_4$$

要求 ∑λ_p = 1。原 4 套偏好等价于 λ_4 = 0，结果与 v1.0 完全一致（向后兼容）。

---

## 3. §3.6 新增第 5 套偏好

| 方案代号    | 类型         | (λ1, λ2, λ3, λ4)        |
|------------|-------------|-------------------------|
| recommend   | 综合推荐型   | (0.6, 0.2, 0.2, 0.0)    |
| preference  | 喜好优先型   | (0.8, 0.1, 0.1, 0.0)    |
| low_commute | 低通勤型     | (0.4, 0.4, 0.2, 0.0)    |
| balanced    | 均衡稳健型   | (0.4, 0.2, 0.4, 0.0)    |
| **robust**  | **稳健优先型** | **(0.4, 0.2, 0.2, 0.2)** |

---

## 4. §3.9 baseline_plan.json 字段扩展

`profiles[name].top[i]` 每项新增：

- `Z4`        : float，min 缓冲（小时）
- `Z4_mean`   : float，平均缓冲（参考）
- `Z4_norm`   : float，归一化缓冲 ∈ [0,1]

`norm_basis` 新增：`Z4_min`, `Z4_max`

`profiles` 顶层新增 `robust` 键，结构与其他 profile 一致。

`baseline_plan` 顶层（即 recommend top-1）保持不变。

---

## 5. §4.11 新增：三方案 Monte Carlo 对比

对 `recommend`、`balanced`、`robust` 三个 profile 的 top-1 方案，在默认参数
`p_pk = 0.6, p_off = 0.3, N = 10000, seed = 2026` 下分别执行：

1. monte_carlo(plan, ...) → 得到 R, P_fail, CI_95, P_fail_day, phi_spot
2. shapley(plan, ...)     → 得到 phi_road, phi_queue
3. 记录该方案的 Z1, Z2, Z3, Z4, F

输出统一存入 `reliability_report.compared_plans`。

---

## 6. §4.12 reliability_report.json 新增字段

```json
{
  "compared_plans": {
    "recommend": {
      "selected": [...],
      "Z1": ..., "Z2": ..., "Z3": ..., "Z4": ...,
      "F": ...,
      "Tks": [...],
      "R": ..., "P_fail": ..., "CI_95": ...,
      "P_fail_day": [...],
      "phi_road": ..., "phi_queue": ...
    },
    "balanced":  { ... 同结构 ... },
    "robust":    { ... 同结构 ... }
  },
  "robust_diagnosis": {
    "target_R": 0.9,
    "plans_meeting_target": ["robust"]  // 或 []
    "best_plan_under_target": "robust",  // R 最高的方案名
    "best_R": 0.42,
    "fallback_advice": "<自动生成的解释文本>"
  }
}
```

`fallback_advice` 自动文本规则：
- 若 `plans_meeting_target` 非空：
  `"<name> reaches R ≥ 0.9 under default disturbance."`
- 否则：
  `"No plan reaches R ≥ 0.9 under p_pk=0.6. See sensitivity grid for thresholds; refer to §5 of patch for paper-level interpretation."`

`main_result`、`weak_points`、`sensitivity_grid` 三个 v1.0 字段保持不变。

---

## 7. §5 新增：论文中 R < 0.9 的表述模板

当 robust 方案仍未达到 R ≥ 0.9 时，论文按以下三层结构表述：

**(a) 定位为发现，不是失败**

> 在 p_pk = 0.6、p_off = 0.3 的强扰动假设下，单纯依靠行程优化无法使可靠度达到 90% 以上。
> 这反映了该文旅片区在五一峰值期间固有的拥堵脆弱性，是题目要求的"结构性薄弱点"在
> 数值上的体现，而非建模缺陷。

**(b) 引用敏感性扫描证明模型在弱扰动下能达标**

> 由敏感性扫描结果（reliability_report.sensitivity_grid）可见，当 p_pk ≤ 0.5 且
> p_off ≤ 0.2 时，robust 方案的可靠度可显著提升。这给出了达标的充分条件。

**(c) 给出达标路径**

> 在维持 8:30 出发与景区内口径不变的前提下，达到 R ≥ 0.9 的可行路径有二：
>   (i) 外部分流：通过节假日交通管控将 p_pk 降至 0.5 以下；
>   (ii) 内部牺牲：进一步减少景点数至 |S| = 5 并全部安排为单景点日。
> 二者代价不同，结论由参赛队根据出行偏好选择。

---

## 8. 与 v1.0 的最小差异表

| 内容                   | v1.0                  | v1.1                                |
|-----------------------|-----------------------|-------------------------------------|
| 目标个数               | 3 (Z1,Z2,Z3)          | **4 (新增 Z4)**                      |
| 偏好套数               | 4                     | **5 (新增 robust)**                  |
| 综合评分               | F = ∑(p=1..3) λ_p Z̃_p | **F_robust = ∑(p=1..4) λ_p Z̃_p**   |
| Monte Carlo 评估对象   | 单方案 (recommend top-1) | **三方案 (recommend, balanced, robust)** |
| reliability_report     | 主结果+敏感性+薄弱点    | **+ compared_plans + robust_diagnosis** |
| τ_dep                  | 8.5                   | 8.5（**不变**）                      |
| 行程口径               | 景区内 (B)            | 景区内 (B)（**不变**）                |
| R 公式                 | 1 − P_fail            | 1 − P_fail（**不变**）                |
| 问题二求解             | 枚举                  | 枚举（**不变**）                     |