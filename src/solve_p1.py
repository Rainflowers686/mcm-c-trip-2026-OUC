"""solve_p1.py — 问题一：景点特征分析与综合优先级评分

按 model_spec_v1.0.md §2 实现：
  - 四维评分 S_i, L_i, D_i_comm, C_i  →  综合优先级 P_i
  - 拥堵敏感度 C_i 由 4 个子指标 C_1i..C_4i 加权（先各自 min-max 归一化）
  - 输出 5 张表 + 汇总 JSON + 1 张图（综合优先级排序）

权重：
  W_P = (W1,W2,W3,W4) = (0.3, 0.3, 0.2, 0.2)   用于 P_i
  W_C = (w1,w2,w3,w4) = (0.3, 0.3, 0.2, 0.2)   用于 C_i

时段定义：
  高峰 δ(t)=1 当 t∈[7,9)∪[11,13)∪[16,18)
  排队风险 γ(t): t∈[9,12) → 1，其他 → 0.2
  速度系数 µ(t): δ=1 → 2.5，δ=0 → 0.75
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------- 路径常量 ----------
ROOT = Path(__file__).resolve().parent
OUT_TABLES = ROOT / "output" / "tables"
OUT_FIGURES = ROOT / "output" / "figures"
OUT_LOGS = ROOT / "output" / "logs"
for _d in (OUT_TABLES, OUT_FIGURES, OUT_LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# 中文字体（matplotlib 需要兼容）
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 模型常量 ----------
TAU_DEP = 8.5
W_P = np.array([0.3, 0.3, 0.2, 0.2])  # P_i 权重 (S, D_comm, L, 1-C)
W_C = np.array([0.3, 0.3, 0.2, 0.2])  # C_i 权重 (C1, C2, C3, C4)

# 全天开放景点（A3, A7）的 O_i 取活动窗 14 小时
DAY_WINDOW_LEN = 14.0


# ---------- 时段判别函数 ----------
def delta_peak(t: float) -> int:
    """高峰判别函数 δ(t)：t∈[7,9)∪[11,13)∪[16,18) 返回 1，否则 0。"""
    return int((7 <= t < 9) or (11 <= t < 13) or (16 <= t < 18))


def mu_speed(t: float) -> float:
    """速度/时间系数 µ(t)：高峰 2.5，平峰 0.75。"""
    return 2.5 if delta_peak(t) == 1 else 0.75


def gamma_queue(t: float) -> float:
    """排队风险函数 γ(t)：t∈[9,12) 返回 1，其他返回 0.2。"""
    return 1.0 if 9 <= t < 12 else 0.2


# ---------- 数据装载 ----------
def load_data(root: Path = ROOT) -> tuple[pd.DataFrame, np.ndarray]:
    """读取 attractions.csv 与 dist.csv，返回 (景点表, 11x11 距离矩阵)。"""
    attractions = pd.read_csv(root / "attractions.csv")
    dist = np.loadtxt(root / "dist.csv", delimiter=",")
    assert dist.shape == (11, 11), f"距离矩阵形状错误：{dist.shape}"
    assert len(attractions) == 10, "景点数应为 10"
    return attractions, dist


# ---------- 四维评分 ----------
def compute_four_dim(attractions: pd.DataFrame, dist: np.ndarray) -> pd.DataFrame:
    """计算四维评分 S_i, L_i, D_i_comm 以及拥堵敏感度子指标 C_1i..C_4i。

    返回 DataFrame，含字段：
        id, S_i, L_i, D_i_comm,
        C_1i_raw, C_2i_raw, C_3i_raw, C_4i_raw,    （原始）
        C_1i, C_2i, C_3i, C_4i,                    （min-max 归一化后）
        C_i                                         （加权后综合）
    """
    n = len(attractions)
    score = attractions["score"].to_numpy()
    l_min = attractions["l_min"].to_numpy()
    l_comf = attractions["l_comf"].to_numpy()
    open_h = attractions["open_hour"].to_numpy()
    close_h = attractions["close_hour"].to_numpy()

    # 距离：D_{0,i}，dist[0, i+1]
    d0 = dist[0, 1:11]

    # 主体三维
    S = score / 10.0
    L = 1.0 - l_min / np.max(l_min)
    D_comm = 1.0 - d0 / np.max(d0)

    # 子指标原始值
    C1_raw = np.zeros(n)
    C2_raw = np.zeros(n)
    C3_raw = np.zeros(n)
    C4_raw = np.zeros(n)

    for i in range(n):
        # 到达 / 离开时刻
        arr_i = TAU_DEP + d0[i]
        leave_i = arr_i + l_comf[i]
        # C1: 出发与离开时段风险
        C1_raw[i] = 0.5 * delta_peak(TAU_DEP) + 0.5 * delta_peak(leave_i)
        # C2: 高峰通勤影响（原稿：[µ(8.5)+µ(t_leave)]/2 再 /4，区间约 [0.19, 0.625]）
        C2_raw[i] = (0.5 * mu_speed(TAU_DEP) + 0.5 * mu_speed(leave_i)) / 4.0
        # C3: 排队风险
        C3_raw[i] = gamma_queue(arr_i)
        # C4: 最小游览时长 / 每日开放时长
        O_i = max(close_h[i] - open_h[i], DAY_WINDOW_LEN)
        # 注：全天开放（open=7, close=21）→ O_i=14，与 spec 一致
        C4_raw[i] = l_min[i] / O_i

    # min-max 归一化（避免量纲不一致）
    def minmax(arr: np.ndarray) -> np.ndarray:
        lo, hi = arr.min(), arr.max()
        if hi - lo < 1e-12:
            return np.zeros_like(arr)
        return (arr - lo) / (hi - lo)

    C1 = minmax(C1_raw)
    C2 = minmax(C2_raw)
    C3 = minmax(C3_raw)
    C4 = minmax(C4_raw)
    C = W_C[0] * C1 + W_C[1] * C2 + W_C[2] * C3 + W_C[3] * C4

    return pd.DataFrame({
        "id": attractions["id"],
        "S_i": S,
        "L_i": L,
        "D_i_comm": D_comm,
        "C_1i_raw": C1_raw, "C_2i_raw": C2_raw,
        "C_3i_raw": C3_raw, "C_4i_raw": C4_raw,
        "C_1i": C1, "C_2i": C2, "C_3i": C3, "C_4i": C4,
        "C_i": C,
    })


# ---------- 综合优先级 ----------
def compute_priority(four_dim: pd.DataFrame) -> pd.DataFrame:
    """计算综合优先级 P_i = W1 S + W2 D_comm + W3 L + W4 (1-C)。

    返回排名表，按 P_i 降序，含分项贡献与 tier 划分（高/中/低）。
    """
    S = four_dim["S_i"].to_numpy()
    L = four_dim["L_i"].to_numpy()
    D_comm = four_dim["D_i_comm"].to_numpy()
    C = four_dim["C_i"].to_numpy()
    one_minus_C = 1.0 - C
    P = W_P[0] * S + W_P[1] * D_comm + W_P[2] * L + W_P[3] * one_minus_C

    df = pd.DataFrame({
        "id": four_dim["id"],
        "P_i": P,
        "S_i": S,
        "L_i": L,
        "D_i_comm": D_comm,
        "one_minus_C_i": one_minus_C,
    }).sort_values("P_i", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", np.arange(1, len(df) + 1))

    # 高/中/低 tier 划分：高 = P_i ≥ Q_0.7 或前 4 名；低 = P_i < Q_0.3
    q70 = np.quantile(P, 0.7)
    q30 = np.quantile(P, 0.3)

    def classify(row):
        if row["rank"] <= 4 or row["P_i"] >= q70:
            return "high"
        if row["P_i"] < q30:
            return "low"
        return "mid"

    df["tier"] = df.apply(classify, axis=1)
    return df


# ---------- 类型归类表 ----------
def build_type_table(attractions: pd.DataFrame) -> pd.DataFrame:
    """从 attractions.csv 提取类型归类表。"""
    df = attractions[
        ["id", "name", "primary_type", "secondary_type", "family_friendly"]
    ].copy()
    df["family_friendly"] = df["family_friendly"].astype(bool)
    return df


# ---------- 联动对挖掘 ----------
def build_combo_pairs(attractions: pd.DataFrame, dist: np.ndarray,
                      threshold: float = 0.5) -> pd.DataFrame:
    """挖掘可联动游玩组合 (D_ij ≤ threshold)，按联动度降序。

    联动度：Link_ij = 1 / (1 + D_ij)，仅对 D_ij ≤ 0.5 输出。
    feasible_one_day：调用问题二同日方案构建逻辑做可行性校验。
    """
    n = len(attractions)
    open_h = attractions["open_hour"].to_numpy()
    close_h = attractions["close_hour"].to_numpy()
    l_comf = attractions["l_comf"].to_numpy()
    p_type = attractions["primary_type"].to_numpy()
    ids = attractions["id"].to_numpy()

    rows = []
    LUNCH = 1.0
    T_SCENIC_MAX = 14.0 - 1.5  # 12.5

    for i in range(n):
        for j in range(i + 1, n):
            d_ij = dist[i + 1, j + 1]
            if d_ij > threshold + 1e-9:
                continue
            link = 1.0 / (1.0 + d_ij)

            # 检测同日可行（顺序 i→j）
            arr_i = TAU_DEP + dist[0, i + 1]
            lv_i = arr_i + l_comf[i]
            lun_e = lv_i + LUNCH
            arr_j = lun_e + d_ij
            lv_j = arr_j + l_comf[j]
            back = lv_j + dist[j + 1, 0]
            feas_ij = (
                arr_i >= open_h[i] and lv_i <= close_h[i] and
                arr_j >= open_h[j] and lv_j <= close_h[j] and
                back <= 21.0 and
                (back - TAU_DEP) <= T_SCENIC_MAX + 1e-6
            )
            # 检测同日可行（顺序 j→i）
            arr_j2 = TAU_DEP + dist[0, j + 1]
            lv_j2 = arr_j2 + l_comf[j]
            lun_e2 = lv_j2 + LUNCH
            arr_i2 = lun_e2 + d_ij
            lv_i2 = arr_i2 + l_comf[i]
            back2 = lv_i2 + dist[i + 1, 0]
            feas_ji = (
                arr_j2 >= open_h[j] and lv_j2 <= close_h[j] and
                arr_i2 >= open_h[i] and lv_i2 <= close_h[i] and
                back2 <= 21.0 and
                (back2 - TAU_DEP) <= T_SCENIC_MAX + 1e-6
            )
            feasible = bool(feas_ij or feas_ji)
            rows.append({
                "pair": f"{ids[i]}-{ids[j]}",
                "D_ij": float(d_ij),
                "Link_ij": float(link),
                "feasible_one_day": feasible,
                "combined_type": f"{p_type[i]}+{p_type[j]}",
            })
    return pd.DataFrame(rows).sort_values("Link_ij", ascending=False).reset_index(drop=True)


# ---------- 优先级池 ----------
def build_priority_pool(ranking: pd.DataFrame) -> pd.DataFrame:
    """根据 tier 字段输出高/中/低优先级景点池。"""

    def role(tier: str) -> str:
        return {"high": "必选", "mid": "推荐", "low": "备选"}[tier]

    df = ranking[["tier", "id", "P_i"]].copy()
    df["recommend_role"] = df["tier"].map(role)
    # 重排顺序：high → mid → low，组内按 P_i 降序
    tier_order = {"high": 0, "mid": 1, "low": 2}
    df["__order"] = df["tier"].map(tier_order)
    df = df.sort_values(["__order", "P_i"], ascending=[True, False]).drop(columns="__order")
    return df.reset_index(drop=True)


# ---------- 绘图 ----------
def plot_priority_ranking(ranking: pd.DataFrame, out_path: Path) -> None:
    """绘制综合优先级排序条形图（含分项贡献堆叠）。"""
    df = ranking.copy()
    fig, ax = plt.subplots(figsize=(10, 6))

    components = [
        ("S_i", W_P[0], "#4C72B0", "S (preference)"),
        ("D_i_comm", W_P[1], "#55A868", "D_comm (commute)"),
        ("L_i", W_P[2], "#C44E52", "L (duration fit)"),
        ("one_minus_C_i", W_P[3], "#8172B2", "1-C (anti-congestion)"),
    ]

    bottom = np.zeros(len(df))
    x = np.arange(len(df))
    for col, w, color, label in components:
        contrib = df[col].to_numpy() * w
        ax.bar(x, contrib, bottom=bottom, color=color, label=label, edgecolor="white", linewidth=0.5)
        bottom += contrib

    # 在柱顶标注 P_i 和 tier
    for k, (xi, pi, tier) in enumerate(zip(x, df["P_i"], df["tier"])):
        marker = {"high": "★", "mid": "●", "low": "○"}[tier]
        ax.text(xi, pi + 0.005, f"{marker}\n{pi:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(df["id"], rotation=0)
    ax.set_ylabel("Priority score P_i (stacked)")
    ax.set_title("Problem 1 — Attraction Priority Ranking\n(★ high  ● mid  ○ low)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_ylim(0, max(df["P_i"]) * 1.18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------- 主流程 ----------
def run(verbose: bool = True) -> dict:
    """执行问题一全部流程：评分、排序、导出表与图。

    返回 dict，含 weights、5 张表的内容，便于上层调用与日志记录。
    """
    log_path = OUT_LOGS / "solve_p1.log"
    logger = logging.getLogger("solve_p1")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.info("== solve_p1.py START ==")

    attractions, dist = load_data()
    logger.info("Loaded attractions (n=%d) and dist matrix %s",
                len(attractions), dist.shape)

    four_dim = compute_four_dim(attractions, dist)
    ranking = compute_priority(four_dim)
    type_tbl = build_type_table(attractions)
    combos = build_combo_pairs(attractions, dist, threshold=0.5)
    pool = build_priority_pool(ranking)

    # 保存 CSV
    type_tbl.to_csv(OUT_TABLES / "p1_type_classification.csv", index=False, encoding="utf-8-sig")
    four_dim_out = four_dim[
        ["id", "S_i", "L_i", "D_i_comm", "C_i", "C_1i", "C_2i", "C_3i", "C_4i"]
    ]
    four_dim_out.to_csv(OUT_TABLES / "p2_four_dim_scores.csv", index=False, encoding="utf-8-sig")
    ranking[["rank", "id", "P_i", "S_i", "L_i", "D_i_comm", "one_minus_C_i", "tier"]].to_csv(
        OUT_TABLES / "p3_priority_ranking.csv", index=False, encoding="utf-8-sig"
    )
    combos.to_csv(OUT_TABLES / "p4_combo_pairs.csv", index=False, encoding="utf-8-sig")
    pool.to_csv(OUT_TABLES / "p5_priority_pool.csv", index=False, encoding="utf-8-sig")

    # 汇总 JSON
    result = {
        "weights_P": W_P.tolist(),
        "weights_C": W_C.tolist(),
        "type_classification": type_tbl.to_dict(orient="records"),
        "four_dim_scores": four_dim_out.round(6).to_dict(orient="records"),
        "priority_ranking": ranking[
            ["rank", "id", "P_i", "S_i", "L_i", "D_i_comm", "one_minus_C_i", "tier"]
        ].round(6).to_dict(orient="records"),
        "combo_pairs": combos.round(6).to_dict(orient="records"),
        "priority_pool": {
            "high": pool[pool["tier"] == "high"][["id", "P_i", "recommend_role"]].round(6).to_dict(orient="records"),
            "mid":  pool[pool["tier"] == "mid"][["id", "P_i", "recommend_role"]].round(6).to_dict(orient="records"),
            "low":  pool[pool["tier"] == "low"][["id", "P_i", "recommend_role"]].round(6).to_dict(orient="records"),
        },
    }
    with open(ROOT / "p1_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 绘图
    plot_priority_ranking(ranking, OUT_FIGURES / "fig_priority_ranking.png")

    if verbose:
        print("[P1] Priority ranking (top 5):")
        print(ranking.head(5)[["rank", "id", "P_i", "tier"]].to_string(index=False))
        print(f"[P1] Combo pairs found: {len(combos)}  (saved to {OUT_TABLES})")
        print(f"[P1] High tier: {[r['id'] for r in result['priority_pool']['high']]}")

    logger.info("Top 5: %s", ranking.head(5)["id"].tolist())
    logger.info("Combos: %d, High tier size: %d",
                len(combos), len(result["priority_pool"]["high"]))
    logger.info("== solve_p1.py END ==")
    return result


if __name__ == "__main__":
    run()
