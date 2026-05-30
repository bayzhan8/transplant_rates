# Examples & synthetic data

This folder lets you run the full package without any real data.

## Files

- `generate_synthetic_data.py`: fabricates a small dataset under `synthetic_data/`.
  Every value is randomly generated; nothing here reads SRTR, OASIM, or any
  real/cluster data.
- `synthetic_data/`: the generated CSV/TXT inputs (core tables, two policy outputs
  plus a two-iteration policy group, and offers files).
- `quickstart_synthetic.ipynb`: a notebook that runs both `TransplantRatesCalculator`
  and `OffersCalculator` on the synthetic data, with summary tables, subgroup rates,
  and plots. It regenerates the data if it is missing.

## Run it

```bash
python generate_synthetic_data.py            # writes synthetic_data/
jupyter notebook quickstart_synthetic.ipynb   # runs the full pipeline
```

The synthetic dataset is intentionally tiny (a few hundred candidates/donors) so it
runs in seconds and keeps the repository small. It is meant to demonstrate the API
and exercise the code paths, not to produce clinically meaningful rates.

## Real data

For real analyses, point `load_core_data(...)` at your own OASIM-generated candidate
and donor files and SRTR `can_race.csv`, and pass your simulator's policy output
`.txt` files to `add_policies(...)` / `add_policy_group(...)`. See the top-level
`README.md` for the expected schema.
