"""Radial plasma profiles — density and temperature across the minor radius.

Uses generalized parabolic profiles:
    F(r) = F_core * (1 - (r/a)^2)^alpha

where alpha is dynamically linked to li (internal inductance):
    alpha = alpha_base * (li / li_ref)^2

Higher li → more peaked profile, lower li → flatter.
"""
from __future__ import annotations
import numpy as np

_LI_REF = 0.85
_ALPHA_BASE_DENSITY = 1.0
_ALPHA_BASE_TEMPERATURE = 1.5  # Temperature profiles are naturally more peaked


def _li_to_alpha(li: float, alpha_base: float) -> float:
    """Convert internal inductance to profile exponent."""
    return alpha_base * (li / _LI_REF) ** 2


def get_radial_data(
    n_e: float,
    Te_core: float,
    li: float,
    a: float = 2.0,
    points: int = 50,
) -> dict[str, np.ndarray]:
    """Generate radial profiles for density and temperature.

    Args:
        n_e: Line-averaged electron density (1e20 m^-3).
        Te_core: Core electron temperature (keV).
        li: Internal inductance (controls peaking).
        a: Minor radius (m).
        points: Number of radial points.

    Returns:
        Dict with keys: "r", "n_e_profile", "Te_profile", "alpha_n", "alpha_T"
    """
    r = np.linspace(0, a, points)
    rho = r / a  # normalized radius 0..1

    alpha_n = _li_to_alpha(li, _ALPHA_BASE_DENSITY)
    alpha_t = _li_to_alpha(li, _ALPHA_BASE_TEMPERATURE)

    # n_e_core derived from line-averaged: n_e_avg ≈ n_e_core / (alpha+1)
    # so n_e_core = n_e * (alpha_n + 1)
    n_e_core = n_e * (alpha_n + 1)

    n_profile = n_e_core * (1 - rho**2) ** alpha_n
    t_profile = Te_core * (1 - rho**2) ** alpha_t

    return {
        "r": r,
        "n_e_profile": n_profile,
        "Te_profile": t_profile,
        "alpha_n": alpha_n,
        "alpha_t": alpha_t,
    }
