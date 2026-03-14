from dataclasses import dataclass
from enum import Enum


class ThresholdDirection(Enum):
    """How to compare value to threshold."""
    ABOVE = "above"          # value > threshold = alert
    BELOW = "below"          # value < threshold = alert
    ABS_ABOVE = "abs_above"  # |value| > threshold = alert
    DROP_PCT = "drop_pct"    # (nominal - value) / nominal > threshold = alert


@dataclass(frozen=True)
class ParameterDef:
    """Definition of a plasma parameter."""
    name: str
    unit: str
    nominal: float
    noise_sigma_pct: float | None  # % of nominal, None for derived params
    noise_sigma_abs: float | None  # Absolute sigma, for params with nominal=0
    risk_threshold: float | None
    risk_direction: ThresholdDirection | None
    critical_threshold: float | None
    critical_direction: ThresholdDirection | None

    @property
    def effective_sigma(self) -> float:
        """Return the effective noise standard deviation."""
        if self.noise_sigma_abs is not None:
            return self.noise_sigma_abs
        if self.noise_sigma_pct is not None:
            return abs(self.nominal) * self.noise_sigma_pct / 100.0
        return 0.0


PARAMETERS: list[ParameterDef] = [
    ParameterDef(
        name="greenwald_fraction",
        unit="",
        nominal=0.75,
        noise_sigma_pct=None,
        noise_sigma_abs=None,
        risk_threshold=0.85,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="n_e",
        unit="1e20 m\u207b\u00b3",
        nominal=0.9,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=None,
        critical_direction=None,
    ),
    ParameterDef(
        name="Ip",
        unit="MA",
        nominal=15.0,
        noise_sigma_pct=0.1,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=0.20,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="q95",
        unit="",
        nominal=3.1,
        noise_sigma_pct=None,
        noise_sigma_abs=None,
        risk_threshold=2.5,
        risk_direction=ThresholdDirection.BELOW,
        critical_threshold=2.0,
        critical_direction=ThresholdDirection.BELOW,
    ),
    ParameterDef(
        name="Te_core",
        unit="keV",
        nominal=20.0,
        noise_sigma_pct=1.0,
        noise_sigma_abs=None,
        risk_threshold=0.30,
        risk_direction=ThresholdDirection.DROP_PCT,
        critical_threshold=0.50,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="Wmhd",
        unit="MJ",
        nominal=350.0,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=0.20,
        risk_direction=ThresholdDirection.DROP_PCT,
        # Spec: "chute > 40% en < 5 ms" — simplified to static drop % in v1
        critical_threshold=0.40,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="radiated_fraction",
        unit="",
        nominal=0.5,
        noise_sigma_pct=1.0,
        noise_sigma_abs=None,
        risk_threshold=0.7,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=0.9,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="li",
        unit="",
        nominal=0.85,
        noise_sigma_pct=0.3,
        noise_sigma_abs=None,
        risk_threshold=1.2,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.4,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="n1_amplitude",
        unit="mT",
        nominal=0.05,
        noise_sigma_pct=2.0,
        noise_sigma_abs=None,
        risk_threshold=0.5,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="v_loop",
        unit="V",
        nominal=0.2,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="beta_n",
        unit="",
        nominal=1.8,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=2.8,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=3.5,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="zcur",
        unit="m",
        nominal=0.0,
        noise_sigma_pct=None,
        noise_sigma_abs=0.002,
        risk_threshold=0.1,
        risk_direction=ThresholdDirection.ABS_ABOVE,
        critical_threshold=0.2,
        critical_direction=ThresholdDirection.ABS_ABOVE,
    ),
    ParameterDef(
        name="p_input",
        unit="MW",
        nominal=50.0,
        noise_sigma_pct=0.1,
        noise_sigma_abs=None,
        risk_threshold=0.30,
        risk_direction=ThresholdDirection.DROP_PCT,
        critical_threshold=0.50,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
]

_PARAM_INDEX: dict[str, ParameterDef] = {p.name: p for p in PARAMETERS}


def get_parameter(name: str) -> ParameterDef:
    """Get a parameter definition by name. Raises KeyError if not found."""
    return _PARAM_INDEX[name]
