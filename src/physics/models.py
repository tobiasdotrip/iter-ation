"""
Physics Layer: Formules exactes du document de référence "Gardien du Réacteur".

Scénario 1 (Greenwald) : fGW = n_e / (Ip / (π × a²))
Scénario 2 (Beta)       : β   = p / (B² / 2μ₀),  p dérivée de Wmhd
Scénario 3 (q95)        : q   ≈ R·BT / (a·BP),   approximation calibrée via li
Scénario 4 (tau_E)      : dW/dt = Pin - W/τE  →  τE = W / Pin (état quasi-stationnaire)
"""
import math

# Constante physique
MU_0 = 4 * math.pi * 1e-7  # Perméabilité du vide (H/m)


class ITER:
    """Constantes machine ITER (fixes, utilisées dans les formules)."""
    R_0      = 6.2    # Rayon majeur (m)
    a        = 2.0    # Rayon mineur (m)
    B_T      = 5.3    # Champ toroïdal (T)
    kappa    = 1.7    # Élongation
    V_plasma = 830.0  # Volume plasma (m³)


# ---------------------------------------------------------------------------
# Scénario 1 : Limite de Greenwald
# ---------------------------------------------------------------------------
def calc_greenwald_fraction(n_e: float, Ip: float) -> float:
    """
    fGW = n_e / n_G   avec   n_G = Ip / (π × a²)
    n_e en 10²⁰ m⁻³, Ip en MA → fGW sans dimension.
    Seuil critique : fGW > 0.8
    """
    if Ip <= 0:
        return 0.0
    n_G = Ip / (math.pi * ITER.a ** 2)
    return n_e / n_G


# ---------------------------------------------------------------------------
# Scénario 2 : Efficacité magnétique (Beta normalisé)
# ---------------------------------------------------------------------------
def calc_pressure_from_energy(Wmhd: float) -> float:
    """
    Pression interne dérivée de l'énergie stockée.
    p = (2/3) × Wmhd / V_plasma
    Wmhd en MJ → p en Pa.
    """
    return (2.0 / 3.0) * (Wmhd * 1e6) / ITER.V_plasma


def calc_beta(Wmhd: float) -> float:
    """
    β = p / (B_T² / 2μ₀)
    Document : "rapport de force entre l'intérieur et l'extérieur".
    Retourne β en % pour lisibilité.
    """
    p = calc_pressure_from_energy(Wmhd)             # Pa
    B2_over_2mu0 = ITER.B_T ** 2 / (2 * MU_0)      # Pa
    return (p / B2_over_2mu0) * 100.0               # en %


def calc_beta_n(Wmhd: float, Ip: float = 15.0) -> float:
    """
    Beta normalisé : beta_n = beta(%) / (Ip / (a × B_T))
    Valeur nominale : ~1.8  (Wmhd=350 MJ, Ip=15 MA)
    Seuil critique  : > 2.8
    """
    beta_pct = calc_beta(Wmhd)
    ip_factor = Ip / (ITER.a * ITER.B_T)   # MA / (m·T)
    if ip_factor <= 0:
        return 0.0
    return beta_pct / ip_factor


# ---------------------------------------------------------------------------
# Scénario 3 : Facteur de sécurité (déchirure)
# ---------------------------------------------------------------------------
def calc_q95(li: float) -> float:
    """
    Document : q ≈ R·BT / (a·BP)
    Approximation calibrée ITER (BP est piloté par li) :
      q95 = 3.1 × (0.85 / li)
    Plus li ↑ (profil de courant piqué), plus BP ↑ → q95 ↓.
    Seuil critique : q95 < 2.0
    """
    if li <= 0:
        return 0.0
    return 3.1 * (0.85 / li)


# ---------------------------------------------------------------------------
# Scénario 4 : Temps de confinement de l'énergie (fuite thermique)
# ---------------------------------------------------------------------------
def calc_tau_E(Wmhd: float, p_input: float) -> float:
    """
    Balance thermique du document : dW/dt = Pin - W/τE
    En régime quasi-stationnaire (dW/dt ≈ 0) : τE = W / Pin
    Wmhd en MJ, p_input en MW → τE en secondes.
    Seuil critique : τE < 2.0 s
    """
    if p_input <= 0:
        return 0.0
    return Wmhd / p_input
