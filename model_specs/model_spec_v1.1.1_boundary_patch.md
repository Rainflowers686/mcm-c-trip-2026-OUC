# model_spec_v1.1.1_boundary_patch.md

> 中国海洋大学数学建模校赛 C 题 —— 边界与冗余项最小修订补丁
> 版本：v1.1.1（仅对 v1.0 + v1.1 的最小外科修订；不重写全文）
> 适用范围：solve_p2.py、solve_p3.py、main.py、baseline_plan.json、reliability_report.json、论文叙述
> 不动项：决策变量、目标函数、归一化方法、Shapley、敏感性网格、五套偏好权重数值

---

## 0. 修订范围概览

本补丁仅修订 4 处，按红队审稿意见对症处理：

| 修订点 | 来源 | 性质 |
|---|---|---|
| §1 day-specific 边界（day1 / day5 半日处理） | 红队 S1 | 必改（消除自相矛盾） |
| §2 早到景区不判失败（visit_start） | 红队 S3 | 必改（消除约束过严） |
| §3 失败事件冗余项 | 红队 S4 | 必改（消除表达硬伤） |
| §4 robust 的论文叙述 | 红队 M3 | 论文叙述层修订（无代码改动） |

**显式不修订**：C1–C4 子指标定义（红队 S2 已在 solve_p1.py 中实现，本补丁仅要求 model_spec 与代码保持一致，详见 §6）。

---

## 1. Day-Specific 边界修订（红队 S1）

### 1.1 问题诊断

v1.0 假设每天 8:30–21:00 完整景区活动窗，与赛题"家到酒店 4.0 h + 不安排夜间长途行车 + 5 月 1–5 日 5 天"自相矛盾：
- 5 月 1 日：家 7:00 出发，11:00 抵达酒店，0.5 h 入住后最早 11:30 才能开始景区活动；
- 5 月 5 日：若坚持 21:00 返酒店，再加 0.5 h 退房 + 4.0 h 返家 = 凌晨 1:30 到家，违反"不安排夜间长途行车"。

### 1.2 修订定义

引入 day-specific 的出发时刻、最迟返程时刻与景区耗时上限：

| 天 $k$ | $\tau^{\text{dep}}_k$（h） | $\tau^{\text{back,max}}_k$（h） | $T^{\text{scenic,max}}_k$（h） |
|---|---|---|---|
| 1 | **11.5**（11:30） | 21.0 | 9.5 |
| 2 | 8.5（8:30） | 21.0 | 12.5 |
| 3 | 8.5 | 21.0 | 12.5 |
| 4 | 8.5 | 21.0 | 12.5 |
| 5 | 8.5 | **16.5**（16:30） | 8.0 |

满足关系 $T^{\text{scenic,max}}_k = \tau^{\text{back,max}}_k - \tau^{\text{dep}}_k$。

**Day 1 推导**：家 7:00 出发 + 4.0 h 车程 = 11:00 到酒店 + 0.5 h 入住 = 11:30 开始景区活动。
**Day 5 推导**：要求"不安排夜间长途行车"，假定 21:00 前到家。从酒店到家 4.0 h，含 0.5 h 退房，则 16:30 + 0.5 + 4.0 = 21:00，即最迟 16:30 必须回到酒店。

### 1.3 修订约束

原 v1.0 §3.2 约束 (C7)（$T_k^{\text{all}} \le 14$）与 (C9)（$\tau_k^{\text{back}} \le 21$）替换为：

$$\boxed{\;\tau_k^{\text{back}} \le \tau_k^{\text{back,max}},\quad \forall k=1,\dots,5\;} \quad \text{(C7')}$$

等价于：

$$T_k^{\text{scenic}} \le T_k^{\text{scenic,max}}, \quad \forall k$$

原 (C9) 删除（与 C7' 合并）。

### 1.4 时间轴起点

§3.3 时间轴中所有的 "8.5" 替换为 "$\tau^{\text{dep}}_k$"：

- 双景点日：$\tau_{k,i}^{\text{arr}} = \tau^{\text{dep}}_k + D_{0,i}$（不再固定 8.5）
- 单景点日：同上

午餐插入规则、各景点离开时刻、返程时刻递推公式保持不变。

### 1.5 v1.1 Z_4 同步修订

由于不同天的活动窗上限不同，$Z_4$ 定义改为：

$$B_k = T^{\text{scenic,max}}_k - T_k^{\text{scenic}}, \qquad Z_4 = \min_{k=1,\dots,5} B_k$$

注意 $B_k$ 现在使用 day-specific 上限。归一化方式不变。

### 1.6 论文模型假设补充条目

假设 16（新增）：5 日行程的边界处理

> 根据赛题"家到酒店基准车程 4.0 h"与"不安排夜间长途行车"约束，本文采用 day-specific 边界：
> - 5 月 1 日（day 1）：家 7:00 出发，4.0 h 车程到酒店，0.5 h 入住后于 11:30 开始景区活动；
> - 5 月 2–4 日（day 2–4）：8:30 从酒店出发；
> - 5 月 5 日（day 5）：最迟 16:30 回到酒店，预留 0.5 h 退房与 4.0 h 返家，于当日 21:00 前到家。
> 由此 day 1 与 day 5 为"半日景区活动"，景区耗时上限分别为 9.5 h 与 8.0 h；day 2–4 为完整景区活动日，上限为 12.5 h。

---

## 2. 早到景区的可行性修订（红队 S3）

### 2.1 修订定义

引入"实际游览开始时刻" $\tau_{k,i}^{\text{visit\_st}}$，允许早到等候：

$$\tau_{k,i}^{\text{visit\_st}} = \max\!\big(\tau_{k,i}^{\text{arr}},\; o_i^{\text{op}}\big)$$

后续离开时刻按 $\tau_{k,i}^{\text{visit\_st}}$ 计算：

$$\tau_{k,i}^{\text{lv}} = \tau_{k,i}^{\text{visit\_st}} + t_i$$

### 2.2 修订开放时间约束 (C8)

原 v1.0 (C8)：$o_i^{\text{op}} \le \tau_{k,i}^{\text{arr}} \le \tau_{k,i}^{\text{lv}} \le o_i^{\text{cl}}$

新 (C8')：

$$\boxed{\;\tau_{k,i}^{\text{lv}} \le o_i^{\text{cl}}, \quad \forall (k,i):\,z_{k,i}=1\;}$$

不再约束 $\tau_{k,i}^{\text{arr}} \ge o_i^{\text{op}}$；早到等候为合法状态。

### 2.3 问题三中的对应处理

在 Monte Carlo 时间轴递推（v1.0 §4.5）中，$\tilde t_i$ 截断公式同步修订：

$$\tilde t^{(s)}_{k,i} = \max\!\Big(0,\;\min\!\big(l_i^{\text{comf}},\;o_i^{\text{cl}} - \tau_{k,i}^{\text{visit\_st},(s)} - Q^{(s)}_{k,i}\big)\Big)$$

其中

$$\tau_{k,i}^{\text{visit\_st},(s)} = \max\!\big(\tau_{k,i}^{\text{arr},(s)},\; o_i^{\text{op}}\big)$$

排队从 $\tau_{k,i}^{\text{visit\_st}}$ 之后开始（早到的等候时间不计入排队，仅占用日内时间轴）。

---

## 3. 失败事件冗余项修订（红队 S4）

### 3.1 修订定义

原 v1.0 §4.6（含三项 OR）：

$$F_k^{(s)} = \mathbb{1}\big\{T_k^{\text{scenic},(s)} > 12.5 \;\vee\; \tau_k^{\text{back},(s)} > 21 \;\vee\; \exists i:\,\tilde t_i < l_i^{\min}\big\}$$

由于 $T_k^{\text{scenic}} = \tau_k^{\text{back}} - \tau_k^{\text{dep}}$，前两项在固定 $\tau_k^{\text{dep}}$ 下数学等价，存在冗余。

新失败事件统一为两项 OR，同时与 §1 的 day-specific 上限对齐：

$$\boxed{\;F_k^{(s)} = \mathbb{1}\!\Big\{\tau_k^{\text{back},(s)} > \tau_k^{\text{back,max}} \;\vee\; \exists i \in \text{visit}_k:\,\tilde t^{(s)}_{k,i} < l_i^{\min}\Big\}\;}$$

整次行程失败保持不变：

$$F^{(s)} = \mathbb{1}\!\Big\{\sum_{k=1}^{5} F_k^{(s)} \ge 1\Big\}$$

### 3.2 等价表述

亦可写成：

$$F_k^{(s)} = \mathbb{1}\!\Big\{T_k^{\text{scenic},(s)} > T_k^{\text{scenic,max}} \;\vee\; \exists i:\,\tilde t^{(s)}_{k,i} < l_i^{\min}\Big\}$$

两种写法等价；论文与代码任选其一，但**全文必须一致**。

---

## 4. robust 偏好的论文叙述修订（红队 M3）

### 4.1 修订原则

robust 方案在论文中**不得**以"v1.1 新增 / 补丁 / 事后扩展"叙述。论文应将 5 套偏好作为**并列的同级方案**陈述，避免"为应对评估失败临时加挡板"的痕迹。

### 4.2 论文叙述模板修订

| 原叙述 | 修订后叙述 |
|---|---|
| "v1.0 四套偏好" + "v1.1 新增 robust" | **"本文设计 5 套偏好方案以反映不同出游偏好"** |
| "v1.1 引入 $Z_4$ 时间缓冲指标" | "为更全面刻画行程对随机扰动的承受能力，本文设计第 4 个目标 $Z_4$（时间缓冲）作为'逐日宽裕'的度量；与 $Z_3$（天间齐平）共同构成'行程均衡性'的两层含义" |
| "为回应 $R \ge 90\%$ 目标" | "**在 $R \ge 90\%$ 的假设性达标要求下识别薄弱点**" |

### 4.3 "均衡"概念的两层区分（红队 M2）

论文 §5.4 应明确：

> "行程松紧均衡性"在本文中分为两层度量：
> - $Z_3$（**天间齐平**）：5 天总耗时的方差，刻画天与天之间的忙闲差异；
> - $Z_4$（**逐日宽裕**）：5 天中最忙一日距离活动窗上限的余量，刻画"最弱一日"对扰动的承受能力。
> 二者数学上不冗余：方案 $T_k = (12,12,12,12,12)$ 的 $Z_3 = 0$（最齐平）但 $Z_4 = 0.5$（最紧绷）。

### 4.4 5 套偏好统一表（论文 §5.6）

| 方案代号 | 偏好类型 | $(\lambda_1, \lambda_2, \lambda_3, \lambda_4)$ | 角色定位 |
|---|---|---|---|
| `recommend` | 综合推荐型 | $(0.6, 0.2, 0.2, 0.0)$ | **问题二主基准** |
| `preference` | 喜好优先型 | $(0.8, 0.1, 0.1, 0.0)$ | 备选 |
| `low_commute` | 低通勤型 | $(0.4, 0.4, 0.2, 0.0)$ | 备选 |
| `balanced` | 均衡稳健型 | $(0.4, 0.2, 0.4, 0.0)$ | 备选 |
| `robust` | 稳健优先型 | $(0.4, 0.2, 0.2, 0.2)$ | **问题三稳健对比** |

**问题二输出**：5 套方案 top-1 完整结果；主基准 = `recommend` top-1。
**问题三输出**：对 `recommend`、`balanced`、`robust` 三套方案做 Monte Carlo 对比。

### 4.5 摘要叙述修订

摘要中原"四 / 五套"统一为：

> "本文设计 5 套偏好备选方案（综合推荐型、喜好优先型、低通勤型、均衡稳健型、稳健优先型），分别对应不同的家庭出游偏好。"

---

## 5. 给 Codex 的最小修改清单

### 5.1 `solve_p2.py` 修改清单

**[P2-1]** 顶部常量替换为 day-specific 数组：

```python
# 删除：
#   TAU_DEP = 8.5
#   DAY_WIN_END = 21.0
#   T_SCENIC_MAX = 14.0 - MORNING  # = 12.5

# 改为：
TAU_DEP_K       = [11.5, 8.5, 8.5, 8.5, 8.5]   # 每天出发时刻
TAU_BACK_MAX_K  = [21.0, 21.0, 21.0, 21.0, 16.5]  # 每天最迟返程
T_SCENIC_MAX_K  = [tb - td for tb, td in zip(TAU_BACK_MAX_K, TAU_DEP_K)]
# 结果应为 [9.5, 12.5, 12.5, 12.5, 8.0]
```

**[P2-2]** `build_day(spots, k, ...)` 函数签名增加参数 `k`（0-indexed 天数）：

```python
def build_day(spots, k, l_comf, o_op, o_cl, D):
    tau_dep = TAU_DEP_K[k]
    tau_back_max = TAU_BACK_MAX_K[k]
    t_scenic_max = T_SCENIC_MAX_K[k]
    # ...
```

**[P2-3]** `build_day` 内部时间轴：所有 `arr_i = TAU_DEP + D[...]` 改为：

```python
arr_i = tau_dep + D[0, i+1]
visit_st_i = max(arr_i, o_op[i])     # 新增：早到等候
lv_i = visit_st_i + l_comf[i]         # 改：用 visit_st_i

# 午餐
lun_s = lv_i
lun_e = lun_s + LUNCH

# 双景点日的第二个景点：
arr_j = lun_e + D[i+1, j+1]
visit_st_j = max(arr_j, o_op[j])     # 新增
lv_j = visit_st_j + l_comf[j]         # 改

back = lv_j + D[j+1, 0]
```

**[P2-4]** `build_day` 可行性判断：

```python
# 旧：feas = (arr_i >= o_op[i]) and (lv_i <= o_cl[i]) and (back <= DAY_WIN_END)
# 新（删除早到判定，启用 day-specific 上限）：
feas = (lv_i <= o_cl[i] + EPS) and (back <= tau_back_max + EPS)
# 双景点日还要加 (lv_j <= o_cl[j] + EPS)
feas = feas and (T_sc <= t_scenic_max + EPS)
```

**[P2-5]** 时间轴 dict 增加字段（写入 baseline_plan.json）：

```python
tl = {
    "seq": [...],
    "arr": [arr_i, ...],
    "visit_st": [visit_st_i, ...],   # 新增字段
    "lv": [lv_i, ...],
    "lunch": [lun_s, lun_e],
    "back": back,
}
```

**[P2-6]** `assign_to_days` 与 `enumerate_all` 在调用 `build_day` 时**传入对应天数 k**。注意：因为 day-specific 上限不同，**单日方案不能跨天复用**，要为每个 $k\in\{0,1,2,3,4\}$ 分别枚举单日方案池。

**[P2-7]** `Z4` 计算改为 day-specific：

```python
# 旧：cand["Z4"] = float(min(12.5 - t for t in Tks))
# 新：
cand["Z4"] = float(min(T_SCENIC_MAX_K[k] - Tks[k] for k in range(5)))
cand["Z4_mean"] = float(sum(T_SCENIC_MAX_K[k] - Tks[k] for k in range(5)) / 5)
```

**[P2-8]** `export_plan` 中每个 day dict 增加 `depart` 字段使用 `TAU_DEP_K[k]`：

```python
{
    "day": k + 1,
    "depart": TAU_DEP_K[k],          # 用 day-specific
    "T_scenic_max": T_SCENIC_MAX_K[k],  # 新增：当日上限
    "back_max": TAU_BACK_MAX_K[k],   # 新增：当日最迟返程
    "T_scenic": ...,
    # T_all 字段：保留与否由你们决定；若保留，仍为 T_scenic + 1.5
    "buffer": T_SCENIC_MAX_K[k] - T_sc,  # 新增：当日缓冲 B_k
    # ...
}
```

**[P2-9]** PREF_PROFILES 不变（5 套权重数值保持）。

---

### 5.2 `solve_p3.py` 修改清单

**[P3-1]** 顶部常量同步：删除单值 `TAU_DEP / T_SCENIC_MAX / DAY_WIN_END`；从 `solve_p2` 导入 day-specific 数组，或独立定义：

```python
TAU_DEP_K       = [11.5, 8.5, 8.5, 8.5, 8.5]
TAU_BACK_MAX_K  = [21.0, 21.0, 21.0, 21.0, 16.5]
T_SCENIC_MAX_K  = [9.5, 12.5, 12.5, 12.5, 8.0]
```

**[P3-2]** `simulate_day(day, ...)` 函数：

```python
def simulate_day(day, road_on, queue_on, p_pk, p_off, ..., rng):
    k = day["day"] - 1   # 0-indexed
    tau = TAU_DEP_K[k]   # 使用 day-specific 出发时刻
    tau_back_max = TAU_BACK_MAX_K[k]
    t_scenic_max = T_SCENIC_MAX_K[k]
    # ...
```

**[P3-3]** 受扰动时间轴：所有 `tau += D[...] + w` 后增加 visit_start：

```python
w = sample_road(tau, p_pk, p_off, road_on, rng)
tau += D[prev, sp+1] + w
arr = tau
visit_st = max(arr, o_op[sp])     # 新增：早到等候
tau = visit_st                     # 排队从 visit_st 开始
q = sample_queue(visit_st, queue_on, rng)   # 排队抽样基于 visit_st
tau += q
# 闭园截断改为基于 visit_st：
t_real = max(0.0, min(l_comf[sp], o_cl[sp] - tau))
tau += t_real
# ...
```

**注意**：`sample_queue` 的"排队是否高峰"判定，应基于 **visit_st**（实际入园开始时刻），而非 arr（到达停车场时刻）。这是与 §2.3 一致的。

**[P3-4]** 失败判定改为 day-specific（实施 §3 修订）：

```python
# 旧：
# fail = (T_sc > 12.5 + 1e-6) or (back > 21.0 + 1e-6)

# 新（统一两项 OR）：
fail = (back > tau_back_max + 1e-6)
for idx, sp in enumerate(seq):
    if t_acts[idx] < l_min[sp] - 1e-6:
        fail = True
```

**[P3-5]** `sample_road` 中"出发时刻 t 判峰段"逻辑不变；但要注意 day 1 的 11:30 出发已经在峰段定义 [11, 13) 内，会增大堵车采样概率，这是符合实际的，**不要"修正"**。

**[P3-6]** `monte_carlo` 主循环不变；`shapley` 不变；`sensitivity_scan` 不变。

**[P3-7]** `weak_points` 中 $\theta_k = 1 - 0.9^{1/5} \approx 0.0209$ 不变；但论文叙述中应注明 day 1 与 day 5 因活动窗较窄，$P_{\text{fail},k}$ 可能本就更高。

---

### 5.3 `main.py` 校验项修改清单

**[M-1]** `check_baseline_plan` 中：

```python
# 旧：
#   if d["T_all"] > 14.0 + 1e-6:
#       errors.append(...)
#   if d["back"] > 21.0 + 1e-6:
#       errors.append(...)

# 新（使用每天的 day-specific 上限）：
TAU_BACK_MAX_K = [21.0, 21.0, 21.0, 21.0, 16.5]
T_SCENIC_MAX_K = [9.5, 12.5, 12.5, 12.5, 8.0]
TAU_DEP_K      = [11.5, 8.5, 8.5, 8.5, 8.5]

for d in days:
    k = d["day"] - 1
    if d["depart"] != TAU_DEP_K[k]:
        errors.append(f"day {d['day']} depart={d['depart']} != {TAU_DEP_K[k]}")
    if d["back"] > TAU_BACK_MAX_K[k] + 1e-6:
        errors.append(f"day {d['day']} back={d['back']:.3f} > {TAU_BACK_MAX_K[k]}")
    if d["T_scenic"] > T_SCENIC_MAX_K[k] + 1e-6:
        errors.append(f"day {d['day']} T_scenic={d['T_scenic']:.3f} > {T_SCENIC_MAX_K[k]}")
```

**[M-2]** 删除"所有 T_all ≤ 14"的旧校验；新增"每天的 T_scenic ≤ T_scenic_max[k]" 校验。

**[M-3]** 开放时间校验**放宽**（早到允许）：

```python
# 旧：
#   if d["arr"][k] < attr["open_hour"] - 1e-6:
#       errors.append(...)

# 新：使用 visit_st 校验（visit_st = max(arr, open_hour) 总满足）
# 仅校验 lv ≤ close_hour
for k_spot, name in enumerate(d["seq"]):
    attr = attr_idx[name]
    if d["lv"][k_spot] > attr["close_hour"] + 1e-6:
        errors.append(f"day {d['day']} {name} lv={d['lv'][k_spot]:.3f} > close={attr['close_hour']}")
    # 注：早到不再判失败；仅记录 visit_st >= open_hour 这一恒成立性质
```

**[M-4]** 校验摘要打印同步修改文案：

```python
print(f"       - 每天 T_scenic ≤ day-specific 上限 ✓")
print(f"       - 每天 back ≤ day-specific 最迟时刻 ✓ ")
print(f"       - day 1 depart=11.5, day 5 back_max=16.5 ✓")
```

---

### 5.4 `baseline_plan.json` 新增/调整字段

**新增顶层字段** `boundary_v111`（标注本补丁已生效）：

```json
{
  "scope": "scenic_area_only",
  "boundary_v111": {
    "tau_dep_per_day":      [11.5, 8.5, 8.5, 8.5, 8.5],
    "tau_back_max_per_day": [21.0, 21.0, 21.0, 21.0, 16.5],
    "T_scenic_max_per_day": [9.5, 12.5, 12.5, 12.5, 8.0],
    "day1_rationale": "家 7:00 出发 + 4.0h 车程 + 0.5h 入住 = 11:30 开始景区活动",
    "day5_rationale": "16:30 回酒店 + 0.5h 退房 + 4.0h 返家 = 21:00 前到家"
  }
}
```

**`constants` 字段调整**：删除旧的 `tau_depart: 8.5`、`day_window_end: 21.0`、`T_scenic_max: 12.5`；保留 `lunch_duration: 1.0`。

**每个 `days[]` 元素新增字段**：

```json
{
  "day": 1,
  "depart": 11.5,
  "T_scenic_max": 9.5,
  "back_max": 21.0,
  "buffer": 4.3,
  "seq": [...],
  "arr": [...],
  "visit_st": [...],
  "lv": [...],
  "lunch": [...],
  "back": 17.2,
  "T_scenic": 5.7,
  "drive": 1.2
}
```

**删除字段**：`T_all`（或保留但不参与校验；建议保留为 `depart + T_scenic` 的诊断量）。

---

### 5.5 `reliability_report.json` 新增/调整字段

**`assumptions` 字段新增**：

```json
{
  "assumptions": {
    "boundary_v111_applied": true,
    "tau_dep_per_day":      [11.5, 8.5, 8.5, 8.5, 8.5],
    "tau_back_max_per_day": [21.0, 21.0, 21.0, 21.0, 16.5],
    "T_scenic_max_per_day": [9.5, 12.5, 12.5, 12.5, 8.0],
    "p_peak_default": 0.6,
    "p_off_default": 0.3,
    "N_simulations": 10000,
    "trip_scope": "scenic_area_only",
    "seed": 2026,
    "early_arrival_handling": "wait_until_open"
  }
}
```

**`main_result` / `compared_plans` 字段不变**（结构兼容）；但数值因边界修订与早到处理会变化，需重新运行。

**`weak_points` 字段说明补充**（不增删字段，仅在论文叙述中提示）：day 1 与 day 5 因活动窗窄，$P_{\text{fail},k}$ 可能本就高于 day 2–4；论文应分开评论"窄窗自然性"与"扰动诱发"两类薄弱点。

---

### 5.6 不允许修改项（强制约束）

Codex **不得**修改以下任何一项：

1. **5 套偏好权重的具体数值** —— 全部保留 v1.0 / v1.1 数值，包括 robust = $(0.4, 0.2, 0.2, 0.2)$；
2. **目标函数 $Z_1, Z_2, Z_3, Z_4$ 的数学定义** —— 仅 $Z_4$ 的 $B_k$ 上限改为 day-specific（这是 §1.5 已写明的同步修订），其余不变；
3. **归一化方法** —— 共享归一化基准、min-max 公式不变；
4. **Shapley 开关法公式** —— $\phi_{\text{road}}, \phi_{\text{queue}}$ 计算不变；
5. **敏感性扫描网格** —— $p^{\text{pk}} \in \{0.4, 0.5, 0.6, 0.7\}$、$p^{\text{off}} \in \{0.1, 0.2, 0.3, 0.4\}$ 共 16 组；
6. **Monte Carlo 参数** —— $N = 10000$，种子 2026；
7. **景区内行程口径（口径 B）** —— 家↔酒店与入退房仍不进入 $Z_1, Z_2, Z_3, Z_4$ 优化目标；
8. **景点参数表 `attractions.csv` 与距离矩阵 `dist.csv`** —— 一行一列都不许动；
9. **PREF_PROFILES 中的方案代号与排序** —— `recommend`、`preference`、`low_commute`、`balanced`、`robust` 五个键名不变；
10. **`baseline_plan.baseline_plan` 仍指向 recommend top-1** —— 主基准定位不变；
11. **`solve_p1.py` 全部内容** —— 问题一代码不动；本补丁仅在论文层要求"$C_1$–$C_4$ 子指标公式以 `solve_p1.py` 实际实现为准"（详见 §6）；
12. **失败事件 OR 关系的本质** —— 仅去除冗余项，"违反时间窗"与"游览时长不达标"两项 OR 保留。

---

## 6. C1–C4 公式与代码一致性提醒（红队 S2 配套）

红队 S2 指出 v1.0 §2.1 未给出 $C_{1i}$–$C_{4i}$ 的显式公式。**本补丁不重新定义 $C_1$–$C_4$**，但明确规定如下流程：

### 6.1 单一真相源

$C_{1i}, C_{2i}, C_{3i}, C_{4i}$ 的具体计算公式，**以 `solve_p1.py` 中已实现的 `compute_four_dim` 函数为准**。该实现已在 v1.0 阶段定稿并通过校验，作为唯一真相源。

### 6.2 论文同步要求

论文 §4.3 必须**完整列出**该函数中的 4 个公式，与代码一字不差；包括但不限于：

- $C_{1i}$ 的具体表达式（基于 $\delta(\tau^{\text{dep}}), \delta(\tau_{\text{lv},i})$）；
- $C_{2i}$ 的具体表达式（基于 $\mu(\tau^{\text{dep}}), \mu(\tau_{\text{lv},i})$）；
- $C_{3i}$ 的具体表达式（基于 $\gamma(\tau_{\text{arr},i})$）；
- $C_{4i}$ 的具体表达式（基于 $l_i^{\min}, O_i$）；
- min-max 归一化的具体公式；
- 加权权重 $(w_1, w_2, w_3, w_4) = (0.3, 0.3, 0.2, 0.2)$。

### 6.3 编程手验证

提交前由参赛队人工核对：论文公式 ↔ `solve_p1.py` 实现 ↔ `output/tables/p2_four_dim_scores.csv` 数值 三者完全一致。

### 6.4 问题一的 $\tau^{\text{dep}}$ 处理

问题一 §2.4.1 中"统一出发时刻 $\tau^{\text{dep}} = 8.5$"**保留不变**，作为问题一专有的评分基准。问题一不使用 day-specific 出发时刻，理由：问题一是景点层的"先验"打分，不涉及具体天数安排；day-specific 边界仅适用于问题二与问题三的行程层。论文 §4.3 末尾应加一句脚注说明此点，避免与新引入的 §1 day-specific 混淆。

---

## 7. 论文叙述同步修订清单（无代码改动）

以下章节需要按本补丁同步修订论文文字：

| 论文章节 | 修订要点 |
|---|---|
| §1.3（工作概览） | 删除"为回应 R ≥ 90% 目标"等承诺式措辞；改为"在 R ≥ 90% 假设性达标要求下识别薄弱点" |
| §2 模型假设 | 新增假设 16（day-specific 边界）；假设 1 末尾补充"day 1/day 5 为半日活动" |
| §3.2 问题二符号 | 新增 $\tau^{\text{dep}}_k$、$\tau^{\text{back,max}}_k$、$T^{\text{scenic,max}}_k$、$\tau_{k,i}^{\text{visit\_st}}$、$B_k$；删除单值 $\tau^{\text{dep}}$ |
| §4.3 末尾 | 加脚注说明问题一 $\tau^{\text{dep}} = 8.5$ 与问题二 day-specific 的关系 |
| §5.2 约束 | (C7) 改为 day-specific；(C8) 改为放宽形式；(C9) 删除 |
| §5.3 时间轴 | $\tau^{\text{dep}}_k$ 替换 $8.5$；新增 $\tau_{k,i}^{\text{visit\_st}}$ 步骤 |
| §5.4 / §5.7 | 增加 "Z3 vs Z4 两层均衡含义"一段；删除"v1.1 新增"等措辞 |
| §5.6 | 改为"5 套偏好方案"统一表，含 robust 同级 |
| §6.4 受扰动时间轴 | 同 §5.3 修订；增加 visit_st 步骤 |
| §6.5 失败事件 | 删除冗余项；用 $\tau^{\text{back,max}}_k$ |
| §6.8 三方案对比 | 删除"v1.1 补丁"措辞；改为"问题三选取 recommend、balanced、robust 三套方案做稳健性对比" |
| §6.10 R < 90% 解释 | 修订 M4：删除"外部分流：节假日交通管控"；改为"扰动假设减弱（敏感性分析中 p_pk ≤ 0.5）或方案进一步收缩（|S| = 5 且全部单景点日）" |
| §6.11 文字 | "导致失败的贡献率"改为"在失败日中出现的频率"（M7） |
| 摘要 | 删除"四 / 五套"；统一为"5 套备选方案" |

---

## 8. 版本与差异表

| 项 | v1.0 | v1.1 | **v1.1.1（本补丁）** |
|---|---|---|---|
| $\tau^{\text{dep}}$ | 8.5（全天统一） | 8.5（全天统一） | **day-specific** |
| $T^{\text{scenic,max}}$ | 12.5（全天统一） | 12.5（全天统一） | **day-specific [9.5, 12.5, 12.5, 12.5, 8.0]** |
| 早到处理 | 判失败 | 判失败 | **wait until open** |
| 失败事件 OR 项数 | 3 | 3 | **2（删冗余）** |
| Z_4 缓冲基准 | — | 全天 12.5 | **day-specific** |
| robust 叙述 | — | "v1.1 新增" | **5 套之一（并列）** |
| 5 套偏好权重 | 4 套 | 5 套 | **5 套（不变）** |
| 目标函数 | $Z_1, Z_2, Z_3$ | $Z_1, Z_2, Z_3, Z_4$ | **不变** |
| 归一化 | 共享基准 | 共享基准 | **不变** |
| Shapley / 敏感性 | — / 16 格 | 完整 / 16 格 | **不变** |
| `solve_p1.py` | — | — | **不动** |

---

## 9. Codex 任务摘要（可直接复制）

```
任务：基于 model_spec_v1.1.1_boundary_patch.md 修改 solve_p2.py, solve_p3.py, main.py。

强制约束：
1. 不改 solve_p1.py 任何一行；
2. 不改 attractions.csv, dist.csv 任何一行；
3. 5 套偏好权重数值保持不变；
4. 不改目标函数 Z1, Z2, Z3, Z4 的数学定义（仅 Z4 的 B_k 上限按 day-specific）；
5. 不改 Shapley 公式、敏感性网格、N=10000、种子 2026。

必改 4 项：
1. day-specific 边界：
   TAU_DEP_K = [11.5, 8.5, 8.5, 8.5, 8.5]
   TAU_BACK_MAX_K = [21.0, 21.0, 21.0, 21.0, 16.5]
   T_SCENIC_MAX_K = [9.5, 12.5, 12.5, 12.5, 8.0]
2. 早到等候：visit_st = max(arr, open_hour)；游览离开时间用 visit_st 起算；
   只校验 lv <= close_hour；排队抽样基于 visit_st。
3. 失败事件去冗余：
   fail = (back > TAU_BACK_MAX_K[k]) or (any t_real < l_min)
4. baseline_plan.json 顶层增 boundary_v111 字段；
   每个 days[] 增字段：T_scenic_max, back_max, buffer, visit_st。
   reliability_report.json 的 assumptions 增 boundary_v111_applied, *_per_day, early_arrival_handling。

main.py 校验项：
- 删除 T_all <= 14 的统一校验；
- 改为每天 T_scenic <= T_SCENIC_MAX_K[k] 与 back <= TAU_BACK_MAX_K[k]；
- 删除"arr >= open"校验；改为"lv <= close"；
- 校验 depart == TAU_DEP_K[k]。

回归点：
- recommend 偏好的 top-1 在重跑后不一定与 v1.1 相同（因为边界变了，是预期内的）；
- 但 v1.0 的 4 套偏好 top-1 的相对排序模式应仍合理；
- Shapley 公式、CI 公式、敏感性 16 格输出格式应完全一致。

完成标准：
- main.py 全部校验 PASS；
- baseline_plan.json 含 boundary_v111 字段；
- reliability_report.json 含 boundary_v111_applied=true；
- 每天 day 1 depart=11.5、day 5 back<=16.5；
- 早到等候已实现（可通过插一个测试用例验证）。
```

---

**补丁文档结束。**