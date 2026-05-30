"""Tests for the transplant-rates pipeline on synthetic data."""

from __future__ import annotations

import math

import pandas as pd

from conftest import SIM_BEGIN, SIM_END


def _policy(data_dir):
    return data_dir / "policy_current.txt"


def test_load_core_data_filters_to_kidney(calc):
    # Pancreas candidates (wl_org == "PA") must be dropped.
    assert (calc.static["wl_org"] == "KI").all()
    # real_age is derived during loading.
    assert "real_age" in calc.static.columns
    assert "can_abo_replaced" in calc.static.columns
    # ABO subtypes are collapsed to major groups.
    assert set(calc.static["can_abo_replaced"].unique()) <= {"A", "B", "AB", "O"}


def test_person_times_positive(calc, data_dir):
    calc.add_policies([_policy(data_dir)])
    pt = calc.compute_person_times_for(_policy(data_dir))
    assert len(pt) > 0
    assert "time_difference" in pt.columns
    # Total person-time on the waitlist must be strictly positive.
    assert pt["time_difference"].clip(lower=0).sum() > 0
    # epts joined in.
    assert "epts_pct" in pt.columns
    assert pt["epts_pct"].between(0, 1).all()


def test_summary_table_shape_and_values(calc, data_dir):
    calc.add_policies([_policy(data_dir)], name_map={_policy(data_dir): "Current"})
    calc.add_policy_group(
        [data_dir / "policy_proposed_iter1.txt", data_dir / "policy_proposed_iter2.txt"],
        group_name="Proposed",
    )
    summary = calc.compute_summary_table()
    assert isinstance(summary, pd.DataFrame)
    assert len(summary) > 0
    # Single policy column + group mean/min/max columns.
    cols = set(summary.columns)
    assert "Current_mean" in cols
    assert {"Proposed_mean", "Proposed_min", "Proposed_max"} <= cols
    # Rates are finite and non-negative.
    numeric = summary.select_dtypes("number")
    assert (numeric.fillna(0) >= 0).all().all()
    assert numeric.to_numpy().sum() > 0


def test_age_rates_cover_bins(calc, data_dir):
    calc.add_policies([_policy(data_dir)])
    rates = calc.get_age_rates(_policy(data_dir))
    expected_bins = {(0, 18), (18, 35), (35, 50), (50, 65), (65, 90)}
    assert set(rates) == expected_bins
    assert all(math.isfinite(v) and v >= 0 for v in rates.values())


def test_race_rates_present(calc, data_dir):
    calc.add_policies([_policy(data_dir)])
    rates = calc.get_race_rates(_policy(data_dir))
    assert len(rates) > 0
    assert all(v >= 0 for v in rates.values())
