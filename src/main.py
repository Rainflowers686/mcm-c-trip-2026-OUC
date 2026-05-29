"""main.py — 一键运行 solve_p1 → solve_p2 → solve_p3，并执行最终校验。

校验内容（按用户清单）：
  1. 是否成功生成全部输出文件；
  2. baseline_plan.json 中每天是否只有 1–2 个景点；
  3. 是否每个景点最多出现一次；
  4. 是否总景点数在 5–8 个之间；
  5. 是否所有离开时间满足闭园时间，早到等待 visit_st 是否正确；
  6. 是否满足 v1.1.1 day-specific 边界；
  7. reliability_report.json 中是否包含主结果、敏感性分析和薄弱点识别。
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_LOGS = ROOT / "output" / "logs"
OUT_LOGS.mkdir(parents=True, exist_ok=True)

import solve_p1
import solve_p2
import solve_p3

EXPECTED_FILES = [
    "p1_results.json",
    "baseline_plan.json",
    "reliability_report.json",
    "output/tables/p1_type_classification.csv",
    "output/tables/p2_four_dim_scores.csv",
    "output/tables/p3_priority_ranking.csv",
    "output/tables/p4_combo_pairs.csv",
    "output/tables/p5_priority_pool.csv",
    "output/figures/fig_priority_ranking.png",
    "output/figures/fig_profile_comparison.png",
    "output/figures/fig_daily_fail.png",
    "output/figures/fig_contribution.png",
    "output/figures/fig_sensitivity_heatmap.png",
    "output/figures/fig_robustness_comparison.png",
    "output/logs/main.log",
    "output/logs/solve_p1.log",
    "output/logs/solve_p2.log",
    "output/logs/solve_p3.log",
]

TAU_DEP_K = [11.5, 8.5, 8.5, 8.5, 8.5]
TAU_BACK_MAX_K = [21.0, 21.0, 21.0, 21.0, 16.5]
T_SCENIC_MAX_K = [9.5, 12.5, 12.5, 12.5, 8.0]
EPS = 1e-6


# ---------- 校验函数 ----------
def check_files_exist() -> list[str]:
    """检查全部输出文件存在。"""
    missing = []
    for rel in EXPECTED_FILES:
        if not (ROOT / rel).exists():
            missing.append(rel)
    return missing


def check_baseline_plan(bp_doc: dict, attractions: pd.DataFrame) -> list[str]:
    """校验 baseline_plan：v1.1.1 边界、每天 1–2 个景点、不重复、开放时间。"""
    errors = []
    plan = bp_doc["baseline_plan"]
    days = plan["days"]
    selected = plan["selected"]

    boundary = bp_doc.get("boundary_v111")
    if not boundary:
        errors.append("缺少 boundary_v111")
    else:
        if boundary.get("tau_dep_per_day") != TAU_DEP_K:
            errors.append(f"boundary_v111.tau_dep_per_day 错误：{boundary.get('tau_dep_per_day')}")
        if boundary.get("tau_back_max_per_day") != TAU_BACK_MAX_K:
            errors.append(f"boundary_v111.tau_back_max_per_day 错误：{boundary.get('tau_back_max_per_day')}")
        if boundary.get("T_scenic_max_per_day") != T_SCENIC_MAX_K:
            errors.append(f"boundary_v111.T_scenic_max_per_day 错误：{boundary.get('T_scenic_max_per_day')}")

    # 5 天
    if len(days) != 5:
        errors.append(f"days 数量 = {len(days)}（应为 5）")

    # 每天 1–2 个景点
    all_visited: list[str] = []
    for d in days:
        seq = d["seq"]
        if len(seq) not in (1, 2):
            errors.append(f"day {d['day']} seq 长度 = {len(seq)}（应为 1 或 2）")
        all_visited.extend(seq)

    # 不重复
    if len(all_visited) != len(set(all_visited)):
        dup = [x for x in set(all_visited) if all_visited.count(x) > 1]
        errors.append(f"景点重复：{dup}")

    # 总数 5–8
    if not (5 <= len(selected) <= 8):
        errors.append(f"总景点数 = {len(selected)}（应在 5–8 之间）")

    # selected vs all_visited 一致
    if set(selected) != set(all_visited):
        errors.append(f"selected ≠ visited: selected={selected}, visited={sorted(set(all_visited))}")

    # v1.1.1 day-specific 边界 + 开放时间
    attr_idx = {row["id"]: row for _, row in attractions.iterrows()}
    for d in days:
        day = int(d["day"])
        k_day = day - 1
        if d.get("depart") != TAU_DEP_K[k_day]:
            errors.append(f"day {day} depart={d.get('depart')} != {TAU_DEP_K[k_day]}")
        if d.get("back_max") != TAU_BACK_MAX_K[k_day]:
            errors.append(f"day {day} back_max={d.get('back_max')} != {TAU_BACK_MAX_K[k_day]}")
        if d.get("T_scenic_max") != T_SCENIC_MAX_K[k_day]:
            errors.append(f"day {day} T_scenic_max={d.get('T_scenic_max')} != {T_SCENIC_MAX_K[k_day]}")
        if d["back"] > TAU_BACK_MAX_K[k_day] + EPS:
            errors.append(f"day {day} back = {d['back']:.4f} > {TAU_BACK_MAX_K[k_day]}")
        if d["T_scenic"] > T_SCENIC_MAX_K[k_day] + EPS:
            errors.append(f"day {day} T_scenic = {d['T_scenic']:.4f} > {T_SCENIC_MAX_K[k_day]}")
        expected_buffer = T_SCENIC_MAX_K[k_day] - d["T_scenic"]
        if abs(d.get("buffer", np.nan) - expected_buffer) > 1e-5:
            errors.append(f"day {day} buffer={d.get('buffer')} != {expected_buffer:.6f}")

        for k, name in enumerate(d["seq"]):
            attr = attr_idx[name]
            if "visit_st" not in d:
                errors.append(f"day {day} 缺少 visit_st")
                continue
            expected_visit_st = max(d["arr"][k], attr["open_hour"])
            if abs(d["visit_st"][k] - expected_visit_st) > 1e-5:
                errors.append(
                    f"day {day} {name} visit_st={d['visit_st'][k]:.3f} "
                    f"!= max(arr, open)={expected_visit_st:.3f}"
                )
            if d["lv"][k] > attr["close_hour"] + EPS:
                errors.append(f"day {day} {name} lv={d['lv'][k]:.3f} > close={attr['close_hour']}")

    if "Z4" in plan:
        expected_z4 = min(d["buffer"] for d in days)
        if abs(plan["Z4"] - expected_z4) > 1e-5:
            errors.append(f"baseline Z4={plan['Z4']} != min(buffer)={expected_z4:.6f}")
    return errors


def check_reliability_report(report: dict) -> list[str]:
    """校验 reliability_report 包含主结果 / 敏感性 / 薄弱点。"""
    errors = []
    if "main_result" not in report:
        errors.append("缺少 main_result")
    else:
        m = report["main_result"]
        for k in ("R", "P_fail", "CI_95", "P_fail_day", "phi_road", "phi_queue"):
            if k not in m:
                errors.append(f"main_result 缺少字段 {k}")
    if "sensitivity_grid" not in report:
        errors.append("缺少 sensitivity_grid")
    elif len(report["sensitivity_grid"]) != 16:
        errors.append(f"sensitivity_grid 长度 = {len(report['sensitivity_grid'])}（应为 16）")
    if "weak_points" not in report:
        errors.append("缺少 weak_points")
    else:
        for k in ("theta_per_day", "target_R_met", "weak_days", "weak_spots"):
            if k not in report["weak_points"]:
                errors.append(f"weak_points 缺少字段 {k}")
    assumptions = report.get("assumptions", {})
    if assumptions.get("boundary_v111_applied") is not True:
        errors.append("assumptions.boundary_v111_applied 不是 true")
    if assumptions.get("early_arrival_handling") != "wait_until_open":
        errors.append("assumptions.early_arrival_handling 不是 wait_until_open")
    if assumptions.get("tau_dep_per_day") != TAU_DEP_K:
        errors.append("assumptions.tau_dep_per_day 错误")
    if assumptions.get("tau_back_max_per_day") != TAU_BACK_MAX_K:
        errors.append("assumptions.tau_back_max_per_day 错误")
    if assumptions.get("T_scenic_max_per_day") != T_SCENIC_MAX_K:
        errors.append("assumptions.T_scenic_max_per_day 错误")
    compared = report.get("compared_plans", {})
    for name in ("recommend", "balanced", "robust"):
        if name not in compared:
            errors.append(f"compared_plans 缺少 {name}")
    return errors


# ---------- 主入口 ----------
def main():
    log_path = OUT_LOGS / "main.log"
    logger = logging.getLogger("main")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.info("== main.py START ==")
    print("=" * 60)
    print("中国海洋大学数学建模校赛 C 题 — 自动化求解")
    print("=" * 60)

    t0 = time.time()
    print("\n--- [1/3] solve_p1.py: 景点特征与综合优先级 ---")
    p1_result = solve_p1.run(verbose=True)
    logger.info("solve_p1 done (%.2fs)", time.time() - t0)

    t1 = time.time()
    print("\n--- [2/3] solve_p2.py: 基准行程与多套备选 ---")
    p2_result = solve_p2.run(verbose=True)
    logger.info("solve_p2 done (%.2fs)", time.time() - t1)

    t2 = time.time()
    print("\n--- [3/3] solve_p3.py: Monte Carlo 稳定性评估 ---")
    p3_result = solve_p3.run(verbose=True)
    logger.info("solve_p3 done (%.2fs)", time.time() - t2)

    print("\n" + "=" * 60)
    print("校验输出文件与模型一致性")
    print("=" * 60)

    all_errors: list[str] = []

    # 1) 文件存在性
    missing = check_files_exist()
    if missing:
        print(f"[FAIL] 缺失文件：")
        for m in missing:
            print(f"       - {m}")
        all_errors.extend(missing)
    else:
        print(f"[PASS] 全部 {len(EXPECTED_FILES)} 个输出文件存在")

    # 2-6) baseline_plan 校验
    with open(ROOT / "baseline_plan.json", "r", encoding="utf-8") as f:
        bp = json.load(f)
    attractions = pd.read_csv(ROOT / "attractions.csv")
    plan_errors = check_baseline_plan(bp, attractions)
    if plan_errors:
        print(f"[FAIL] baseline_plan 校验错误：")
        for e in plan_errors:
            print(f"       - {e}")
        all_errors.extend(plan_errors)
    else:
        bp_plan = bp["baseline_plan"]
        print(f"[PASS] baseline_plan 全部校验通过：")
        print(f"       - 每天 1-2 个景点 [OK]")
        print(f"       - 无重复 [OK]")
        print(f"       - 总景点数 {len(bp_plan['selected'])} in [5, 8] [OK]")
        print(f"       - visit_st = max(arr, open_hour) [OK]")
        print(f"       - 离开时间 lv <= close_hour [OK]")
        print(f"       - 每天 T_scenic <= day-specific 上限 [OK]")
        print(f"       - 每天 back <= day-specific 最迟时刻 [OK]")
        print(f"       - day 1 depart=11.5, day 5 back_max=16.5 [OK]")

    # 7) reliability_report 校验
    with open(ROOT / "reliability_report.json", "r", encoding="utf-8") as f:
        rep = json.load(f)
    rep_errors = check_reliability_report(rep)
    if rep_errors:
        print(f"[FAIL] reliability_report 校验错误：")
        for e in rep_errors:
            print(f"       - {e}")
        all_errors.extend(rep_errors)
    else:
        print(f"[PASS] reliability_report 全部校验通过：")
        print(f"       - main_result 字段齐全 [OK]")
        print(f"       - sensitivity_grid (16 cells) [OK]")
        print(f"       - weak_points 字段齐全 [OK]")
        print(f"       - compared_plans 含 recommend / balanced / robust [OK]")
        print(f"       - boundary_v111_applied=true [OK]")

    # 关键数值摘要
    print("\n" + "=" * 60)
    print("关键结果摘要")
    print("=" * 60)
    print(f"问题一：高优先级景点 = {[r['id'] for r in p1_result['priority_pool']['high']]}")
    print(f"        前 3 名 = {[(r['id'], round(r['P_i'], 4)) for r in p1_result['priority_ranking'][:3]]}")

    bpp = bp["baseline_plan"]
    print(f"\n问题二：基准行程（综合推荐型 lambda=(0.6,0.2,0.2,0.0)）")
    print(f"        selected = {bpp['selected']}")
    print(f"        Z1={bpp['Z1']:.2f}  Z2={bpp['Z2']:.2f}  "
          f"Z3={bpp['Z3']:.4f}  Z4={bpp['Z4']:.4f}  F={bpp['F']:.4f}")
    print(f"        共 {bp['n_feasible_plans']} 个可行解")
    print(f"        五套 profile top-1：")
    for name, profile in bp["profiles"].items():
        top1 = profile["top"][0]
        print(f"        - {name:12s} F={top1['F']:.4f} Z4={top1['Z4']:.3f} "
              f"selected={top1['selected']}")
    for d in bpp["days"]:
        print(f"        day{d['day']}: {' -> '.join(d['seq']):20s}"
              f" depart={d['depart']:.1f} back={d['back']:.2f} "
              f"T_scenic={d['T_scenic']:.2f}/{d['T_scenic_max']:.2f} "
              f"buffer={d['buffer']:.2f}")

    mr = rep["main_result"]
    wp = rep["weak_points"]
    print(f"\n问题三：可靠度评估（p_pk={rep['assumptions']['p_peak_default']}, "
          f"p_off={rep['assumptions']['p_off_default']}, N={rep['assumptions']['N_simulations']}）")
    print(f"        R = {mr['R']:.4f}  P_fail = {mr['P_fail']:.4f}  CI95 = ±{mr['CI_95']:.4f}")
    print(f"        phi_road = {mr['phi_road']:.3f}  phi_queue = {mr['phi_queue']:.3f}")
    print(f"        target_R>=0.9 达标 = {wp['target_R_met']}")
    print(f"        薄弱日 = {wp['weak_days']}  薄弱景点 = {wp['weak_spots']}")
    print(f"        三方案对比：")
    for name in ("recommend", "balanced", "robust"):
        cp = rep["compared_plans"][name]
        print(f"        - {name:9s} R={cp['R']:.4f} P_fail={cp['P_fail']:.4f} "
              f"Z4={cp['Z4']:.3f} Z4_mean={cp['Z4_mean']:.3f}")
    rd = rep["robust_diagnosis"]
    print(f"        R>=0.9 达标方案 = {rd['plans_meeting_target']}")

    # 终止
    print("\n" + "=" * 60)
    total = time.time() - t0
    if all_errors:
        print(f"[FAIL] 校验失败，共 {len(all_errors)} 项错误")
        print(f"总耗时 {total:.2f}s")
        logger.error("Validation FAILED with %d errors", len(all_errors))
        sys.exit(1)
    else:
        print(f"[OK] 全部校验通过  总耗时 {total:.2f}s")
        logger.info("Validation PASSED, total %.2fs", total)


if __name__ == "__main__":
    main()
