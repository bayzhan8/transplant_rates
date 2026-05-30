# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Synthetic data generator (`examples/generate_synthetic_data.py`) and a runnable
  quick-start notebook (`examples/quickstart_synthetic.ipynb`) so the full workflow
  can be run without restricted registry data.
- Automated test suite (`tests/`) covering the rate and offer calculations on the
  synthetic dataset.
- Packaging via `pyproject.toml` for `pip install` support.
- Continuous integration running the test suite on Python 3.10–3.12.
- JOSS paper draft (`paper.md`, `paper.bib`) and `CONTRIBUTING.md`.

### Changed
- Reworked plotting helpers: EPTS axis labelled on a 0–100 scale, simplified the
  candidate age plot title, and removed box-plot whiskers and outlier markers.

### Removed
- Legacy example notebooks that depended on restricted data paths, replaced by the
  synthetic quick-start notebook.

## [1.0.0]

### Added
- Initial public release of `transplant_rates` with `TransplantRatesCalculator` and
  `OffersCalculator`, subgroup transplant-rate computation, multi-policy comparison,
  and the plotting and offers-analysis modules.
