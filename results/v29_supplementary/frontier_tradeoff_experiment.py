"""v2.9 supplementary reliability-experience frontier experiment.

This script is intentionally placed under output/v29/ and writes only to that
directory. It re-enumerates the Q2 feasible pool but does not modify Q2/P3
source code or frozen result files.
"""
from __future__ import annotations

import csv
import heapq
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "v29"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import solve_p2
import solve_p3


SPOT_COUNTS = [5, 6, 7, 8]
TOP_K = int(os.environ.get("V29_FRONTIER_TOP_K", "20"))
N_SIM = int(os.environ.get("V29_FRONTIER_N", "5000"))
SEED = 2026
P_PEAK = 0.60
P_OFF = 0.30
TARGET_R = 0.90


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


def candidate_sort_key(c: dict) -> tuple:
    return (
        float(c["Z4"]),
        float(c["Z4_mean"]),
        -float(c["Z2"]),
        float(c["Z1"]),
        -float(c["Z3"]),
    )


def select_top_by_buffer(cands: list[dict], top_k: int) -> tuple[dict[int, list[dict]], dict[int, int]]:
    heaps: dict[int, list[tuple[tuple, int, dict]]] = {n: [] for n in SPOT_COUNTS}
    counts = {n: 0 for n in SPOT_COUNTS}
    for idx, cand in enumerate(cands):
        n_spots = len(cand["S"])
        if n_spots not in heaps:
            continue
        counts[n_spots] += 1
        item = (candidate_sort_key(cand), idx, cand)
        heap = heaps[n_spots]
        if len(heap) < top_k:
            heapq.heappush(heap, item)
        elif item[0] > heap[0][0]:
            heapq.heapreplace(heap, item)

    selected = {
        n: [item[2] for item in sorted(heaps[n], key=lambda x: x[0], reverse=True)]
        for n in SPOT_COUNTS
    }
    return selected, counts


def export_candidate_plan(c: dict, plan_id: str, rank_by_buffer: int) -> dict:
    days = []
    Tks_ordered = []
    for k, opt in enumerate(c["opts"]):
        Tks_ordered.append(float(opt["T_sc"]))
        buffer_k = solve_p2.T_SCENIC_MAX_K[k] - float(opt["T_sc"])
        days.append({
            "day": k + 1,
            "depart": solve_p2.TAU_DEP_K[k],
            "T_scenic_max": solve_p2.T_SCENIC_MAX_K[k],
            "back_max": solve_p2.TAU_BACK_MAX_K[k],
            "buffer": float(buffer_k),
            "seq": opt["tl"]["seq"],
            "arr": [float(x) for x in opt["tl"]["arr"]],
            "visit_st": [float(x) for x in opt["tl"]["visit_st"]],
            "lv": [float(x) for x in opt["tl"]["lv"]],
            "lunch": [float(opt["tl"]["lunch"][0]), float(opt["tl"]["lunch"][1])],
            "back": float(opt["tl"]["back"]),
            "T_scenic": float(opt["T_sc"]),
            "drive": float(opt["T_dr"]),
        })
    return {
        "plan_id": plan_id,
        "rank_by_buffer": rank_by_buffer,
        "n_spots": len(c["S"]),
        "selected": sorted([f"A{i + 1}" for i in c["S"]]),
        "selected_by_day": [spot for day in days for spot in day["seq"]],
        "Z1": float(c["Z1"]),
        "Z2": float(c["Z2"]),
        "Z3": float(c["Z3"]),
        "Z4": float(c["Z4"]),
        "Z4_mean": float(c["Z4_mean"]),
        "Tks": [float(t) for t in Tks_ordered],
        "buffers": [float(solve_p2.T_SCENIC_MAX_K[k] - t) for k, t in enumerate(Tks_ordered)],
        "days": days,
    }


def evaluate_candidate(plan: dict, arrays: tuple[np.ndarray, ...]) -> dict:
    l_min, l_comf, o_op, o_cl, D = arrays
    mc = solve_p3.monte_carlo(
        plan, N_SIM, True, True, P_PEAK, P_OFF,
        l_min, l_comf, o_op, o_cl, D, seed=SEED,
    )
    return {
        **plan,
        "R": mc["R"],
        "P_fail": mc["P_fail"],
        "CI_95": mc["CI_95"],
        "n_fail": mc["n_fail"],
        "P_fail_day": mc["P_fail_day"],
        "phi_spot": mc["phi_spot"],
    }


def flatten_rows(evaluated: list[dict]) -> list[dict]:
    rows = []
    for item in evaluated:
        row = {
            "n_spots": item["n_spots"],
            "rank_by_buffer": item["rank_by_buffer"],
            "plan_id": item["plan_id"],
            "R": item["R"],
            "P_fail": item["P_fail"],
            "CI_95": item["CI_95"],
            "n_fail": item["n_fail"],
            "Z1": item["Z1"],
            "Z2": item["Z2"],
            "Z3": item["Z3"],
            "Z4": item["Z4"],
            "Z4_mean": item["Z4_mean"],
            "selected": ",".join(item["selected"]),
            "selected_by_day": ",".join(item["selected_by_day"]),
            "buffers": ",".join(f"{x:.4f}" for x in item["buffers"]),
            "Tks": ",".join(f"{x:.4f}" for x in item["Tks"]),
        }
        for idx, p in enumerate(item["P_fail_day"], start=1):
            row[f"P_fail_day{idx}"] = p
        rows.append(row)
    return rows


def plot_frontier(evaluated: list[dict], best_by_size: dict[int, dict], out_path: Path) -> None:
    require_new(out_path)
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    x_all = np.array([item["n_spots"] for item in evaluated], dtype=float)
    jitter = np.array([((item["rank_by_buffer"] % 7) - 3) * 0.018 for item in evaluated])
    y_all = np.array([item["R"] for item in evaluated], dtype=float)
    z1_all = np.array([item["Z1"] for item in evaluated], dtype=float)

    scatter = ax.scatter(
        x_all + jitter,
        y_all,
        c=z1_all,
        cmap="viridis",
        s=52,
        alpha=0.72,
        edgecolors="black",
        linewidths=0.35,
        label="Top-K candidates",
    )
    xs = np.array(SPOT_COUNTS, dtype=float)
    ys = np.array([best_by_size[n]["R"] for n in SPOT_COUNTS], dtype=float)
    ax.plot(xs, ys, color="#C44E52", marker="o", linewidth=2.0, label="Best R per spot count")
    for n in SPOT_COUNTS:
        item = best_by_size[n]
        ax.text(n, min(item["R"] + 0.018, 1.02), f"{item['R']:.3f}",
                ha="center", va="bottom", fontsize=9)
    ax.axhline(TARGET_R, color="#555555", linestyle="--", linewidth=1.1, label="R=0.90")
    ax.set_xticks(SPOT_COUNTS)
    ax.set_xlabel("Number of selected spots")
    ax.set_ylabel("Reliability R under strong scenario")
    ax.set_ylim(0, 1.05)
    ax.set_title("v2.9 reliability-experience frontier among high-buffer Q2 candidates")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Experience score Z1")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_digest(report: dict) -> str:
    lines = [
        "# v2.9 体验--可靠度权衡探索摘要",
        "",
        "本实验是问题三补充探索：不改变问题二主模型，只从问题二可行方案池中按景点数分组，优先复核确定性缓冲较大的 Top-K 方案。",
        "",
        f"- Top-K：{report['assumptions']['top_k_per_group']}",
        f"- Monte Carlo 次数：N={report['assumptions']['N_simulations']}",
        f"- 拥堵情景：p_peak={report['assumptions']['p_peak']:.2f}, p_off={report['assumptions']['p_off']:.2f}",
        f"- 随机种子：{report['assumptions']['seed']}",
        "",
        "| 景点数 | 最高 R | P_fail | Z1 | 最小缓冲 Z4 | 方案 |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for n in SPOT_COUNTS:
        best = report["best_by_spot_count"][str(n)]
        lines.append(
            f"| {n} | {best['R']:.4f} | {best['P_fail']:.4f} | "
            f"{best['Z1']:.1f} | {best['Z4']:.2f} | {','.join(best['selected'])} |"
        )
    lines.extend([
        "",
        "这些结果用于说明“减少景点数/提高缓冲”与“五天联合可靠度”的权衡关系，不替代原 recommend / balanced / robust 或 target90 方案。",
        "",
        "输出文件：",
        "- `frontier_tradeoff_report.json`",
        "- `frontier_tradeoff_table.csv`",
        "- `fig_frontier_tradeoff.png`",
    ])
    return "\n".join(lines) + "\n"


def main() -> dict:
    t0 = time.perf_counter()
    s, l_min, l_comf, o_op, o_cl, D, _ = solve_p2.load_data(ROOT)
    print("[frontier] re-enumerating Q2 feasible plan pool")
    cands = solve_p2.enumerate_all(s, l_comf, o_op, o_cl, D, logger=None)
    enum_seconds = time.perf_counter() - t0
    print(f"[frontier] feasible plans={len(cands):,} enumeration_seconds={enum_seconds:.2f}")

    selected, group_counts = select_top_by_buffer(cands, TOP_K)
    arrays = (l_min, l_comf, o_op, o_cl, D)

    evaluated: list[dict] = []
    for n in SPOT_COUNTS:
        for rank, cand in enumerate(selected[n], start=1):
            plan = export_candidate_plan(cand, f"S{n}_buffer_rank{rank:02d}", rank)
            result = evaluate_candidate(plan, arrays)
            evaluated.append(result)
            print(
                f"[frontier] n={n} rank={rank:02d} "
                f"R={result['R']:.4f} Z4={result['Z4']:.2f} Z1={result['Z1']:.1f}"
            )

    best_by_size: dict[int, dict] = {}
    for n in SPOT_COUNTS:
        items = [item for item in evaluated if item["n_spots"] == n]
        best_by_size[n] = max(
            items,
            key=lambda item: (item["R"], item["Z4"], item["Z4_mean"], item["Z1"]),
        )

    report = {
        "assumptions": {
            "experiment": "v2.9 supplementary reliability-experience tradeoff",
            "does_not_replace_frozen_main_results": True,
            "feasible_pool_source": "re-enumerated with solve_p2.enumerate_all",
            "top_k_per_group": TOP_K,
            "N_simulations": N_SIM,
            "seed": SEED,
            "p_peak": P_PEAK,
            "p_off": P_OFF,
            "selection_rule": "Top-K by (Z4, Z4_mean, -Z2, Z1, -Z3) within each spot count",
            "visit_duration_source": "solve_p2/solve_p3 l_comf for Q2 feasible plans",
            "failure_rule": "back > back_max[k] or actual_visit_time < l_min",
            "trip_reliability_definition": "P(all five days succeed)",
        },
        "search_summary": {
            "n_feasible_plans": len(cands),
            "enumeration_seconds": enum_seconds,
            "group_counts": group_counts,
            "evaluated_candidates": len(evaluated),
        },
        "best_by_spot_count": {str(n): best_by_size[n] for n in SPOT_COUNTS},
        "evaluated_top_k": evaluated,
        "target90_threshold_met_by_group_best": {
            str(n): bool(best_by_size[n]["R"] >= TARGET_R) for n in SPOT_COUNTS
        },
    }

    rows = flatten_rows(evaluated)
    fieldnames = [
        "n_spots", "rank_by_buffer", "plan_id", "R", "P_fail", "CI_95", "n_fail",
        "Z1", "Z2", "Z3", "Z4", "Z4_mean", "selected", "selected_by_day",
        "buffers", "Tks",
        "P_fail_day1", "P_fail_day2", "P_fail_day3", "P_fail_day4", "P_fail_day5",
    ]
    write_json_new(OUT_DIR / "frontier_tradeoff_report.json", report)
    write_csv_new(OUT_DIR / "frontier_tradeoff_table.csv", rows, fieldnames)
    plot_frontier(evaluated, best_by_size, OUT_DIR / "fig_frontier_tradeoff.png")
    write_text_new(OUT_DIR / "frontier_tradeoff_digest.md", make_digest(report))

    print(f"[frontier] wrote {OUT_DIR}")
    return report


if __name__ == "__main__":
    main()
