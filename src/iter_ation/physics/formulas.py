import math


def greenwald_density(Ip: float, a: float) -> float:
    """Greenwald density limit: n_G [1e20 m^-3] = Ip [MA] / (pi * a^2 [m^2])."""
    return Ip / (math.pi * a**2)


def greenwald_fraction(n_e: float, Ip: float, a: float) -> float:
    """Greenwald fraction fGW = n_e / n_G."""
    return n_e / greenwald_density(Ip, a)


def q95(a: float, kappa: float, B_T: float, R_0: float, Ip: float) -> float:
    """Safety factor at 95% flux surface (simplified cylindrical)."""
    return (5.0 * a**2 * kappa * B_T) / (R_0 * Ip)
