"""Econometric lag-time detector (EIA vs. EPPO/DOEB) and Bio-BCP policy engine."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
import sys
from typing import Dict, List, Optional, Sequence, Tuple

LITERS_PER_BARREL = 158.987
BASELINE_CRUDE_USD = 74.0
BASELINE_DIESEL_THB = 30.50
DAILY_FUEL_DEMAND_ML = 98.0
TARGETED_SECTOR_SHARE = 0.42


def generate_calibrated_series(
    days: int = 120,
    true_lag_days: int = 10,
    seed: int = 2026,
) -> List[Dict[str, float]]:
    """Generates calibrated daily EIA crude (USD/bbl) and domestic retail diesel (THB/L)."""
    rng = random.Random(seed)
    eia_crude: List[float] = [BASELINE_CRUDE_USD]

    for t in range(1, days):
        geopolitical_pulse = (
            22.0 * math.exp(-((t - 34) ** 2) / 18.0)
            + 15.0 * math.exp(-((t - 82) ** 2) / 22.0)
        )
        next_crude = 0.74 * eia_crude[-1] + 0.26 * (BASELINE_CRUDE_USD + geopolitical_pulse)
        eia_crude.append(round(next_crude + rng.gauss(0.0, 0.65), 3))

    domestic_diesel: List[float] = [BASELINE_DIESEL_THB] * days
    for t in range(1, days):
        lag_idx = max(0, t - true_lag_days)
        lagged_shock = 0.145 * (eia_crude[lag_idx] - BASELINE_CRUDE_USD)
        next_diesel = (
            0.62 * domestic_diesel[t - 1]
            + 0.38 * (BASELINE_DIESEL_THB + lagged_shock)
            + rng.gauss(0.0, 0.06)
        )
        domestic_diesel[t] = round(next_diesel, 3)

    return [
        {
            "day_index": float(idx),
            "eia_crude_usd_bbl": eia_crude[idx],
            "domestic_diesel_thb_l": domestic_diesel[idx],
        }
        for idx in range(days)
    ]


def _first_differences(values: Sequence[float]) -> List[float]:
    return [values[i] - values[i - 1] for i in range(1, len(values))]


def _pearson_r(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 3 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    if den_x <= 1e-12 or den_y <= 1e-12:
        return 0.0
    return num / math.sqrt(den_x * den_y)


def detect_optimal_lag(
    crude_series: Sequence[float],
    diesel_series: Sequence[float],
    max_lag: int = 20,
) -> Dict[str, object]:
    """Finds the transmission lag k maximizing first-difference cross-correlation."""
    d_crude = _first_differences(crude_series)
    d_diesel = _first_differences(diesel_series)

    profile: List[Dict[str, float]] = []
    best_lag = 0
    best_corr = -2.0

    for lag in range(0, max_lag + 1):
        xs = d_crude[: len(d_crude) - lag] if lag > 0 else d_crude
        ys = d_diesel[lag:]
        r_val = round(_pearson_r(xs, ys), 4)
        profile.append({"lag_days": float(lag), "correlation_r": r_val})
        if r_val > best_corr:
            best_corr = r_val
            best_lag = lag

    return {
        "optimal_lag_days": best_lag,
        "peak_correlation_r": best_corr,
        "lag_profile": profile,
    }


def _solve_linear_system(matrix: List[List[float]], rhs: List[float]) -> List[float]:
    """Solves A * beta = rhs via Gaussian elimination with partial pivoting."""
    m = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]

    for col in range(m):
        pivot_row = max(range(col, m), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot_row][col]) < 1e-12:
            aug[pivot_row][col] = 1e-12
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

        pivot_val = aug[col][col]
        for r in range(col + 1, m):
            factor = aug[r][col] / pivot_val
            for c in range(col, m + 1):
                aug[r][c] -= factor * aug[col][c]

    solution = [0.0] * m
    for r in range(m - 1, -1, -1):
        s = aug[r][m] - sum(aug[r][c] * solution[c] for c in range(r + 1, m))
        solution[r] = s / aug[r][r]
    return solution


def _ols_rss(design_rows: List[List[float]], y_vals: Sequence[float]) -> float:
    """Computes Ordinary Least Squares Residual Sum of Squares (RSS)."""
    k = len(design_rows[0])
    xtx = [[0.0] * k for _ in range(k)]
    xty = [0.0] * k

    for row, y in zip(design_rows, y_vals):
        for i in range(k):
            xty[i] += row[i] * y
            ri = row[i]
            for j in range(i, k):
                xtx[i][j] += ri * row[j]

    for i in range(k):
        for j in range(i):
            xtx[i][j] = xtx[j][i]

    beta = _solve_linear_system(xtx, xty)
    rss = 0.0
    for row, y in zip(design_rows, y_vals):
        pred = sum(b * x for b, x in zip(beta, row))
        rss += (y - pred) ** 2
    return rss


def compute_granger_f_stat(
    crude_series: Sequence[float],
    diesel_series: Sequence[float],
    lag_order: int = 10,
) -> Tuple[float, float, float]:
    """Tests whether lagged crude changes Granger-cause domestic diesel changes."""
    dx = _first_differences(crude_series)
    dy = _first_differences(diesel_series)
    n_obs = len(dy) - lag_order
    if n_obs <= (2 * lag_order + 2):
        raise ValueError("Time series too short for requested lag_order.")

    restricted_x: List[List[float]] = []
    unrestricted_x: List[List[float]] = []
    target_y: List[float] = []

    for t in range(lag_order, len(dy)):
        ar_terms = [dy[t - k] for k in range(1, lag_order + 1)]
        x_lags = [dx[t - k] for k in range(1, lag_order + 1)]
        restricted_x.append([1.0] + ar_terms)
        unrestricted_x.append([1.0] + ar_terms + x_lags)
        target_y.append(dy[t])

    rss_r = _ols_rss(restricted_x, target_y)
    rss_u = _ols_rss(unrestricted_x, target_y)
    df_num = float(lag_order)
    df_den = float(n_obs - (2 * lag_order) - 1)

    f_stat = ((rss_r - rss_u) / df_num) / (rss_u / df_den)
    return round(max(0.0, f_stat), 3), round(rss_r, 4), round(rss_u, 4)


def simulate_bio_bcp_policy(
    crude_spike_usd: float = 115.0,
    bio_blend_pct: float = 18.0,
    excise_buffer_thb: float = 1.50,
    cap_price_thb: float = 32.00,
) -> Dict[str, object]:
    """Compares Blanket Mass Subsidy against PetroPulse Bio-BCP + Targeted Subsidy."""
    bounded_blend = max(5.0, min(35.0, float(bio_blend_pct)))
    crude_delta = max(0.0, float(crude_spike_usd) - BASELINE_CRUDE_USD)

    unmitigated_retail_thb = round(BASELINE_DIESEL_THB + (crude_delta * 0.22), 2)
    per_liter_gap_blanket = max(0.0, unmitigated_retail_thb - cap_price_thb)
    blanket_daily_burn_m_thb = round(DAILY_FUEL_DEMAND_ML * per_liter_gap_blanket, 2)

    bio_dampening_thb = crude_delta * 0.22 * (0.32 * (bounded_blend / 20.0))
    bcp_market_price_thb = round(
        max(BASELINE_DIESEL_THB, unmitigated_retail_thb - bio_dampening_thb - excise_buffer_thb),
        2,
    )

    targeted_volume_ml = DAILY_FUEL_DEMAND_ML * TARGETED_SECTOR_SHARE
    targeted_gap_thb = max(0.0, bcp_market_price_thb - cap_price_thb)
    targeted_daily_burn_m_thb = round(targeted_volume_ml * targeted_gap_thb, 2)

    fiscal_savings_m_thb = round(blanket_daily_burn_m_thb - targeted_daily_burn_m_thb, 2)
    fiscal_savings_pct = (
        round((fiscal_savings_m_thb / blanket_daily_burn_m_thb) * 100.0, 1)
        if blanket_daily_burn_m_thb > 0
        else 0.0
    )

    displaced_liters_m = DAILY_FUEL_DEMAND_ML * (bounded_blend / 100.0)
    crude_import_offset_kbd = round((displaced_liters_m * 1_000_000.0) / LITERS_PER_BARREL / 1000.0, 2)

    return {
        "crude_spike_usd_bbl": round(float(crude_spike_usd), 2),
        "bio_blend_pct": bounded_blend,
        "unmitigated_diesel_thb_l": unmitigated_retail_thb,
        "bcp_stabilized_diesel_thb_l": bcp_market_price_thb,
        "blanket_oil_fund_burn_m_thb_day": blanket_daily_burn_m_thb,
        "targeted_oil_fund_burn_m_thb_day": targeted_daily_burn_m_thb,
        "daily_fiscal_savings_m_thb": fiscal_savings_m_thb,
        "fiscal_leakage_reduction_pct": fiscal_savings_pct,
        "crude_import_offset_kbd": crude_import_offset_kbd,
        "lead_time_protocol": {
            "t_minus_1_to_3_days": "Activate dynamic Oil Fund buffer & temporary Excise Tax absorber",
            "t_minus_7_to_14_days": "Release DOEB strategic reserve & scale E20/B10 UCO domestic blending",
        },
    }


def run_full_analysis(
    crude_spike_usd: float,
    bio_blend_pct: float,
    output_dir: Path,
) -> Dict[str, object]:
    """Generates calibrated dataset, runs Granger/lag statistics, and writes artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = generate_calibrated_series(days=120, true_lag_days=10, seed=2026)

    crude = [r["eia_crude_usd_bbl"] for r in rows]
    diesel = [r["domestic_diesel_thb_l"] for r in rows]

    lag_result = detect_optimal_lag(crude, diesel, max_lag=20)
    f_lag10, rss_r10, rss_u10 = compute_granger_f_stat(crude, diesel, lag_order=10)
    f_lag5, _, _ = compute_granger_f_stat(crude, diesel, lag_order=5)
    policy_sim = simulate_bio_bcp_policy(crude_spike_usd=crude_spike_usd, bio_blend_pct=bio_blend_pct)

    csv_path = output_dir / "eia_eppo_lag_series.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["day_index", "eia_crude_usd_bbl", "domestic_diesel_thb_l"])
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "model": "PetroPulse Shockwave Lag-Time & Bio-BCP Simulator",
        "econometric_validation": {
            "detected_optimal_lag_days": lag_result["optimal_lag_days"],
            "peak_cross_correlation_r": lag_result["peak_correlation_r"],
            "granger_f_stat_lag_10": f_lag10,
            "granger_f_stat_lag_5_pre_window": f_lag5,
            "restricted_rss": rss_r10,
            "unrestricted_rss": rss_u10,
        },
        "policy_simulation": policy_sim,
    }

    json_path = output_dir / "petropulse_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run PetroPulse lag-time & Bio-BCP analysis.")
    parser.add_argument("--crude-spike", type=float, default=115.0, help="Global crude shock price (USD/bbl).")
    parser.add_argument("--bio-blend-pct", type=float, default=18.0, help="Domestic E20/B10 bio-fuel blend %.")
    parser.add_argument("--output-dir", type=str, default="./outputs", help="Directory for CSV & JSON outputs.")
    args = parser.parse_args(argv)

    report = run_full_analysis(
        crude_spike_usd=args.crude_spike,
        bio_blend_pct=args.bio_blend_pct,
        output_dir=Path(args.output_dir),
    )
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
