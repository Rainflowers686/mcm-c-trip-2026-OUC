# model_spec_v1.0.md

> 中国海洋大学数学建模校赛 C 题：五一五日自驾景点优选与行程规划
> 编程实现规范（终稿）
> 版本：v1.0 — 适合直接交给 Codex / Python 编程手

---

## 0. 通用约定

| 约定 | 取值 |
|---|---|
| 景点数 | $N_{\text{spot}}=10$（A1–A10） |
| 天数 | $N_{\text{day}}=5$（5 月 1 日–5 月 5 日） |
| 时间表示 | 24h 制小数；如 `13.5` 表示 13:30 |
| 距离矩阵 | $D\in\mathbb{R}^{11\times 11}$，索引 0 = 酒店，1–10 对应 A1–A10；$D_{ii}=0$，$D_{ab}=D_{ba}$ |
| 每日活动窗 | 7:00–21:00（共 14h） |
| 每日出发时刻 | $\tau^{\text{dep}}=8.5$（固定，全模型） |
| 午餐时长 | $\tau^{\text{lunch}}=1.0$ h（固定） |
| 晨间整装 | $\tau^{\text{morn}}=1.5$ h（固定，7:00–8:30 间完成） |
| 模型口径 | 景区内行程口径（见 §1.3） |

---

## 1. 时间窗与口径定义

### 1.1 两种总耗时

**景区内总耗时**（参与优化）：

$$T_k^{\text{scenic}} = \tau_k^{\text{back}} - \tau^{\text{dep}} = \tau_k^{\text{back}} - 8.5$$

**全日总耗时**（用于活动窗约束）：

$$T_k^{\text{all}} = \tau^{\text{morn}} + T_k^{\text{scenic}} = 1.5 + T_k^{\text{scenic}}$$

### 1.2 每日活动窗约束

$$\boxed{\;T_k^{\text{all}} \le 14, \quad \forall k=1,\dots,5\;}$$

等价于：

$$T_k^{\text{scenic}} \le 12.5$$

晨间整装 1.5h 在 7:00–8:30 内完成；返程酒店时刻 $\tau_k^{\text{back}} \le 21.0$。

### 1.3 行程口径

**口径 B：景区内行程口径**（主优化口径）：
- 每天以"8:30 离开酒店 → 当日 $\tau_k^{\text{back}}$ 回到酒店"为优化对象
- $T_k^{\text{scenic}}$ 包含：景区车程、景点游览、午餐、排队（问题三）
- 用于 $Z_2, Z_3$ 计算与每日活动窗约束

**固定边界耗时**（不进入 $Z_1, Z_2, Z_3$，仅在完整行程说明中单独列示）：
- 家↔酒店 4.0h × 2 = 8.0h（5 月 1 日抵达酒店 + 5 月 5 日返家）
- 入住 0.5h（5 月 1 日）+ 退房 0.5h（5 月 5 日）= 1.0h
- 晨间整装 1.5h × 5 天 = 7.5h
- 论文中独立列出，不参与优化排序

> 注：题目硬约束"不安排夜间长途行车"——5 月 1 日抵达酒店时间应安排在白天合理时段（例如建议家→酒店出发不晚于上午），具体抵达时刻由参赛队在论文边界说明中给出，不影响 5 天景区内行程的优化。

---

## 2. 问题一：景点特征与综合优先级

### 2.1 评分公式（保留原模型）

$$S_i = \frac{s_i}{10}, \quad L_i = 1 - \frac{l_i^{\min}}{\max_i l_i^{\min}}, \quad D_i^{\text{comm}} = 1 - \frac{D_{0,i}}{\max_i D_{0,i}}$$

$$C_i = w_1 C_{1i} + w_2 C_{2i} + w_3 C_{3i} + w_4 C_{4i}$$

$$P_i = W_1 S_i + W_2 D_i^{\text{comm}} + W_3 L_i + W_4(1 - C_i)$$

权重：$W = (0.3, 0.3, 0.2, 0.2)$。

> 注：$C_{1i},\dots,C_{4i}$ 在加权前各自做 min-max 归一化到 $[0,1]$，避免量纲不一致。

### 2.2 问题一必须输出的 5 张表

#### 表 1：景点类型归类表 `p1_type_classification.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | A1–A10 |
| name | str | 景点名称 |
| primary_type | str | 一级类型：人文 / 自然 / 休闲 / 主题 |
| secondary_type | str | 二级类型（题目给定，如"古迹"） |
| family_friendly | bool | 是否亲子向 |

参考归类（论文需说明依据）：

| id | 名称 | primary_type | secondary_type |
|---|---|---|---|
| A1 | 古城老街 | 人文 | 古迹 |
| A2 | 海洋乐园 | 主题 | 游乐 |
| A3 | 滨海浴场 | 休闲 | 度假 |
| A4 | 森林公园 | 自然 | 山林 |
| A5 | 民俗古村 | 人文 | 乡村 |
| A6 | 山野溪谷 | 自然 | 徒步 |
| A7 | 环湖湿地 | 自然 | 生态 |
| A8 | 亲子农庄 | 主题 | 亲子 |
| A9 | 山地观景台 | 自然 | 观景 |
| A10 | 文创小镇 | 人文 | 休闲 |

#### 表 2：四维评分表 `p2_four_dim_scores.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | A1–A10 |
| S_i | float | 喜好度（归一化）|
| L_i | float | 游览耗时适配度 |
| D_i_comm | float | 通勤便捷度 |
| C_i | float | 拥堵敏感度（综合）|
| C_1i, C_2i, C_3i, C_4i | float | 4 个子指标（归一化后）|

#### 表 3：综合优先级排序表 `p3_priority_ranking.csv`

| 字段 | 类型 | 说明 |
|---|---|---|
| rank | int | 1–10 |
| id | str | A1–A10 |
| P_i | float | 综合优先级评分 |
| S_i, L_i, D_i_comm, one_minus_C_i | float | 4 个分项贡献 |
| tier | str | 高 / 中 / 低 |

#### 表 4：可联动游玩组合表 `p4_combo_pairs.csv`

定义联动度：

$$\text{Link}_{ij} = \frac{1}{1+D_{ij}}\cdot \mathbb{1}\{D_{ij}\le 0.5\}$$

| 字段 | 类型 | 说明 |
|---|---|---|
| pair | str | "Ai-Aj" |
| D_ij | float | 直达车程（h）|
| Link_ij | float | 联动度 |
| feasible_one_day | bool | 是否可同日游览（按口径 B 模拟可行）|
| combined_type | str | 类型组合，如"人文+人文" |

输出条件：$D_{ij}\le 0.5$ h 的所有 pair，按 Link 降序。

#### 表 5：高/中/低优先级景点池 `p5_priority_pool.csv`

按 $P_i$ 分位划分：

- 高优先级：$P_i\ge Q_{0.7}(P)$ 或前 4 名
- 中优先级：$Q_{0.3}(P)\le P_i<Q_{0.7}(P)$
- 低优先级：其他

| 字段 | 类型 |
|---|---|
| tier | str（high/mid/low）|
| id | str |
| P_i | float |
| recommend_role | str | 必选 / 推荐 / 备选 |

### 2.3 问题一输出汇总 JSON `p1_results.json`

```json
{
  "weights_P": [0.3, 0.3, 0.2, 0.2],
  "weights_C": [0.3, 0.3, 0.2, 0.2],
  "type_classification": [...],
  "four_dim_scores": [...],
  "priority_ranking": [...],
  "combo_pairs": [...],
  "priority_pool": {"high":[...], "mid":[...], "low":[...]}
}
```

---

## 3. 问题二：基准行程与多套备选方案

### 3.1 决策变量

| 变量 | 类型 | 含义 |
|---|---|---|
| $x_i$ | $\{0,1\}$ | 是否选择景点 $i$ |
| $z_{k,i}$ | $\{0,1\}$ | 第 $k$ 天是否游览 $i$ |
| $y_{k,i,j}$ | $\{0,1\}$ | 第 $k$ 天路线 = 酒店→$i$→$j$→酒店；$i=j$ 表示单景点日 |
| $t_i$ | 固定常量 | $t_i = l_i^{\text{comf}}$（不再作为决策变量）|

### 3.2 约束体系

| 编号 | 约束 |
|---|---|
| C1 | $\sum_{i,j} y_{k,i,j} = 1, \quad \forall k$ |
| C2 | $z_{k,i} = \sum_j y_{k,i,j} + \sum_{j\ne i} y_{k,j,i}, \quad \forall k,i$ |
| C3 | $\sum_k z_{k,i} = x_i, \quad \forall i$ |
| C4 | $5 \le \sum_i x_i \le 8$ |
| C5 | $\sum_i z_{k,i}\le 2, \quad \forall k$ |
| C6 | $t_i = l_i^{\text{comf}}$ |
| C7 | $T_k^{\text{all}}\le 14$，等价于 $T_k^{\text{scenic}}\le 12.5$ |
| C8 | $o_i^{\text{op}}\le \tau_{k,i}^{\text{arr}}$ 且 $\tau_{k,i}^{\text{lv}}\le o_i^{\text{cl}}$ 对所有 $z_{k,i}=1$ |
| C9 | $\tau_k^{\text{back}}\le 21.0$ |

### 3.3 每日时间轴（午餐插入规则）

**论文表述**：单次正餐 1.0h 统一等效计入首个景点游览结束后、下一段通勤前；若首个景点游览较长（如 A2 海洋乐园舒适 5h），可理解为在景点内完成正餐。

**编程实现规则**：

双景点日 ($y_{k,i,j}=1, i\ne j$)：

```
8.5
  → 车程 D[0,i]  → arr_i
  → 游览 t_i     → lv_i
  → 午餐 1.0     → lunch_end
  → 车程 D[i,j]  → arr_j
  → 游览 t_j     → lv_j
  → 车程 D[j,0]  → back
```

单景点日 ($y_{k,i,i}=1$)：

```
8.5
  → 车程 D[0,i]  → arr_i
  → 游览 t_i     → lv_i
  → 午餐 1.0     → lunch_end
  → 车程 D[i,0]  → back
```

### 3.4 目标函数

$$Z_1 = \sum_i s_i x_i \quad(\max)$$

$$Z_2 = \sum_{k=1}^{5} T_k^{\text{drive}} = \sum_k \sum_{i,j} y_{k,i,j}\big(D_{0,i}+\lambda_{k,i,j}D_{i,j}+D_{j,0}\big) \quad(\min)$$

$$\bar T = \tfrac{1}{5}\sum_k T_k^{\text{scenic}}, \quad Z_3 = \tfrac{1}{5}\sum_k (T_k^{\text{scenic}}-\bar T)^2 \quad(\min)$$

其中 $\lambda_{k,i,j}=0$ 当 $i=j$，否则 $=1$。

### 3.5 归一化与综合评分

在所有可行解集合 $\mathcal{F}$ 上：

$$\tilde Z_1 = \frac{Z_1 - Z_1^{\min}}{Z_1^{\max}-Z_1^{\min}}, \quad \tilde Z_2 = \frac{Z_2^{\max}-Z_2}{Z_2^{\max}-Z_2^{\min}}, \quad \tilde Z_3 = \frac{Z_3^{\max}-Z_3}{Z_3^{\max}-Z_3^{\min}}$$

$$\boxed{\;F(\lambda) = \lambda_1 \tilde Z_1 + \lambda_2 \tilde Z_2 + \lambda_3 \tilde Z_3\;}$$

### 3.6 多套备选方案（不同偏好）

**同一可行解集合 $\mathcal{F}$，更换 $\lambda$ 重新排序**：

| 方案代号 | 偏好类型 | $\lambda = (\lambda_1, \lambda_2, \lambda_3)$ |
|---|---|---|
| `recommend` | 综合推荐型 | (0.6, 0.2, 0.2) |
| `preference` | 喜好优先型 | (0.8, 0.1, 0.1) |
| `low_commute` | 低通勤型 | (0.4, 0.4, 0.2) |
| `balanced` | 均衡稳健型 | (0.4, 0.2, 0.4) |

> 注意：$Z_1^{\min},Z_1^{\max}$ 等极值由可行解集 $\mathcal{F}$ 决定，在 4 套方案中**共用同一组归一化基准**，确保 $F$ 跨方案可比。

### 3.7 求解方法：枚举法（主方法）

**枚举规模估算**：
- 选择子集 $S$ 数：$\binom{10}{5}+\binom{10}{6}+\binom{10}{7}+\binom{10}{8}=627$
- 每个 $S$ 的 5 天分拆数有限（每天 1 或 2 景点，有序），总规模 $10^5$–$10^6$ 量级
- 笔记本秒级完成

> MILP 作为理论补充：需对 $T_k$ 非线性项做 McCormick 线性化、对 C8 用大 M 法。编程主流程不用。

### 3.8 问题二伪代码

```python
# ===================== 问题二枚举求解 =====================
import numpy as np, json
from itertools import combinations, permutations

# -------- 输入常量 --------
N_SPOT, N_DAY = 10, 5
TAU_DEP       = 8.5
LUNCH         = 1.0
MORNING       = 1.5
DAY_WIN_END   = 21.0      # tau_back 上限
T_SCENIC_MAX  = 14.0 - MORNING   # = 12.5

s      = np.array([8.6,9.2,7.5,8.0,7.2,7.8,6.8,8.3,7.0,7.6])
l_min  = np.array([2.0,3.0,1.0,3.5,2.0,3.0,1.5,2.0,1.5,2.0])
l_comf = np.array([3.5,5.0,3.0,4.5,3.0,4.0,2.5,3.0,2.5,3.0])
o_op   = np.array([8,9,7,8,8,8,7,9,8,9])         # 全天开放→7
o_cl   = np.array([17.5,18,21,17,17.5,17,21,18,17.5,20])
D      = np.loadtxt('dist.csv', delimiter=',')   # 11x11，含酒店

PREF_PROFILES = {
    'recommend':    (0.6, 0.2, 0.2),
    'preference':   (0.8, 0.1, 0.1),
    'low_commute':  (0.4, 0.4, 0.2),
    'balanced':     (0.4, 0.2, 0.4),
}

# -------- 单日方案构建 --------
def build_day(spots):
    """spots: tuple, 1 或 2 个景点（有序）"""
    if len(spots) == 1:
        i = spots[0]
        arr_i = TAU_DEP + D[0, i+1]
        lv_i  = arr_i + l_comf[i]
        lun_s, lun_e = lv_i, lv_i + LUNCH
        back  = lun_e + D[i+1, 0]
        feas = (arr_i >= o_op[i]) and (lv_i <= o_cl[i]) and (back <= DAY_WIN_END)
        T_sc = back - TAU_DEP
        T_dr = D[0, i+1] + D[i+1, 0]
        tl = {'seq':[f'A{i+1}'],'arr':[arr_i],'lv':[lv_i],
              'lunch':[lun_s,lun_e],'back':back}
    else:
        i, j = spots
        arr_i = TAU_DEP + D[0, i+1]
        lv_i  = arr_i + l_comf[i]
        lun_s, lun_e = lv_i, lv_i + LUNCH
        arr_j = lun_e + D[i+1, j+1]
        lv_j  = arr_j + l_comf[j]
        back  = lv_j + D[j+1, 0]
        feas  = ((arr_i >= o_op[i]) and (lv_i <= o_cl[i])
              and (arr_j >= o_op[j]) and (lv_j <= o_cl[j])
              and (back <= DAY_WIN_END))
        T_sc  = back - TAU_DEP
        T_dr  = D[0,i+1] + D[i+1,j+1] + D[j+1,0]
        tl    = {'seq':[f'A{i+1}',f'A{j+1}'],'arr':[arr_i,arr_j],
                 'lv':[lv_i,lv_j],'lunch':[lun_s,lun_e],'back':back}
    feas = feas and (T_sc <= T_SCENIC_MAX + 1e-6)
    return {'spots':spots,'T_sc':T_sc,'T_dr':T_dr,'feas':feas,'tl':tl}

def all_day_options(S):
    opts = []
    S_lst = list(S)
    for i in S_lst:
        o = build_day((i,))
        if o['feas']: opts.append(o)
    for i, j in permutations(S_lst, 2):
        o = build_day((i, j))
        if o['feas']: opts.append(o)
    return opts

# -------- 把 S 分配到 5 天（无休息日） --------
def assign_to_days(S):
    plans = []
    target = set(S)
    options = all_day_options(S)
    
    def bt(day, remaining, current):
        if day == N_DAY:
            if not remaining:
                plans.append(tuple(current))
            return
        for opt in options:
            sp_set = set(opt['spots'])
            if sp_set.issubset(remaining) and len(sp_set) == len(opt['spots']):
                rem_after = remaining - sp_set
                days_left = N_DAY - day - 1
                # 剪枝：每天 1 或 2 个景点，必须出游
                if days_left <= len(rem_after) <= 2 * days_left:
                    current.append(opt)
                    bt(day + 1, rem_after, current)
                    current.pop()
    bt(0, target, [])
    return plans

def eval_plan(S, day_opts):
    Z1 = sum(s[i] for i in S)
    Z2 = sum(d['T_dr'] for d in day_opts)
    Tks = [d['T_sc'] for d in day_opts]
    Tbar = sum(Tks) / N_DAY
    Z3 = sum((t - Tbar)**2 for t in Tks) / N_DAY
    return Z1, Z2, Z3, Tks

# -------- 枚举所有可行解 --------
def enumerate_all():
    cands = []
    for size in (5, 6, 7, 8):
        for S in combinations(range(N_SPOT), size):
            S = frozenset(S)
            for day_opts in assign_to_days(S):
                Z1, Z2, Z3, Tks = eval_plan(S, day_opts)
                cands.append({'S':S, 'opts':day_opts,
                              'Z1':Z1, 'Z2':Z2, 'Z3':Z3, 'Tks':Tks})
    return cands

# -------- 归一化与多套备选 --------
def normalize_and_rank(cands, profiles=PREF_PROFILES, top_n=5):
    Z1s = np.array([c['Z1'] for c in cands])
    Z2s = np.array([c['Z2'] for c in cands])
    Z3s = np.array([c['Z3'] for c in cands])
    Z1lo, Z1hi = Z1s.min(), Z1s.max()
    Z2lo, Z2hi = Z2s.min(), Z2s.max()
    Z3lo, Z3hi = Z3s.min(), Z3s.max()
    
    # 共享归一化（4 套方案可比）
    for c in cands:
        c['z1n'] = (c['Z1']-Z1lo)/(Z1hi-Z1lo+1e-9)
        c['z2n'] = (Z2hi-c['Z2'])/(Z2hi-Z2lo+1e-9)
        c['z3n'] = (Z3hi-c['Z3'])/(Z3hi-Z3lo+1e-9)
    
    ranked = {}
    for name, lam in profiles.items():
        for c in cands:
            c['F'] = lam[0]*c['z1n'] + lam[1]*c['z2n'] + lam[2]*c['z3n']
        ordered = sorted(cands, key=lambda x: -x['F'])
        ranked[name] = {
            'lambda': lam,
            'top': [export_plan(c, lam) for c in ordered[:top_n]]
        }
    return ranked

def export_plan(c, lam):
    return {
        'selected': sorted([f'A{i+1}' for i in c['S']]),
        'Z1': float(c['Z1']),'Z2': float(c['Z2']),'Z3': float(c['Z3']),
        'Z1_norm':float(c['z1n']),'Z2_norm':float(c['z2n']),'Z3_norm':float(c['z3n']),
        'F': float(c['F']),
        'lambda': lam,
        'Tks': [float(t) for t in c['Tks']],
        'days':[{
            'day': k+1,
            'depart': TAU_DEP,
            'seq': opt['tl']['seq'],
            'arr': [float(x) for x in opt['tl']['arr']],
            'lv':  [float(x) for x in opt['tl']['lv']],
            'lunch':[float(x) for x in opt['tl']['lunch']],
            'back': float(opt['tl']['back']),
            'T_scenic': float(opt['T_sc']),
            'T_all':    float(opt['T_sc'] + MORNING),
            'drive':    float(opt['T_dr'])
        } for k, opt in enumerate(c['opts'])]
    }

# -------- 主流程 --------
if __name__ == '__main__':
    cands = enumerate_all()
    ranked = normalize_and_rank(cands)
    
    output = {
        'scope': 'scenic_area_only',
        'fixed_boundary_hours': {
            'home_to_hotel_one_way': 4.0,
            'checkin': 0.5,
            'checkout': 0.5,
            'morning_per_day': 1.5
        },
        'constants': {
            'tau_depart': TAU_DEP,
            'lunch_duration': LUNCH,
            'T_scenic_max': T_SCENIC_MAX,
            'day_window_end': DAY_WIN_END
        },
        'profiles': ranked,
        'baseline_plan': ranked['recommend']['top'][0]  # 主基准 = 综合推荐型 top-1
    }
    with open('baseline_plan.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
```

### 3.9 `baseline_plan.json` 字段规范

```json
{
  "scope": "scenic_area_only",
  "fixed_boundary_hours": {
    "home_to_hotel_one_way": 4.0,
    "checkin": 0.5,
    "checkout": 0.5,
    "morning_per_day": 1.5
  },
  "constants": {
    "tau_depart": 8.5,
    "lunch_duration": 1.0,
    "T_scenic_max": 12.5,
    "day_window_end": 21.0
  },
  "profiles": {
    "recommend":   {"lambda":[0.6,0.2,0.2],"top":[{...},{...}, ...]},
    "preference":  {"lambda":[0.8,0.1,0.1],"top":[...]},
    "low_commute": {"lambda":[0.4,0.4,0.2],"top":[...]},
    "balanced":    {"lambda":[0.4,0.2,0.4],"top":[...]}
  },
  "baseline_plan": {
    "selected": ["A1","A2","A3","A4","A5","A8"],
    "Z1": 51.4, "Z2": 7.8, "Z3": 0.94,
    "Z1_norm":0.92,"Z2_norm":0.81,"Z3_norm":0.76,
    "F": 0.866,
    "lambda":[0.6,0.2,0.2],
    "Tks":[9.2, 10.4, 8.7, 11.1, 9.0],
    "days":[
      {
        "day":1,"depart":8.5,
        "seq":["A3","A1"],
        "arr":[8.8,13.7],"lv":[11.8,17.2],
        "lunch":[11.8,12.8],
        "back":17.7,
        "T_scenic":9.2,"T_all":10.7,"drive":1.4
      }
    ]
  }
}
```

---

## 4. 问题三：随机扰动下的稳定性评估

### 4.1 新增符号

| 符号 | 含义 |
|---|---|
| $s = 1,\dots,N$ | Monte Carlo 第 $s$ 次模拟，默认 $N=10000$ |
| $W^{(s)}_{k,\ell}$ | 第 $s$ 次第 $k$ 天第 $\ell$ 段路堵车延时 |
| $\xi^{(s)}_{k,\ell}\in\{0,1\}$ | 是否发生堵车 |
| $Q^{(s)}_{k,i}$ | 第 $s$ 次第 $k$ 天景点 $i$ 排队时间 |
| $\tilde t^{(s)}_{k,i}$ | 受闭园截断的实际游览时长 |
| $T_k^{\text{scenic},(s)}, \tau_k^{\text{back},(s)}$ | 模拟下的景区耗时与返程时刻 |
| $F_k^{(s)}, F^{(s)}$ | 日级 / 整次失败标识 |
| $R, P_{\text{fail}}$ | 可靠度 / 失败概率 |

### 4.2 时段判别函数

$$\delta(t)=\begin{cases}1,& t\in[7,9)\cup[11,13)\cup[16,18)\\0,& \text{otherwise}\end{cases}$$

$$\rho(t)=\begin{cases}1,& t\in[9,12)\\0,& \text{otherwise}\end{cases}$$

### 4.3 堵车采样（含敏感性参数）

$$p_{\text{jam}}(\tau)=\begin{cases}p^{\text{pk}},& \delta(\tau)=1\\p^{\text{off}},& \delta(\tau)=0\end{cases}$$

$$\xi^{(s)}_{k,\ell}\sim\text{Bernoulli}(p_{\text{jam}}(\tau_{k,\ell}^{\text{drive\_st}}))$$

$$W^{(s)}_{k,\ell}=\xi^{(s)}_{k,\ell}\cdot\begin{cases}U(1,4),&\delta(\tau)=1\\U(0,1.5),&\delta(\tau)=0\end{cases}$$

**敏感性网格**（必跑）：
- $p^{\text{pk}}\in\{0.4, 0.5, 0.6, 0.7\}$
- $p^{\text{off}}\in\{0.1, 0.2, 0.3, 0.4\}$
- 共 16 组组合
- 主结果汇报 $(p^{\text{pk}},p^{\text{off}})=(0.6,0.3)$ 一组

### 4.4 排队采样（题目给定，无额外概率）

$$Q^{(s)}_{k,i}=\begin{cases}U(0.5,3),&9\le\tau_{k,i}^{\text{arr},(s)}<12\\U(0,1),&\text{otherwise}\end{cases}$$

排队不计入 $\tilde t_i$，但占用日内时间轴。

### 4.5 受扰动时间轴（含午餐插入）

双景点日：

$$\tau_{k,i}^{\text{arr},(s)} = 8.5 + D_{0,i} + W^{(s)}_{k,1}$$

$$\tilde t^{(s)}_{k,i} = \max\!\Big(0,\,\min\!\big(l_i^{\text{comf}},\,o_i^{\text{cl}} - \tau_{k,i}^{\text{arr},(s)} - Q^{(s)}_{k,i}\big)\Big)$$

$$\tau_{k,i}^{\text{lv},(s)} = \tau_{k,i}^{\text{arr},(s)} + Q^{(s)}_{k,i} + \tilde t^{(s)}_{k,i}$$

$$\tau_k^{\text{lun\_st},(s)} = \tau_{k,i}^{\text{lv},(s)}, \quad \tau_k^{\text{lun\_ed},(s)} = \tau_k^{\text{lun\_st},(s)} + 1.0$$

$$\tau_{k,j}^{\text{arr},(s)} = \tau_k^{\text{lun\_ed},(s)} + D_{i,j} + W^{(s)}_{k,2}$$

$$\tilde t^{(s)}_{k,j} = \max\!\Big(0,\,\min\!\big(l_j^{\text{comf}},\,o_j^{\text{cl}} - \tau_{k,j}^{\text{arr},(s)} - Q^{(s)}_{k,j}\big)\Big)$$

$$\tau_{k,j}^{\text{lv},(s)} = \tau_{k,j}^{\text{arr},(s)} + Q^{(s)}_{k,j} + \tilde t^{(s)}_{k,j}$$

$$\tau_k^{\text{back},(s)} = \tau_{k,j}^{\text{lv},(s)} + D_{j,0} + W^{(s)}_{k,3}$$

单景点日：午餐插在游览后、返程前，2 段路。

景区内总耗时：

$$T_k^{\text{scenic},(s)} = \tau_k^{\text{back},(s)} - 8.5$$

### 4.6 失败事件

$$\boxed{\;F_k^{(s)} = \mathbb{1}\!\Big\{T_k^{\text{scenic},(s)} > 12.5 \;\vee\; \tau_k^{\text{back},(s)} > 21 \;\vee\; \exists i\in\text{visit}_k:\,\tilde t^{(s)}_{k,i} < l_i^{\min}\Big\}\;}$$

$$F^{(s)} = \mathbb{1}\!\Big\{\sum_k F_k^{(s)} \ge 1\Big\}$$

### 4.7 可靠度与失败概率

$$\hat P_{\text{fail}} = \frac{1}{N}\sum_{s=1}^{N} F^{(s)}, \quad \hat R = 1 - \hat P_{\text{fail}}$$

$$\text{CI}_{95\%}:\quad \hat P_{\text{fail}} \pm 1.96\sqrt{\hat P_{\text{fail}}(1-\hat P_{\text{fail}})/N}$$

### 4.8 贡献度分解（Shapley 开关法）

4 个场景：

| 场景 | road | queue | 失败概率 |
|---|---|---|---|
| 基线 | 关 | 关 | $\hat P_0$（≈0）|
| 仅堵车 | 开 | 关 | $\hat P_R$ |
| 仅排队 | 关 | 开 | $\hat P_Q$ |
| 全扰动 | 开 | 开 | $\hat P_F$ |

$$\Delta_R = \hat P_R - \hat P_0, \quad \Delta_Q = \hat P_Q - \hat P_0, \quad \Delta_J = \hat P_F - \hat P_R - \hat P_Q + \hat P_0$$

$$\boxed{\;\phi_{\text{road}} = \frac{\Delta_R + \tfrac{1}{2}\Delta_J}{\hat P_F - \hat P_0},\quad \phi_{\text{queue}} = \frac{\Delta_Q + \tfrac{1}{2}\Delta_J}{\hat P_F - \hat P_0}\;}$$

$\phi_{\text{road}} + \phi_{\text{queue}} = 1$。

### 4.9 结构性薄弱点

日级阈值（目标 $R\ge 0.9$）：

$$\theta_k = 1 - 0.9^{1/5} \approx 0.0209$$

$$\text{Weak Days} = \{k: \hat P_{\text{fail},k} > \theta_k\}, \quad \hat P_{\text{fail},k} = \tfrac{1}{N}\sum_s F_k^{(s)}$$

景点贡献率：

$$\phi_i = \frac{\sum_{s,k}\mathbb{1}\{F_k^{(s)}=1\wedge i\in\text{visit}_k\}}{\sum_{s,k}\mathbb{1}\{F_k^{(s)}=1\}}$$

### 4.10 问题三伪代码

```python
# ===================== 问题三 Monte Carlo =====================
import numpy as np, json
RNG = np.random.default_rng(2026)

P_PK_DEFAULT  = 0.6
P_OFF_DEFAULT = 0.3
N_SIM         = 10000

def in_peak(t):     return (7<=t<9) or (11<=t<13) or (16<=t<18)
def in_queue_pk(t): return 9<=t<12

def sample_road(t, p_pk, p_off, on):
    if not on: return 0.0
    if in_peak(t):
        return RNG.uniform(1,4) if RNG.random() < p_pk else 0.0
    return RNG.uniform(0,1.5) if RNG.random() < p_off else 0.0

def sample_queue(t_arr, on):
    if not on: return 0.0
    return RNG.uniform(0.5, 3) if in_queue_pk(t_arr) else RNG.uniform(0, 1)

def simulate_day(day, road_on, queue_on, p_pk, p_off,
                 l_min, l_comf, o_cl, D):
    seq = [int(name[1:]) - 1 for name in day['seq']]
    n = len(seq)
    tau = 8.5
    prev = 0
    legs = []; queues = []; t_acts = []
    
    for idx in range(n):
        sp = seq[idx]
        w = sample_road(tau, p_pk, p_off, road_on)
        legs.append(w)
        tau += D[prev, sp+1] + w
        arr = tau
        q = sample_queue(arr, queue_on)
        queues.append(q)
        tau += q
        t_real = max(0, min(l_comf[sp], o_cl[sp] - tau))
        t_acts.append(t_real)
        tau += t_real
        # 午餐在首个景点后
        if idx == 0:
            tau += 1.0
        prev = sp + 1
    
    # 返程
    w_back = sample_road(tau, p_pk, p_off, road_on)
    legs.append(w_back)
    tau += D[prev, 0] + w_back
    back = tau
    T_sc = back - 8.5
    
    fail = (T_sc > 12.5 + 1e-6) or (back > 21.0 + 1e-6)
    for idx, sp in enumerate(seq):
        if t_acts[idx] < l_min[sp] - 1e-6:
            fail = True
    
    return {'T_sc':T_sc, 'back':back, 'fail':fail,
            'seq':seq, 'legs':legs, 'queues':queues, 't_acts':t_acts}

def monte_carlo(plan, N, road_on, queue_on, p_pk, p_off,
                l_min, l_comf, o_cl, D):
    n_fail = 0
    day_fail = np.zeros(5)
    spot_fail = np.zeros(10)
    
    for _ in range(N):
        trip_fail = False
        spot_this = set()
        for k, day in enumerate(plan['days']):
            r = simulate_day(day, road_on, queue_on, p_pk, p_off,
                             l_min, l_comf, o_cl, D)
            if r['fail']:
                day_fail[k] += 1
                trip_fail = True
                spot_this.update(r['seq'])
        if trip_fail:
            n_fail += 1
            for i in spot_this: spot_fail[i] += 1
    
    P_fail = n_fail / N
    return {
        'P_fail': P_fail,
        'R': 1 - P_fail,
        'CI_95': 1.96*np.sqrt(P_fail*(1-P_fail)/N),
        'P_fail_day': (day_fail/N).tolist(),
        'phi_spot':   (spot_fail/max(n_fail,1)).tolist()
    }

def shapley(plan, N, p_pk, p_off, l_min, l_comf, o_cl, D):
    args = (l_min, l_comf, o_cl, D)
    P0 = monte_carlo(plan, N, False, False, p_pk, p_off, *args)['P_fail']
    PR = monte_carlo(plan, N, True,  False, p_pk, p_off, *args)['P_fail']
    PQ = monte_carlo(plan, N, False, True,  p_pk, p_off, *args)['P_fail']
    PF = monte_carlo(plan, N, True,  True,  p_pk, p_off, *args)['P_fail']
    dR, dQ = PR-P0, PQ-P0
    dJ = PF - PR - PQ + P0
    denom = max(PF - P0, 1e-9)
    return {
        'P0':P0,'PR':PR,'PQ':PQ,'PF':PF,
        'phi_road':  (dR + 0.5*dJ)/denom,
        'phi_queue': (dQ + 0.5*dJ)/denom,
        'R': 1 - PF
    }

def sensitivity_scan(plan, N, l_min, l_comf, o_cl, D):
    results = []
    for p_pk in [0.4, 0.5, 0.6, 0.7]:
        for p_off in [0.1, 0.2, 0.3, 0.4]:
            mc = monte_carlo(plan, N, True, True, p_pk, p_off,
                             l_min, l_comf, o_cl, D)
            sh = shapley(plan, N//4, p_pk, p_off, l_min, l_comf, o_cl, D)
            results.append({
                'p_pk':p_pk,'p_off':p_off,
                'R':mc['R'],'P_fail':mc['P_fail'],'CI_95':mc['CI_95'],
                'P_fail_day':mc['P_fail_day'],
                'phi_spot':mc['phi_spot'],
                'phi_road':sh['phi_road'],'phi_queue':sh['phi_queue']
            })
    return results

def weak_points(mc):
    theta = 1 - 0.9**(1/5)
    weak_days = [k+1 for k,p in enumerate(mc['P_fail_day']) if p>theta]
    weak_spots = sorted(enumerate(mc['phi_spot']), key=lambda x:-x[1])[:3]
    return {
        'theta_per_day': theta,
        'target_R_met': mc['R'] >= 0.9,
        'weak_days': weak_days,
        'weak_spots':[(f'A{i+1}', round(p,3)) for i,p in weak_spots if p>0]
    }

if __name__ == '__main__':
    with open('baseline_plan.json','r',encoding='utf-8') as f:
        bp = json.load(f)
    plan = bp['baseline_plan']
    
    l_min  = np.array([2.0,3.0,1.0,3.5,2.0,3.0,1.5,2.0,1.5,2.0])
    l_comf = np.array([3.5,5.0,3.0,4.5,3.0,4.0,2.5,3.0,2.5,3.0])
    o_cl   = np.array([17.5,18,21,17,17.5,17,21,18,17.5,20])
    D      = np.loadtxt('dist.csv', delimiter=',')
    
    mc_main = monte_carlo(plan, N_SIM, True, True,
                          P_PK_DEFAULT, P_OFF_DEFAULT,
                          l_min, l_comf, o_cl, D)
    sh_main = shapley(plan, N_SIM, P_PK_DEFAULT, P_OFF_DEFAULT,
                      l_min, l_comf, o_cl, D)
    wp      = weak_points(mc_main)
    sens    = sensitivity_scan(plan, N_SIM//2, l_min, l_comf, o_cl, D)
    
    report = {
        'assumptions': {
            'p_peak_default': P_PK_DEFAULT,
            'p_off_default': P_OFF_DEFAULT,
            'queue_no_extra_prob': True,
            'N_simulations': N_SIM,
            'trip_scope': 'scenic_area_only'
        },
        'main_result': {
            'R': mc_main['R'],
            'P_fail': mc_main['P_fail'],
            'CI_95': mc_main['CI_95'],
            'P_fail_day': mc_main['P_fail_day'],
            'phi_road': sh_main['phi_road'],
            'phi_queue': sh_main['phi_queue']
        },
        'weak_points': wp,
        'sensitivity_grid': sens
    }
    with open('reliability_report.json','w',encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
```

### 4.11 `reliability_report.json` 字段规范

```json
{
  "assumptions": {
    "p_peak_default": 0.6,
    "p_off_default": 0.3,
    "queue_no_extra_prob": true,
    "N_simulations": 10000,
    "trip_scope": "scenic_area_only"
  },
  "main_result": {
    "R": 0.873,
    "P_fail": 0.127,
    "CI_95": 0.0066,
    "P_fail_day": [0.018, 0.045, 0.022, 0.061, 0.014],
    "phi_road":  0.58,
    "phi_queue": 0.42
  },
  "weak_points": {
    "theta_per_day": 0.0209,
    "target_R_met": false,
    "weak_days": [2, 4],
    "weak_spots": [["A4", 0.31], ["A6", 0.22], ["A2", 0.18]]
  },
  "sensitivity_grid": [
    {"p_pk":0.4,"p_off":0.1,"R":0.951,"phi_road":0.51,"phi_queue":0.49,"...":"..."}
  ]
}
```

---

## 5. 编程交付清单

| 文件 | 来源 | 用途 |
|---|---|---|
| `dist.csv` | 题目附件 | 11×11 距离矩阵 |
| `attractions.csv` | 题目附件整理 | 景点参数表 |
| `solve_p1.py` | Codex 实现 | 输出 p1_results.json + 5 张 CSV |
| `solve_p2.py` | §3.8 伪代码 | 输出 baseline_plan.json |
| `solve_p3.py` | §4.10 伪代码 | 输出 reliability_report.json |
| `p1_results.json` | solve_p1.py | 问题一全部结果 |
| `baseline_plan.json` | solve_p2.py | 问题二 4 套方案 + 主基准 |
| `reliability_report.json` | solve_p3.py | 问题三主结果 + 敏感性 |

### 5.1 模块调用顺序

```
solve_p1.py  →  p1_results.json  + 5 张 CSV
solve_p2.py  →  baseline_plan.json
solve_p3.py  ←  baseline_plan.json
             →  reliability_report.json
```

---

## 6. 仍需队伍确认的假设清单

| 编号 | 假设 | 默认值 | 影响 | 优先级 |
|---|---|---|---|---|
| A1 | 高峰堵车发生概率 $p^{\text{pk}}$ | 0.6（敏感性网格 0.4–0.7）| 问题三 $R$ | 高 |
| A2 | 平峰堵车发生概率 $p^{\text{off}}$ | 0.3（敏感性网格 0.1–0.4）| 问题三 $R$ | 高 |
| A3 | 排队按题目分布直接抽样（无额外发生概率） | 是 | 问题三排队 | 已确认 |
| A4 | 各路段堵车延时独立 | 是 | 问题三 | 中 |
| A5 | 各景点排队独立 | 是 | 问题三 | 中 |
| A6 | 排队时间不计入游览时长 $\tilde t_i$ | 是 | 问题三失败定义 | 中 |
| A7 | 闭园截断后 $\tilde t_i<l_i^{\min}$ 计为失败 | 是 | 问题三 | 高 |
| A8 | 每日固定 8:30 出发 | 是 | 问题二 + 三 | 已确认 |
| A9 | 午餐 1.0h 插入首个景点游览后 | 是 | 时间轴 | 已确认 |
| A10 | 问题二游览时长固定 $t_i=l_i^{\text{comf}}$ | 是 | 问题二 | 已确认 |
| A11 | 行程口径 = 景区内行程口径（口径 B）| 是 | 全模型 | 已确认 |
| A12 | 综合评分权重默认 $\lambda=(0.6,0.2,0.2)$，并列出 4 套偏好 | 是 | 问题二排序 | 已确认 |
| A13 | 5 天每天必出游，无休息日 | 是 | C1 等式 | 已确认 |
| A14 | 失败判定为 OR 关系 | 是 | 问题三 | 中 |
| A15 | $N=10000$，Shapley 单场景 $N/4$ | 是 | 精度 | 低 |
| A16 | 晨间整装 1.5h 在 7:00–8:30 完成，不进入 $T_k^{\text{scenic}}$ | 是 | 时间窗 | 已确认 |
| A17 | 4 套偏好共用同一组归一化基准 $(Z_p^{\min},Z_p^{\max})$ | 是 | 问题二多方案可比 | 已确认 |
| A18 | $C_{1i},\dots,C_{4i}$ 加权前各自 min-max 归一化 | 是 | 问题一 $C_i$ | 已确认 |
| A19 | 联动度阈值 $D_{ij}\le 0.5$h | 是 | 问题一表 4 | 中 |
| A20 | 优先级分位阈值 $Q_{0.7}/Q_{0.3}$ 划分 高/中/低 | 是 | 问题一表 5 | 中 |

**最关键**：A1, A2 必须做敏感性分析；A11 必须在论文"模型假设"章节明确。

---

## 7. 版本说明

- v1.0（本稿）：定稿，可直接交编程实现
- 主要变更点（vs 第二轮修订稿）：
  1. 时间窗约束改为 $T_k^{\text{all}}\le 14$，等价 $T_k^{\text{scenic}}\le 12.5$
  2. 家↔酒店、入退房明确为固定边界耗时，不进入 $Z_1/Z_2/Z_3$
  3. 午餐论文表述柔化为"等效计入"
  4. 新增 4 套偏好备选方案（recommend / preference / low_commute / balanced），共享归一化基准
  5. 问题一补全 5 张输出表规范
