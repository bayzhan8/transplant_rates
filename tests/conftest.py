"""Shared pytest fixtures.

Tests run entirely on the bundled synthetic dataset (fabricated values, no real
SRTR/OASIM data and no cluster paths). If the dataset is missing it is generated
on the fly into a temporary directory.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")  # never open a window during tests

REPO_ROOT = Path(__file__).resolve().parents[1]
# Make `import transplant_rates` work from a source checkout (not just pip install).
sys.path.insert(0, str(REPO_ROOT.parent))
# Make `import generate_synthetic_data` work.
sys.path.insert(0, str(REPO_ROOT / "examples"))

SIM_BEGIN = datetime(2021, 3, 15)
SIM_END = datetime(2022, 3, 15)


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    """Path to a synthetic dataset, generated fresh into a temp dir."""
    import generate_synthetic_data as gen

    out = tmp_path_factory.mktemp("synthetic_data")
    gen.OUT_DIR = out
    gen.main()
    return out


@pytest.fixture()
def core_paths(data_dir) -> dict:
    return dict(
        donor_path=data_dir / "cleaned_donor_data.csv",
        candidate_path=data_dir / "cleaned_timevarying_KAS_candidate_data.csv",
        static_path=data_dir / "cleaned_static_candidate_data.csv",
        timevarying_path=data_dir / "cleaned_timevarying_candidate_data.csv",
        gen_removal_path=data_dir / "generated_removal_candidate_data.csv",
        gen_hist_path=data_dir / "generated_history_candidate_data.csv",
        race_path=data_dir / "can_race.csv",
    )


@pytest.fixture()
def calc(core_paths):
    from transplant_rates import TransplantRatesCalculator

    c = TransplantRatesCalculator(SIM_BEGIN, SIM_END, cache_dir=None)
    c.load_core_data(**core_paths)
    return c


@pytest.fixture()
def offers_calc(core_paths, data_dir):
    from transplant_rates import OffersCalculator

    c = OffersCalculator(SIM_BEGIN, SIM_END, cache_dir=None)
    c.load_core_data(**core_paths)
    c.register_offers([data_dir / "offers_current.txt"])
    return c
