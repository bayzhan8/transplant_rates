"""Tests for the OffersCalculator on synthetic data."""

from __future__ import annotations

import pandas as pd

from transplant_rates import read_offers_csv


def _offers(data_dir):
    return data_dir / "offers_current.txt"


def test_read_offers_csv_schema(data_dir):
    df = read_offers_csv(_offers(data_dir))
    required = {"don_id", "cand_id", "rank", "segment", "accepted", "probability", "iteration"}
    assert required <= set(df.columns)
    assert df["accepted"].dtype == bool
    # IDs are normalized to strings.
    assert df["don_id"].map(type).eq(str).all()


def test_offers_per_kidney_summary(offers_calc, data_dir):
    stats = offers_calc.summarize_offers_per_kidney(_offers(data_dir))
    assert stats["n_kidneys"] > 0
    assert stats["n_offers"] >= stats["n_kidneys"]
    assert stats["min"] >= 1
    assert stats["mean"] >= 1


def test_enriched_offers_has_joins(offers_calc, data_dir):
    enr = offers_calc.enriched_offers(_offers(data_dir))
    assert isinstance(enr, pd.DataFrame)
    for col in ("epts_pct", "kdpi_at_allocation", "can_race_srtr", "don_age"):
        assert col in enr.columns
    # KDPI in 0-100, EPTS in 0-1 where present.
    kdpi = enr["kdpi_at_allocation"].dropna()
    assert kdpi.between(0, 100).all()
    epts = enr["epts_pct"].dropna()
    assert epts.between(0, 1).all()


def test_kdpi_by_race_table(offers_calc, data_dir):
    table = offers_calc.summarize_kdpi_by_race(_offers(data_dir))
    assert isinstance(table, pd.DataFrame)
    assert len(table) > 0
    assert "median_kdpi" in table.columns
