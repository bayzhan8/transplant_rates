"""
Shared matplotlib / seaborn styling for transplant_rates figures.

Matches the conventions used across ``plots.py`` (Spectral palette, light grids,
``savefig`` DPI 300, typical figure sizes).
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

# Align with existing bar/line plots in plots.py
GRID_ALPHA = 0.3
SAVEFIG_DPI = 300
DEFAULT_FIGSIZE = (12, 6)
SPECTRAL_PALETTE_NAME = "Spectral"

_style_applied = False


def apply_plot_style() -> None:
    """
    Idempotent: set seaborn theme and matplotlib defaults once per session.
    Call at the start of each public plotting function for consistent figures.
    """
    global _style_applied
    sns.set_theme(style="whitegrid", context="notebook")
    mpl.rcParams["axes.grid"] = True
    mpl.rcParams["grid.alpha"] = GRID_ALPHA
    mpl.rcParams["grid.linestyle"] = "-"
    mpl.rcParams["legend.frameon"] = True
    mpl.rcParams["legend.framealpha"] = 0.95
    mpl.rcParams["figure.facecolor"] = "white"
    mpl.rcParams["axes.facecolor"] = "white"
    mpl.rcParams["savefig.dpi"] = SAVEFIG_DPI
    mpl.rcParams["savefig.bbox"] = "tight"
    if not _style_applied:
        _style_applied = True


def spectral_colors(n: int, alpha: float = 0.8) -> List[Tuple[float, float, float, float]]:
    """Same semi-transparent Spectral palette as grouped bar charts in ``plots.py``."""
    base = sns.color_palette(SPECTRAL_PALETTE_NAME, n_colors=max(n, 1))
    return [(float(r), float(g), float(b), alpha) for r, g, b in base[:n]]


def spectral_rgba_rgb(color: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
    """Strip alpha for APIs that need RGB only (e.g. some seaborn line plots)."""
    return color[0], color[1], color[2]
