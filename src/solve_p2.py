"""solve_p2.py — 问题二：基准行程与多套备选方案（枚举法）

按 model_spec_v1.0 + v1.1 + v1.1.1 实现：
  - 决策变量 x_i, z_{k,i}, y_{k,i,j}；t_i = l_i^comf 固定
  - day-specific 时间边界：Day1 11:30 出发，Day5 16:30 前回酒店
  - 早到景区允许等待开门：visit_st = max(arr, open_hour)
  - 午餐 1.0h 插入首个景点游览结束后、下一段通勤前
  - 5 套偏好（含 robust）共享归一化基准

【枚举说明】
  v1.1.1 后 Day1 / Day5 活动窗不同，天数标号会影响可行性与 Z4。
  因此必须枚举 day-labeled 方案，不能复用无标签单日方案池。
"""
from __future__ import annotations

import heapq
import json
import logging
import time
from itertools import combinations
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

plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 模型常量 ----------
N_SPOT = 10
N_DAY = 5
LUNCH = 1.0
MORNING = 1.5
TAU_DEP_K = [11.5, 8.5, 8.5, 8.5, 8.5]
TAU_BACK_MAX_K = [21.0, 21.0, 21.0, 21.0, 16.5]
T_SCENIC_MAX_K = [tb - td for tb, td in zip(TAU_BACK_MAX_K, TAU_DEP_K)]

PREF_PROFILES = {
    "recommend":   (0.6, 0.2, 0.2, 0.0),
    "preference":  (0.8, 0.1, 0.1, 0.0),
    "low_commute": (0.4, 0.4, 0.2, 0.0),
    "balanced":    (0.4, 0.2, 0.4, 0.0),
    "robust":      (0.4, 0.2, 0.2, 0.2),
}

EPS = 1e-6


# ---------- 数据装载 ----------
def load_data(root: Path = ROOT):
    """读取 attractions.csv 与 dist.csv。"""
    attractions = pd.read_csv(root / "attractions.csv")
    s = attractions["score"].to_numpy()
    l_min = attractions["l_min"].to_numpy()
    l_comf = attractions["l_comf"].to_numpy()
    o_op = attractions["open_hour"].to_numpy()
    o_cl = attractions["close_hour"].to_numpy()
    D = np.loadtxt(root / "dist.csv", delimiter=",")
    assert D.shape == (11, 11)
    return s, l_min, l_comf, o_op, o_cl, D, attractions


# ---------- 单日方案构建 ----------
def build_day(spots: tuple, k: int, l_comf: np.ndarray, o_op: np.ndarray,
              o_cl: np.ndarray, D: np.ndarray) -> dict:
    """根据 spots（1 个或 2 个景点，有序）构建单日方案。

    遵循 §3.3 时间轴：午餐 1.0h 插入首个景点游览结束后、下一段通勤前。

    返回 dict：spots, T_sc, T_dr, feas, tl
        - T_sc：景区内总耗时 = tau_back - tau_dep_k
        - T_dr：当日总车程
        - feas：是否满足开放时间 + day-specific 活动窗
        - tl：时间轴 dict
    """
    tau_dep = TAU_DEP_K[k]
    tau_back_max = TAU_BACK_MAX_K[k]
    t_scenic_max = T_SCENIC_MAX_K[k]

    if len(spots) == 1:
        i = spots[0]
        arr_i = tau_dep + D[0, i + 1]
        visit_st_i = max(arr_i, o_op[i])
        lv_i = visit_st_i + l_comf[i]
        lun_s = lv_i
        lun_e = lun_s + LUNCH
        back = lun_e + D[i + 1, 0]
        feas = (
            lv_i <= o_cl[i] + EPS
            and back <= tau_back_max + EPS
        )
        T_sc = back - tau_dep
        T_dr = float(D[0, i + 1] + D[i + 1, 0])
        tl = {"seq": [f"A{i + 1}"], "arr": [arr_i],
              "visit_st": [visit_st_i], "lv": [lv_i],
              "lunch": [lun_s, lun_e], "back": back}
    elif len(spots) == 2:
        i, j = spots
        arr_i = tau_dep + D[0, i + 1]
        visit_st_i = max(arr_i, o_op[i])
        lv_i = visit_st_i + l_comf[i]
        lun_s = lv_i
        lun_e = lun_s + LUNCH
        arr_j = lun_e + D[i + 1, j + 1]
        visit_st_j = max(arr_j, o_op[j])
        lv_j = visit_st_j + l_comf[j]
        back = lv_j + D[j + 1, 0]
        feas = (
            lv_i <= o_cl[i] + EPS
            and lv_j <= o_cl[j] + EPS
            and back <= tau_back_max + EPS
        )
        T_sc = back - tau_dep
        T_dr = float(D[0, i + 1] + D[i + 1, j + 1] + D[j + 1, 0])
        tl = {"seq": [f"A{i + 1}", f"A{j + 1}"], "arr": [arr_i, arr_j],
              "visit_st": [visit_st_i, visit_st_j], "lv": [lv_i, lv_j],
              "lunch": [lun_s, lun_e], "back": back}
    else:
        raise ValueError("spots must have 1 or 2 elements")
    feas = bool(feas and T_sc <= t_scenic_max + EPS)
    return {"spots": spots, "T_sc": float(T_sc), "T_dr": T_dr,
            "feas": feas, "tl": tl}


# ---------- 单/双景点日预过滤 ----------
def feasibility_cache(l_comf, o_op, o_cl, D):
    """按天为所有单点、所有景点对（双向）预计算 build_day 结果。

    返回：
        single_opt[k][i]      = build_day 结果（None 若不可行）
        pair_opt[k][(i,j)]    = build_day((i,j)) 结果（None 若不可行）；保留双向
    """
    single_opt = [{ } for _ in range(N_DAY)]
    pair_opt = [{ } for _ in range(N_DAY)]
    for k in range(N_DAY):
        for i in range(N_SPOT):
            d = build_day((i,), k, l_comf, o_op, o_cl, D)
            single_opt[k][i] = d if d["feas"] else None
        for i in range(N_SPOT):
            for j in range(N_SPOT):
                if i == j:
                    continue
                d = build_day((i, j), k, l_comf, o_op, o_cl, D)
                pair_opt[k][(i, j)] = d if d["feas"] else None
    return single_opt, pair_opt


# ---------- day-labeled 分配枚举 ----------
def assign_labeled_days(S, single_opt, pair_opt):
    """把景点集合 S 分配到 5 个有标号的天。

    v1.1.1 中 Day1 / Day5 的边界不同，必须在递归时按 day k 选用
    该天自己的单日可行方案池。
    """
    target = frozenset(S)
    current = []

    def bt(day: int, remaining: frozenset):
        if day == N_DAY:
            if not remaining:
                yield tuple(current)
            return

        days_left = N_DAY - day - 1

        # 单景点日
        for i in sorted(remaining):
            rem_after = remaining - {i}
            if not (days_left <= len(rem_after) <= 2 * days_left):
                continue
            opt = single_opt[day].get(i)
            if opt is None:
                continue
            current.append(opt)
            yield from bt(day + 1, frozenset(rem_after))
            current.pop()

        # 双景点日，内部顺序有意义
        rem_sorted = sorted(remaining)
        for i in rem_sorted:
            for j in rem_sorted:
                if i == j:
                    continue
                rem_after = remaining - {i, j}
                if not (days_left <= len(rem_after) <= 2 * days_left):
                    continue
                opt = pair_opt[day].get((i, j))
                if opt is None:
                    continue
                current.append(opt)
                yield from bt(day + 1, frozenset(rem_after))
                current.pop()

    yield from bt(0, target)


def enumerate_all(s, l_comf, o_op, o_cl, D, logger=None):
    """枚举所有可行 5 天行程方案（day-labeled）。

    每个 cand 保存：
        S          : frozenset(int)
        opts       : tuple of day-option dicts （5 个，顺序即 day1..day5）
        Z1, Z2, Z3, Z4 : float
        Tks        : list of T_scenic
    """
    single_opt, pair_opt = feasibility_cache(l_comf, o_op, o_cl, D)
    cands = []
    t0 = time.time()

    for size in (5, 6, 7, 8):
        size_cnt = 0
        for S in combinations(range(N_SPOT), size):
            for day_opts in assign_labeled_days(S, single_opt, pair_opt):
                Z1 = float(sum(s[i] for i in S))
                Z2 = float(sum(d["T_dr"] for d in day_opts))
                Tks = [d["T_sc"] for d in day_opts]
                Tbar = sum(Tks) / N_DAY
                Z3 = float(sum((t - Tbar) ** 2 for t in Tks) / N_DAY)
                buffers = [T_SCENIC_MAX_K[k] - Tks[k] for k in range(N_DAY)]
                Z4 = float(min(buffers))
                Z4_mean = float(sum(buffers) / N_DAY)
                cands.append({
                    "S": frozenset(S),
                    "opts": day_opts,
                    "Z1": Z1, "Z2": Z2, "Z3": Z3,
                    "Z4": Z4, "Z4_mean": Z4_mean,
                    "Tks": Tks,
                })
                size_cnt += 1

        if logger:
            logger.info("size=%d feasible plans = %d (cum=%d, %.2fs)",
                        size, size_cnt, len(cands), time.time() - t0)
    return cands


# ---------- 归一化 + 多套备选 ----------
def normalize_and_rank(cands, profiles=PREF_PROFILES, top_n=5):
    """共享归一化基准，对每套权重做 top_n 选择。"""
    Z1s = np.array([c["Z1"] for c in cands])
    Z2s = np.array([c["Z2"] for c in cands])
    Z3s = np.array([c["Z3"] for c in cands])
    Z4s = np.array([c["Z4"] for c in cands])

    Z1lo, Z1hi = float(Z1s.min()), float(Z1s.max())
    Z2lo, Z2hi = float(Z2s.min()), float(Z2s.max())
    Z3lo, Z3hi = float(Z3s.min()), float(Z3s.max())
    Z4lo, Z4hi = float(Z4s.min()), float(Z4s.max())

    for c in cands:
        c["z1n"] = (c["Z1"] - Z1lo) / (Z1hi - Z1lo + 1e-12)
        c["z2n"] = (Z2hi - c["Z2"]) / (Z2hi - Z2lo + 1e-12)
        c["z3n"] = (Z3hi - c["Z3"]) / (Z3hi - Z3lo + 1e-12)
        c["z4n"] = (c["Z4"] - Z4lo) / (Z4hi - Z4lo + 1e-12)

    ranked = {}
    for name, lam in profiles.items():
        # 用堆维护 top_n（小顶堆，键=F；超过 top_n 时弹出最小）
        heap: list[tuple] = []
        for idx, c in enumerate(cands):
            F = (
                lam[0] * c["z1n"]
                + lam[1] * c["z2n"]
                + lam[2] * c["z3n"]
                + lam[3] * c["z4n"]
            )
            if len(heap) < top_n:
                heapq.heappush(heap, (F, idx))
            else:
                if F > heap[0][0]:
                    heapq.heapreplace(heap, (F, idx))
        # 取出按 F 降序
        sorted_top = sorted(heap, key=lambda kv: -kv[0])
        top_plans = [export_plan(cands[idx], lam, F) for F, idx in sorted_top]
        ranked[name] = {"lambda": list(lam), "top": top_plans}

    norm_basis = {
        "Z1_min": Z1lo, "Z1_max": Z1hi,
        "Z2_min": Z2lo, "Z2_max": Z2hi,
        "Z3_min": Z3lo, "Z3_max": Z3hi,
        "Z4_min": Z4lo, "Z4_max": Z4hi,
    }
    return ranked, norm_basis


def export_plan(c, lam, F):
    """把 cand 转成最终 JSON 输出 dict。"""
    ordered = c["opts"]
    days = []
    Tks_ordered = []
    for k, opt in enumerate(ordered):
        Tks_ordered.append(opt["T_sc"])
        buffer_k = T_SCENIC_MAX_K[k] - opt["T_sc"]
        days.append({
            "day": k + 1,
            "depart": TAU_DEP_K[k],
            "T_scenic_max": T_SCENIC_MAX_K[k],
            "back_max": TAU_BACK_MAX_K[k],
            "buffer": float(buffer_k),
            "seq": opt["tl"]["seq"],
            "arr": [float(x) for x in opt["tl"]["arr"]],
            "visit_st": [float(x) for x in opt["tl"]["visit_st"]],
            "lv":  [float(x) for x in opt["tl"]["lv"]],
            "lunch": [float(opt["tl"]["lunch"][0]), float(opt["tl"]["lunch"][1])],
            "back": float(opt["tl"]["back"]),
            "T_scenic": float(opt["T_sc"]),
            "drive": float(opt["T_dr"]),
        })
    return {
        "selected": sorted([f"A{i + 1}" for i in c["S"]]),
        "Z1": float(c["Z1"]), "Z2": float(c["Z2"]),
        "Z3": float(c["Z3"]), "Z4": float(c["Z4"]),
        "Z4_mean": float(c["Z4_mean"]),
        "Z1_norm": float(c["z1n"]),
        "Z2_norm": float(c["z2n"]),
        "Z3_norm": float(c["z3n"]),
        "Z4_norm": float(c["z4n"]),
        "F": float(F),
        "lambda": list(lam),
        "Tks": [float(t) for t in Tks_ordered],
        "buffers": [float(T_SCENIC_MAX_K[k] - t) for k, t in enumerate(Tks_ordered)],
        "days": days,
    }


# ---------- 绘图 ----------
def plot_profile_comparison(ranked, out_path: Path) -> None:
    """5 套偏好下 top-1 方案的归一化目标与 F 对比图。"""
    names = list(ranked.keys())
    z1 = [ranked[n]["top"][0]["Z1_norm"] for n in names]
    z2 = [ranked[n]["top"][0]["Z2_norm"] for n in names]
    z3 = [ranked[n]["top"][0]["Z3_norm"] for n in names]
    z4 = [ranked[n]["top"][0]["Z4_norm"] for n in names]
    F  = [ranked[n]["top"][0]["F"] for n in names]

    fig, ax = plt.subplots(figsize=(11, 5.8))
    x = np.arange(len(names))
    w = 0.16
    ax.bar(x - 2 * w, z1, w, label="Z1_norm (preference)", color="#4C72B0")
    ax.bar(x - 1 * w, z2, w, label="Z2_norm (low commute)", color="#55A868")
    ax.bar(x, z3, w, label="Z3_norm (day balance)", color="#C44E52")
    ax.bar(x + 1 * w, z4, w, label="Z4_norm (buffer)", color="#DD8452")
    ax.bar(x + 2 * w, F,  w, label="F (composite)", color="#8172B2",
           edgecolor="black", linewidth=1.0)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\nλ={tuple(ranked[n]['lambda'])}" for n in names],
                       fontsize=9)
    ax.set_ylabel("Normalized score")
    ax.set_title("Problem 2 — Top-1 plan comparison across 5 preference profiles")
    ax.set_ylim(0, max(1.05, max(F) * 1.15))
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------- 主流程 ----------
def run(verbose: bool = True) -> dict:
    """问题二完整流程：枚举 → 归一化 → 5 套方案排序 → 输出 JSON + 图。"""
    log_path = OUT_LOGS / "solve_p2.log"
    logger = logging.getLogger("solve_p2")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.info("== solve_p2.py START ==")

    s, l_min, l_comf, o_op, o_cl, D, _ = load_data()

    t0 = time.time()
    cands = enumerate_all(s, l_comf, o_op, o_cl, D, logger=logger)
    elapsed = time.time() - t0
    logger.info("Total feasible plans: %d  (%.2fs)", len(cands), elapsed)
    if verbose:
        print(f"[P2] enumerated {len(cands):,} feasible plans in {elapsed:.2f}s")
    assert cands, "No feasible plan found — check constraints"

    ranked, norm_basis = normalize_and_rank(cands, PREF_PROFILES, top_n=5)
    logger.info("Norm basis: %s", norm_basis)

    output = {
        "scope": "scenic_area_only",
        "boundary_v111": {
            "tau_dep_per_day": TAU_DEP_K,
            "tau_back_max_per_day": TAU_BACK_MAX_K,
            "T_scenic_max_per_day": T_SCENIC_MAX_K,
            "day1_rationale": "家 7:00 出发 + 4.0h 车程 + 0.5h 入住 = 11:30 开始景区活动",
            "day5_rationale": "16:30 回酒店 + 0.5h 离店整备/取车取行李 + 4.0h 返家 = 21:00 前到家",
        },
        "fixed_boundary_hours": {
            "home_to_hotel_one_way": 4.0,
            "checkin": 0.5,
            "checkout": 0.5,
            "morning_per_day": 1.5,
        },
        "constants": {
            "lunch_duration": LUNCH,
        },
        "norm_basis": norm_basis,
        "n_feasible_plans": len(cands),
        "profiles": ranked,
        "baseline_plan": ranked["recommend"]["top"][0],
    }
    with open(ROOT / "baseline_plan.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    plot_profile_comparison(ranked, OUT_FIGURES / "fig_profile_comparison.png")

    if verbose:
        for name in PREF_PROFILES:
            top1 = ranked[name]["top"][0]
            print(f"[P2] profile={name:12s} λ={tuple(PREF_PROFILES[name])}  "
                  f"F={top1['F']:.4f}  Z4={top1['Z4']:.3f}  selected={top1['selected']}")

    logger.info("baseline_plan.selected = %s",
                ranked["recommend"]["top"][0]["selected"])
    logger.info("baseline_plan.F = %.4f",
                ranked["recommend"]["top"][0]["F"])
    logger.info("== solve_p2.py END ==")
    return output


if __name__ == "__main__":
    run()
