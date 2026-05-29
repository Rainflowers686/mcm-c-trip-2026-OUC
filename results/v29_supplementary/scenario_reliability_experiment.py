"""v2.9 supplementary scenario reliability experiment.

This script is intentionally placed under output/v29/ and writes only to that
directory. It does not modify the frozen main-result files.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "v29"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import solve_p3


SCENARIOS = [
    {"scenario": "low", "p_peak": 0.30, "p_off": 0.10},
    {"scenario": "mid", "p_peak": 0.45, "p_off": 0.20},
    {"scenario": "strong", "p_peak": 0.60, "p_off": 0.30},
]
PLAN_NAMES = ["recommend", "balanced", "robust", "target90"]
SEED = 2026
N_SIM = int(os.environ.get("V29_SCENARIO_N", "10000"))
TARGET_R = 0.90
EPS = 1e-6


def require_new(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json_new(path: Path, payload: dict) -> None:
    require_new(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_text_new(path: Path, text: str) -> None:
    require_new(path)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_csv_new(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    require_new(path)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_inputs() -> tuple[dict, dict, dict, tuple[np.ndarray, ...], pd.DataFrame]:
    with open(ROOT / "baseline_plan.json", "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(ROOT / "reliability_report.json", "r", encoding="utf-8") as f:
        reliability = json.load(f)
    with open(ROOT / "output" / "target90" / "target90_best_plan.json", "r", encoding="utf-8") as f:
        target90 = json.load(f)

    arrays = solve_p3.load_arrays(ROOT)
    attractions = pd.read_csv(ROOT / "attractions.csv")
    return baseline, reliability, target90, arrays, attractions


def regular_plan_summary(plan: dict) -> dict:
    return {
        "selected": plan["selected"],
        "n_spots": len(plan["selected"]),
        "Z1": plan.get("Z1"),
        "Z2": plan.get("Z2"),
        "Z3": plan.get("Z3"),
        "Z4": plan.get("Z4"),
        "Z4_mean": plan.get("Z4_mean"),
        "buffers": plan.get("buffers", []),
        "day_sequences": [day["seq"] for day in plan["days"]],
        "visit_duration_source": "solve_p3 l_comf for Q2 profiles",
    }


def target90_plan_summary(plan: dict, attractions: pd.DataFrame) -> dict:
    score_by_id = dict(zip(attractions["id"], attractions["score"]))
    selected_order = [day["spot"] for day in plan["days"]]
    selected_unique = list(dict.fromkeys(selected_order))
    buffers = [float(day["buffer"]) for day in plan["days"]]
    return {
        "selected": selected_unique,
        "n_spots": len(selected_unique),
        "Z1": float(sum(score_by_id[s] for s in selected_unique)),
        "Z2": float(sum(day["drive"] for day in plan["days"])),
        "Z3": None,
        "Z4": float(min(buffers)),
        "Z4_mean": float(sum(buffers) / len(buffers)),
        "buffers": buffers,
        "departures": plan.get("departures", [day["depart"] for day in plan["days"]]),
        "day_sequences": [[day["spot"]] for day in plan["days"]],
        "visit_duration_source": "stored target90 actual_visit values",
    }


def simulate_target90_day(
    day: dict,
    p_pk: float,
    p_off: float,
    l_min: np.ndarray,
    o_op: np.ndarray,
    o_cl: np.ndarray,
    D: np.ndarray,
    rng: np.random.Generator,
) -> dict:
    spot = int(day["spot"][1:]) - 1
    k = int(day["day"]) - 1
    tau = float(day["depart"])

    w_go = solve_p3.sample_road(tau, p_pk, p_off, True, rng)
    tau += float(D[0, spot + 1]) + w_go
    arr = tau
    visit_st = max(arr, float(o_op[spot]))
    tau = visit_st

    q = solve_p3.sample_queue(visit_st, True, rng)
    tau += q

    planned_visit = float(day.get("actual_visit", l_min[spot]))
    available = max(0.0, float(o_cl[spot]) - tau)
    actual_visit = float(min(planned_visit, available))
    tau += actual_visit

    tau += solve_p3.LUNCH
    w_back = solve_p3.sample_road(tau, p_pk, p_off, True, rng)
    tau += float(D[spot + 1, 0]) + w_back

    back_late = tau > solve_p3.TAU_BACK_MAX_K[k] + EPS
    short_visit = actual_visit < float(l_min[spot]) - EPS
    fail = back_late or short_visit
    if back_late and short_visit:
        reason = "back_late_and_insufficient_visit"
    elif back_late:
        reason = "back_late"
    elif short_visit:
        reason = "insufficient_visit_time"
    else:
        reason = "none"

    return {
        "fail": bool(fail),
        "reason": reason,
        "spot_index": spot,
        "arr": float(arr),
        "visit_st": float(visit_st),
        "actual_visit": float(actual_visit),
        "back": float(tau),
        "road_delay": float(w_go + w_back),
        "queue": float(q),
    }


def monte_carlo_target90(
    plan: dict,
    N: int,
    p_pk: float,
    p_off: float,
    l_min: np.ndarray,
    o_op: np.ndarray,
    o_cl: np.ndarray,
    D: np.ndarray,
    seed: int = SEED,
) -> dict:
    rng = np.random.default_rng(seed)
    n_fail = 0
    day_fail = np.zeros(solve_p3.N_DAY, dtype=int)
    spot_fail = np.zeros(solve_p3.N_SPOT, dtype=int)
    reason_counts = [
        {
            "none": 0,
            "back_late": 0,
            "insufficient_visit_time": 0,
            "back_late_and_insufficient_visit": 0,
        }
        for _ in range(solve_p3.N_DAY)
    ]

    for _ in range(N):
        trip_fail = False
        spot_this: set[int] = set()
        for k, day in enumerate(plan["days"]):
            result = simulate_target90_day(day, p_pk, p_off, l_min, o_op, o_cl, D, rng)
            reason_counts[k][result["reason"]] += 1
            if result["fail"]:
                day_fail[k] += 1
                trip_fail = True
                spot_this.add(result["spot_index"])
        if trip_fail:
            n_fail += 1
            for spot in spot_this:
                spot_fail[spot] += 1

    P_fail = n_fail / N
    ci = 1.96 * math.sqrt(P_fail * (1.0 - P_fail) / N)
    return {
        "P_fail": float(P_fail),
        "R": float(1.0 - P_fail),
        "CI_95": float(ci),
        "P_fail_day": (day_fail / N).tolist(),
        "phi_spot": (spot_fail / max(n_fail, 1)).tolist(),
        "n_fail": int(n_fail),
        "failure_reason_counts": reason_counts,
    }


def evaluate_plan(
    name: str,
    plan: dict,
    N: int,
    p_pk: float,
    p_off: float,
    arrays: tuple[np.ndarray, ...],
    seed: int,
) -> dict:
    l_min, l_comf, o_op, o_cl, D = arrays
    if name == "target90":
        mc = monte_carlo_target90(plan, N, p_pk, p_off, l_min, o_op, o_cl, D, seed=seed)
    else:
        mc = solve_p3.monte_carlo(
            plan, N, True, True, p_pk, p_off,
            l_min, l_comf, o_op, o_cl, D, seed=seed,
        )
    return mc


def table_rows(results: dict, plan_meta: dict) -> list[dict]:
    rows = []
    for scenario in SCENARIOS:
        scen_name = scenario["scenario"]
        for plan_name in PLAN_NAMES:
            item = results[scen_name][plan_name]
            meta = plan_meta[plan_name]
            row = {
                "scenario": scen_name,
                "p_peak": scenario["p_peak"],
                "p_off": scenario["p_off"],
                "plan": plan_name,
                "n_spots": meta["n_spots"],
                "R": item["R"],
                "P_fail": item["P_fail"],
                "CI_95": item["CI_95"],
                "n_fail": item["n_fail"],
                "Z1": meta["Z1"],
                "Z2": meta["Z2"],
                "Z4": meta["Z4"],
                "Z4_mean": meta["Z4_mean"],
                "selected": ",".join(meta["selected"]),
            }
            for idx, p in enumerate(item["P_fail_day"], start=1):
                row[f"P_fail_day{idx}"] = p
            rows.append(row)
    return rows


def plot_results(results: dict, out_path: Path) -> None:
    require_new(out_path)
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    x = np.arange(len(SCENARIOS))
    width = 0.18
    colors = {
        "recommend": "#4C72B0",
        "balanced": "#55A868",
        "robust": "#DD8452",
        "target90": "#8172B2",
    }
    for idx, plan_name in enumerate(PLAN_NAMES):
        values = [results[s["scenario"]][plan_name]["R"] for s in SCENARIOS]
        offset = (idx - 1.5) * width
        bars = ax.bar(
            x + offset, values, width=width, label=plan_name,
            color=colors[plan_name], edgecolor="black", linewidth=0.5,
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                min(value + 0.018, 1.02),
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.axhline(TARGET_R, color="#C44E52", linestyle="--", linewidth=1.2, label="R=0.90")
    ax.set_xticks(x)
    ax.set_xticklabels([s["scenario"] for s in SCENARIOS])
    ax.set_xlabel("Congestion scenario")
    ax.set_ylabel("Five-day reliability R")
    ax.set_ylim(0, 1.05)
    ax.set_title("v2.9 supplementary scenario reliability check")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(loc="upper center", ncol=5, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_digest(report: dict) -> str:
    lines = [
        "# v2.9 补充情景复核摘要",
        "",
        "本实验仅作为补充情景复核，不替代已经冻结的 recommend / balanced / robust / target90 主结论。",
        "",
        f"- Monte Carlo 次数：N={report['assumptions']['N_simulations']}",
        f"- 随机种子：{report['assumptions']['seed']}",
        "- 排队分布、道路延时分布、失败事件、Day1/Day5 边界、五天联合可靠度定义保持原问题三口径。",
        "- target90 保留 `target90_best_plan.json` 中的单景点日程和发车时刻，仅改变拥堵概率情景。",
        "",
        "| 情景 | p_peak | p_off | recommend R | balanced R | robust R | target90 R |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        scen = scenario["scenario"]
        r = report["results"][scen]
        lines.append(
            f"| {scen} | {scenario['p_peak']:.2f} | {scenario['p_off']:.2f} | "
            f"{r['recommend']['R']:.4f} | {r['balanced']['R']:.4f} | "
            f"{r['robust']['R']:.4f} | {r['target90']['R']:.4f} |"
        )
    lines.extend([
        "",
        f"strong 情景下 target90 是否仍达到 90%：{report['target90_strong_R_ge_90']}",
        "",
        "输出文件：",
        "- `scenario_reliability_report.json`",
        "- `scenario_reliability_table.csv`",
        "- `fig_scenario_reliability.png`",
    ])
    return "\n".join(lines) + "\n"


def main() -> dict:
    baseline, reliability, target90, arrays, attractions = load_inputs()
    plans = {
        "recommend": baseline["profiles"]["recommend"]["top"][0],
        "balanced": baseline["profiles"]["balanced"]["top"][0],
        "robust": baseline["profiles"]["robust"]["top"][0],
        "target90": target90,
    }
    plan_meta = {
        "recommend": regular_plan_summary(plans["recommend"]),
        "balanced": regular_plan_summary(plans["balanced"]),
        "robust": regular_plan_summary(plans["robust"]),
        "target90": target90_plan_summary(target90, attractions),
    }

    results: dict[str, dict[str, dict]] = {}
    for scenario in SCENARIOS:
        scen_name = scenario["scenario"]
        results[scen_name] = {}
        for plan_name in PLAN_NAMES:
            mc = evaluate_plan(
                plan_name,
                plans[plan_name],
                N_SIM,
                scenario["p_peak"],
                scenario["p_off"],
                arrays,
                seed=SEED,
            )
            results[scen_name][plan_name] = mc
            print(
                f"[scenario] {scen_name:>6s} {plan_name:>9s} "
                f"R={mc['R']:.4f} P_fail={mc['P_fail']:.4f}"
            )

    report = {
        "assumptions": {
            "experiment": "v2.9 supplementary scenario reliability check",
            "does_not_replace_frozen_main_results": True,
            "N_simulations": N_SIM,
            "seed": SEED,
            "scenarios": SCENARIOS,
            "road_delay_distribution": "solve_p3.sample_road",
            "queue_distribution": "solve_p3.sample_queue",
            "failure_rule": "back > back_max[k] or actual_visit_time < l_min",
            "trip_reliability_definition": "P(all five days succeed)",
            "target90_schedule_source": "output/target90/target90_best_plan.json",
        },
        "source_files_read": [
            "baseline_plan.json",
            "reliability_report.json",
            "output/target90/target90_best_plan.json",
        ],
        "frozen_reference": {
            "strong_compared_plans_from_reliability_report": {
                name: {
                    "R": reliability["compared_plans"][name]["R"],
                    "P_fail": reliability["compared_plans"][name]["P_fail"],
                    "CI_95": reliability["compared_plans"][name]["CI_95"],
                }
                for name in ("recommend", "balanced", "robust")
            },
            "target90_original": {
                "R": target90.get("R"),
                "P_fail": target90.get("P_fail"),
                "CI_95": target90.get("CI_95"),
            },
        },
        "plan_meta": plan_meta,
        "results": results,
        "target90_strong_R_ge_90": bool(results["strong"]["target90"]["R"] >= TARGET_R),
    }

    rows = table_rows(results, plan_meta)
    fieldnames = [
        "scenario", "p_peak", "p_off", "plan", "n_spots", "R", "P_fail",
        "CI_95", "n_fail", "Z1", "Z2", "Z4", "Z4_mean", "selected",
        "P_fail_day1", "P_fail_day2", "P_fail_day3", "P_fail_day4", "P_fail_day5",
    ]
    write_json_new(OUT_DIR / "scenario_reliability_report.json", report)
    write_csv_new(OUT_DIR / "scenario_reliability_table.csv", rows, fieldnames)
    plot_results(results, OUT_DIR / "fig_scenario_reliability.png")
    write_text_new(OUT_DIR / "scenario_reliability_digest.md", make_digest(report))

    print(f"[scenario] wrote {OUT_DIR}")
    return report


if __name__ == "__main__":
    main()
