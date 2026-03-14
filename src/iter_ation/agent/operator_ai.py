"""AI operator logic: when to call Gemini and how to apply decisions."""
from __future__ import annotations
from iter_ation.agent.gemini_client import GeminiClient
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.monitoring.operator import OperatorAction


class OperatorAI:
    """Autonomous plasma operator powered by Gemini.

    Only consults Gemini when alert level >= WARNING and cooldown has elapsed.
    """

    def __init__(self, api_key: str | None = None, cooldown_ms: float = 500.0) -> None:
        self._client = GeminiClient(api_key=api_key)
        self._cooldown_ms = cooldown_ms
        self._last_call_time: float = -999.0  # sim time of last API call

    @property
    def is_available(self) -> bool:
        return self._client.is_available

    def evaluate(
        self,
        values: dict[str, float],
        alert_level: AlertLevel,
        param_levels: dict[str, AlertLevel],
        sim_time: float,
    ) -> tuple[OperatorAction | None, str]:
        """Evaluate whether to act, and if so, what action to take.

        Returns:
            (action, reason). action is None if no action taken (NOOP, cooldown, or nominal).
        """
        # Only act on WARNING or DANGER
        if alert_level < AlertLevel.WARNING:
            return None, ""

        # Cooldown check (in simulated time)
        elapsed_ms = (sim_time - self._last_call_time) * 1000
        if elapsed_ms < self._cooldown_ms:
            return None, ""

        # Identify which parameters triggered the alert
        triggered = [
            name for name, level in param_levels.items()
            if level >= AlertLevel.WARNING
        ]

        # Call Gemini
        self._last_call_time = sim_time
        action, reason = self._client.decide(
            values=values,
            alert_level=alert_level.name,
            triggered_by=triggered,
        )

        return action, reason
