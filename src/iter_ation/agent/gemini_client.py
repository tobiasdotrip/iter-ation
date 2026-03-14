"""Gemini API client for plasma operator decisions."""
from __future__ import annotations
import json
import os
from google import genai

from iter_ation.monitoring.operator import OperatorAction

_SYSTEM_PROMPT = """\
You are a tokamak plasma operator AI. You monitor 13 plasma parameters \
and take actions to prevent disruptions. Respond with ONLY a single JSON object:
{"action": "<ACTION>", "reason": "<short explanation>"}

Available actions: GAS_UP, GAS_DOWN, POWER_UP, POWER_DOWN, SPI, SCRAM, NOOP

Rules:
- greenwald_fraction > 0.85: density too high, reduce it (GAS_DOWN)
- greenwald_fraction > 1.0: emergency, use SPI or SCRAM
- q95 < 2.5: safety factor too low, reduce current (POWER_DOWN)
- radiated_fraction > 0.7: too much radiation, reduce density (GAS_DOWN)
- n1_amplitude > 0.5: magnetic instability forming, consider SPI
- Only use SPI/SCRAM as last resort when other actions have failed
- Use NOOP if all parameters are acceptable
"""

_ACTION_MAP: dict[str, OperatorAction] = {
    "GAS_UP": OperatorAction.GAS_UP,
    "GAS_DOWN": OperatorAction.GAS_DOWN,
    "POWER_UP": OperatorAction.POWER_UP,
    "POWER_DOWN": OperatorAction.POWER_DOWN,
    "SPI": OperatorAction.SPI,
    "SCRAM": OperatorAction.SCRAM,
}


class GeminiClient:
    """Wrapper around Gemini API for plasma operator decisions."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-3.1-flash-lite-preview") -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model = model
        self._client: genai.Client | None = None

        if self._api_key:
            self._client = genai.Client(api_key=self._api_key)

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def decide(
        self,
        values: dict[str, float],
        alert_level: str,
        triggered_by: list[str],
    ) -> tuple[OperatorAction | None, str]:
        """Ask Gemini for an operator decision.

        Returns:
            (action, reason) tuple. action is None for NOOP.
        """
        if not self._client:
            return None, "No API key"

        payload = json.dumps({
            "parameters": {k: round(v, 4) for k, v in values.items()},
            "alert_level": alert_level,
            "triggered_by": triggered_by,
        })

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=f"Current plasma state:\n{payload}",
                config=genai.types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_output_tokens=150,
                ),
            )

            return self._parse_response(response.text)

        except Exception as e:
            return None, f"API error: {e}"

    def _parse_response(self, text: str) -> tuple[OperatorAction | None, str]:
        """Parse Gemini's JSON response into an action."""
        try:
            # Strip markdown code fences if present
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean
                clean = clean.rsplit("```", 1)[0]
                clean = clean.strip()

            data = json.loads(clean)
            action_str = data.get("action", "NOOP").upper()
            reason = data.get("reason", "")

            if action_str == "NOOP":
                return None, reason or "No action needed"

            action = _ACTION_MAP.get(action_str)
            if action is None:
                return None, f"Unknown action: {action_str}"

            return action, reason

        except (json.JSONDecodeError, KeyError) as e:
            return None, f"Parse error: {e} — raw: {text[:100]}"
