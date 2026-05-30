# Transplant Rates Analysis Pipeline

A Python package for analyzing and comparing kidney transplant allocation policies using SRTR data and OASIM simulation outputs.

## Overview

`transplant_rates` compares kidney allocation policies using OASIM simulation outputs and SRTR registry data. There are two workflows:

1. **Transplant rates** (`TransplantRatesCalculator`): waitlist person-time and transplant rates by subgroup (age, race, ethnicity, sex, blood type, EPTS, CPRA), with summary tables and comparison plots.
2. **Offers analysis** (`OffersCalculator`): offer-level metrics from offers files (one row per candidate/kidney offer), such as offers per kidney, how donor KDPI varies with recipient EPTS, race, and waiting time, and candidate vs. donor age.

One goal of this work is to provide a standard, reusable way to compute transplant rates across demographic groups and to analyze and compare OASIM outputs, instead of rewriting one-off code for each study.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/bayzhan8/transplant_rates
cd transplant_rates
```

2. Install the package (and its dependencies):
```bash
pip install .
# or, for development (editable install + test dependencies):
pip install -e ".[test]"
```

This installs `pandas`, `numpy`, `matplotlib`, and `seaborn` and makes the package
importable as `transplant_rates`.

## Try it on synthetic data (no real data needed)

The repository ships a small, fully synthetic dataset so you can run everything
without SRTR/OASIM access:

```bash
python examples/generate_synthetic_data.py        # fabricates examples/synthetic_data/
jupyter notebook examples/quickstart_synthetic.ipynb   # runs both calculators end-to-end
```

`examples/quickstart_synthetic.ipynb` walks through both `TransplantRatesCalculator`
and `OffersCalculator` on the synthetic data. Every value in the synthetic dataset is
randomly generated; it contains no real patient data. See `examples/README.md` for
details.

## Running the tests

```bash
pip install -e ".[test]"
pytest
```

The test suite runs entirely on the synthetic data and requires no restricted
datasets.

## Quick Start: Transplant Rates

See `examples/quickstart_synthetic.ipynb` for a complete, runnable example on the
bundled synthetic dataset.

```python
from datetime import datetime
from tr_calculator import TransplantRatesCalculator

# Initialize the calculator
calc = TransplantRatesCalculator(
    sim_begin_time=datetime(2021, 3, 15),
    sim_end_time=datetime(2022, 3, 15),
    cache_dir="./person_times_cache"
)

# Load your data
calc.load_core_data(
    donor_path="path/to/cleaned_donor_data.csv",
    candidate_path="path/to/cleaned_timevarying_KAS_candidate_data.csv",
    static_path="path/to/cleaned_static_candidate_data.csv",
    timevarying_path="path/to/cleaned_timevarying_candidate_data.csv",
    gen_removal_path="path/to/generated_removal_candidate_data.csv",
    gen_hist_path="path/to/generated_history_candidate_data.csv",
    race_path="path/to/can_race.csv"
)

# Add allocation policies (OASIM output files)
# Option 1: Single policies with optional display names
calc.add_policies(
    [
        "path/to/policy1_output.txt",
        "path/to/policy2_output.txt",
        "path/to/policy3_output.txt"
    ],
    name_map={
        "path/to/policy1_output.txt": "Current Policy",
        "path/to/policy2_output.txt": "Proposed Policy A",
        "path/to/policy3_output.txt": "Proposed Policy B"
    }
)

# Option 2: Policy groups with multiple iterations
# Each group contains multiple iterations of the same policy
# Metrics will show mean, min, and max across iterations
kas250_iterations = [
    "path/to/kas250_iter1.csv",
    "path/to/kas250_iter2.csv",
    "path/to/kas250_iter3.csv",
    # ... more iterations
]
calc.add_policy_group(kas250_iterations, group_name="KAS250")

newpolicy_iterations = [
    "path/to/newpolicy_iter1.csv",
    "path/to/newpolicy_iter2.csv",
    # ... more iterations
]
calc.add_policy_group(newpolicy_iterations, group_name="NewPolicy")

# Compute person-times for all policies
calc.compute_all_person_times()

# Generate summary table
summary = calc.compute_summary_table()
print(summary)
```

## Offers Analysis

`OffersCalculator` works on **offers files** (one row per candidate/kidney *offer*,
with columns `iteration`, `don_id`, `cand_id`, `rank`, `segment`, `accepted`,
`probability`) rather than final transplant events. It answers questions like "how
many offers does each kidney generate?" and "what KDPI do recipients get across the
EPTS distribution, by race, or by waiting time?".

It is a subclass of `TransplantRatesCalculator`, so it loads the same core data (for
EPTS / KDPI / race joins) and adds offer-level summaries and plots.

```python
from datetime import datetime
from offers_calculator import OffersCalculator

calc = OffersCalculator(
    sim_begin_time=datetime(2021, 3, 15),
    sim_end_time=datetime(2022, 3, 15),
    cache_dir="./person_times_cache",
)

# Same core data as the rates pipeline (needed for EPTS / KDPI / race joins)
calc.load_core_data(
    donor_path="path/to/cleaned_donor_data.csv",
    candidate_path="path/to/cleaned_timevarying_KAS_candidate_data.csv",
    static_path="path/to/cleaned_static_candidate_data.csv",
    timevarying_path="path/to/cleaned_timevarying_candidate_data.csv",
    gen_removal_path="path/to/generated_removal_candidate_data.csv",
    gen_hist_path="path/to/generated_history_candidate_data.csv",
    race_path="path/to/can_race.csv",
)

# Register offers files (one row per candidate-kidney offer)
OFFERS = [
    "path/to/policy1_output_offers.txt",
    "path/to/policy2_output_offers.txt",
]
calc.register_offers(OFFERS, name_map={
    "path/to/policy1_output_offers.txt": "Current Policy",
    "path/to/policy2_output_offers.txt": "Proposed Policy",
})

# Offers-per-kidney summary (use group_by_iteration=True for multi-iteration files)
print(calc.summarize_offers_per_kidney(OFFERS[0]))

# Plots
calc.plot_offers_per_kidney_distribution(OFFERS[0])     # histogram + CDF
calc.plot_epts_kdpi_catplot(OFFERS, epts_step=0.1)      # KDPI across EPTS percentile bins
calc.plot_kdpi_by_race(OFFERS)                          # donor KDPI by recipient SRTR race
calc.plot_candidate_donor_age(OFFERS)                   # candidate vs donor age
```

See **`OFFERS_CALCULATOR_WORKFLOW.md`** for a diagram of inputs, merges, and plot
outputs, and the method-by-method reference under
[Key Classes and Functions](#offerscalculator).

## Data Requirements

### OASim version (2023 vs. 2024)

OASim has produced its candidate/donor data in more than one format over time, so
the pipeline supports two: the **2023** profile (the default) and the **2024**
profile. You must tell the calculator which one your data came from via the
`OASIM` argument to `load_core_data(...)`:

```python
calc.load_core_data(..., OASIM="2023")   # default
calc.load_core_data(..., OASIM="2024")
```

**This only affects how the input data is read, not the methodology** — person-time
and transplant rates are computed the same way for both. The calculator simply
remaps the 2024 layout onto the 2023 conventions internally. Concretely, the
differences it handles are:

- **Column names.** The 2024 format uses `cand_bloodtype`, `listing_dt`, `rem_dt`,
  `age_at_listing`, `cpra`, `gender`, donor `kdpi`, and `cand_center_longitude/latitude`;
  these are renamed to the 2023 names (`can_abo`, `can_listing_dt`, `can_rem_dt`,
  `can_age_at_listing`, `canhx_cpra`, `can_gender`, `kdpi_at_allocation`,
  `can_center_longitude/latitude`).
- **Time-varying data.** 2023 provides a separate time-varying candidate table;
  2024 does not, so all fields are taken from the static candidate table.
- **CPRA.** In 2023, CPRA is time-varying (the last value before simulation start,
  or the first value after). In 2024, CPRA is a single static value read directly
  from `canhx_cpra`.
- **Datetimes.** 2024 timestamps are timezone-aware and are converted to naive
  (timezone-stripped); 2023 dates are parsed as-is.

Use the version that matches the OASim run that produced your data; using the wrong
one will misread columns (or fail to find them).

### Input Files

**OASIM-Generated Data:**
1. **Donor Data** (`cleaned_donor_data.csv`): OASIM-generated donor characteristics and event dates
2. **Candidate Data** (`cleaned_timevarying_KAS_candidate_data.csv`): OASIM-generated time-varying candidate data
3. **Static Data** (`cleaned_static_candidate_data.csv`): OASIM-generated static candidate characteristics
4. **Time-varying Data** (`cleaned_timevarying_candidate_data.csv`): OASIM-generated additional time-varying candidate data
5. **Removal Data** (`generated_removal_candidate_data.csv`): OASIM-generated removal candidate data
6. **History Data** (`generated_history_candidate_data.csv`): OASIM-generated history candidate data

**SRTR Data:**
7. **Race Data** (`can_race.csv`): SRTR candidate race/ethnicity information

### Allocation Output Files

Each allocation policy requires an **OASIM-generated output file** containing simulated transplant events. Each row represents one transplant event with columns:
- `cand_id`: Candidate ID
- `don_id`: Donor ID
- `organ`: Organ type (should be 'KI' for kidney)
- `don_event_datetime`: Transplant date
- Additional donor characteristics (KDPI, center location, etc.)

## Package Structure

```
├── README.md
├── pyproject.toml          # Packaging / install metadata
├── tr_calculator.py        # Transplant match outputs & person-time pipeline
├── offers_calculator.py    # Offers-level outputs (rank, segment, acceptance)
├── rates.py                # Core statistical functions
├── plots.py                # Visualization functions
├── plot_style.py           # Shared plot styling
├── OFFERS_CALCULATOR_WORKFLOW.md           # Offers analysis inputs/merges/plots reference
├── examples/               # Synthetic data generator + runnable quickstart
├── tests/                  # pytest suite (runs on synthetic data)
└── paper.md, paper.bib     # JOSS paper draft
```

### Key Classes and Functions

#### `TransplantRatesCalculator`
Main class that orchestrates the entire analysis pipeline.

**Key Methods:**
- `load_core_data()`: Load and preprocess all required data
- `add_policies()`: Register allocation policy output files
- `compute_all_person_times()`: Calculate person-times for all policies
- `compute_summary_table()`: Generate comparison table across all policies

#### `OffersCalculator`
Subclass of `TransplantRatesCalculator` for **offers** files (one row per candidate–kidney offer):
`iteration`, `don_id`, `cand_id`, `rank`, `segment`, `accepted`, `probability`.

- `load_core_data(...)`: Same as the parent — required for EPTS/KDPI joins.
- `register_offers(paths, name_map=...)`: Register offers CSV paths.
- `summarize_offers_per_kidney(path)`: Mean, median, etc. of **offers per kidney** (rows per `don_id`).
- `summarize_offers_per_kidney_by_segment(path)`: Same metrics stratified by `segment`.
- `offers_per_kidney_counts(path, group_by_iteration=False)`: Raw counts per kidney.
- `enriched_offers(path)`: Offers rows with `epts_pct`, `kdpi_at_allocation`, candidate `real_age` / `can_age_at_listing` (from static), and `don_age` when present on the donor file.
- `plot_offers_per_kidney_distribution(path, ...)`: Histogram + CDF of offers-per-kidney.
- `plot_epts_kdpi_catplot(paths, epts_step=0.1, kind='box', ...)`: KDPI vs EPTS bins (accepted offers), for comparing policies.
- `plot_candidate_donor_age(paths, ...)`: **catplot** by default — binned candidate age (x) vs donor age (y), like other offer catplots; `as_scatter=True` for raw-age scatter.
- `summarize_kdpi_by_race(path)` / `plot_kdpi_by_race(paths, ...)`: **donor KDPI** by recipient **SRTR race** via `sns.catplot` (needs `race_path` in `load_core_data`).
- `plot_epts_age_catplot(...)`: optional **EPTS bins (x) vs age (y)** box/violin plots (same x-axis as KDPI catplot).

If the file has multiple `iteration` values, use `group_by_iteration=True` when summarizing per-kidney counts so each run is kept separate.

See **`OFFERS_CALCULATOR_WORKFLOW.md`** for a diagram of inputs, merges, and plot outputs.

#### `rates.py`
Contains functions for calculating transplant rates and related statistics:
- `age_rates()`: Age-specific transplant rates
- `race_rates()`: Race-specific transplant rates
- `ethnicity_rates()`: Ethnicity-specific transplant rates
- `gender_rates()`: Gender-specific transplant rates
- `abo_rates()`: Blood type-specific transplant rates
- `epts_rates()`: EPTS-specific transplant rates
- `cpra_rates()`: CPRA-specific transplant rates
- `distance()`: Travel distance calculations

#### `plots.py`
Provides visualization functions:
- `create_policy_table()`: Generate summary tables
- `plot_policies()`: Create grouped bar plots
- `kdpi_rates_heatmap()`: EPTS vs KDPI heatmaps
- `marginal_xy_plot()`: XY plots for rate comparisons

## Detailed Methodology

### Data Sources and Preprocessing

We used a combination of OASIM-generated data and SRTR data. The OASIM system generated donor, candidate, and event files based on SRTR data, while race/ethnicity information was obtained directly from SRTR. All data processing and analysis were performed in Python, using custom code available in this repository.

#### Candidate Inclusion/Exclusion

- **Inclusion:** Only candidates listed for kidney transplantation (WL_ORG = 'KI') were included in the analysis.
- **Exclusion:** Candidates listed for pancreas transplantation (WL_ORG = 'PA') were excluded at the earliest stage of data processing.
- **Relisting:** If a candidate was relisted, each listing interval was treated as a separate observation.

#### Variable Harmonization

- **Demographics:** Candidate age, race, ethnicity, gender, and blood type were harmonized across all data sources.
- **Blood Type:** Subtypes (e.g., A1, A2, A1B, A2B) were collapsed into major ABO groups (A, B, AB, O).
- **Race/Ethnicity:** Missing race/ethnicity values were imputed as "Unknown."
- **Dates:** All date fields were converted to timezone-naive Python `datetime` objects.

#### Calculation of Real Age

- For each candidate, "real age" at simulation start was calculated as:
  $\[
  \text{Real Age} = \text{Age at Listing} + \frac{\text{Days from Listing to Simulation Start}}{365.25}
  \]$
  If the candidate was listed after simulation start, real age was set to age at listing.

### Allocation Policy Outputs
- For each allocation policy under study, we used **OASIM-generated allocation output files** that contain the complete record of all simulated transplant events during the simulation window.
- Each output file contains one row per transplant event, including candidate ID, donor ID, organ type, transplant date, and donor characteristics.

### Person-Time Calculation

Person-time on the waitlist was calculated for each candidate as follows:

#### Step 1: Identify All Listing Intervals
- For each candidate, identify all listing intervals based on `CAN_LISTING_DT` and `CAN_REM_DT` in the OASIM-generated static candidate data.
- If a candidate was listed before simulation start, use the most recent listing interval that overlaps with the simulation window.
- If a candidate was listed after simulation start, use all listing intervals during the simulation window.

#### Step 2: Adjust for Transplant Events
- For each candidate, identify all transplant events from the OASIM allocation output file.
- For each listing interval, if a transplant occurred during that interval, truncate the interval at the transplant date.
- This ensures that candidates who received transplants do not contribute waitlist time after their transplant.

#### Step 3: Calculate Waitlist Time
- For each listing interval, calculate waitlist time as:
  $\[
  \text{Waitlist Time} = \min(\text{Removal Date}, \text{Transplant Date}, \text{Simulation End}) - \max(\text{Listing Date}, \text{Simulation Start})
  \]$
- If the result is negative or zero, exclude that interval from analysis.

#### Step 4: Handle Multiple Intervals
- Candidates with multiple listing intervals (due to relisting) contribute separate waitlist time intervals.
- Each interval is treated independently in the analysis.

### Assignment of Clinical Covariates

- **EPTS (Estimated Post-Transplant Survival):** For each candidate, the most recent EPTS value prior to simulation start was used. If no value was available before simulation start, the first value after simulation start was used.
- **CPRA (Calculated Panel Reactive Antibody):** Assigned using the same logic as EPTS.
- **Race/Ethnicity:** Assigned based on the most recent available value prior to simulation start. If missing, imputed as "Unknown."

### Calculation of Transplant Rates

For each allocation policy and candidate subgroup, transplant rates were calculated as:

$\[
\text{Transplant Rate} = \frac{\text{Number of transplants in group}}{\text{Total waitlist time in group (days)}} \times 365
\]$

#### Numerator: Transplant Events
- Count the number of transplant events in the OASIM allocation output file for each candidate subgroup.
- Each row in the output file represents one transplant event.
- Only kidney transplants (`organ != 'PA'`) are included.

#### Denominator: Waitlist Time
- Sum the total waitlist time (in days) for all candidates in each subgroup, as calculated above.
- This accounts for the fact that candidates may have different amounts of time on the waitlist.

#### Stratification
- Rates were calculated separately by age group, race, ethnicity, gender, blood type, EPTS bin, and CPRA bin.
- **Age bins:** <18, 18–34, 35–49, 50–64, 65+ years
- **EPTS bins:** 0–20%, 20–40%, 40–60%, 60–80%, 80–100%
- **CPRA bins:** 0–60%, 60–80%, 80–98%, 98–100%

### Travel Distance Calculation

- For each transplant event in the OASIM allocation output, calculate the great-circle (haversine) distance between donor and recipient centers using their latitude and longitude coordinates.
- The median travel distance was reported for each policy.

## Example Usage

See `examples/quickstart_synthetic.ipynb` for a complete, runnable example on the bundled synthetic dataset.

### Basic Analysis

```python
from datetime import datetime
from transplant_rates.tr_calculator import TransplantRatesCalculator

# Set up paths to your data files
DONOR_PATH = "path/to/cleaned_donor_data.csv"  # OASIM-generated
CANDIDATE_PATH = "path/to/cleaned_timevarying_KAS_candidate_data.csv"  # OASIM-generated
STATIC_PATH = "path/to/cleaned_static_candidate_data.csv"  # OASIM-generated
TIMEVARYING_PATH = "path/to/cleaned_timevarying_candidate_data.csv"  # OASIM-generated
GEN_REMOVAL_PATH = "path/to/generated_removal_candidate_data.csv"  # OASIM-generated
GEN_HIST_PATH = "path/to/generated_history_candidate_data.csv"  # OASIM-generated
RACE_PATH = "path/to/can_race.csv"  # SRTR

# Initialize calculator
calc = TransplantRatesCalculator(
    sim_begin_time=datetime(2021, 3, 15),
    sim_end_time=datetime(2022, 3, 15),
    cache_dir="./person_times_cache"
)

# Load data
calc.load_core_data(
    donor_path=DONOR_PATH,
    candidate_path=CANDIDATE_PATH,
    static_path=STATIC_PATH,
    timevarying_path=TIMEVARYING_PATH,
    gen_removal_path=GEN_REMOVAL_PATH,
    gen_hist_path=GEN_HIST_PATH,
    race_path=RACE_PATH
)

# Add policies (OASIM allocation outputs)
calc.add_policies([
    "path/to/policy1_output.txt",
    "path/to/policy2_output.txt"
])

# Compute person-times
calc.compute_all_person_times()

# Generate summary
summary = calc.compute_summary_table()
print(summary)
```

### Advanced Analysis

```python
# Get specific rates for a policy
age_rates = calc.age_rates("path/to/policy1_output.txt")
race_rates = calc.race_rates("path/to/policy1_output.txt")

# Create visualizations
from plots import plot_policies, kdpi_rates_heatmap

# Plot summary table
plot_policies(summary)

# Create heatmap
kdpi_rates_heatmap("path/to/policy1_output.txt", calc.final_epts, calc.donor)
```

## Assumptions and Limitations

- Only candidates listed for kidney transplantation were included; pancreas candidates were excluded.
- Waitlist time was censored at the earliest of transplant, removal, or simulation end.
- Candidates could contribute multiple intervals if relisted.
- EPTS and CPRA values were assigned based on the most recent value before simulation start, or the first after if missing.
- All rates are reported per person-year (365 days).
- Missing or inconsistent dates were handled by exclusion of affected intervals.
- The accuracy of results depends on the completeness and correctness of the underlying OASIM-generated data and allocation outputs.
- **OASIM allocation outputs are assumed to be complete and accurate records of all simulated transplant events for each policy.**
- Race/ethnicity data from SRTR may have missing values, which were imputed as "Unknown."

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or issues, contact Bayzhan Mukatay (bayzhan.mukatay@gmail.com),
Daniyar Akizhanov (daniyar.akizhanov@nyulangone.org), and
Sommer Gentry (Sommer.Gentry@nyulangone.org).
