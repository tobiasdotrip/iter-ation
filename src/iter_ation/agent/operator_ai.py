"""AI operator logic: when to call Gemini and how to apply decisions."""
from __future__ import annotations
from iter_ation.agent.gemini_client import GeminiClient
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.monitoring.operator import OperatorAction
from iter_ation.physics.constants import ITER
from iter_ation.physics.formulas import greenwald_density


def compute_plasma_profile(values: dict[str, float]) -> dict[str, float]:
    """Compute derived plasma profile quantities from raw parameters."""
    p_input = values.get("p_input", 50.0)
    rad_frac = values.get("radiated_fraction", 0.5)
    wmhd = values.get("Wmhd", 350.0)
    n_e = values.get("n_e", 0.9)
    te = values.get("Te_core", 20.0)
    ip = values.get("Ip", 15.0)

    p_net = p_input * (1.0 - rad_frac)
    tau_e = wmhd / p_net if p_net > 0.1 else 0.0
    n_g = greenwald_density(Ip=ip, a=ITER.a) if ip > 0.01 else 0.0
    p_rad = p_input * rad_frac
    p_fusion = 500.0 * (n_e / 0.9) ** 2 * (te / 20.0) ** 2
    q_gain = p_fusion / p_input if p_input > 0.1 else 0.0

    return {
        "tau_E": tau_e,
        "n_G": n_g,
        "P_rad": p_rad,
        "P_net": p_net,
        "P_fusion": p_fusion,
        "Q": q_gain,
    }


class OperatorAI:
    """Autonomous plasma operator powered by Gemini.

    Only consults Gemini when alert level >= WARNING and cooldown has elapsed.
    Returns action + intensity (0.0-1.0) decided by the model.
    """

    def __init__(self, api_key: str | None = None, cooldown_ms: float = 500.0) -> None:
        self._client = GeminiClient(api_key=api_key)
        self._cooldown_ms = cooldown_ms
        self._last_call_time: float = -999.0

    @property
    def is_available(self) -> bool:
        return self._client.is_available

    def evaluate(
        self,
        values: dict[str, float],
        alert_level: AlertLevel,
        param_levels: dict[str, AlertLevel],
        sim_time: float,
    ) -> tuple[OperatorAction | None, float, str]:
        """Evaluate whether to act, and if so, what action and how intensely.

        Returns:
            (action, intensity, reason). action is None if no action taken.
        """
        if alert_level < AlertLevel.WARNING:
            return None, 0.0, ""

        elapsed_ms = (sim_time - self._last_call_time) * 1000
        if elapsed_ms < self._cooldown_ms:
            return None, 0.0, ""

        triggered = [
            name for name, level in param_levels.items()
            if level >= AlertLevel.WARNING
        ]

        profile = compute_plasma_profile(values)

        self._last_call_time = sim_time
        action, intensity, reason = self._client.decide(
            values=values,
            profile=profile,
            alert_level=alert_level.name,
            triggered_by=triggered,
        )

        return action, intensity, reason
