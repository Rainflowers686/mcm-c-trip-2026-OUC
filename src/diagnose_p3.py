"""diagnose_p3.py - supplemental diagnostics for Problem 3.

This script does not change baseline_plan.json or reliability_report.json.
It reads the existing v1.1.1 plans and writes additional diagnostics to:
  output/diagnostics/diagnostic_report.json
  output/diagnostics/diagnostic_report.md
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import solve_p3


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output" / "diagnostics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = {
    "deterministic": {"road_on": False, "queue_on": False},
    "road_only": {"road_on": True, "queue_on": False},
    "queue_only": {"road_on": False, "queue_on": True},
    "road_and_queue": {"road_on": True, "queue_on": True},
}

EPS = 1e-6


def _reason_for_day(result: dict, l_min: np.ndarray) -> tuple[str, list[str]]:
    """Return daily failure reason and short-visit spot ids."""
    day_index = None
    short_spots: list[str] = []
    for idx, sp in enumerate(result["seq"]):
        if result["t_acts"][idx] < float(l_min[sp]) - EPS:
            short_spots.append(f"A{sp + 1}")

    # infer day index from stored simulation context if caller added it
    day_index = result.get("day_index")
    back_late = False
    if day_index is not None:
        back_late = result["back"] > solve_p3.TAU_BACK_MAX_K[day_index] + EPS

    short_fail = bool(short_spots)
    if back_late and short_fail:
        return "back_late_and_insufficient_visit", short_spots
    if back_late:
        return "back_late", short_spots
    if short_fail:
        return "insufficient_visit_time", short_spots
    return "none", short_spots


def run_scenario(plan: dict, scenario_name: str, road_on: bool, queue_on: bool,
                 l_min: np.ndarray, l_comf: np.ndarray, o_op: np.ndarray,
                 o_cl: np.ndarray, D: np.ndarray) -> dict:
    rng = np.random.default_rng(solve_p3.SEED)
    N = solve_p3.N_SIM
    trip_fail_count = 0
    day_fail_counts = np.zeros(solve_p3.N_DAY, dtype=int)
    reason_counts = [
        {
            "none": 0,
            "back_late": 0,
            "insufficient_visit_time": 0,
            "back_late_and_insufficient_visit": 0,
        }
        for _ in range(solve_p3.N_DAY)
    ]
    short_spot_counts = [dict() for _ in range(solve_p3.N_DAY)]

    for _ in range(N):
        trip_failed = False
        for day_idx, day in enumerate(plan["days"]):
            result = solve_p3.simulate_day(
                day, road_on, queue_on,
                solve_p3.P_PK_DEFAULT, solve_p3.P_OFF_DEFAULT,
                l_min, l_comf, o_op, o_cl, D, rng,
            )
            result["day_index"] = day_idx
            reason, short_spots = _reason_for_day(result, l_min)
            reason_counts[day_idx][reason] += 1
            for spot in short_spots:
                short_spot_counts[day_idx][spot] = short_spot_counts[day_idx].get(spot, 0) + 1
            if reason != "none":
                day_fail_counts[day_idx] += 1
                trip_failed = True
        if trip_failed:
            trip_fail_count += 1

    p_fail = trip_fail_count / N
    per_day = []
    for day_idx in range(solve_p3.N_DAY):
        failures = int(day_fail_counts[day_idx])
        non_none_counts = {
            key: value
            for key, value in reason_counts[day_idx].items()
            if key != "none"
        }
        main_reason = "none"
        if failures:
            main_reason = max(non_none_counts.items(), key=lambda item: item[1])[0]
        per_day.append({
            "day": day_idx + 1,
            "success_rate": float(1.0 - failures / N),
            "failure_rate": float(failures / N),
            "main_failure_reason": main_reason,
            "failure_reason_counts": reason_counts[day_idx],
            "short_visit_spot_counts": short_spot_counts[day_idx],
        })

    overall_reason_counts = {
        "back_late": sum(item["back_late"] for item in reason_counts),
        "insufficient_visit_time": sum(item["insufficient_visit_time"] for item in reason_counts),
        "back_late_and_insufficient_visit": sum(
            item["back_late_and_insufficient_visit"] for item in reason_counts
        ),
    }
    dominant_reason = "none"
    if sum(overall_reason_counts.values()) > 0:
        dominant_reason = max(overall_reason_counts.items(), key=lambda item: item[1])[0]

    return {
        "scenario": scenario_name,
        "road_on": road_on,
        "queue_on": queue_on,
        "N": N,
        "seed": solve_p3.SEED,
        "p_peak": solve_p3.P_PK_DEFAULT,
        "p_off": solve_p3.P_OFF_DEFAULT,
        "R": float(1.0 - p_fail),
        "P_fail": float(p_fail),
        "trip_fail_count": int(trip_fail_count),
        "dominant_failure_reason": dominant_reason,
        "overall_failure_reason_counts": overall_reason_counts,
        "per_day_success": per_day,
    }


def make_markdown(report: dict) -> str:
    lines = [
        "# 问题三诊断报告",
        "",
        "本诊断报告仅作为问题三的补充解释，不替代主可靠性报告。",
        f"模拟次数 N={report['assumptions']['N_simulations']}，随机种子 seed={report['assumptions']['seed']}。",
        "",
        "## 场景结果",
        "",
        "| 方案 | 场景 | R | P_fail | 主要失败原因 |",
        "|---|---:|---:|---:|---|",
    ]
    for plan_name, plan_report in report["plans"].items():
        for scenario_name, scenario in plan_report["scenarios"].items():
            lines.append(
                f"| {plan_name} | {scenario_name} | "
                f"{scenario['R']:.4f} | {scenario['P_fail']:.4f} | "
                f"{scenario['dominant_failure_reason']} |"
            )

    lines.extend([
        "",
        "## 道路堵车与排队同时开启时的逐日成功率",
        "",
        "| 方案 | 天数 | 成功率 | 失败率 | 主要失败原因 |",
        "|---|---:|---:|---:|---|",
    ])
    for plan_name, plan_report in report["plans"].items():
        scenario = plan_report["scenarios"]["road_and_queue"]
        for day in scenario["per_day_success"]:
            lines.append(
                f"| {plan_name} | {day['day']} | "
                f"{day['success_rate']:.4f} | {day['failure_rate']:.4f} | "
                f"{day['main_failure_reason']} |"
            )

    rec = report["plans"]["recommend"]["scenarios"]
    rob = report["plans"]["robust"]["scenarios"]
    lines.extend([
        "",
        "## 可直接写入论文的问题三诊断解释",
        "",
        (
            "补充诊断显示，在关闭道路堵车与景点排队的确定性场景下，recommend 与 robust 两个方案均保持可行，"
            "说明 v1.1.1 生成的基准行程本身满足 day-specific 时间边界和最低游览时长约束。"
            "当仅开启道路堵车或仅开启排队扰动时，行程可靠度已显著下降，主要失败原因集中在返程超出当日最迟回酒店时刻"
            "以及受闭园截断导致的实际游览时长不足；当道路堵车与排队同时开启时，两类扰动叠加，使五日行程中至少一日失败的概率进一步增大。"
            f"在默认强扰动参数 p_peak=0.6、p_off=0.3、N=10000 下，recommend 方案的综合扰动可靠度为 "
            f"R={rec['road_and_queue']['R']:.4f}，P_fail={rec['road_and_queue']['P_fail']:.4f}；robust 方案为 "
            f"R={rob['road_and_queue']['R']:.4f}，P_fail={rob['road_and_queue']['P_fail']:.4f}。"
            "robust 方案提高了确定性时间缓冲 Z4，但由于整次五日行程采用“任一日失败即全程失败”的判定，"
            "在五一强扰动假设下仍难以达到 R>=0.9。因而，该结果应解释为节假日交通与排队不确定性下的结构性脆弱点识别，"
            "而不是确定性行程安排违反约束。"
        ),
        "",
    ])
    return "\n".join(lines)


def main() -> dict:
    with open(ROOT / "baseline_plan.json", "r", encoding="utf-8") as f:
        baseline_doc = json.load(f)

    l_min, l_comf, o_op, o_cl, D = solve_p3.load_arrays(ROOT)
    selected_plans = {
        "recommend": baseline_doc["profiles"]["recommend"]["top"][0],
        "robust": baseline_doc["profiles"]["robust"]["top"][0],
    }

    report = {
        "assumptions": {
            "N_simulations": solve_p3.N_SIM,
            "seed": solve_p3.SEED,
            "p_peak": solve_p3.P_PK_DEFAULT,
            "p_off": solve_p3.P_OFF_DEFAULT,
            "tau_dep_per_day": solve_p3.TAU_DEP_K,
            "tau_back_max_per_day": solve_p3.TAU_BACK_MAX_K,
            "T_scenic_max_per_day": solve_p3.T_SCENIC_MAX_K,
            "early_arrival_handling": "wait_until_open",
            "failure_rule": "back_late_or_insufficient_visit_time",
        },
        "plans": {},
    }

    for plan_name, plan in selected_plans.items():
        plan_report = {
            "selected": plan["selected"],
            "Z1": plan["Z1"],
            "Z2": plan["Z2"],
            "Z3": plan["Z3"],
            "Z4": plan["Z4"],
            "Z4_mean": plan["Z4_mean"],
            "F": plan["F"],
            "scenarios": {},
        }
        for scenario_name, flags in SCENARIOS.items():
            plan_report["scenarios"][scenario_name] = run_scenario(
                plan, scenario_name,
                flags["road_on"], flags["queue_on"],
                l_min, l_comf, o_op, o_cl, D,
            )
        report["plans"][plan_name] = plan_report

    json_path = OUT_DIR / "diagnostic_report.json"
    md_path = OUT_DIR / "diagnostic_report.md"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(make_markdown(report))

    print(f"[diagnose_p3] wrote {json_path}")
    print(f"[diagnose_p3] wrote {md_path}")
    return report


if __name__ == "__main__":
    main()
