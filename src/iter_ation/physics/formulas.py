import math


def greenwald_density(Ip: float, a: float) -> float:
    """Greenwald density limit: n_G [1e20 m^-3] = Ip [MA] / (pi * a^2 [m^2])."""
    return Ip / (math.pi * a**2)


def greenwald_fraction(n_e: float, Ip: float, a: float) -> float:
    """Greenwald fraction fGW = n_e / n_G."""
    return n_e / greenwald_density(Ip, a)


def q95(
    a: float, kappa: float, B_T: float, R_0: float, Ip: float,
    li: float = 0.85, li_ref: float = 0.85,
) -> float:
    """Safety factor at 95% flux surface, corrected by internal inductance.

    q95 = (5 * a^2 * kappa * B_T) / (R_0 * Ip) * (li_ref / li)

    When li increases above li_ref (current profile peaks), q95 drops —
    simulating approach toward q=2 resonance surface even at constant Ip.
    """
    q_cyl = (5.0 * a**2 * kappa * B_T) / (R_0 * Ip)
    return q_cyl * (li_ref / li)
