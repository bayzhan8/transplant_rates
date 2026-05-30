"""
Transplant Rates Analysis Pipeline

A comprehensive Python package for analyzing and comparing kidney transplant 
allocation policies using SRTR data and OASIM simulation outputs.

Installation:
    pip install -r requirements.txt

For more information, see README.md
"""

__version__ = "1.0.0"

from .tr_calculator import TransplantRatesCalculator
from .offers_calculator import OffersCalculator, read_offers_csv

__all__ = [
    "TransplantRatesCalculator",
    "OffersCalculator",
    "read_offers_csv",
]
