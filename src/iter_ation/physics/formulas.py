import math


def greenwald_density(Ip: float, a: float) -> float:
    """Greenwald density limit: n_G [1e20 m^-3] = Ip [MA] / (pi * a^2 [m^2])."""
    return Ip / (math.pi * a**2)


def greenwald_fraction(n_e: float, Ip: float, a: float) -> float:
    """Greenwald fraction fGW = n_e / n_G."""
    return n_e / greenwald_density(Ip, a)


def q95(
    Ip: float,
    li: float = 0.85,
    Ip_ref: float = 15.0,
    li_ref: float = 0.85,
    q95_ref: float = 3.1,
) -> float:
    """Safety factor at 95% flux surface, scaled from ITER reference.

    q95 = q95_ref * (Ip_ref / Ip) * (li_ref / li)

    The simplified cylindrical formula (5a^2*kappa*B_T)/(R_0*Ip) gives ~1.94
    for ITER due to missing shape corrections (triangularity, etc.).
    Instead we calibrate on ITER's known q95 ~ 3.1 at Ip=15 MA, li=0.85.

    Scaling: q95 ∝ 1/Ip (more current = lower q) and q95 ∝ 1/li
    (peaked current profile = lower edge q, approaching q=2 resonance).
    """
    return q95_ref * (Ip_ref / Ip) * (li_ref / li)
