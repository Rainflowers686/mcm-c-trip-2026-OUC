"""solve_p3.py — 问题三：随机扰动下的稳定性评估（Monte Carlo）

按 model_spec_v1.0 + v1.1 + v1.1.1 实现：
  - 堵车采样：高峰 Bernoulli(p_pk)·U(1,4)，平峰 Bernoulli(p_off)·U(0,1.5)
  - 排队采样：高峰入园（9–12）U(0.5,3)，其他 U(0,1)（无额外发生概率）
  - 受扰动时间轴：day-specific 出发；早到等待；午餐 1.0h 插入首个景点后
  - 失败事件：back>back_max_k ∨ ∃ \tilde t_i < l_min_i
  - 贡献度分解：Shapley 开关法（4 场景）
  - 敏感性扫描：p_pk × p_off = 16 组
  - 输出 reliability_report.json + 4 张图
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

plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 模型常量 ----------
P_PK_DEFAULT = 0.6
P_OFF_DEFAULT = 0.3
N_SIM = 10000
SEED = 2026

LUNCH = 1.0
TAU_DEP_K = [11.5, 8.5, 8.5, 8.5, 8.5]
TAU_BACK_MAX_K = [21.0, 21.0, 21.0, 21.0, 16.5]
T_SCENIC_MAX_K = [9.5, 12.5, 12.5, 12.5, 8.0]
N_DAY = 5
N_SPOT = 10

P_PK_GRID = [0.4, 0.5, 0.6, 0.7]
P_OFF_GRID = [0.1, 0.2, 0.3, 0.4]


# ---------- 时段判别函数 ----------
def in_peak(t: float) -> bool:
    """高峰判别：t∈[7,9)∪[11,13)∪[16,18)。"""
    return (7 <= t < 9) or (11 <= t < 13) or (16 <= t < 18)


def in_queue_peak(t: float) -> bool:
    """排队高峰判别：t∈[9,12)。"""
    return 9 <= t < 12


# ---------- 随机采样 ----------
def sample_road(t: float, p_pk: float, p_off: float, on: bool,
                rng: np.random.Generator) -> float:
    """采样路段堵车延时 W。

    参数：
        t: 出发该路段的时刻
        p_pk/p_off: 高峰/平峰拥堵发生概率
        on: True 启用堵车扰动，False 关闭（返回 0）
        rng: 随机数生成器
    """
    if not on:
        return 0.0
    if in_peak(t):
        return float(rng.uniform(1.0, 4.0)) if rng.random() < p_pk else 0.0
    return float(rng.uniform(0.0, 1.5)) if rng.random() < p_off else 0.0


def sample_queue(t_arr: float, on: bool, rng: np.random.Generator) -> float:
    """采样景点排队时长 Q：题目给定分布，凡入园即抽样（无 p_Q）。"""
    if not on:
        return 0.0
    if in_queue_peak(t_arr):
        return float(rng.uniform(0.5, 3.0))
    return float(rng.uniform(0.0, 1.0))


# ---------- 单日单次模拟 ----------
def simulate_day(day: dict, road_on: bool, queue_on: bool,
                 p_pk: float, p_off: float,
                 l_min: np.ndarray, l_comf: np.ndarray,
                 o_op: np.ndarray, o_cl: np.ndarray,
                 D: np.ndarray, rng: np.random.Generator) -> dict:
    """对一天的行程做一次随机模拟，返回 dict。

    遵循 §4.5 时间轴递推：
        - 起点 TAU_DEP_K[k]
        - 段 ℓ=1：酒店→第 1 个景点  （含堵车 W1）
        - 排队 Q1，游览 \tilde t1（受闭园截断）
        - 午餐 1.0h（首个景点后）
        - 若双景点：段 ℓ=2 → 第 2 个景点、排队、游览
        - 末段：→ 酒店

    返回字段：T_sc, back, fail, seq, legs, queues, t_acts
    """
    seq = [int(name[1:]) - 1 for name in day["seq"]]
    k = int(day["day"]) - 1
    tau_dep = TAU_DEP_K[k]
    tau_back_max = TAU_BACK_MAX_K[k]
    tau = tau_dep
    prev = 0
    legs: list[float] = []
    queues: list[float] = []
    t_acts: list[float] = []
    arrivals: list[float] = []
    visit_starts: list[float] = []

    for idx, sp in enumerate(seq):
        # 段 ℓ：从 prev 出发到景点 sp
        w = sample_road(tau, p_pk, p_off, road_on, rng)
        legs.append(w)
        tau += float(D[prev, sp + 1]) + w
        arr = tau
        arrivals.append(float(arr))
        visit_st = max(arr, float(o_op[sp]))
        visit_starts.append(float(visit_st))
        tau = visit_st
        q = sample_queue(visit_st, queue_on, rng)
        queues.append(q)
        tau += q
        # 闭园截断：实际可游览时长
        max_stay = max(0.0, float(o_cl[sp]) - tau)
        t_real = float(min(l_comf[sp], max_stay))
        if t_real < 0.0:
            t_real = 0.0
        t_acts.append(t_real)
        tau += t_real
        # 午餐插在首个景点后
        if idx == 0:
            tau += LUNCH
        prev = sp + 1

    # 末段：返程酒店
    w_back = sample_road(tau, p_pk, p_off, road_on, rng)
    legs.append(w_back)
    tau += float(D[prev, 0]) + w_back
    back = tau
    T_sc = back - tau_dep

    # v1.1.1 失败判定：违反 day-specific 返程边界或实际游览时长不足
    fail = back > tau_back_max + 1e-6
    for idx, sp in enumerate(seq):
        if t_acts[idx] < float(l_min[sp]) - 1e-6:
            fail = True

    return {"T_sc": float(T_sc), "back": float(back), "fail": bool(fail),
            "seq": seq, "legs": legs, "queues": queues, "t_acts": t_acts,
            "arr": arrivals, "visit_st": visit_starts}


# ---------- N 次模拟 ----------
def monte_carlo(plan: dict, N: int, road_on: bool, queue_on: bool,
                p_pk: float, p_off: float,
                l_min: np.ndarray, l_comf: np.ndarray,
                o_op: np.ndarray, o_cl: np.ndarray,
                D: np.ndarray, seed: int = SEED) -> dict:
    """对基准行程 plan 跑 N 次 Monte Carlo 模拟。

    返回字段：P_fail, R, CI_95, P_fail_day(5), phi_spot(10)
    """
    rng = np.random.default_rng(seed)
    n_fail = 0
    day_fail = np.zeros(N_DAY)
    spot_fail = np.zeros(N_SPOT)

    for _ in range(N):
        trip_fail = False
        spot_this = set()
        for k, day in enumerate(plan["days"]):
            r = simulate_day(day, road_on, queue_on, p_pk, p_off,
                             l_min, l_comf, o_op, o_cl, D, rng)
            if r["fail"]:
                day_fail[k] += 1
                trip_fail = True
                spot_this.update(r["seq"])
        if trip_fail:
            n_fail += 1
            for sp in spot_this:
                spot_fail[sp] += 1

    P_fail = n_fail / N
    ci = 1.96 * float(np.sqrt(P_fail * (1.0 - P_fail) / N))
    return {
        "P_fail": float(P_fail),
        "R": float(1.0 - P_fail),
        "CI_95": ci,
        "P_fail_day": (day_fail / N).tolist(),
        "phi_spot": (spot_fail / max(n_fail, 1)).tolist(),
        "n_fail": int(n_fail),
    }


# ---------- Shapley 贡献度分解 ----------
def shapley(plan: dict, N: int, p_pk: float, p_off: float,
            l_min: np.ndarray, l_comf: np.ndarray,
            o_op: np.ndarray, o_cl: np.ndarray,
            D: np.ndarray, seed: int = SEED) -> dict:
    """开关法 4 场景计算 phi_road, phi_queue（满足 phi_road + phi_queue = 1）。"""
    args = (l_min, l_comf, o_op, o_cl, D)
    P0 = monte_carlo(plan, N, False, False, p_pk, p_off, *args, seed=seed)["P_fail"]
    PR = monte_carlo(plan, N, True,  False, p_pk, p_off, *args, seed=seed + 1)["P_fail"]
    PQ = monte_carlo(plan, N, False, True,  p_pk, p_off, *args, seed=seed + 2)["P_fail"]
    PF = monte_carlo(plan, N, True,  True,  p_pk, p_off, *args, seed=seed + 3)["P_fail"]

    dR = PR - P0
    dQ = PQ - P0
    dJ = PF - PR - PQ + P0
    denom = max(PF - P0, 1e-9)
    return {
        "P0": float(P0), "PR": float(PR), "PQ": float(PQ), "PF": float(PF),
        "phi_road":  float((dR + 0.5 * dJ) / denom),
        "phi_queue": float((dQ + 0.5 * dJ) / denom),
        "R": float(1.0 - PF),
    }


# ---------- 敏感性扫描 ----------
def sensitivity_scan(plan: dict, N: int,
                     l_min: np.ndarray, l_comf: np.ndarray,
                     o_op: np.ndarray, o_cl: np.ndarray,
                     D: np.ndarray, logger=None) -> list:
    """对 p_pk × p_off 网格做 16 组模拟，返回 list。"""
    results = []
    for p_pk in P_PK_GRID:
        for p_off in P_OFF_GRID:
            mc = monte_carlo(plan, N, True, True, p_pk, p_off,
                             l_min, l_comf, o_op, o_cl, D, seed=SEED)
            sh = shapley(plan, max(N // 4, 1000), p_pk, p_off,
                         l_min, l_comf, o_op, o_cl, D, seed=SEED + 1000)
            results.append({
                "p_pk": p_pk, "p_off": p_off,
                "R": mc["R"], "P_fail": mc["P_fail"], "CI_95": mc["CI_95"],
                "P_fail_day": mc["P_fail_day"],
                "phi_spot": mc["phi_spot"],
                "phi_road": sh["phi_road"], "phi_queue": sh["phi_queue"],
            })
            if logger:
                logger.info(
                    "scan p_pk=%.1f p_off=%.1f → R=%.4f phi_road=%.3f phi_queue=%.3f",
                    p_pk, p_off, mc["R"], sh["phi_road"], sh["phi_queue"],
                )
    return results


# ---------- 薄弱点识别 ----------
def weak_points(mc_main: dict) -> dict:
    """根据主结果识别日级 / 景点级薄弱点。"""
    theta = 1.0 - 0.9 ** (1.0 / N_DAY)  # ≈ 0.0209
    weak_days = [k + 1 for k, p in enumerate(mc_main["P_fail_day"]) if p > theta]
    spot_pairs = sorted(enumerate(mc_main["phi_spot"]), key=lambda x: -x[1])
    weak_spots = [(f"A{i + 1}", round(float(p), 4))
                  for i, p in spot_pairs if p > 0][:3]
    return {
        "theta_per_day": float(theta),
        "target_R_met": bool(mc_main["R"] >= 0.9),
        "weak_days": weak_days,
        "weak_spots": weak_spots,
    }


# ---------- 绘图 ----------
def plot_daily_fail(P_fail_day: list, theta: float, out_path: Path) -> None:
    """每日失败概率柱图 + 阈值线。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(1, len(P_fail_day) + 1)
    bars = ax.bar(x, P_fail_day, color="#4C72B0", edgecolor="black", linewidth=0.5)
    for b, v in zip(bars, P_fail_day):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.001, f"{v:.4f}",
                ha="center", va="bottom", fontsize=9)
    ax.axhline(theta, color="#C44E52", linestyle="--", linewidth=1.2,
               label=f"theta = 1 - 0.9^(1/5) = {theta:.4f}")
    ax.set_xlabel("Day k")
    ax.set_ylabel("Daily failure probability P_fail_k")
    ax.set_title("Problem 3 — Per-day failure probability")
    ax.legend(loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_xticks(x)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_contrib(phi_road: float, phi_queue: float, out_path: Path) -> None:
    """堵车 vs 排队 贡献度饼图 + 柱图。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax1.pie([phi_road, phi_queue], labels=["road (jam)", "queue"],
            colors=["#C44E52", "#4C72B0"], autopct="%1.1f%%",
            startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax1.set_title("Shapley contribution share")

    ax2.bar(["road", "queue"], [phi_road, phi_queue],
            color=["#C44E52", "#4C72B0"], edgecolor="black", linewidth=0.5)
    for i, v in enumerate([phi_road, phi_queue]):
        ax2.text(i, v + 0.01, f"{v:.3f}", ha="center", va="bottom", fontsize=10)
    ax2.set_ylim(0, max(phi_road, phi_queue) * 1.2 + 0.05)
    ax2.set_ylabel("phi")
    ax2.set_title("Road vs Queue contribution")
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    fig.suptitle("Problem 3 — Contribution decomposition (Shapley switch method)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_sensitivity_heatmap(sens: list, out_path: Path) -> None:
    """p_pk × p_off → R 的热力图（4×4 网格）。"""
    R_grid = np.zeros((len(P_PK_GRID), len(P_OFF_GRID)))
    P_grid = np.zeros_like(R_grid)
    for entry in sens:
        i = P_PK_GRID.index(entry["p_pk"])
        j = P_OFF_GRID.index(entry["p_off"])
        R_grid[i, j] = entry["R"]
        P_grid[i, j] = entry["P_fail"]

    fig, ax = plt.subplots(figsize=(7, 5.5))
    im = ax.imshow(R_grid, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Reliability R")

    ax.set_xticks(np.arange(len(P_OFF_GRID)))
    ax.set_yticks(np.arange(len(P_PK_GRID)))
    ax.set_xticklabels([f"{p:.1f}" for p in P_OFF_GRID])
    ax.set_yticklabels([f"{p:.1f}" for p in P_PK_GRID])
    ax.set_xlabel("p_off (off-peak jam prob.)")
    ax.set_ylabel("p_pk (peak jam prob.)")
    ax.set_title("Problem 3 — Sensitivity of R to (p_pk, p_off)")

    # 标注 R 和 P_fail
    for i in range(R_grid.shape[0]):
        for j in range(R_grid.shape[1]):
            text_color = "black" if R_grid[i, j] > 0.5 else "white"
            ax.text(j, i, f"R={R_grid[i, j]:.3f}\nPf={P_grid[i, j]:.3f}",
                    ha="center", va="center", color=text_color, fontsize=8)
    # 标注默认点
    di = P_PK_GRID.index(P_PK_DEFAULT)
    dj = P_OFF_GRID.index(P_OFF_DEFAULT)
    ax.add_patch(plt.Rectangle((dj - 0.5, di - 0.5), 1, 1, fill=False,
                                edgecolor="blue", linewidth=2.5))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_robustness_comparison(compared_plans: dict, out_path: Path) -> None:
    """recommend / balanced / robust 的可靠度与 Z4 对比图。"""
    names = list(compared_plans.keys())
    R_vals = [compared_plans[n]["R"] for n in names]
    Z4_vals = [compared_plans[n]["Z4"] for n in names]

    fig, ax1 = plt.subplots(figsize=(8.5, 4.8))
    x = np.arange(len(names))
    bars = ax1.bar(x - 0.18, R_vals, width=0.36, color="#4C72B0",
                   edgecolor="black", linewidth=0.5, label="Reliability R")
    ax1.axhline(0.9, color="#C44E52", linestyle="--", linewidth=1.2,
                label="target R=0.9")
    ax1.set_ylabel("Reliability R")
    ax1.set_ylim(0, 1.05)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    for b, v in zip(bars, R_vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}",
                 ha="center", va="bottom", fontsize=9)

    ax2 = ax1.twinx()
    ax2.plot(x + 0.18, Z4_vals, marker="o", color="#55A868",
             linewidth=2.0, label="Z4 (min buffer)")
    ax2.set_ylabel("Z4 min buffer (h)")
    for xi, v in zip(x + 0.18, Z4_vals):
        ax2.text(xi, v, f"{v:.2f}", ha="left", va="bottom", fontsize=9,
                 color="#2E6F40")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.set_title("Problem 3 — Robustness comparison of three plans")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def evaluate_plan(plan: dict, N: int, p_pk: float, p_off: float,
                  l_min: np.ndarray, l_comf: np.ndarray,
                  o_op: np.ndarray, o_cl: np.ndarray, D: np.ndarray,
                  seed: int) -> dict:
    """对单个方案执行默认 Monte Carlo + Shapley，并合并方案目标值。"""
    mc = monte_carlo(plan, N, True, True, p_pk, p_off,
                     l_min, l_comf, o_op, o_cl, D, seed=seed)
    sh = shapley(plan, N, p_pk, p_off,
                 l_min, l_comf, o_op, o_cl, D, seed=seed + 100)
    return {
        "selected": plan["selected"],
        "Z1": plan["Z1"], "Z2": plan["Z2"], "Z3": plan["Z3"],
        "Z4": plan["Z4"], "Z4_mean": plan["Z4_mean"],
        "F": plan["F"],
        "Tks": plan["Tks"],
        "buffers": plan.get("buffers", []),
        "R": mc["R"], "P_fail": mc["P_fail"], "CI_95": mc["CI_95"],
        "P_fail_day": mc["P_fail_day"],
        "daily_fail_probability": mc["P_fail_day"],
        "phi_spot": mc["phi_spot"],
        "phi_road": sh["phi_road"], "phi_queue": sh["phi_queue"],
    }


# ---------- 数据装载 ----------
def load_arrays(root: Path = ROOT):
    """读取 attractions.csv + dist.csv，返回 l_min, l_comf, o_op, o_cl, D。"""
    attractions = pd.read_csv(root / "attractions.csv")
    l_min = attractions["l_min"].to_numpy()
    l_comf = attractions["l_comf"].to_numpy()
    o_op = attractions["open_hour"].to_numpy()
    o_cl = attractions["close_hour"].to_numpy()
    D = np.loadtxt(root / "dist.csv", delimiter=",")
    return l_min, l_comf, o_op, o_cl, D


# ---------- 主流程 ----------
def run(verbose: bool = True) -> dict:
    """问题三完整流程：主结果 + Shapley + 敏感性扫描 + 薄弱点 + 4 张图。"""
    log_path = OUT_LOGS / "solve_p3.log"
    logger = logging.getLogger("solve_p3")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.info("== solve_p3.py START ==")

    with open(ROOT / "baseline_plan.json", "r", encoding="utf-8") as f:
        bp_doc = json.load(f)
    plan = bp_doc["baseline_plan"]
    logger.info("baseline_plan loaded: selected=%s, F=%.4f",
                plan["selected"], plan["F"])

    l_min, l_comf, o_op, o_cl, D = load_arrays()

    # 主结果
    logger.info("Run MC main: N=%d  p_pk=%.2f  p_off=%.2f",
                N_SIM, P_PK_DEFAULT, P_OFF_DEFAULT)
    mc_main = monte_carlo(plan, N_SIM, True, True,
                          P_PK_DEFAULT, P_OFF_DEFAULT,
                          l_min, l_comf, o_op, o_cl, D, seed=SEED)
    sh_main = shapley(plan, N_SIM, P_PK_DEFAULT, P_OFF_DEFAULT,
                      l_min, l_comf, o_op, o_cl, D, seed=SEED + 100)
    wp = weak_points(mc_main)
    logger.info("MC main R=%.4f  P_fail=%.4f  CI=%.4f",
                mc_main["R"], mc_main["P_fail"], mc_main["CI_95"])
    logger.info("Shapley phi_road=%.3f phi_queue=%.3f",
                sh_main["phi_road"], sh_main["phi_queue"])

    # 敏感性扫描
    logger.info("Sensitivity scan: %dx%d grid, N=%d per cell",
                len(P_PK_GRID), len(P_OFF_GRID), N_SIM)
    sens = sensitivity_scan(plan, N_SIM, l_min, l_comf, o_op, o_cl, D, logger=logger)

    # 三方案默认扰动对比
    compared_plans = {}
    for idx, name in enumerate(("recommend", "balanced", "robust")):
        cmp_plan = bp_doc["profiles"][name]["top"][0]
        compared_plans[name] = evaluate_plan(
            cmp_plan, N_SIM, P_PK_DEFAULT, P_OFF_DEFAULT,
            l_min, l_comf, o_op, o_cl, D, seed=SEED,
        )
        logger.info("compare %s: R=%.4f P_fail=%.4f Z4=%.3f",
                    name, compared_plans[name]["R"],
                    compared_plans[name]["P_fail"],
                    compared_plans[name]["Z4"])

    plans_meeting = [name for name, item in compared_plans.items() if item["R"] >= 0.9]
    best_name = max(compared_plans, key=lambda n: compared_plans[n]["R"])
    if plans_meeting:
        fallback_advice = f"{plans_meeting[0]} reaches R >= 0.9 under default disturbance."
    else:
        fallback_advice = (
            "No plan reaches R >= 0.9 under p_pk=0.6. See sensitivity grid for thresholds; "
            "refer to v1.1/v1.1.1 paper-level interpretation."
        )
    robust_diagnosis = {
        "target_R": 0.9,
        "plans_meeting_target": plans_meeting,
        "best_plan_under_target": best_name,
        "best_R": compared_plans[best_name]["R"],
        "fallback_advice": fallback_advice,
    }

    # 汇总 JSON
    report = {
        "assumptions": {
            "boundary_v111_applied": True,
            "tau_dep_per_day": TAU_DEP_K,
            "tau_back_max_per_day": TAU_BACK_MAX_K,
            "T_scenic_max_per_day": T_SCENIC_MAX_K,
            "p_peak_default": P_PK_DEFAULT,
            "p_off_default": P_OFF_DEFAULT,
            "queue_no_extra_prob": True,
            "N_simulations": N_SIM,
            "sensitivity_N_simulations": N_SIM,
            "trip_scope": "scenic_area_only",
            "seed": SEED,
            "early_arrival_handling": "wait_until_open",
        },
        "main_result": {
            "R": mc_main["R"],
            "P_fail": mc_main["P_fail"],
            "CI_95": mc_main["CI_95"],
            "P_fail_day": mc_main["P_fail_day"],
            "phi_spot": mc_main["phi_spot"],
            "phi_road": sh_main["phi_road"],
            "phi_queue": sh_main["phi_queue"],
            "shapley_raw": {
                "P0": sh_main["P0"], "PR": sh_main["PR"],
                "PQ": sh_main["PQ"], "PF": sh_main["PF"],
            },
        },
        "weak_points": wp,
        "sensitivity_grid": sens,
        "compared_plans": compared_plans,
        "robust_diagnosis": robust_diagnosis,
    }
    with open(ROOT / "reliability_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 绘图
    plot_daily_fail(mc_main["P_fail_day"], wp["theta_per_day"],
                    OUT_FIGURES / "fig_daily_fail.png")
    plot_contrib(sh_main["phi_road"], sh_main["phi_queue"],
                 OUT_FIGURES / "fig_contribution.png")
    plot_sensitivity_heatmap(sens, OUT_FIGURES / "fig_sensitivity_heatmap.png")
    plot_robustness_comparison(compared_plans,
                               OUT_FIGURES / "fig_robustness_comparison.png")

    if verbose:
        print(f"[P3] R = {mc_main['R']:.4f}  P_fail = {mc_main['P_fail']:.4f}  "
              f"± {mc_main['CI_95']:.4f}")
        print(f"[P3] phi_road = {sh_main['phi_road']:.3f}  "
              f"phi_queue = {sh_main['phi_queue']:.3f}")
        print(f"[P3] target_R_met = {wp['target_R_met']}  "
              f"weak_days = {wp['weak_days']}  weak_spots = {wp['weak_spots']}")
        print(f"[P3] sensitivity grid: {len(sens)} cells")
        for name in ("recommend", "balanced", "robust"):
            cp = compared_plans[name]
            print(f"[P3] compare={name:9s} R={cp['R']:.4f} "
                  f"P_fail={cp['P_fail']:.4f} Z4={cp['Z4']:.3f}")

    logger.info("== solve_p3.py END ==")
    return report


if __name__ == "__main__":
    run()
