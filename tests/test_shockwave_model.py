"""Unit tests for PetroPulse 10-day lag detection, Granger F-test, and Bio-BCP math."""

from pathlib import Path
import tempfile
import unittest

from src.shockwave_model import (
    compute_granger_f_stat,
    detect_optimal_lag,
    generate_calibrated_series,
    run_full_analysis,
    simulate_bio_bcp_policy,
)


class PetroPulseModelTestSuite(unittest.TestCase):
    def test_cross_correlation_recovers_exact_10_day_shockwave_lag(self) -> None:
        rows = generate_calibrated_series(days=120, true_lag_days=10, seed=2026)
        crude = [r["eia_crude_usd_bbl"] for r in rows]
        diesel = [r["domestic_diesel_thb_l"] for r in rows]

        lag_info = detect_optimal_lag(crude, diesel, max_lag=20)
        self.assertEqual(lag_info["optimal_lag_days"], 10)
        self.assertGreater(lag_info["peak_correlation_r"], 0.50)

    def test_granger_f_stat_becomes_highly_significant_at_10_day_horizon(self) -> None:
        rows = generate_calibrated_series(days=120, true_lag_days=10, seed=2026)
        crude = [r["eia_crude_usd_bbl"] for r in rows]
        diesel = [r["domestic_diesel_thb_l"] for r in rows]

        f_pre_lag, _, _ = compute_granger_f_stat(crude, diesel, lag_order=5)
        f_at_lag10, rss_r, rss_u = compute_granger_f_stat(crude, diesel, lag_order=10)

        self.assertLess(rss_u, rss_r)
        self.assertGreater(f_at_lag10, f_pre_lag)
        self.assertGreater(f_at_lag10, 4.0)

    def test_targeted_bio_bcp_reduces_oil_fund_burn_and_offsets_crude_imports(self) -> None:
        sim = simulate_bio_bcp_policy(crude_spike_usd=120.0, bio_blend_pct=20.0)

        self.assertLess(
            sim["targeted_oil_fund_burn_m_thb_day"],
            sim["blanket_oil_fund_burn_m_thb_day"],
        )
        self.assertGreater(sim["fiscal_leakage_reduction_pct"], 55.0)
        self.assertGreater(sim["crude_import_offset_kbd"], 100.0)

    def test_end_to_end_pipeline_exports_csv_and_json_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir)
            report = run_full_analysis(crude_spike_usd=115.0, bio_blend_pct=18.0, output_dir=out_path)

            self.assertTrue((out_path / "eia_eppo_lag_series.csv").is_file())
            self.assertTrue((out_path / "petropulse_report.json").is_file())
            self.assertEqual(report["econometric_validation"]["detected_optimal_lag_days"], 10)


if __name__ == "__main__":
    unittest.main()
