"""target90_experiment.py - independent reliability-priority experiment.

This script does not modify the final v1.1.1 model outputs:
  - baseline_plan.json
  - reliability_report.json
  - output/diagnostics/diagnostic_report.json

It constructs an optional sixth plan, "target90", for Problem 3 discussion only.
All outputs are written under output/target90/.
"""
from __future__ import annotations

import heapq
import json
import math
from itertools import permutations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import solve_p3


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output" / "target90"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_COARSE = 1000
N_FINAL = 10000
TARGET_R = 0.9
TOP_K = 20
EPS = 1e-6

DAY_DEPART_CANDIDATES = [
    [11.5, 12.0, 12.5, 13.0, 13.5, 14.0],
    [8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 12.5, 13.0, 13.5],
    [8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 12.5, 13.0, 13.5],
    [8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 12.5, 13.0, 13.5],
    [8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 12.5, 13.0],
]

REASON_NONE = "none"
REASON_BACK_LATE = "back_late"
REASON_SHORT_VISIT = "insufficient_visit_time"
REASON_BOTH = "back_late_and_insufficient_visit"


def load_inputs():
    attractions = pd.read_csv(ROOT / "attractions.csv")
    D = np.loadtxt(ROOT / "dist.csv", delimiter=",")
    with open(ROOT / "baseline_plan.json", "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(ROOT / "reliability_report.json", "r", encoding="utf-8") as f:
        reliability = json.load(f)
    return attractions, D, baseline, reliability


def deterministic_day(spot: int, day: int, depart: float,
                      l_min: np.ndarray, o_op: np.ndarray,
                      o_cl: np.ndarray, D: np.ndarray) -> dict:
    arr = depart + float(D[0, spot + 1])
    visit_st = max(arr, float(o_op[spot]))
    actual_visit = max(0.0, min(float(l_min[spot]), float(o_cl[spot]) - visit_st))
    lv = visit_st + actual_visit
    lunch_st = lv
    lunch_ed = lunch_st + solve_p3.LUNCH
    back = lunch_ed + float(D[spot + 1, 0])
    back_max = solve_p3.TAU_BACK_MAX_K[day]
    feasible = (back <= back_max + EPS) and (actual_visit >= float(l_min[spot]) - EPS)
    return {
        "day": day + 1,
        "depart": depart,
        "spot_index": spot,
        "spot": f"A{spot + 1}",
        "arr": arr,
        "visit_st": visit_st,
        "actual_visit": actual_visit,
        "lv": lv,
        "lunch": [lunch_st, lunch_ed],
        "back": back,
        "back_max": back_max,
        "buffer": back_max - back,
        "drive": float(D[0, spot + 1] + D[spot + 1, 0]),
        "feasible": feasible,
    }


def simulate_day_target90(spot: int, day: int, depart: float,
                          road_on: bool, queue_on: bool,
                          l_min: np.ndarray, o_op: np.ndarray,
                          o_cl: np.ndarray, D: np.ndarray,
                          rng: np.random.Generator) -> dict:
    tau = depart
    w_go = solve_p3.sample_road(
        tau, solve_p3.P_PK_DEFAULT, solve_p3.P_OFF_DEFAULT, road_on, rng
    )
    tau += float(D[0, spot + 1]) + w_go
    arr = tau
    visit_st = max(arr, float(o_op[spot]))
    tau = visit_st
    queue = solve_p3.sample_queue(visit_st, queue_on, rng)
    tau += queue
    actual_visit = max(0.0, min(float(l_min[spot]), float(o_cl[spot]) - tau))
    tau += actual_visit
    lunch_st = tau
    tau += solve_p3.LUNCH
    w_back = solve_p3.sample_road(
        tau, solve_p3.P_PK_DEFAULT, solve_p3.P_OFF_DEFAULT, road_on, rng
    )
    tau += float(D[spot + 1, 0]) + w_back
    back = tau

    back_late = back > solve_p3.TAU_BACK_MAX_K[day] + EPS
    short_visit = actual_visit < float(l_min[spot]) - EPS
    if back_late and short_visit:
        reason = REASON_BOTH
    elif back_late:
        reason = REASON_BACK_LATE
    elif short_visit:
        reason = REASON_SHORT_VISIT
    else:
        reason = REASON_NONE

    return {
        "fail": reason != REASON_NONE,
        "reason": reason,
        "arr": arr,
        "visit_st": visit_st,
        "actual_visit": actual_visit,
        "back": back,
        "road_delay": w_go + w_back,
        "queue": queue,
    }


def evaluate_option(spot: int, day: int, depart: float, N: int, seed: int,
                    l_min: np.ndarray, o_op: np.ndarray,
                    o_cl: np.ndarray, D: np.ndarray) -> dict:
    rng = np.random.default_rng(seed)
    fail_count = 0
    reasons = {
        REASON_NONE: 0,
        REASON_BACK_LATE: 0,
        REASON_SHORT_VISIT: 0,
        REASON_BOTH: 0,
    }
    for _ in range(N):
        result = simulate_day_target90(
            spot, day, depart, True, True, l_min, o_op, o_cl, D, rng
        )
        reasons[result["reason"]] += 1
        if result["fail"]:
            fail_count += 1
    fail_rate = fail_count / N
    return {
        "spot": spot,
        "day": day,
        "depart": depart,
        "N": N,
        "success_rate": 1.0 - fail_rate,
        "fail_rate": fail_rate,
        "reason_counts": reasons,
    }


def precompute_best_day_options(attractions: pd.DataFrame, D: np.ndarray) -> tuple[dict, dict]:
    l_min = attractions["l_min"].to_numpy()
    o_op = attractions["open_hour"].to_numpy()
    o_cl = attractions["close_hour"].to_numpy()

    all_options = {}
    best_options = {}
    deterministic_checked = 0
    deterministic_feasible = 0

    for day in range(solve_p3.N_DAY):
        for spot in range(solve_p3.N_SPOT):
            feasible_options = []
            for depart_idx, depart in enumerate(DAY_DEPART_CANDIDATES[day]):
                deterministic_checked += 1
                det = deterministic_day(spot, day, depart, l_min, o_op, o_cl, D)
                if not det["feasible"]:
                    continue
                deterministic_feasible += 1
                seed = solve_p3.SEED + day * 10000 + spot * 100 + depart_idx
                coarse = evaluate_option(
                    spot, day, depart, N_COARSE, seed, l_min, o_op, o_cl, D
                )
                option = {
                    "day": day,
                    "spot": spot,
                    "depart": depart,
                    "deterministic": det,
                    "coarse": coarse,
                }
                feasible_options.append(option)
                all_options[(day, spot, depart)] = option

            if feasible_options:
                # Dominance pruning: for a fixed day and spot, the departure with the
                # highest estimated day success dominates lower-success departures in
                # one-spot-per-day plans.
                feasible_options.sort(
                    key=lambda x: (
                        x["coarse"]["success_rate"],
                        x["deterministic"]["buffer"],
                        -x["deterministic"]["drive"],
                    ),
                    reverse=True,
                )
                best_options[(day, spot)] = feasible_options[0]

    search_space = {
        "spot_combinations_10_choose_5": math.comb(10, 5),
        "spot_to_day_assignments_P_10_5": math.factorial(10) // math.factorial(5),
        "raw_departure_products_per_assignment": (
            len(DAY_DEPART_CANDIDATES[0])
            * len(DAY_DEPART_CANDIDATES[1])
            * len(DAY_DEPART_CANDIDATES[2])
            * len(DAY_DEPART_CANDIDATES[3])
            * len(DAY_DEPART_CANDIDATES[4])
        ),
        "raw_candidate_schedules": (
            (math.factorial(10) // math.factorial(5))
            * len(DAY_DEPART_CANDIDATES[0])
            * len(DAY_DEPART_CANDIDATES[1])
            * len(DAY_DEPART_CANDIDATES[2])
            * len(DAY_DEPART_CANDIDATES[3])
            * len(DAY_DEPART_CANDIDATES[4])
        ),
        "deterministic_day_options_checked": deterministic_checked,
        "deterministic_day_options_feasible": deterministic_feasible,
        "dominance_pruned_day_spot_options": len(best_options),
        "coarse_N": N_COARSE,
        "final_N": N_FINAL,
        "pruning_rules": [
            "Discard day-spot-depart options that are infeasible with no road delay and no queue.",
            "For each fixed (day, spot), keep the departure candidate with the highest N=1000 day success rate.",
            "Enumerate all distinct five-spot-to-five-day assignments using the retained day-spot options.",
        ],
    }
    return best_options, search_space


def enumerate_coarse_candidates(best_options: dict) -> list[dict]:
    heap: list[tuple[float, int, dict]] = []
    evaluated = 0

    for assignment in permutations(range(solve_p3.N_SPOT), solve_p3.N_DAY):
        opts = []
        feasible = True
        for day, spot in enumerate(assignment):
            opt = best_options.get((day, spot))
            if opt is None:
                feasible = False
                break
            opts.append(opt)
        if not feasible:
            continue

        evaluated += 1
        day_success = [opt["coarse"]["success_rate"] for opt in opts]
        R_est = float(np.prod(day_success))
        candidate = {
            "assignment": list(assignment),
            "spots": [f"A{s + 1}" for s in assignment],
            "departures": [opt["depart"] for opt in opts],
            "coarse_R": R_est,
            "coarse_P_fail": 1.0 - R_est,
            "coarse_day_fail": [opt["coarse"]["fail_rate"] for opt in opts],
            "coarse_day_success": day_success,
            "coarse_options": opts,
        }
        entry = (R_est, evaluated, candidate)
        if len(heap) < TOP_K:
            heapq.heappush(heap, entry)
        elif R_est > heap[0][0]:
            heapq.heapreplace(heap, entry)

    top = [item[2] for item in sorted(heap, key=lambda x: -x[0])]
    for cand in top:
        cand["coarse_candidates_evaluated"] = evaluated
    return top


def evaluate_plan_final(candidate: dict, attractions: pd.DataFrame, D: np.ndarray,
                        N: int = N_FINAL, seed: int = solve_p3.SEED) -> dict:
    l_min = attractions["l_min"].to_numpy()
    o_op = attractions["open_hour"].to_numpy()
    o_cl = attractions["close_hour"].to_numpy()
    rng = np.random.default_rng(seed)

    trip_fail_count = 0
    day_fail_counts = np.zeros(solve_p3.N_DAY, dtype=int)
    reason_counts = [
        {REASON_NONE: 0, REASON_BACK_LATE: 0, REASON_SHORT_VISIT: 0, REASON_BOTH: 0}
        for _ in range(solve_p3.N_DAY)
    ]

    for _ in range(N):
        trip_failed = False
        for day, spot in enumerate(candidate["assignment"]):
            depart = candidate["departures"][day]
            result = simulate_day_target90(
                spot, day, depart, True, True, l_min, o_op, o_cl, D, rng
            )
            reason_counts[day][result["reason"]] += 1
            if result["fail"]:
                day_fail_counts[day] += 1
                trip_failed = True
        if trip_failed:
            trip_fail_count += 1

    P_fail = trip_fail_count / N
    R = 1.0 - P_fail
    ci = 1.96 * math.sqrt(P_fail * (1.0 - P_fail) / N)

    deterministic_days = []
    for day, spot in enumerate(candidate["assignment"]):
        det = deterministic_day(
            spot, day, candidate["departures"][day],
            l_min, o_op, o_cl, D,
        )
        deterministic_days.append({
            "day": day + 1,
            "spot": det["spot"],
            "depart": det["depart"],
            "arr": det["arr"],
            "visit_st": det["visit_st"],
            "actual_visit": det["actual_visit"],
            "lv": det["lv"],
            "lunch": det["lunch"],
            "back": det["back"],
            "back_max": det["back_max"],
            "buffer": det["buffer"],
            "drive": det["drive"],
        })

    per_day_success = []
    per_day_fail = []
    main_failure_reasons = []
    for day in range(solve_p3.N_DAY):
        fail_rate = day_fail_counts[day] / N
        per_day_fail.append(float(fail_rate))
        per_day_success.append(float(1.0 - fail_rate))
        non_none = {k: v for k, v in reason_counts[day].items() if k != REASON_NONE}
        main_reason = REASON_NONE
        if sum(non_none.values()) > 0:
            main_reason = max(non_none.items(), key=lambda item: item[1])[0]
        main_failure_reasons.append(main_reason)

    return {
        "plan_name": "target90",
        "selected": [f"A{s + 1}" for s in candidate["assignment"]],
        "departures": candidate["departures"],
        "days": deterministic_days,
        "R": float(R),
        "P_fail": float(P_fail),
        "CI_95": float(ci),
        "per_day_success": per_day_success,
        "per_day_fail": per_day_fail,
        "main_failure_reasons": main_failure_reasons,
        "failure_reason_counts": reason_counts,
        "N": N,
        "seed": seed,
        "coarse_R": candidate["coarse_R"],
        "coarse_P_fail": candidate["coarse_P_fail"],
    }


def plot_comparison(existing: dict, best_plan: dict) -> None:
    names = ["recommend", "balanced", "robust", "target90"]
    R_values = [
        existing["recommend"]["R"],
        existing["balanced"]["R"],
        existing["robust"]["R"],
        best_plan["R"],
    ]
    ci_values = [
        existing["recommend"].get("CI_95", 0.0),
        existing["balanced"].get("CI_95", 0.0),
        existing["robust"].get("CI_95", 0.0),
        best_plan["CI_95"],
    ]

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    x = np.arange(len(names))
    bars = ax.bar(x, R_values, yerr=ci_values, capsize=4, color=["#4C72B0", "#55A868", "#DD8452", "#8172B2"],
                  edgecolor="black", linewidth=0.6)
    ax.axhline(TARGET_R, color="#C44E52", linestyle="--", linewidth=1.4, label="target R=0.9")
    for bar, value in zip(bars, R_values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.01, f"{value:.3f}",
                ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Reliability R")
    ax.set_title("Target90 reliability comparison")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "fig_target90_comparison.png", dpi=150)
    plt.close(fig)


def make_markdown(report: dict) -> str:
    best = report["best_plan"]
    first = report["first_target_met_plan"]
    existing = report["comparison_with_existing"]
    lines = [
        "# target90 可靠性优先备用方案实验",
        "",
        "本实验为独立补充实验，不替代问题二五套方案，不覆盖 `baseline_plan.json` 或 `reliability_report.json`。",
        "",
        "## 1. 与前五套方案的区别",
        "",
        "`target90` 是问题三可靠性优先备用方案。前五套方案基于问题二的确定性多目标排序；`target90` 允许重新选择 5 个景点、每天 1 个景点，并枚举给定出发时间候选，以最大化五日整体可靠度 `R=P(5天全部成功)`。",
        "",
        "## 2. 保持不变的条件",
        "",
        "- v1.1.1 Day1 / Day5 边界不变：Day1 最早 11.5，Day5 最迟 16.5 回酒店。",
        "- `p_peak=0.6`、`p_off=0.3` 不变。",
        "- 道路堵车为额外延时，排队分布不变。",
        "- `visit_st=max(arr, open_hour)` 不变。",
        "- 失败事件不变：`back > back_max[k]` 或任一景点实际游览时长 `< l_min`。",
        "- 五天整体可靠度定义不变，任一日失败则整次失败。",
        "",
        "## 3. 搜索空间与剪枝",
        "",
        f"- 原始景点组合数：{report['search_space']['spot_combinations_10_choose_5']}",
        f"- 5 个不同景点到 5 天的排列数：{report['search_space']['spot_to_day_assignments_P_10_5']}",
        f"- 每个排列的出发时间组合数：{report['search_space']['raw_departure_products_per_assignment']}",
        f"- 原始候选日程数：{report['search_space']['raw_candidate_schedules']}",
        f"- 确定性日选项检查数：{report['search_space']['deterministic_day_options_checked']}",
        f"- 确定性可行日选项数：{report['search_space']['deterministic_day_options_feasible']}",
        f"- 保留的 day-spot 优势选项数：{report['search_space']['dominance_pruned_day_spot_options']}",
        "",
        "剪枝规则：先剔除无扰动确定性不可行的日选项；对同一 `(day, spot)`，保留 `N=1000` 粗模拟下日成功率最高的出发时间。由于本实验限定每天 1 个景点，较低日成功率的同日同景点出发时间不会提高五天同时成功概率。",
        "",
        "## 4. 最优 target90 结果",
        "",
        f"- 是否找到 `R>=0.9` 方案：{report['target_met']}",
        f"- 最高 R：{best['R']:.4f}",
        f"- P_fail：{best['P_fail']:.4f}",
        f"- CI_95 半宽：{best['CI_95']:.4f}",
        f"- 选中景点：{','.join(best['selected'])}",
        "",
        "| day | spot | depart | back | back_max | buffer | fail_rate | main reason |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for day in best["days"]:
        idx = day["day"] - 1
        lines.append(
            f"| {day['day']} | {day['spot']} | {day['depart']:.1f} | "
            f"{day['back']:.2f} | {day['back_max']:.1f} | {day['buffer']:.2f} | "
            f"{best['per_day_fail'][idx]:.4f} | {best['main_failure_reasons'][idx]} |"
        )

    lines.extend([
        "",
        "## 5. 与现有方案对比",
        "",
        "| plan | R | P_fail | CI_95 |",
        "|---|---:|---:|---:|",
        f"| recommend | {existing['recommend']['R']:.4f} | {existing['recommend']['P_fail']:.4f} | {existing['recommend']['CI_95']:.4f} |",
        f"| balanced | {existing['balanced']['R']:.4f} | {existing['balanced']['P_fail']:.4f} | {existing['balanced']['CI_95']:.4f} |",
        f"| robust | {existing['robust']['R']:.4f} | {existing['robust']['P_fail']:.4f} | {existing['robust']['CI_95']:.4f} |",
        f"| target90 | {best['R']:.4f} | {best['P_fail']:.4f} | {best['CI_95']:.4f} |",
        "",
    ])

    if first:
        lines.extend([
            "## 6. R>=0.9 的解释",
            "",
            "本实验若达到 `R>=0.9`，原因不是事后调参：堵车概率、排队分布、失败标准和 Day1/Day5 边界均保持不变；变化仅来自题目允许的可靠性优先重设计，即减少景点数量、每天只安排一个景点，并在给定候选集合内选择出发时间。",
            "",
        ])
    else:
        lines.extend([
            "## 6. 未达到 R>=0.9 的解释",
            "",
            "本实验在更保守的可靠性优先重设计下仍未达到 `R>=0.9`，说明在默认强扰动假设 `p_peak=0.6, p_off=0.3` 下，90% 整体可靠度要求偏紧。主要瓶颈来自五天串联系统：任一日失败即全程失败，因此即使单日风险下降，五日同时成功概率仍会被显著压低。",
            "",
        ])

    lines.extend([
        "## 7. 可直接放入论文的问题三解释段落",
        "",
        report["explanation"],
        "",
    ])
    return "\n".join(lines)


def main() -> dict:
    attractions, D, baseline, reliability = load_inputs()
    best_options, search_space = precompute_best_day_options(attractions, D)
    top20 = enumerate_coarse_candidates(best_options)
    search_space["coarse_candidates_evaluated"] = top20[0]["coarse_candidates_evaluated"] if top20 else 0
    search_space["coarse_top_k_retained"] = len(top20)

    final_evals = [
        evaluate_plan_final(candidate, attractions, D, N_FINAL, solve_p3.SEED)
        for candidate in top20
    ]
    final_evals.sort(key=lambda item: item["R"], reverse=True)
    best_plan = final_evals[0]
    first_target_met = next((item for item in final_evals if item["R"] >= TARGET_R), None)

    existing = {
        name: {
            "R": reliability["compared_plans"][name]["R"],
            "P_fail": reliability["compared_plans"][name]["P_fail"],
            "CI_95": reliability["compared_plans"][name]["CI_95"],
            "Z4": reliability["compared_plans"][name]["Z4"],
        }
        for name in ("recommend", "balanced", "robust")
    }
    existing["target90"] = {
        "R": best_plan["R"],
        "P_fail": best_plan["P_fail"],
        "CI_95": best_plan["CI_95"],
    }

    improvement_vs_recommend = best_plan["R"] - existing["recommend"]["R"]
    improvement_vs_robust = best_plan["R"] - existing["robust"]["R"]
    target_met = first_target_met is not None

    if target_met:
        explanation = (
            "target90 在不改变堵车概率、排队分布、失败标准和 Day1/Day5 边界的前提下达到 R>=0.9。"
            "其原因是方案定位从确定性多目标游览优化转为可靠性优先备用方案：总景点数收缩为 5 个、每天仅安排 1 个景点，"
            "并在给定出发时间候选内避开高风险时间窗。这属于出行策略重设计，而不是事后调参。"
        )
    else:
        bottleneck_day = int(np.argmax(best_plan["per_day_fail"])) + 1
        bottleneck_reason = best_plan["main_failure_reasons"][bottleneck_day - 1]
        explanation = (
            f"target90 在保留原始扰动假设和失败标准的情况下，最高 R={best_plan['R']:.4f}，仍未达到 0.9。"
            f"主要瓶颈为 Day{bottleneck_day} 的 {bottleneck_reason}。"
            "这说明在 p_peak=0.6、p_off=0.3 的强扰动假设下，即使采用 5 景点、单景点日和出发时间重设计，"
            "五天整体可靠度达到 90% 仍偏紧。"
        )

    report = {
        "assumptions": {
            "experiment": "target90 independent reliability-priority backup plan",
            "does_not_replace_existing_profiles": True,
            "N_coarse": N_COARSE,
            "N_final": N_FINAL,
            "seed": solve_p3.SEED,
            "p_peak": solve_p3.P_PK_DEFAULT,
            "p_off": solve_p3.P_OFF_DEFAULT,
            "tau_back_max_per_day": solve_p3.TAU_BACK_MAX_K,
            "day_depart_candidates": DAY_DEPART_CANDIDATES,
            "failure_rule": "back > back_max[k] or actual_visit_time < l_min",
            "visit_duration_for_target90": "l_min",
            "early_arrival_handling": "visit_st=max(arr, open_hour)",
            "trip_reliability_definition": "P(all five days succeed)",
        },
        "search_space": search_space,
        "best_plan": best_plan,
        "first_target_met_plan": first_target_met,
        "target_met": target_met,
        "comparison_with_existing": existing,
        "per_day_success": best_plan["per_day_success"],
        "per_day_fail": best_plan["per_day_fail"],
        "main_failure_reasons": best_plan["main_failure_reasons"],
        "CI_95": best_plan["CI_95"],
        "improvement_vs_recommend": improvement_vs_recommend,
        "improvement_vs_robust": improvement_vs_robust,
        "top20_final": final_evals,
        "explanation": explanation,
    }

    with open(OUT_DIR / "target90_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(OUT_DIR / "target90_best_plan.json", "w", encoding="utf-8") as f:
        json.dump(best_plan, f, ensure_ascii=False, indent=2)
    with open(OUT_DIR / "target90_report.md", "w", encoding="utf-8") as f:
        f.write(make_markdown(report))
    plot_comparison(existing, best_plan)

    print(f"[target90] target_met={target_met}")
    print(f"[target90] best R={best_plan['R']:.4f} P_fail={best_plan['P_fail']:.4f}")
    print(f"[target90] selected={best_plan['selected']}")
    print(f"[target90] wrote {OUT_DIR}")
    return report


if __name__ == "__main__":
    main()
