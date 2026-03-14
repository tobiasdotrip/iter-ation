from dataclasses import dataclass


@dataclass(frozen=True)
class MachineConstants:
    """Tokamak machine constants."""
    R_0: float    # Major radius (m)
    a: float      # Minor radius (m)
    B_T: float    # Toroidal field (T)
    kappa: float  # Elongation
    V_plasma: float  # Plasma volume (m³)


ITER = MachineConstants(
    R_0=6.2,
    a=2.0,
    B_T=5.3,
    kappa=1.7,
    V_plasma=830.0,
)
