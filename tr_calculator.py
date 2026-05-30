from __future__ import annotations

import logging
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Constants
OASIM_VERSION_2023 = "2023"
OASIM_VERSION_2024 = "2024"
DEFAULT_OASIM_VERSION = OASIM_VERSION_2023

# Try relative import first, then fall back to absolute import
try:
    from .pt import five_year_survival
    from .rates import gender_rates, race_rates, ethnicity_rates, epts_rates, abo_rates, cpra_rates, age_rates, epts_percentages, distance, age_at_listing_rates
    from .plots import create_policy_table, plot_policies, kdpi_rates_heatmap, age_listing_matching_heatmap, age_difference_percentage_plot, age_difference_xy_plot, marginal_difference_heatmap, median_kdpi_comparison_bar_chart, marginal_xy_plot, age_rate_xy_plot, cpra_rate_xy_plot, offer_analysis_plot
except ImportError:
    # Fall back to absolute import
    from pt import five_year_survival
    from rates import gender_rates, race_rates, ethnicity_rates, epts_rates, abo_rates, cpra_rates, age_rates, epts_percentages, distance, age_at_listing_rates
    from plots import create_policy_table, plot_policies, kdpi_rates_heatmap, age_listing_matching_heatmap, age_difference_percentage_plot, age_difference_xy_plot, marginal_difference_heatmap, median_kdpi_comparison_bar_chart, marginal_xy_plot, age_rate_xy_plot, cpra_rate_xy_plot, offer_analysis_plot

"""
Transplant_rates_calculator
"""

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class TransplantRatesCalculator:
    """
    Provides a user-friendly interface for analyzing and comparing kidney transplant allocation policies.

    This class loads and preprocesses all required data, manages policy definitions, computes person-time
    statistics, and provides wrappers for analysis and reporting functions. It is designed for researchers
    and analysts who want to compare different allocation policies without needing to know the internal
    details of the data or the underlying analysis functions.
    """


    def __init__(self, sim_begin_time: datetime, sim_end_time: datetime,
                 cache_dir: str | os.PathLike | None = None) -> None:
        """
        Initialize the calculator with simulation time window and optional cache.

        Args:
            sim_begin_time (datetime): Start of the simulation period.
            sim_end_time (datetime): End of the simulation period.
            cache_dir (str | os.PathLike, optional): Directory for caching person-time results.
        """
        logger.info("TransplantRatesCalculator initialized. Note: If you're upgrading, you may need to clear your cache directory.")

        self.sim_begin_time = sim_begin_time.replace(tzinfo=None)
        self.sim_end_time = sim_end_time.replace(tzinfo=None)

        self.skip_cache = True
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir).expanduser()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.skip_cache = False
        else:
            self.cache_dir = None
            self.skip_cache = True
        self.name_map: Dict[str, str] = {}

        # Core dataframes, loaded by load_core_data()
        self.donor: pd.DataFrame | None = None
        self.candidate: pd.DataFrame | None = None
        self.static: pd.DataFrame | None = None
        self.timevarying: pd.DataFrame | None = None
        self.gen_removal: pd.DataFrame | None = None
        self.gen_hist: pd.DataFrame | None = None
        self.race_df: pd.DataFrame | None = None

        # Derived tables
        self.final_epts: pd.Series | None = None
        self.final_cpra: pd.Series | None = None

        # Registered policies and their computed person-time tables
        self._person_times_for: Dict[str, Optional[pd.DataFrame]] = {}
        # Policy groups: maps group name to list of iteration paths
        self._policy_groups: Dict[str, List[str]] = {}
        self._summary_table: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Public high‑level API
    # ------------------------------------------------------------------

    def load_core_data(
        self,
        *,
        donor_path: str | os.PathLike,
        candidate_path: str | os.PathLike,
        static_path: str | os.PathLike,
        timevarying_path: str | os.PathLike,
        gen_removal_path: str | os.PathLike,
        gen_hist_path: str | os.PathLike,
        race_path: str | os.PathLike | None = None,
        OASIM = DEFAULT_OASIM_VERSION,
    ) -> "TransplantRatesCalculator":
        """
        Load and preprocess all required data from CSV files.

        Args:
            donor_path: Path to donor data CSV.
            candidate_path: Path to candidate time-varying data CSV.
            static_path: Path to static candidate data CSV.
            timevarying_path: Path to additional time-varying candidate data CSV.
            gen_removal_path: Path to generated removal candidate data CSV.
            gen_hist_path: Path to generated history candidate data CSV.
            race_path: Path to candidate race/ethnicity CSV.
        Returns:
            self (for chaining)
        """
        self.donor = pd.read_csv(donor_path)
        self.candidate = pd.read_csv(candidate_path)
        self.static = pd.read_csv(static_path)
        self.timevarying = pd.read_csv(timevarying_path)
        self.gen_removal = pd.read_csv(gen_removal_path)
        self.gen_hist = pd.read_csv(gen_hist_path)

        # Make all columns lower case for self.static
        self.donor.columns = [col.lower() for col in self.donor.columns]
        self.static.columns = [col.lower() for col in self.static.columns]
        self.candidate.columns = [col.lower() for col in self.candidate.columns]
        self.timevarying.columns = [col.lower() for col in self.timevarying.columns]
        self.gen_removal.columns = [col.lower() for col in self.gen_removal.columns]
        self.gen_hist.columns = [col.lower() for col in self.gen_hist.columns]
        self.OASIM = OASIM

        if self.OASIM == OASIM_VERSION_2024:
            self.static.rename(columns = {"cand_bloodtype": "can_abo"}, inplace = True)
            self.static.rename(columns = {"listing_dt": "can_listing_dt"}, inplace = True)
            self.static.rename(columns = {"rem_dt": "can_rem_dt"}, inplace = True)
            self.static.rename(columns = {"age_at_listing": "can_age_at_listing"}, inplace = True)
            self.static.rename(columns = {"cpra": "canhx_cpra"}, inplace = True)
            self.static.rename(columns = {"gender": "can_gender"}, inplace = True)
            self.donor.rename(columns = {"kdpi": "kdpi_at_allocation"}, inplace = True)
            self.static.rename(columns = {"cand_center_longitude": "can_center_longitude"}, inplace = True)
            self.static.rename(columns = {"cand_center_latitude": "can_center_latitude"}, inplace = True)
            self.timevarying = self.static.copy()



        self.skip_race_analysis = False
        if race_path is not None:
            self.race_df = (
                pd.read_csv(race_path)
                .rename(columns={"px_id": "cand_id"})
                .assign(can_race_srtr=lambda df: df["can_race_srtr"].fillna("Unknown"))
            )
            self.race_df.columns = [col.lower() for col in self.race_df.columns]
        else:
            self.race_df = None
            self.skip_race_analysis = True

        # Standardize and filter data for analysis
        self._standardise_static_table() #
        self._filter_non_pancreas_candidates() # 
        self._compute_real_age()

        # Compute initial EPTS and CPRA values for all candidates
        self.final_epts = epts_at_start(self.candidate, self.gen_hist, self.sim_begin_time)
        self.final_cpra = cpra_at_start(self.timevarying, self.sim_begin_time, self.OASIM)
        return self

    def add_policies(self, paths: Iterable[str | os.PathLike], 
                     name_map: Optional[Dict[str | os.PathLike, str]] = None) -> None:
        """
        Register one or more policy output file paths for later analysis.

        Args:
            paths: Iterable of file paths to OASIM output files, one per policy.
            name_map: Optional dictionary mapping policy paths to display names.
                     Keys can be full paths or just filenames. If a path is not in name_map,
                     the filename will be used as the display name.
        """
        if name_map is not None:
            # Update the name_map with the provided mappings
            for key, value in name_map.items():
                # Normalize the key - try both full path and filename
                key_str = str(key)
                key_filename = Path(key).name
                self.name_map[key_str] = value
                self.name_map[key_filename] = value
        
        for p in paths:
            p = str(p)
            self._person_times_for.setdefault(p, None)  # Avoid overwriting if re‑added

    def add_policy_group(self, paths: Iterable[str | os.PathLike], 
                         group_name: str) -> None:
        """
        Register a group of policy iterations (e.g., multiple runs of the same policy).
        Metrics will be aggregated across iterations showing mean, min, and max.

        Args:
            paths: Iterable of file paths to OASIM output files for iterations of the same policy.
            group_name: Display name for this policy group (e.g., "KAS250", "NewPolicy").
        """
        group_paths = [str(p) for p in paths]
        self._policy_groups[group_name] = group_paths
        
        # Register all paths in the group
        for p in group_paths:
            self._person_times_for.setdefault(p, None)

    def compute_person_times_for(self, path: str | os.PathLike, save_cache = True) -> pd.DataFrame:
        """
        Return (and cache) the person-times table for a given policy output file.
        A path to a CSV file containing matches is assumed.

        Args:
            path: Path to the OASIM output file for the policy.
        Returns:
            DataFrame of person-times for the policy.
        """
        path = str(path)
        if path not in self._person_times_for:
            raise KeyError(f"Policy not registered: {path}")
        if self._person_times_for[path] is None:
            self._person_times_for[path] = get_or_load_person_times(
                path,
                self.cache_dir,
                save_cache and not self.skip_cache,
                self.donor,    # type: ignore[arg-type]
                self.static,   # type: ignore[arg-type]
                self.sim_begin_time,
                self.sim_end_time,
                self.gen_removal,
                self.final_epts,
                self.final_cpra,
                self.race_df,  # type: ignore[arg-type]
                OASIM=self.OASIM,
            )
        return self._person_times_for[path]  # type: ignore[return-value]

    def compute_summary_table(self, save_cache = True) -> pd.DataFrame:
        """
        Compute a summary table comparing all registered policies across multiple metrics.
        For policy groups, computes mean, min, and max across iterations.
        The result is cached for repeated use.

        Returns:
            Multi-index DataFrame (policy × category) with summary statistics.
        """

        if self._summary_table is not None:
            return self._summary_table  # Cached

        data_per_policy: dict[str, dict[str, pd.Series | float | dict]] = {}
        
        # Process policy groups (iterations)
        for group_name, group_paths in self._policy_groups.items():
            # Collect metrics for all iterations in this group
            metrics_by_category: dict[str, list] = {}
            
            for path in group_paths:
                pt = self.compute_person_times_for(path, save_cache)
                pt.columns = [col.lower() for col in pt.columns]

                if not self.skip_race_analysis:
                    categories = {
                        "age": age_rates(path, pt, read_output_default),
                        "age at listing": age_at_listing_rates(path, pt, read_output_default),
                        "race": race_rates(path, pt, self.race_df, read_output_default),
                        "ethnicity": ethnicity_rates(path, pt, self.race_df, read_output_default),
                        "epts (bins of 20)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                        "epts (bins of 10)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=10),
                        "gender": gender_rates(path, pt, read_output_default),
                        "distance": distance(path, self.final_epts, self.final_cpra, self.donor, self.static, read_output_default),
                        "abo": abo_rates(path, pt, read_output_default),
                    }
                else:
                    categories = {
                        "age": age_rates(path, pt, read_output_default),
                        "age at listing": age_at_listing_rates(path, pt, read_output_default),
                        "epts (bins of 20)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                        "epts (bins of 10)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=10),
                        "gender": gender_rates(path, pt, read_output_default),
                        "distance": distance(path, self.final_epts, self.final_cpra, self.donor, self.static, read_output_default),
                        "abo": abo_rates(path, pt, read_output_default),
                    }
                
                # Collect metrics for aggregation
                for cat, metric in categories.items():
                    if cat not in metrics_by_category:
                        metrics_by_category[cat] = []
                    metrics_by_category[cat].append(metric)
            
            # Aggregate metrics across iterations
            aggregated = {}
            for cat, metrics_list in metrics_by_category.items():
                aggregated_metrics = self._aggregate_metrics(metrics_list)
                aggregated[cat] = aggregated_metrics
            
            data_per_policy[group_name] = aggregated
        
        # Process single policies (not in groups)
        # Preserve insertion order by iterating over _person_times_for.keys() in order
        all_group_paths = set()
        for group_paths in self._policy_groups.values():
            all_group_paths.update(group_paths)
        
        for path in self._person_times_for.keys():
            # Skip paths that are part of groups (already processed)
            if path in all_group_paths:
                continue
            short_name = self._friendly_name(path)
            pt = self.compute_person_times_for(path, save_cache)
            pt.columns = [col.lower() for col in pt.columns]

            if not self.skip_race_analysis:
                data_per_policy[short_name] = {
                    "age": age_rates(path, pt, read_output_default),
                    "age at listing": age_at_listing_rates(path, pt, read_output_default),
                    "race": race_rates(path, pt, self.race_df, read_output_default),
                    "ethnicity": ethnicity_rates(path, pt, self.race_df, read_output_default),
                    "epts (bins of 20)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                    "epts (bins of 10)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=10),
                    "gender": gender_rates(path, pt, read_output_default),
                    "distance": distance(path, self.final_epts, self.final_cpra, self.donor, self.static, read_output_default),
                    "abo": abo_rates(path, pt, read_output_default),
                    # "cpra": cpra_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                    # "five_year_survival": get_five_year_survival(path, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                }
            else:
                data_per_policy[short_name] = {
                    "age": age_rates(path, pt, read_output_default),
                    "age at listing": age_at_listing_rates(path, pt, read_output_default),
                    "epts (bins of 20)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                    "epts (bins of 10)": epts_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=10),
                    "gender": gender_rates(path, pt, read_output_default),
                    "distance": distance(path, self.final_epts, self.final_cpra, self.donor, self.static, read_output_default),
                    "abo": abo_rates(path, pt, read_output_default),
                    # "cpra": cpra_rates(path, pt, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                    # "five_year_survival": get_five_year_survival(path, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra),
                }


        self._summary_table = create_policy_table(data_per_policy)
        return self._summary_table

    # ------------------------------------------------------------------
    # Convenience plotting wrappers (optional)
    # ------------------------------------------------------------------
    def get_age_rates(self, path: str | os.PathLike) -> dict:
        person_times = self.compute_person_times_for(path)
        return age_rates(path, person_times, read_output_default)
    
    def get_age_at_listing_rates(self, path: str | os.PathLike) -> dict:
        person_times = self.compute_person_times_for(path)
        return age_at_listing_rates(path, person_times, read_output_default)
    
    def get_gender_rates(self, path: str | os.PathLike) -> dict:
        person_times = self.compute_person_times_for(path)
        return gender_rates(path, person_times, read_output_default)

    def get_race_rates(self, path: str | os.PathLike) -> dict:
        person_times = self.compute_person_times_for(path)
        return race_rates(path, person_times, self.race_df, read_output_default)

    def plot_dataframe(self, *, save_plot: bool = False, name: Optional[str] = None) -> None:
        plot_policies(self._summary_table, save_plot=save_plot, name=name)

    def plot_kdpi_heatmap(self, policy: str | os.PathLike, *, step: int = 10, save_plot: bool = False, name: Optional[str] = None) -> None:
        policy_name = self._friendly_name(policy)
        kdpi_rates_heatmap(policy, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=step, save_plot=save_plot, name=name, policy_name=policy_name)

    def plot_age_matching_heatmap(self, policy: str | os.PathLike, *, step: int = 5, save_plot: bool = False, name: Optional[str] = None):
        person_times = self.compute_person_times_for(policy)
        age_listing_matching_heatmap(policy, person_times, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_age_difference(self, policies: Iterable[str | os.PathLike], *, step: int = 5, save_plot: bool = False, name: Optional[str] = None) -> None:
        """
        Plot age difference distributions for multiple policies.
        
        Args:
            policies: Iterable of policy paths to compare
            step: Bin size for age difference bins, default=5
            save_plot: Whether to save the plot
            name: Optional filename for saving
        """
        # Resolve policies to groups
        groups = self._resolve_policies_to_groups(policies)
        
        # For groups, use first path from each group
        # For single policies, use the path directly
        policy_person_time_pairs = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            if len(group_paths) > 1:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
            else:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
        
        combined_name_map = {**self.name_map, **name_map_for_plot}
        age_difference_xy_plot(policy_person_time_pairs, self.final_epts, self.final_cpra, self.donor, combined_name_map, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_marginal_difference(
        self,
        reference_policy: str | os.PathLike,   
        comparison_policy: str | os.PathLike,
        *,
        step: int = 10,
        save_plot: bool = False,
        name: Optional[str] = None,
    ) -> None:
        marginal_difference_heatmap(reference_policy, comparison_policy, self.final_epts, self.final_cpra, self.donor, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_median_kdpi_bars(self, policies: Iterable[str | os.PathLike], *, step: int = 20, save_plot: bool = False, name: Optional[str] = None) -> None:
        # Resolve policies to groups
        groups = self._resolve_policies_to_groups(policies)
        
        # For groups, use first path from each group (aggregation handled in summary table)
        # For single policies, use the path directly
        paths_to_plot = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            if len(group_paths) > 1:
                # Group - use first path and group name
                paths_to_plot.append(group_paths[0])
                name_map_for_plot[group_paths[0]] = group_name
            else:
                # Single policy
                paths_to_plot.append(group_paths[0])
                name_map_for_plot[group_paths[0]] = group_name
        
        # Merge with existing name_map
        combined_name_map = {**self.name_map, **name_map_for_plot}
        median_kdpi_comparison_bar_chart(paths_to_plot, self.final_epts, self.final_cpra, combined_name_map, self.donor, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_marginal_xy(self, policies: Iterable[str | os.PathLike], *, step: int = 20, save_plot: bool = False, name: Optional[str] = None) -> None:
        # Resolve policies to groups
        groups = self._resolve_policies_to_groups(policies)
        
        # For groups, use first path from each group
        paths_to_plot = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            if len(group_paths) > 1:
                paths_to_plot.append(group_paths[0])
                name_map_for_plot[group_paths[0]] = group_name
            else:
                paths_to_plot.append(group_paths[0])
                name_map_for_plot[group_paths[0]] = group_name
        
        combined_name_map = {**self.name_map, **name_map_for_plot}
        marginal_xy_plot(paths_to_plot, self.final_epts, self.final_cpra, self.donor, combined_name_map, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_age_rate_xy(self, policies: Iterable[str | os.PathLike], *, step: int = -1, save_plot: bool = False, name: Optional[str] = None) -> None:
        # Resolve policies to groups
        groups = self._resolve_policies_to_groups(policies)
        
        # For groups, use first path from each group
        policy_person_time_pairs = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            if len(group_paths) > 1:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
            else:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
        
        combined_name_map = {**self.name_map, **name_map_for_plot}
        age_rate_xy_plot(policy_person_time_pairs, self.final_epts, self.final_cpra, self.donor, combined_name_map, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_cpra_rate_xy(self, policies: Iterable[str | os.PathLike], *, step: int = -1, save_plot: bool = False, name: Optional[str] = None) -> None:
        # Resolve policies to groups
        groups = self._resolve_policies_to_groups(policies)
        
        # For groups, use first path from each group
        policy_person_time_pairs = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            if len(group_paths) > 1:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
            else:
                policy_person_time_pairs.append((group_paths[0], self.compute_person_times_for(group_paths[0])))
                name_map_for_plot[group_paths[0]] = group_name
        
        combined_name_map = {**self.name_map, **name_map_for_plot}
        cpra_rate_xy_plot(policy_person_time_pairs, self.final_epts, self.final_cpra, self.donor, combined_name_map, read_output_epts_cpra, step=step, save_plot=save_plot, name=name)

    def plot_offer_analysis(self, policies: Iterable[str | os.PathLike], *, step: int = 10, cutoff: int | float = float("inf"), save_plot: bool = False, name: Optional[str] = None) -> pd.DataFrame:
        """
        Analyse how many offers are made before acceptance across policies.

        Reads the ``rank`` column from each OASIM output file and produces:
          - A histogram showing the distribution of acceptance ranks.
          - A CDF overlay for easy percentile reading.
          - A printed summary table (mean, median, percentiles).

        Args:
            policies: Iterable of policy paths (or group names) to compare.
            step: Bin width for the rank histogram (default 10).
            cutoff: Ignore transplants where rank exceeds this value (default inf).
            save_plot: Whether to save the figure to disk.
            name: Optional filename when saving.

        Returns:
            DataFrame with summary statistics per policy.
        """
        groups = self._resolve_policies_to_groups(policies)

        paths_to_plot = []
        name_map_for_plot = {}
        for group_name, group_paths in groups.items():
            paths_to_plot.append(group_paths[0])
            name_map_for_plot[group_paths[0]] = group_name

        combined_name_map = {**self.name_map, **name_map_for_plot}
        return offer_analysis_plot(paths_to_plot, combined_name_map, read_output_default, step=step, cutoff=cutoff, save_plot=save_plot, name=name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _friendly_name(self, path: str | os.PathLike) -> str:
        """Return a short, human‑readable policy identifier."""
        path_str = str(path)
        name = Path(path).name
        # Check both full path and filename in name_map
        return self.name_map.get(path_str, self.name_map.get(name, name))
    
    def _aggregate_metrics(self, metrics_list: List[Dict[str, float] | float]) -> Dict[str, Dict[str, float]]:
        """
        Aggregate metrics across iterations.
        Returns dict with 'mean', 'min', 'max' for each metric.
        
        Args:
            metrics_list: List of metric dictionaries or floats from multiple iterations
            
        Returns:
            Dictionary with aggregated statistics (mean, min, max) for each metric
        """
        if not metrics_list:
            return {}
        
        # Check if metrics are dicts or floats
        first_metric = metrics_list[0]
        if isinstance(first_metric, dict):
            # Dictionary metrics (e.g., age rates: {"18-35": 0.5, "35-50": 0.7})
            # or distance: {"Median Travel Distance: ": 100.0}
            all_keys = set()
            for m in metrics_list:
                if isinstance(m, dict):
                    all_keys.update(m.keys())
            
            result = {}
            for key in all_keys:
                values = [m.get(key, 0.0) if isinstance(m, dict) else 0.0 for m in metrics_list]
                result[key] = {
                    'mean': float(np.mean(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values))
                }
            return result
        else:
            # Float metrics - convert to dict format
            values = [float(m) if not isinstance(m, dict) else 0.0 for m in metrics_list]
            return {
                'value': {
                    'mean': float(np.mean(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values))
                }
            }
    
    def _resolve_policies_to_groups(self, policies: Iterable[str | os.PathLike]) -> Dict[str, List[str]]:
        """
        Resolve policies to groups. Returns a dict mapping group names to lists of paths.
        Policies not in groups are returned as single-item groups.
        
        Args:
            policies: Iterable of policy paths
            
        Returns:
            Dictionary mapping group names to lists of paths
        """
        policies_list = [str(p) for p in policies]
        resolved: Dict[str, List[str]] = {}
        
        for policy in policies_list:
            # Check if this policy is part of a registered group
            found_in_group = False
            for group_name, group_paths in self._policy_groups.items():
                if policy in group_paths:
                    # Use the group name and all paths in the group
                    resolved[group_name] = group_paths
                    found_in_group = True
                    break
            
            if not found_in_group:
                # Single policy, not part of a group
                resolved[self._friendly_name(policy)] = [policy]
        
        return resolved

    # ----- cleaning helpers -------------------------------------------------

    def _filter_non_pancreas_candidates(self) -> None:
        """Keep kidney‑only candidates (mirrors original notebook logic)."""
        if self.static is None:
            raise RuntimeError("Static table not loaded yet")
        non_pa_ids = set(self.static[self.static["wl_org"] == "KI"]["cand_id"])
        for df_name in ("candidate", "timevarying", "static", "gen_hist", "gen_removal"):
            df = getattr(self, df_name)
            setattr(self, df_name, df[df["cand_id"].isin(non_pa_ids)])


    def _standardise_static_table(self) -> None:
        """Drop bookkeeping columns + harmonise ABO codes."""
        if self.static is None:
            raise RuntimeError("Static table not loaded yet")
        self.static["can_abo_replaced"] = self.static["can_abo"].replace({
            "A2B": "AB",
            "A1B": "AB",
            "A1": "A",
            "A2": "A",
        })

        drop_cols = [
            "wl_id", "don_ty", "can_listing_ctr_cd", "can_listing_ctr_ty",
            "can_activate_dt", "can_tiebreaker_dt", "can_rem_cd", "can_on_dial",
            "can_dial_dt", "can_min_peak_creat", "can_max_mile", "can_min_wgt",
            "can_max_wgt", "can_max_mm_abdr", "can_max_mm_a", "can_max_mm_dr",
            "can_min_age", "can_max_age", "can_acpt_hcv_pos", "can_donated_org",
            "can_hgt_cm", "can_wgt_kg", "can_dial", "doncrit_acpt_dcd",
            "doncrit_acpt_dcd_import", "can_listing_opo_id", "can_prev_tx", "ki_ln_oar",
            "ki_ln_oar_lowrisk", "ki_ln_oar_medrisk", "ki_ln_oar_highrisk", "kp_ln_oar",
            "kp_ln_oar_highbmi28", "kp_ln_oar_phshighrisk", "pa_ln_oar", "pa_ln_oar_highbmi28",
            "pa_ln_oar_phshighrisk", "can_bsa", "can_bmi", "filter_criteria",
            "removal_reason", "txc_ctr_id", "can_opo_ctr_cd", "can_opo_ctr_ty",
            "li_rec_tx_dt", "liver_safety_net",
        ]
        self.static.drop(columns=[c for c in drop_cols if c in self.static.columns], inplace=True)

        # Normalise datetime columns for downstream ops
        if self.OASIM == OASIM_VERSION_2024:
            self.static["can_listing_dt"] = pd.to_datetime(self.static["can_listing_dt"]).dt.tz_localize(None)
            self.static["can_rem_dt"] = pd.to_datetime(self.static["can_rem_dt"]).dt.tz_localize(None)
        else:
            self.static["can_listing_dt"] = pd.to_datetime(self.static["can_listing_dt"])
            self.static["can_rem_dt"] = pd.to_datetime(self.static["can_rem_dt"])

        # Make all columns lower case for self.static
        self.static.columns = [col.lower() for col in self.static.columns]

    def _compute_real_age(self) -> None:
        """Add *real_age* column (exact age at simulation start)."""
        def _real_age(row):
            if row["can_listing_dt"] < self.sim_begin_time:
                delta_years = (self.sim_begin_time - row["can_listing_dt"]).days / 365.25
                return row["can_age_at_listing"] + delta_years
            return row["can_age_at_listing"]

        if self.static is None:
            raise RuntimeError("Static table not loaded yet")
        self.static["real_age"] = self.static.apply(_real_age, axis=1)

    # ------------------------------------------------------------------
    # Dunder helpers for a *nice* REPL experience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a string representation of the calculator, showing the number of policies registered.
        """
        n_policies = len(self._person_times_for)
        policies = ", ".join(self._friendly_name(p) for p in self._person_times_for) or "<none>"
        return (
            f"TransplantRatesCalculator(policies={n_policies}, "
            f"registered=[{policies}])"
        )


def kdpi_rates_matrix(path, final_epts, final_cpra, donor, read_output, step = 10):
    output = read_output(path, final_epts, final_cpra, donor)

    # xedges = np.linspace(0, 1, 11)
    # yedges = np.linspace(0, 100, 11)

    xedges = np.linspace(0, 1, int(1/(step/100)) + 1)   # 0.0, 0.05, 0.10, …, 1.0
    yedges = np.linspace(0, 100, int(100/step) + 1) 

    x_bins = pd.cut(output["epts_pct"], xedges, include_lowest=True, right=True)
    y_bins = pd.cut(output["kdpi_at_allocation"], yedges, include_lowest=True, right=True)

    # 2D histogram with right-closed bins
    ct = pd.crosstab(x_bins, y_bins)
    matrix = ct.to_numpy() / ct.values.sum()

    return matrix


def make_distribution(path, final_epts, final_cpra, donor, read_output, step=10):
    """
    Reads the output and computes distributions for epts_pct (0–1 scale) 
    and kdpi_at_allocation (0–100 scale).

    Parameters
    ----------
    path : str
        Input path for read_output.
    final_epts : any
        Parameter for read_output.
    final_cpra : any
        Parameter for read_output.
    donor : any
        Parameter for read_output.
    read_output : read_output_epts_cpra
        Function to read data. Must return a DataFrame with 'epts_pct' and 'kdpi_at_allocation'.
    step : int, optional (default=10)
        Step size for kdpi_at_allocation bins (in percent).
        epts_pct will always use step=0.1.

    Returns
    -------
    dict
        {
            "epts_counts": counts per bin for epts_pct,
            "epts_perc": percentages per bin for epts_pct,
            "kdpi_counts": counts per bin for kdpi_at_allocation,
            "kdpi_perc": percentages per bin for kdpi_at_allocation
        }
    """
    output = read_output(path, final_epts, final_cpra, donor)

    # EPTS distribution (0–1, step 0.1)
    epts_bins = np.arange(0, 1.0 + step/100, step/100)
    epts_cats = pd.cut(output["epts_pct"], bins=epts_bins,
                       include_lowest=True, right=True)
    epts_counts = epts_cats.value_counts().sort_index()
    epts_perc = (epts_counts / len(output)).round(4)

    # KDPI distribution (0–100, step)
    kdpi_bins = np.arange(0, 100 + step, step)
    kdpi_cats = pd.cut(output["kdpi_at_allocation"], bins=kdpi_bins,
                       include_lowest=True, right=True)
    kdpi_counts = kdpi_cats.value_counts().sort_index()
    kdpi_perc = (kdpi_counts / len(output)).round(4)

    return {
        "epts_counts": epts_counts,
        "epts_perc": epts_perc,
        "kdpi_counts": kdpi_counts,
        "kdpi_perc": kdpi_perc,
    }


def epts_at_start(candidate: pd.DataFrame, gen_hist: pd.DataFrame, sim_begin_time: datetime) -> pd.DataFrame:
    """
    Computes EPTS_PCT values for candidates at the start of simulation / listing date

    Input:
    ----------
    candidate : Candidate data, pandas DataFrame
    gen_hist : Historical event data, pandas DataFrame
    sim_begin_time : Simulation start time, datetime

    Returns:
    -------
    final_epts : EPTS_PCT values at the start of simulation, pandas DataFrame
    """
    all_epts = pd.concat([candidate[["cand_id", "cand_event_datetime", "epts_pct"]], gen_hist], ignore_index=True)
    all_epts['cand_event_datetime'] = pd.to_datetime(all_epts['cand_event_datetime'], errors='coerce').dt.tz_localize(None)
    simul_epts = all_epts[all_epts['cand_event_datetime'] < sim_begin_time].copy()
    simul_epts = simul_epts.sort_values(by=['cand_id', 'cand_event_datetime'])
    simul_epts = simul_epts.drop_duplicates(subset=['cand_id'], keep='last')
    
    simul_ids = set(simul_epts["cand_id"])
    missing_epts = all_epts[(~all_epts["cand_id"].isin(simul_ids)) & (all_epts['cand_event_datetime'] > sim_begin_time)].copy()
    missing_epts = missing_epts.sort_values(by=['cand_id', 'cand_event_datetime'])
    missing_epts = missing_epts.drop_duplicates(subset=['cand_id'], keep='first')
    
    final_epts = pd.concat([missing_epts, simul_epts], ignore_index=True)
    
    return final_epts


def cpra_at_start(timevarying: pd.DataFrame, sim_begin_time: datetime, OASIM: str = DEFAULT_OASIM_VERSION) -> pd.DataFrame:
    """
    This function processes the candidate's cPRA values before the simulation starts.
    It returns the last cPRA value before the simulation start or the first one after the start.
    Works in tandem with generate_raw_person_times function.

    Args:
    - timevarying (DataFrame): DataFrame containing time-varying candidate data including cPRA values.
    - sim_begin_time (datetime): The start time of the simulation.

    Returns:
    - final_cpra (DataFrame): DataFrame with the relevant cPRA values for each candidate at the start of the simulation.
    """
    if OASIM == OASIM_VERSION_2024:
        final_cpra = timevarying[["cand_id", "canhx_cpra"]]
        return final_cpra


    # Convert event datetime to proper datetime format and remove timezone information
    timevarying['cand_event_datetime'] = pd.to_datetime(timevarying['cand_event_datetime'], errors='coerce').dt.tz_localize(None)
    
    # Get the last cPRA value before the simulation starts
    simul_cpra = timevarying[timevarying['cand_event_datetime'] < sim_begin_time].copy()
    simul_cpra = simul_cpra.sort_values(by=['cand_id', 'cand_event_datetime'])
    simul_cpra = simul_cpra.drop_duplicates(subset=['cand_id'], keep='last')

    # Identify candidates missing from simul_cpra and get their first cPRA value after simulation starts
    simul_ids = set(simul_cpra["cand_id"])
    missing_cpra = timevarying[(~timevarying["cand_id"].isin(simul_ids)) & (timevarying['cand_event_datetime'] > sim_begin_time)].copy()
    missing_cpra = missing_cpra.drop_duplicates(subset=['cand_id'], keep='first')

    # Combine both DataFrames to get the final cPRA at the start of the simulation
    final_cpra = pd.concat([missing_cpra, simul_cpra], ignore_index=True)
    
    return final_cpra



def get_transplant_times(path: str | os.PathLike, donor: pd.DataFrame) -> pd.DataFrame:
    output = read_output_default(path)    
    donor['don_id'] = donor['don_id'].astype(str)
    output['don_id'] = output['don_id'].astype(str)
    
    output = pd.merge(output, donor[['don_id', 'don_event_datetime', 'kdpi_at_allocation']], on='don_id', how='left')
    output["don_event_datetime"] = pd.to_datetime(output["don_event_datetime"], errors='coerce').dt.tz_localize(None)
    return output



def get_person_times(path, donor, static, sim_begin_time, sim_end_time, generated_removal, final_epts = None, final_cpra = None, race_df = None, OASIM = DEFAULT_OASIM_VERSION):
    static = static.copy()
    transplant_times = get_transplant_times(path, donor)
    
    # Change the removal date 
    static = pd.merge(static, transplant_times[['cand_id', 'don_event_datetime']], on='cand_id', how='left')
    # Convert don_event_datetime to datetime before assignment
    static['don_event_datetime'] = pd.to_datetime(static['don_event_datetime']).dt.tz_localize(None)
    static.loc[static['don_event_datetime'].notna(), 'can_rem_dt'] = static['don_event_datetime']
    
    # Ensure can_rem_dt is properly converted to datetime before comparison
    static['can_rem_dt'] = pd.to_datetime(static['can_rem_dt']).dt.tz_localize(None)
    static['can_rem_dt'] = static['can_rem_dt'].apply(lambda x: min(x, sim_end_time) if pd.notna(x) and x > sim_end_time else x)
    
    # Step 1: Split the DataFrame into rows with listing date before and after sim_begin_time
    before_sim_begin = static[static['can_listing_dt'] < sim_begin_time]
    after_sim_begin = static[static['can_listing_dt'] >= sim_begin_time]
    
    # Step 2: Get the most recent row per pers_id before sim_begin_time
    most_recent_before_sim_begin = before_sim_begin.loc[before_sim_begin.groupby('pers_id')['can_listing_dt'].idxmax()]
    
    # Update can_rem_dt for the most recent row if necessary
    for idx, row in most_recent_before_sim_begin.iterrows():
        if pd.isna(row['can_rem_dt']):
            # Find the earliest row for the same pers_id with can_listing_dt after sim_begin_time
            earliest_after_sim_begin = after_sim_begin[after_sim_begin['pers_id'] == row['pers_id']].sort_values(by='can_listing_dt').head(1)
            if not earliest_after_sim_begin.empty:
                # Update can_rem_dt with the earliest can_listing_dt of the subsequent row
                most_recent_before_sim_begin.at[idx, 'can_rem_dt'] = earliest_after_sim_begin.iloc[0]['can_listing_dt']
    
    # Step 3: For pers_ids with multiple rows after sim_begin_time, sort by can_listing_dt and fix overlaps
    def fix_overlaps(group):
        group = group.sort_values(by='can_listing_dt').copy()  # Sort by can_listing_dt
        for i in range(len(group) - 1):  # Iterate through all but the last row
            if pd.isna(group.iloc[i]['can_rem_dt']) or group.iloc[i]['can_rem_dt'] >= group.iloc[i + 1]['can_listing_dt']:
                # If there is an overlap, adjust the can_rem_dt of the current row to the can_listing_dt of the next row
                group.at[group.index[i], 'can_rem_dt'] = group.iloc[i + 1]['can_listing_dt'] - pd.Timedelta(days=1)
        return group

    # Apply the fix_overlaps function to each pers_id group with multiple rows after sim_begin_time
    static = pd.concat([most_recent_before_sim_begin, after_sim_begin])
    static = static.groupby('pers_id', group_keys=False).apply(fix_overlaps)

    # Optional: Reset the index 
    static = static.reset_index(drop=True)

    # Step 6: Calculate TIME_DIFFERENCE
    static['time1'] = static['can_listing_dt'].apply(lambda x: max(x, sim_begin_time) if pd.notna(x) else sim_begin_time)
    static['time2'] = static['can_rem_dt'].apply(lambda x: min(x, sim_end_time) if pd.notna(x) else sim_end_time)
    
    static['time_difference'] = (static['time2'] - static['time1']).apply(lambda x: x.days)

    # Add EPTS at simulation start / listing / last value before simulation start and race
    if final_epts is not None:
        static = pd.merge(static, final_epts[['cand_id', 'epts_pct']], on='cand_id', how='left')    
    if final_cpra is not None:
        if OASIM == OASIM_VERSION_2024:
            if "canhx_cpra" not in final_cpra.columns:
                logger.warning(f"canhx_cpra not in final_cpra. Available columns: {final_cpra.columns.tolist()}")
            else:
                static = pd.merge(static, final_cpra[['cand_id', 'canhx_cpra']], on='cand_id', how='left')
        else:
            static = pd.merge(static, final_cpra[['cand_id', 'canhx_cpra']], on='cand_id', how='left')
    if race_df is not None:
        static = pd.merge(static, race_df[['cand_id', 'can_race_srtr', 'can_ethnicity_srtr']], on='cand_id', how='left')
    return static

def get_person_times2(path, donor, static, sim_begin_time, sim_end_time, generated_removal, final_epts = None, final_cpra = None, race_df = None, OASIM = DEFAULT_OASIM_VERSION):
    static = static.copy()

    # Remove people who were removed before simulation start
    static[~(static["can_rem_dt"] < sim_begin_time)]

    transplant_times = get_transplant_times(path, donor)

    # Change the removal date to a generated one for people who are de-transplanted
    static = pd.merge(static, generated_removal[['cand_id', 'cand_event_datetime']], on='cand_id', how='left')
    # Convert cand_event_datetime to datetime before assignment
    static['cand_event_datetime'] = pd.to_datetime(static['cand_event_datetime']).dt.tz_localize(None)
    static.loc[static['cand_event_datetime'].notna(), 'can_rem_dt'] = static['cand_event_datetime']

    # Change the removal date to a simulated transplant date 
    static = pd.merge(static, transplant_times[['cand_id', 'don_event_datetime']], on='cand_id', how='left')
    # Convert don_event_datetime to datetime before assignment
    static['don_event_datetime'] = pd.to_datetime(static['don_event_datetime']).dt.tz_localize(None)
    static.loc[static['don_event_datetime'].notna(), 'can_rem_dt'] = static['don_event_datetime']

    # Ensure can_rem_dt is properly converted to datetime before comparison
    static['can_rem_dt'] = pd.to_datetime(static['can_rem_dt']).dt.tz_localize(None)

    # Take the min between the actual removal date and simulation end time
    static['can_rem_dt'] = static['can_rem_dt'].apply(lambda x: min(x, sim_end_time) if pd.notna(x) and x > sim_end_time else x)

    static['time1'] = static['can_listing_dt'].apply(lambda x: max(x, sim_begin_time) if pd.notna(x) else sim_begin_time)
    static['time2'] = static['can_rem_dt'].apply(lambda x: min(x, sim_end_time) if pd.notna(x) else sim_end_time)

    static['time_difference'] = (static['time2'] - static['time1']).apply(lambda x: x.days)


    # Add EPTS at simulation start / listing / last value before simulation start and race
    if final_epts is not None:
        static = pd.merge(static, final_epts[['cand_id', 'epts_pct']], on='cand_id', how='left')   

    if final_cpra is not None:
        if OASIM == OASIM_VERSION_2024:
            if "canhx_cpra" not in final_cpra.columns:
                logger.warning(f"canhx_cpra not in final_cpra. Available columns: {final_cpra.columns.tolist()}")
            else:
                static = pd.merge(static, final_cpra[['cand_id', 'canhx_cpra']], on='cand_id', how='left')
        else:
            static = pd.merge(static, final_cpra[['cand_id', 'canhx_cpra']], on='cand_id', how='left')

    if race_df is not None:
        static = pd.merge(static, race_df[['cand_id', 'can_race_srtr', 'can_ethnicity_srtr']], on='cand_id', how='left')

    person_times = static

    return person_times


def get_or_load_person_times(path, CACHE_DIR, save_cache = True, *args, OASIM = DEFAULT_OASIM_VERSION):
    if not save_cache or CACHE_DIR is None:
        logger.debug(f"Computing person_times without caching for: {path}.")
        return get_person_times2(path, *args, OASIM = OASIM)
    else:
        """Load cached person_times if available; otherwise compute and cache it."""
        base_name = os.path.splitext(os.path.basename(path))[0]
        cache_file = os.path.join(CACHE_DIR, f"{base_name}_person_times.csv")

        if os.path.exists(cache_file):
            logger.debug(f"Loading cached result: {cache_file}")
            return pd.read_csv(cache_file, low_memory=False)
        else:
            logger.debug(f"Computing person_times with caching for: {base_name}.")

        #Computing and caching person_times for: {base_name}
        person_times = get_person_times2(path, *args, OASIM = OASIM)
        if save_cache:
            person_times.to_csv(cache_file, index=False)
        return person_times


def count_people_in_bins(person_times, step=20):
    """
    Counts the number of people in each EPTS bin.

    Inputs:
        person_times - DataFrame containing 'epts_pct' column with percentages
        step - bin size for EPTS bins, default=20

    Outputs:
        DataFrame with bin ranges and the count of people in each bin
    """
    # Ensure the 'epts_pct' column exists
    if 'epts_pct' not in person_times:
        raise ValueError("The input DataFrame must contain an 'epts_pct' column.")
    
    # Create bins for EPTS, ensuring 0 and 100 are included
    bins = np.arange(0, 101, step) / 100  # Generate bins in percentage form
    bins[-1] = 1.0  # Ensure the last bin edge is exactly 1 (100%)
    person_times['epts_bin'] = pd.cut(person_times['epts_pct'], bins, right=False, include_lowest=True)
    
    # Count the number of people in each bin
    bin_counts = person_times.groupby('epts_bin').size()
    
    # Prepare a DataFrame for output
    result = bin_counts.reset_index(name='People_Count')
    result['Bin_Range'] = result['epts_bin'].apply(lambda x: f"{int(x.left*100)}-{int(x.right*100)}")
    result = result[['Bin_Range', 'People_Count']]

    # Display the result
    return result


def get_five_year_survival(path, final_epts, final_cpra, donor, read_output):
    ret = {}
    output = read_output(path, final_epts, final_cpra, donor)
    output['five_year_survival'] = output.apply(lambda row: five_year_survival(int(row['epts_pct'] * 100), int(row['kdpi_at_allocation'])), axis=1)
    ret['Five Year Survival (Bae)'] = output['five_year_survival'].mean()
    return ret


def read_output_default(path):
    """
    Returns the output file that only has cand_id from candidate data. Filters to only include kidneys.
    """
    output = pd.read_csv(path)
    output.columns = [col.lower() for col in output.columns]
    output = output[(output["organ"]=="LKI") | (output["organ"]=="RKI")]
    output.dropna(subset=["cand_id"], inplace=True)
    return output


def read_output_epts_cpra(path, final_epts, final_cpra, donor) -> pd.DataFrame:
    """
    Returns the output file that only has cand_id from candidate data.
    Adds a column with epts_pct scores most recent to the donor don_event_datetime.

    Input: 
        path - a path to the OASIM output file, string
        candidate - read cleaned_donor_data, pandas dataframe
    Return: 
        A dataframe containing relevant OASIM output rows, pandas dataframe
    """

    output = pd.read_csv(path)
    output.columns = [col.lower() for col in output.columns]
    # Only kidneys
    output = output[(output["organ"]=="LKI") | (output["organ"]=="RKI")]
    output.dropna(subset=["cand_id"], inplace=True)
    
    # Only the candidates that exist in candidates
    cand_id_set = set(final_epts['cand_id'])
    output = output[output['cand_id'].isin(cand_id_set)]
    
    # Adding don_event_datetime to the output file
    output = pd.merge(output, donor[['don_id', 'don_event_datetime', 'kdpi_at_allocation', 'don_age']], on='don_id', how='left')
    output["don_event_datetime"] = pd.to_datetime(output["don_event_datetime"], errors='coerce').dt.tz_localize(None)
    
    merged_df = pd.merge(output, final_epts[['cand_id', 'epts_pct']], on='cand_id', how='left')
    output['epts_pct'] = merged_df['epts_pct']
    
    merged_df = pd.merge(output, final_cpra[['cand_id', 'canhx_cpra']], on='cand_id', how='left')
    output['canhx_cpra'] = merged_df['canhx_cpra']
    
    
    output["cand_id_organ"] = output["cand_id"].astype(str) + "_" + output["organ"]
    
    return output