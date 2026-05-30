"""Generate a small, fully synthetic dataset for the transplant_rates package.

Every value here is randomly fabricated. This script does NOT read SRTR, OASIM,
or any other real data, and it has no dependency on any cluster (``/gpfs``) path.
Its only purpose is to give the package something realistic-shaped to run on so
that examples and tests work for anyone who clones the repository.

The schema (column names, value domains, merge keys) mirrors what the package's
code expects; see the module docstrings in ``tr_calculator.py`` and
``offers_calculator.py``.

Run:
    python examples/generate_synthetic_data.py

Output: CSV / TXT files under ``examples/synthetic_data/``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Simulation window (matches the package examples).
SIM_BEGIN = datetime(2021, 3, 15)
SIM_END = datetime(2022, 3, 15)

# Reproducible fabrication.
RNG = np.random.default_rng(7)

# Cohort sizes (kept small so the files are tiny and tests run fast).
N_KIDNEY_CANDIDATES = 480
N_PANCREAS_CANDIDATES = 20  # exercise the kidney-only (wl_org == "KI") filter
N_DONORS = 300

OUT_DIR = Path(__file__).resolve().parent / "synthetic_data"

ABO_CODES = ["O", "A", "B", "AB", "A1", "A2"]  # subtypes are normalized downstream
ABO_WEIGHTS = [0.45, 0.30, 0.12, 0.05, 0.05, 0.03]
GENDERS = ["M", "F"]
RACES = ["WHITE", "BLACK", "ASIAN", "NATIVE", "PACIFIC", "MULTI"]
ETHNICITIES = ["NLATIN", "LATINO"]
SEGMENTS = ["local", "regional", "national"]


def _rand_dates(start: datetime, end: datetime, n: int) -> np.ndarray:
    """n random datetimes uniformly between start and end."""
    span_days = (end - start).days
    offsets = RNG.integers(0, max(span_days, 1), size=n)
    return np.array([start + timedelta(days=int(d)) for d in offsets])


def _fmt(dates) -> list[str]:
    return [pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates]


def build_candidates():
    """Static candidate table + the id/age/abo bookkeeping reused elsewhere."""
    n = N_KIDNEY_CANDIDATES + N_PANCREAS_CANDIDATES
    # String IDs (like real OASIM/SRTR ids) avoid int/str merge ambiguity.
    cand_id = np.array([f"C{i}" for i in range(100_000, 100_000 + n)], dtype=object)

    # ~8% pediatric so the <18 age bin is populated.
    is_ped = RNG.random(n) < 0.08
    age = np.where(is_ped, RNG.integers(1, 18, n), RNG.integers(18, 86, n)).astype(float)

    # Listing dates spread from ~2 years before the window to mid-window.
    listing = _rand_dates(SIM_BEGIN - timedelta(days=730), SIM_END - timedelta(days=30), n)

    # Most candidates have no removal date; a minority are removed within the window.
    rem = np.array([pd.NaT] * n, dtype="object")
    removed = RNG.random(n) < 0.15
    for i in np.where(removed)[0]:
        low = max(pd.Timestamp(listing[i]), pd.Timestamp(SIM_BEGIN))
        rem[i] = low + timedelta(days=int(RNG.integers(10, 300)))

    wl_org = np.array(["KI"] * n)
    wl_org[N_KIDNEY_CANDIDATES:] = "PA"  # last block are pancreas (filtered out)

    static = pd.DataFrame(
        {
            "cand_id": cand_id,
            "px_id": cand_id,  # 1:1 link to the race file
            "wl_org": wl_org,
            "can_listing_dt": _fmt(listing),
            "can_rem_dt": [pd.Timestamp(x).strftime("%Y-%m-%d") if pd.notna(x) else "" for x in rem],
            "can_age_at_listing": age,
            "can_abo": RNG.choice(ABO_CODES, size=n, p=ABO_WEIGHTS),
            "can_gender": RNG.choice(GENDERS, size=n),
            "can_center_longitude": RNG.uniform(-122.0, -71.0, n).round(4),
            "can_center_latitude": RNG.uniform(25.0, 47.0, n).round(4),
        }
    )
    return static


def build_donors():
    don_id = np.array([f"D{i}" for i in range(900_000, 900_000 + N_DONORS)], dtype=object)
    donor = pd.DataFrame(
        {
            "don_id": don_id,
            "don_event_datetime": _fmt(_rand_dates(SIM_BEGIN, SIM_END, N_DONORS)),
            "kdpi_at_allocation": RNG.uniform(0, 100, N_DONORS).round(1),
            "don_age": RNG.integers(1, 80, N_DONORS),
            "don_center_longitude": RNG.uniform(-122.0, -71.0, N_DONORS).round(4),
            "don_center_latitude": RNG.uniform(25.0, 47.0, N_DONORS).round(4),
        }
    )
    return donor


def build_epts_events(static):
    """KAS time-varying EPTS events (one+ per candidate) and historical EPTS rows."""
    ki = static[static["wl_org"] == "KI"]["cand_id"].to_numpy()

    cand_ids, dates, epts = [], [], []
    for cid in ki:
        n_events = int(RNG.integers(1, 3))
        # At least one event before the window start for ~85% of candidates.
        before = RNG.random() < 0.85
        for k in range(n_events):
            if before and k == 0:
                d = SIM_BEGIN - timedelta(days=int(RNG.integers(1, 400)))
            else:
                d = SIM_BEGIN + timedelta(days=int(RNG.integers(-400, 300)))
            cand_ids.append(cid)
            dates.append(d)
            epts.append(round(float(RNG.uniform(0, 1)), 4))

    candidate = pd.DataFrame(
        {"cand_id": cand_ids, "cand_event_datetime": _fmt(dates), "epts_pct": epts}
    )

    # generated_history: extra historical EPTS rows for ~30% of candidates.
    h_ids, h_dates, h_epts = [], [], []
    for cid in ki:
        if RNG.random() < 0.30:
            h_ids.append(cid)
            h_dates.append(SIM_BEGIN - timedelta(days=int(RNG.integers(400, 1000))))
            h_epts.append(round(float(RNG.uniform(0, 1)), 4))
    gen_hist = pd.DataFrame(
        {"cand_id": h_ids, "cand_event_datetime": _fmt(h_dates), "epts_pct": h_epts}
    )
    return candidate, gen_hist


def build_cpra_events(static):
    """Time-varying CPRA events (OASIM 2023 path reads CPRA from here)."""
    ki = static[static["wl_org"] == "KI"]["cand_id"].to_numpy()
    cand_ids, dates, cpra = [], [], []
    for cid in ki:
        n_events = int(RNG.integers(1, 3))
        for k in range(n_events):
            d = SIM_BEGIN + timedelta(days=int(RNG.integers(-400, 300)))
            # Most candidates low CPRA, a tail of highly sensitized.
            val = float(RNG.beta(1.2, 6.0))
            cand_ids.append(cid)
            dates.append(d)
            cpra.append(round(val, 4))
    return pd.DataFrame(
        {"cand_id": cand_ids, "cand_event_datetime": _fmt(dates), "canhx_cpra": cpra}
    )


def build_gen_removal(static):
    """Generated removal/death events for a subset of candidates."""
    ki = static[static["wl_org"] == "KI"]["cand_id"].to_numpy()
    ids, dates = [], []
    for cid in ki:
        if RNG.random() < 0.15:
            ids.append(cid)
            dates.append(SIM_BEGIN + timedelta(days=int(RNG.integers(10, 360))))
    return pd.DataFrame({"cand_id": ids, "cand_event_datetime": _fmt(dates)})


def build_race(static):
    ids = static["px_id"].to_numpy()
    n = len(ids)
    race = RNG.choice(RACES, size=n, p=[0.55, 0.22, 0.12, 0.04, 0.03, 0.04])
    # Sprinkle a few missing values (filled with "Unknown" by the loader).
    race = race.astype(object)
    race[RNG.random(n) < 0.02] = np.nan
    return pd.DataFrame(
        {
            "px_id": ids,
            "can_race_srtr": race,
            "can_ethnicity_srtr": RNG.choice(ETHNICITIES, size=n, p=[0.82, 0.18]),
        }
    )


def build_policy(static, donor, accept_bias):
    """Match each donor to a distinct kidney candidate -> one transplant per row.

    ``accept_bias`` nudges which candidates get matched so two policies differ.
    Returns the policy transplant table plus the (don_id -> cand_id) mapping so
    the offers file can stay consistent with it.
    """
    ki = static[static["wl_org"] == "KI"]["cand_id"].to_numpy()
    don_ids = donor["don_id"].to_numpy()

    # Rank candidates by a noisy score; higher accept_bias favors a different set.
    score = RNG.random(len(ki)) + accept_bias * np.linspace(0, 1, len(ki))
    order = ki[np.argsort(-score)]
    recipients = order[: len(don_ids)]

    organ = RNG.choice(["LKI", "RKI"], size=len(don_ids))
    policy = pd.DataFrame(
        {
            "cand_id": recipients,
            "don_id": don_ids,
            "organ": organ,
            "rank": RNG.integers(1, 30, len(don_ids)),
        }
    )
    mapping = dict(zip(don_ids, recipients))
    return policy, mapping


def build_offers(static, donor, mapping):
    """One row per candidate-kidney offer; the mapped recipient is 'accepted'."""
    ki = static[static["wl_org"] == "KI"]["cand_id"].to_numpy()
    don_event = dict(zip(donor["don_id"], pd.to_datetime(donor["don_event_datetime"])))

    rows = []
    for don_id, recipient in mapping.items():
        n_offers = int(RNG.integers(3, 12))
        offered = list(RNG.choice(ki, size=n_offers, replace=False))
        if recipient not in offered:
            offered[0] = recipient
        RNG.shuffle(offered)
        base_dt = don_event[don_id]
        for rank, cid in enumerate(offered, start=1):
            rows.append(
                {
                    "iteration": 0,
                    "don_id": don_id,
                    "cand_id": cid,
                    "rank": rank,
                    "segment": RNG.choice(SEGMENTS, p=[0.6, 0.3, 0.1]),
                    "accepted": bool(cid == recipient),
                    "probability": round(float(RNG.uniform(0, 1)), 4),
                    "offer_datetime": pd.Timestamp(base_dt).strftime("%Y-%m-%d"),
                }
            )
    return pd.DataFrame(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    static = build_candidates()
    donor = build_donors()
    candidate, gen_hist = build_epts_events(static)
    timevarying = build_cpra_events(static)
    gen_removal = build_gen_removal(static)
    race = build_race(static)

    policy_current, map_current = build_policy(static, donor, accept_bias=0.0)
    policy_proposed_a, map_prop_a = build_policy(static, donor, accept_bias=1.5)
    policy_proposed_b, map_prop_b = build_policy(static, donor, accept_bias=1.8)

    offers_current = build_offers(static, donor, map_current)
    offers_proposed = build_offers(static, donor, map_prop_a)

    # Core tables.
    static.to_csv(OUT_DIR / "cleaned_static_candidate_data.csv", index=False)
    donor.to_csv(OUT_DIR / "cleaned_donor_data.csv", index=False)
    candidate.to_csv(OUT_DIR / "cleaned_timevarying_KAS_candidate_data.csv", index=False)
    timevarying.to_csv(OUT_DIR / "cleaned_timevarying_candidate_data.csv", index=False)
    gen_removal.to_csv(OUT_DIR / "generated_removal_candidate_data.csv", index=False)
    gen_hist.to_csv(OUT_DIR / "generated_history_candidate_data.csv", index=False)
    race.to_csv(OUT_DIR / "can_race.csv", index=False)

    # Policy outputs (.txt, comma-separated).
    policy_current.to_csv(OUT_DIR / "policy_current.txt", index=False)
    policy_proposed_a.to_csv(OUT_DIR / "policy_proposed_iter1.txt", index=False)
    policy_proposed_b.to_csv(OUT_DIR / "policy_proposed_iter2.txt", index=False)

    # Offers files.
    offers_current.to_csv(OUT_DIR / "offers_current.txt", index=False)
    offers_proposed.to_csv(OUT_DIR / "offers_proposed.txt", index=False)

    print(f"Wrote synthetic dataset to {OUT_DIR}")
    print(f"  candidates (static): {len(static)} ({(static.wl_org=='KI').sum()} kidney)")
    print(f"  donors:              {len(donor)}")
    print(f"  EPTS events:         {len(candidate)} (+{len(gen_hist)} historical)")
    print(f"  CPRA events:         {len(timevarying)}")
    print(f"  generated removals:  {len(gen_removal)}")
    print(f"  policy transplants:  {len(policy_current)} per policy")
    print(f"  offers (current):    {len(offers_current)} rows")


if __name__ == "__main__":
    main()
