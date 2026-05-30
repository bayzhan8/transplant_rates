"""
Offers-level OASIM outputs: one row per offer (candidate × kidney), with rank, segment, acceptance.

Use :class:`OffersCalculator` after :meth:`load_core_data` (same inputs as
:class:`~tr_calculator.TransplantRatesCalculator`) so EPTS and KDPI can be joined.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import numpy as np
import pandas as pd

from .tr_calculator import TransplantRatesCalculator
from .plots import (
    offers_epts_kdpi_catplot,
    offers_epts_age_catplot,
    offers_candidate_donor_age_catplot,
    offers_candidate_donor_age_plot,
    offers_kdpi_by_race_catplot,
    offers_kdpi_by_wait_catplot,
    plot_offers_per_kidney_distribution,
)

logger = logging.getLogger(__name__)

# Log at INFO below this share of rows missing EPTS; WARNING at or above.
EPTS_GAP_WARN_SHARE = 0.01


def _normalize_entity_id(series: pd.Series) -> pd.Series:
    """
    Normalize donor/candidate IDs so merges match across files (e.g. 12345 vs \"12345.0\").
    """
    num = pd.to_numeric(series, errors="coerce")
    out = pd.Series(index=series.index, dtype=object)
    ok = num.notna()
    out[ok] = num[ok].astype(np.int64).astype(str)
    out[~ok] = series[~ok].astype(str).str.strip()
    return out


def _normalize_accepted(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    s = series.astype(str).str.strip().str.lower()
    return s.isin(("true", "1", "yes", "t"))


def read_offers_csv(path: Union[str, os.PathLike]) -> pd.DataFrame:
    """
    Load an offers file with columns:
    iteration, don_id, cand_id, rank, segment, accepted, probability

    **Optional** (for per-offer waiting time — each offer row can fall in a different bin):

    - ``offer_datetime`` / ``offer_dt`` / ``offer_time``: timestamp of the offer (merged with
      ``can_listing_dt`` in :meth:`OffersCalculator.enriched_offers` to get wait years).
    - ``wait_time_years`` / ``wait_years``: precomputed wait in years at that offer.
    - ``wait_time_days`` / ``wait_days``: precomputed wait in days.
    """
    df = pd.read_csv(path, low_memory=False)
    df.columns = [str(c).lower() for c in df.columns]
    required = {"don_id", "cand_id", "rank", "segment", "accepted", "probability"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Offers file {path} missing columns: {sorted(missing)}")
    if "iteration" not in df.columns:
        df["iteration"] = 0
    df["don_id"] = _normalize_entity_id(df["don_id"])
    df["cand_id"] = _normalize_entity_id(df["cand_id"])
    df["accepted"] = _normalize_accepted(df["accepted"])
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df["probability"] = pd.to_numeric(df["probability"], errors="coerce")

    if "offer_datetime" not in df.columns:
        for alias in ("offer_dt", "offer_time"):
            if alias in df.columns:
                df["offer_datetime"] = pd.to_datetime(df[alias], errors="coerce")
                break
    else:
        df["offer_datetime"] = pd.to_datetime(df["offer_datetime"], errors="coerce")

    if "offer_wait_years" not in df.columns:
        if "wait_time_years" in df.columns:
            df["offer_wait_years"] = pd.to_numeric(df["wait_time_years"], errors="coerce")
        elif "wait_years" in df.columns:
            df["offer_wait_years"] = pd.to_numeric(df["wait_years"], errors="coerce")
        elif "wait_time_days" in df.columns:
            df["offer_wait_years"] = pd.to_numeric(df["wait_time_days"], errors="coerce") / 365.25
        elif "wait_days" in df.columns:
            df["offer_wait_years"] = pd.to_numeric(df["wait_days"], errors="coerce") / 365.25

    return df


# Years waited at each offer (bin edges for summaries/plots; last edge may be omitted and +inf appended).
DEFAULT_OFFER_WAIT_EDGES_YEARS: List[float] = [0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, float("inf")]


def _normalize_wait_edges(wait_edges_years: Optional[List[float]]) -> List[float]:
    edges = (
        list(wait_edges_years)
        if wait_edges_years is not None
        else list(DEFAULT_OFFER_WAIT_EDGES_YEARS)
    )
    if len(edges) < 2:
        raise ValueError("wait_edges_years must have at least two values")
    if edges[-1] != float("inf"):
        edges = edges + [float("inf")]
    return edges


def _group_keys_for_kidney(df: pd.DataFrame, group_by_iteration: bool) -> List[str]:
    keys = ["don_id"]
    if group_by_iteration and df["iteration"].nunique() > 1:
        keys = ["iteration", "don_id"]
    return keys


def _counts_per_kidney(df: pd.DataFrame, group_by_iteration: bool) -> pd.Series:
    if not group_by_iteration and df["iteration"].nunique() > 1:
        logger.warning(
            "Multiple iterations in offers file; grouping only by don_id pools across iterations. "
            "Use group_by_iteration=True for per-(iteration, kidney) counts."
        )
    keys = _group_keys_for_kidney(df, group_by_iteration)
    return df.groupby(keys, observed=True).size().rename("n_offers")


def _distribution_stats(counts: pd.Series) -> Dict[str, Any]:
    if len(counts) == 0:
        return {
            "n_kidneys": 0,
            "n_offers": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p25": float("nan"),
            "p75": float("nan"),
        }
    return {
        "n_kidneys": int(len(counts)),
        "n_offers": int(counts.sum()),
        "mean": float(counts.mean()),
        "median": float(counts.median()),
        "std": float(counts.std(ddof=0)) if len(counts) > 1 else 0.0,
        "min": int(counts.min()),
        "max": int(counts.max()),
        "p25": float(counts.quantile(0.25)),
        "p75": float(counts.quantile(0.75)),
    }


class OffersCalculator(TransplantRatesCalculator):
    """
    Analyze OASIM **offers** files (one row per offer) with optional joins to EPTS / KDPI.

    Inherits :meth:`load_core_data` and all transplant-rate tooling from
    :class:`~tr_calculator.TransplantRatesCalculator`. Register offers paths with
    :meth:`register_offers`, then call summarizers or plots.
    """

    def __init__(
        self,
        sim_begin_time,
        sim_end_time,
        cache_dir: Optional[str | os.PathLike] = None,
    ) -> None:
        super().__init__(sim_begin_time, sim_end_time, cache_dir)
        self._offers_paths: Dict[str, Optional[pd.DataFrame]] = {}
        self.offers_name_map: Dict[str, str] = {}
        self._epts_fill_lookup_cache: Optional[pd.DataFrame] = None

    def load_core_data(self, *args, **kwargs):
        """Invalidate cached EPTS lookups when core tables are reloaded."""
        self._epts_fill_lookup_cache = None
        return super().load_core_data(*args, **kwargs)

    def register_offers(
        self,
        paths: Iterable[str | os.PathLike],
        name_map: Optional[Dict[str | os.PathLike, str]] = None,
    ) -> None:
        """Register one or more offers CSV paths (same idea as ``add_policies``)."""
        if name_map:
            for key, value in name_map.items():
                ks, kn = str(key), Path(key).name
                self.offers_name_map[ks] = value
                self.offers_name_map[kn] = value
        for p in paths:
            self._offers_paths.setdefault(str(p), None)

    def _friendly_offers_name(self, path: str | os.PathLike) -> str:
        path_str = str(path)
        name = Path(path).name
        return self.offers_name_map.get(path_str, self.offers_name_map.get(name, name))

    def get_offers(self, path: str | os.PathLike, *, reload: bool = False) -> pd.DataFrame:
        """Load and cache the offers table for *path*."""
        path = str(path)
        if path not in self._offers_paths:
            raise KeyError(f"Offers path not registered: {path}")
        if reload or self._offers_paths[path] is None:
            self._offers_paths[path] = read_offers_csv(path)
        return self._offers_paths[path]  # type: ignore[return-value]

    def offers_per_kidney_counts(
        self,
        path: str | os.PathLike,
        *,
        group_by_iteration: bool = False,
    ) -> pd.Series:
        """Return offer counts per kidney (``don_id``, optionally per ``iteration``)."""
        df = self.get_offers(path)
        return _counts_per_kidney(df, group_by_iteration)

    def summarize_offers_per_kidney(
        self,
        path: str | os.PathLike,
        *,
        group_by_iteration: bool = False,
    ) -> Dict[str, Any]:
        """
        Mean, median, spread, and counts for *number of offers per kidney*.

        Each row in the file is one offer; grouping counts how many offers were made
        for each ``don_id`` (kidney).
        """
        counts = self.offers_per_kidney_counts(path, group_by_iteration=group_by_iteration)
        return _distribution_stats(counts)

    def summarize_offers_per_kidney_by_segment(
        self,
        path: str | os.PathLike,
        *,
        group_by_iteration: bool = False,
    ) -> pd.DataFrame:
        """Same distribution as :meth:`summarize_offers_per_kidney`, stratified by ``segment``."""
        df = self.get_offers(path)
        keys = _group_keys_for_kidney(df, group_by_iteration)
        rows = []
        for seg, sub in df.groupby("segment", observed=True, dropna=False):
            counts = sub.groupby(keys, observed=True).size()
            st = _distribution_stats(counts)
            st["segment"] = seg
            rows.append(st)
        if not rows:
            return pd.DataFrame()
        out = pd.DataFrame(rows)
        cols = ["segment", "n_kidneys", "n_offers", "mean", "median", "std", "min", "max", "p25", "p75"]
        return out[[c for c in cols if c in out.columns]]

    def _dedupe_final_epts_prefer_nonnull(self, fe: pd.DataFrame) -> pd.DataFrame:
        """If ``final_epts`` has duplicate ``cand_id``, keep a row with non-null ``epts_pct`` when possible."""
        fe = fe.copy()
        fe["cand_id"] = _normalize_entity_id(fe["cand_id"])
        fe["_has_epts"] = fe["epts_pct"].notna()
        fe = fe.sort_values(["cand_id", "_has_epts", "epts_pct"], na_position="first")
        fe = fe.drop_duplicates(subset=["cand_id"], keep="last")
        return fe.drop(columns=["_has_epts"])

    def _get_epts_fill_lookup(self) -> pd.DataFrame:
        """
        Last chronologically observed non-null ``epts_pct`` per ``cand_id`` from
        ``candidate`` ∪ ``gen_hist`` (matches how gaps often arise when the last
        event row has missing EPTS but an earlier row does not).
        """
        if self._epts_fill_lookup_cache is not None:
            return self._epts_fill_lookup_cache
        parts: List[pd.DataFrame] = []
        for df in (self.candidate, self.gen_hist):
            if df is None or "cand_id" not in df.columns or "epts_pct" not in df.columns:
                continue
            use_cols = ["cand_id", "epts_pct"]
            if "cand_event_datetime" in df.columns:
                use_cols.append("cand_event_datetime")
            sub = df[use_cols].copy()
            sub["cand_id"] = _normalize_entity_id(sub["cand_id"])
            if "cand_event_datetime" in sub.columns:
                sub["cand_event_datetime"] = pd.to_datetime(
                    sub["cand_event_datetime"], errors="coerce"
                )
            parts.append(sub)
        if not parts:
            self._epts_fill_lookup_cache = pd.DataFrame(columns=["cand_id", "epts_pct"])
            return self._epts_fill_lookup_cache
        combined = pd.concat(parts, ignore_index=True)
        combined = combined[combined["epts_pct"].notna()]
        if combined.empty:
            self._epts_fill_lookup_cache = pd.DataFrame(columns=["cand_id", "epts_pct"])
            return self._epts_fill_lookup_cache
        if "cand_event_datetime" in combined.columns:
            combined = combined.sort_values(["cand_id", "cand_event_datetime"])
        lookup = combined.groupby("cand_id", as_index=False).last()[["cand_id", "epts_pct"]]
        self._epts_fill_lookup_cache = lookup
        return lookup

    def _static_ages_for_merge(self) -> Optional[pd.DataFrame]:
        """
        One row per ``cand_id`` with ``real_age`` and/or ``can_age_at_listing`` from ``static``.
        Uses the latest ``can_listing_dt`` when duplicates exist.
        """
        if self.static is None:
            return None
        cols = ["cand_id"]
        for c in ("real_age", "can_age_at_listing"):
            if c in self.static.columns:
                cols.append(c)
        if len(cols) <= 1:
            return None
        extra = ["can_listing_dt"] if "can_listing_dt" in self.static.columns else []
        base = self.static[cols + extra].copy()
        base["cand_id"] = _normalize_entity_id(base["cand_id"])
        if "can_listing_dt" in base.columns:
            base["can_listing_dt"] = pd.to_datetime(base["can_listing_dt"], errors="coerce")
            base = base.sort_values(["cand_id", "can_listing_dt"]).drop_duplicates(
                subset=["cand_id"], keep="last"
            )
            base = base.drop(columns=["can_listing_dt"])
        else:
            base = base.drop_duplicates(subset=["cand_id"], keep="last")
        return base[cols]

    def _static_listing_dt_for_merge(self) -> Optional[pd.DataFrame]:
        """One ``can_listing_dt`` per ``cand_id`` (latest listing if duplicates)."""
        if self.static is None or "can_listing_dt" not in self.static.columns:
            return None
        base = self.static[["cand_id", "can_listing_dt"]].copy()
        base["cand_id"] = _normalize_entity_id(base["cand_id"])
        base["can_listing_dt"] = pd.to_datetime(base["can_listing_dt"], errors="coerce")
        base = base.sort_values(["cand_id", "can_listing_dt"]).drop_duplicates(
            subset=["cand_id"], keep="last"
        )
        return base

    def enriched_offers(self, path: str | os.PathLike) -> pd.DataFrame:
        """
        Offers rows with ``epts_pct``, donor ``kdpi_at_allocation``, and ages attached:

        - ``real_age``: recipient age at simulation start (from ``static``).
        - ``can_age_at_listing``: age at listing (from ``static``).
        - ``don_age``: donor age (from ``donor``, if column present).
        - ``can_race_srtr`` / ``can_ethnicity_srtr``: from the race file when ``load_core_data(..., race_path=...)`` was used.
        - ``can_listing_dt``: listing time (from ``static``) for wait-time computation.
        - ``offer_wait_years``: years waited **at this offer** — from the offers file
          (``wait_time_years`` / ``offer_datetime`` / …) or computed as
          ``offer_datetime - can_listing_dt`` when both exist. **Each offer row** gets its own
          value, so a candidate with offers across multiple years contributes to each wait bin.

        Requires :meth:`load_core_data` so ``final_epts``, ``donor``, and ``static`` are available.
        """
        if self.donor is None or self.final_epts is None or self.static is None:
            raise RuntimeError("Call load_core_data() before enriched_offers().")
        df = self.get_offers(path).copy()
        df["cand_id"] = _normalize_entity_id(df["cand_id"])
        df["don_id"] = _normalize_entity_id(df["don_id"])

        fe = self._dedupe_final_epts_prefer_nonnull(self.final_epts[["cand_id", "epts_pct"]])

        out = df.merge(fe, on="cand_id", how="left")
        n_miss_epts = int(out["epts_pct"].isna().sum())
        if n_miss_epts:
            lookup = self._get_epts_fill_lookup()
            if len(lookup):
                fill = out["cand_id"].map(lookup.set_index("cand_id")["epts_pct"])
                idx = out["epts_pct"].isna() & fill.notna()
                if idx.any():
                    out.loc[idx, "epts_pct"] = fill.loc[idx].values
                    logger.info(
                        "enriched_offers: filled epts_pct for %s rows from candidate+gen_hist "
                        "(last non-null EPTS per cand_id)",
                        int(idx.sum()),
                    )
                n_miss_epts = int(out["epts_pct"].isna().sum())
        if n_miss_epts:
            ntot = len(out)
            share = n_miss_epts / ntot if ntot else 0.0
            nuniq = int(out.loc[out["epts_pct"].isna(), "cand_id"].nunique())
            sample = (
                out.loc[out["epts_pct"].isna(), "cand_id"].drop_duplicates().head(5).tolist()
            )
            msg = (
                "enriched_offers: %s / %s rows (%.3f%%) still missing epts_pct; "
                "%s distinct cand_id with no EPTS in final_epts or candidate/gen_hist "
                "(sample cand_id: %s). Often simulation-only candidates not in input tables."
            ) % (n_miss_epts, ntot, 100.0 * share, nuniq, sample)
            if share >= EPTS_GAP_WARN_SHARE:
                logger.warning(msg)
            else:
                logger.info(msg)

        sa = self._static_ages_for_merge()
        if sa is not None and len(sa):
            out = out.merge(sa, on="cand_id", how="left")

        listing = self._static_listing_dt_for_merge()
        if listing is not None and len(listing):
            out = out.merge(listing, on="cand_id", how="left")

        d_cols = ["don_id", "kdpi_at_allocation"]
        if "don_age" in self.donor.columns:
            d_cols.append("don_age")
        d = (
            self.donor[d_cols]
            .drop_duplicates(subset=["don_id"], keep="last")
            .copy()
        )
        d["don_id"] = _normalize_entity_id(d["don_id"])

        out = out.merge(d, on="don_id", how="left")
        n_miss_kdpi = int(out["kdpi_at_allocation"].isna().sum())
        if n_miss_kdpi:
            logger.warning(
                "enriched_offers: %s / %s rows missing kdpi_at_allocation after donor merge",
                n_miss_kdpi,
                len(out),
            )

        if self.race_df is not None and not self.skip_race_analysis:
            rf_cols = ["cand_id", "can_race_srtr"]
            if "can_ethnicity_srtr" in self.race_df.columns:
                rf_cols.append("can_ethnicity_srtr")
            rf = self.race_df[[c for c in rf_cols if c in self.race_df.columns]].copy()
            rf["cand_id"] = _normalize_entity_id(rf["cand_id"])
            rf = rf.drop_duplicates(subset=["cand_id"], keep="last")
            out = out.merge(rf, on="cand_id", how="left")

        out = self._attach_offer_wait_years(out)
        return out

    def _attach_offer_wait_years(self, out: pd.DataFrame) -> pd.DataFrame:
        """Set ``offer_wait_years`` from file columns or ``offer_datetime`` − ``can_listing_dt``."""
        if "offer_wait_years" not in out.columns:
            out["offer_wait_years"] = np.nan
        ow = pd.to_numeric(out["offer_wait_years"], errors="coerce")

        if "offer_datetime" in out.columns and "can_listing_dt" in out.columns:
            odt = pd.to_datetime(out["offer_datetime"], errors="coerce")
            ldt = pd.to_datetime(out["can_listing_dt"], errors="coerce")
            computed = (odt - ldt).dt.total_seconds() / (365.25 * 24 * 3600)
            m = ow.isna() & computed.notna()
            ow = ow.where(~m, computed)
        out["offer_wait_years"] = ow
        neg = int((out["offer_wait_years"] < 0).sum())
        if neg:
            logger.info(
                "enriched_offers: clipping %s rows with negative offer_wait_years (offer before listing)",
                neg,
            )
            out["offer_wait_years"] = out["offer_wait_years"].clip(lower=0.0)
        return out

    def plot_offers_per_kidney_distribution(
        self,
        path: str | os.PathLike,
        *,
        group_by_iteration: bool = False,
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> None:
        """Histogram (+ CDF) of offers-per-kidney counts."""
        counts = self.offers_per_kidney_counts(path, group_by_iteration=group_by_iteration)
        title = self._friendly_offers_name(path)
        plot_offers_per_kidney_distribution(
            counts,
            title=title,
            save_plot=save_plot,
            name=name,
        )

    def plot_epts_kdpi_catplot(
        self,
        paths: Iterable[str | os.PathLike],
        *,
        accepted_only: bool = True,
        epts_step: float = 0.1,
        kind: str = "box",
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> Any:
        """
        For accepted offers, show KDPI vs EPTS bins (box / violin / strip).

        ``epts_step`` defines bin width on 0–1 EPTS scale (default 0.1 → deciles).
        """
        paths_list = [str(p) for p in paths]
        enriched_frames = [(self._friendly_offers_name(p), self.enriched_offers(p)) for p in paths_list]
        return offers_epts_kdpi_catplot(
            enriched_frames,
            accepted_only=accepted_only,
            epts_step=epts_step,
            kind=kind,
            save_plot=save_plot,
            name=name,
        )

    def plot_epts_age_catplot(
        self,
        paths: Iterable[str | os.PathLike],
        *,
        age_column: str = "real_age",
        accepted_only: bool = True,
        epts_step: float = 0.1,
        kind: str = "box",
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> Any:
        """
        **EPTS bins (x) vs age (y)** — same layout as :meth:`plot_epts_kdpi_catplot`.
        For **candidate age vs donor age** as a catplot (binned candidate age), use
        :meth:`plot_candidate_donor_age`; for raw-age **scatter**, pass ``as_scatter=True``.

        ``age_column`` must be one of ``real_age``, ``can_age_at_listing``, ``don_age``
        (present on :meth:`enriched_offers` output).
        """
        paths_list = [str(p) for p in paths]
        enriched_frames = [(self._friendly_offers_name(p), self.enriched_offers(p)) for p in paths_list]
        return offers_epts_age_catplot(
            enriched_frames,
            age_column=age_column,
            accepted_only=accepted_only,
            epts_step=epts_step,
            kind=kind,
            save_plot=save_plot,
            name=name,
        )

    def plot_candidate_donor_age(
        self,
        paths: Iterable[str | os.PathLike],
        *,
        candidate_age_col: str = "real_age",
        accepted_only: bool = True,
        as_scatter: bool = False,
        kind: str = "box",
        age_bin_years: float = 5.0,
        max_points: int = 80_000,
        alpha: float = 0.14,
        show_diagonal: bool = True,
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> Any:
        """
        **Donor age** vs **candidate age** for offered kidneys.

        By default uses ``sns.catplot`` (same as :meth:`plot_epts_kdpi_catplot`): **binned
        candidate age** on the x-axis, **donor age** on the y-axis (``kind`` / ``age_bin_years``).

        Set ``as_scatter=True`` for a **scatter** of raw candidate age vs donor age (downsampled
        when large); ``kind`` / ``age_bin_years`` are ignored in that case.

        ``candidate_age_col`` is ``real_age`` or ``can_age_at_listing``.
        """
        paths_list = [str(p) for p in paths]
        enriched_frames = [(self._friendly_offers_name(p), self.enriched_offers(p)) for p in paths_list]
        if as_scatter:
            return offers_candidate_donor_age_plot(
                enriched_frames,
                candidate_age_col=candidate_age_col,
                accepted_only=accepted_only,
                max_points=max_points,
                alpha=alpha,
                show_diagonal=show_diagonal,
                save_plot=save_plot,
                name=name,
            )
        return offers_candidate_donor_age_catplot(
            enriched_frames,
            candidate_age_col=candidate_age_col,
            accepted_only=accepted_only,
            age_bin_years=age_bin_years,
            kind=kind,
            save_plot=save_plot,
            name=name,
        )

    def summarize_kdpi_by_race(
        self,
        path: str | os.PathLike,
        *,
        accepted_only: bool = True,
    ) -> pd.DataFrame:
        """
        For each recipient **SRTR race** (``can_race_srtr``), summarize **donor KDPI**
        on offered kidneys (count, mean, median, spread).

        Requires ``load_core_data(..., race_path=...)`` so :meth:`enriched_offers` includes race.
        """
        df = self.enriched_offers(path)
        if "can_race_srtr" not in df.columns:
            raise ValueError(
                "Race not on enriched offers; call load_core_data(..., race_path=...) with can_race.csv."
            )
        if accepted_only:
            acc = df["accepted"]
            if acc.dtype != bool:
                acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
            df = df[acc]
        df = df.copy()
        df["can_race_srtr"] = df["can_race_srtr"].fillna("Unknown").astype(str)
        df["kdpi_at_allocation"] = pd.to_numeric(df["kdpi_at_allocation"], errors="coerce")
        df = df.dropna(subset=["kdpi_at_allocation"])
        out = (
            df.groupby("can_race_srtr", observed=True)["kdpi_at_allocation"]
            .agg(
                n_offers="count",
                mean_kdpi="mean",
                median_kdpi="median",
                std_kdpi="std",
                p25=lambda s: float(s.quantile(0.25)),
                p75=lambda s: float(s.quantile(0.75)),
            )
            .reset_index()
            .sort_values("can_race_srtr")
        )
        return out

    def plot_kdpi_by_race(
        self,
        paths: Iterable[str | os.PathLike],
        *,
        accepted_only: bool = True,
        kind: str = "box",
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> Any:
        """
        **Donor KDPI** of offers vs **recipient race** (``can_race_srtr``) via ``sns.catplot``
        (same pattern as :meth:`plot_epts_kdpi_catplot` / :meth:`plot_candidate_donor_age`).

        ``kind`` is passed to ``catplot`` (e.g. ``box``, ``violin``, ``strip``). Compare policies
        via ``hue`` when multiple paths are passed.
        """
        paths_list = [str(p) for p in paths]
        enriched_frames = [(self._friendly_offers_name(p), self.enriched_offers(p)) for p in paths_list]
        return offers_kdpi_by_race_catplot(
            enriched_frames,
            accepted_only=accepted_only,
            kind=kind,
            save_plot=save_plot,
            name=name,
        )

    def summarize_kdpi_by_wait_bin(
        self,
        path: str | os.PathLike,
        *,
        wait_edges_years: Optional[List[float]] = None,
        accepted_only: bool = True,
    ) -> pd.DataFrame:
        """
        Summarize **donor KDPI** by **years waited at this offer** (``offer_wait_years``).

        Each offer row has its own wait time, so a candidate with offers in multiple years
        contributes to the corresponding bins. Requires ``offer_wait_years`` on
        :meth:`enriched_offers` (from the offers file and/or ``offer_datetime`` − ``can_listing_dt``).
        """
        edges = _normalize_wait_edges(wait_edges_years)
        df = self.enriched_offers(path)
        if accepted_only:
            if "accepted" not in df.columns:
                raise ValueError("enriched offers must include 'accepted' when accepted_only=True")
            acc = df["accepted"]
            if acc.dtype != bool:
                acc = acc.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "t"))
            df = df[acc]
        df = df.copy()
        df["kdpi_at_allocation"] = pd.to_numeric(df["kdpi_at_allocation"], errors="coerce")
        df["offer_wait_years"] = pd.to_numeric(df["offer_wait_years"], errors="coerce")
        df = df.dropna(subset=["kdpi_at_allocation", "offer_wait_years"])
        if len(df) == 0:
            return pd.DataFrame(
                columns=[
                    "wait_bin",
                    "n_offers",
                    "mean_kdpi",
                    "median_kdpi",
                    "std_kdpi",
                    "p25",
                    "p75",
                ]
            )
        df["wait_bin"] = pd.cut(
            df["offer_wait_years"], bins=edges, right=False, include_lowest=True
        )
        df = df.dropna(subset=["wait_bin"])
        out = (
            df.groupby("wait_bin", observed=True)["kdpi_at_allocation"]
            .agg(
                n_offers="count",
                mean_kdpi="mean",
                median_kdpi="median",
                std_kdpi="std",
                p25=lambda s: float(s.quantile(0.25)),
                p75=lambda s: float(s.quantile(0.75)),
            )
            .reset_index()
        )
        out["_lo"] = out["wait_bin"].apply(
            lambda x: float(x.left) if isinstance(x, pd.Interval) else float("nan")
        )
        out = out.sort_values("_lo").drop(columns=["_lo"])
        return out

    def plot_kdpi_by_wait_time(
        self,
        paths: Iterable[str | os.PathLike],
        *,
        wait_edges_years: Optional[List[float]] = None,
        accepted_only: bool = True,
        kind: str = "box",
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> Any:
        """
        Box/violin/strip: **donor KDPI** vs **wait time at offer** (years).

        Uses the same bin edges as :meth:`summarize_kdpi_by_wait_bin` (default
        ``DEFAULT_OFFER_WAIT_EDGES_YEARS``). Each offer row is binned independently.
        """
        paths_list = [str(p) for p in paths]
        enriched_frames = [(self._friendly_offers_name(p), self.enriched_offers(p)) for p in paths_list]
        return offers_kdpi_by_wait_catplot(
            enriched_frames,
            wait_edges_years=wait_edges_years,
            accepted_only=accepted_only,
            kind=kind,
            save_plot=save_plot,
            name=name,
        )

    def __repr__(self) -> str:
        n_off = len(self._offers_paths)
        names = ", ".join(self._friendly_offers_name(p) for p in self._offers_paths) or "<none>"
        return f"OffersCalculator(offers_files={n_off}, registered=[{names}])"
