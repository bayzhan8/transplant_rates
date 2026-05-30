# Contributing

Thanks for your interest in improving `transplant_rates`. Contributions of all
kinds are welcome: bug reports, documentation fixes, new analyses, and tests.

## Reporting issues / getting support

- Please open an issue on the [GitHub issue tracker](https://github.com/bayzhan8/transplant_rates/issues).
- For bugs, include: what you ran, what you expected, what happened, and the
  versions of Python and the dependencies (`pip list`). A minimal reproducible
  example using the bundled synthetic data (`examples/synthetic_data/`) is ideal.
- For questions and usage help, open an issue with the `question` label.

## Development setup

```bash
git clone https://github.com/bayzhan8/transplant_rates
cd transplant_rates
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

Generate the synthetic dataset and run the example notebook:

```bash
python examples/generate_synthetic_data.py
jupyter notebook examples/quickstart_synthetic.ipynb
```

## Running the tests

```bash
pytest
```

The test suite runs entirely on fabricated synthetic data and does **not** require
SRTR, OASIM, or any restricted dataset.

## Pull requests

1. Fork the repository and create a feature branch.
2. Make your change, keeping functions documented and adding/adjusting tests.
3. Ensure `pytest` passes.
4. Do **not** commit real patient-level or registry data, or notebook outputs that
   contain such data. The synthetic generator is the only data that belongs in the
   repository.
5. Open a pull request describing the change and its motivation.
