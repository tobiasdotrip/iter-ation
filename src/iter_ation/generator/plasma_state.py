from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PlasmaState:
    """Immutable snapshot of all plasma parameters at a given time."""
    sim_time: float

    greenwald_fraction: float
    n_e: float
    Ip: float
    q95: float
    Te_core: float
    Wmhd: float
    radiated_fraction: float
    li: float
    n1_amplitude: float
    v_loop: float
    beta_n: float
    zcur: float
    p_input: float

    _PARAM_NAMES: ClassVar[tuple[str, ...]] = (
        "greenwald_fraction", "n_e", "Ip", "q95", "Te_core", "Wmhd",
        "radiated_fraction", "li", "n1_amplitude", "v_loop", "beta_n",
        "zcur", "p_input",
    )

    def values(self) -> dict[str, float]:
        """Return parameter name -> value dict (excludes sim_time)."""
        return {name: getattr(self, name) for name in self._PARAM_NAMES}

    @classmethod
    def nominal(cls, sim_time: float = 0.0) -> PlasmaState:
        return cls(
            sim_time=sim_time,
            greenwald_fraction=0.75,
            n_e=0.9,
            Ip=15.0,
            q95=3.1,
            Te_core=20.0,
            Wmhd=350.0,
            radiated_fraction=0.5,
            li=0.85,
            n1_amplitude=0.05,
            v_loop=0.2,
            beta_n=1.8,
            zcur=0.0,
            p_input=50.0,
        )
