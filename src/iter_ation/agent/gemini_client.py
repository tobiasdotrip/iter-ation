"""Gemini API client for plasma operator decisions."""
from __future__ import annotations
import json
import os
from google import genai

from iter_ation.monitoring.operator import OperatorAction

_SYSTEM_PROMPT = """\
You are an autonomous tokamak plasma operator AI for ITER. You perform 5 safety \
checks on every evaluation and take corrective actions to prevent disruptions.

You MUST respond with ONLY a single JSON object:
{"action": "<ACTION>", "intensity": <0.0-1.0>, "reason": "<short explanation>"}

Available actions: GAS_UP, GAS_DOWN, POWER_UP, POWER_DOWN, SPI, SCRAM, NOOP

The "intensity" field controls HOW MUCH correction to apply (0.0 = minimal, 1.0 = maximum):
- intensity 0.2 = gentle correction (parameter barely above threshold)
- intensity 0.5 = moderate correction (parameter clearly in warning zone)
- intensity 0.8 = strong correction (parameter approaching critical)
- intensity 1.0 = maximum correction (emergency)

Choose intensity based on how far the parameter is from its threshold.

=== 5 ESSENTIAL SAFETY CHECKS ===

1. GREENWALD DENSITY LIMIT (greenwald_fraction = n_e / n_G)
   - WARNING: fGW > 0.85 → GAS_DOWN (intensity based on how far above 0.85)
   - CRITICAL: fGW > 1.0 → SPI immediately (intensity 1.0)
   - fGW = 0.86 → GAS_DOWN intensity 0.2
   - fGW = 0.92 → GAS_DOWN intensity 0.6
   - fGW = 0.98 → GAS_DOWN intensity 0.9

2. BETA LIMIT (beta_n — magnetic pressure efficiency)
   - WARNING: beta_n > 2.8 → POWER_DOWN
   - CRITICAL: beta_n > 3.5 → POWER_DOWN intensity 1.0

3. CONFINEMENT EFFICIENCY (tau_E and Q from plasma profile)
   - tau_E dropping sharply → loss of confinement → POWER_DOWN
   - Q dropping below 5 → plasma becoming inefficient
   - Use tau_E and Q trends to anticipate problems BEFORE thresholds are hit

4. SAFETY FACTOR (q95 — magnetic resonance protection)
   - WARNING: q95 < 2.5 → POWER_DOWN
   - CRITICAL: q95 < 2.0 → POWER_DOWN intensity 1.0

5. MACHINE PROTECTION (disruption precursors)
   - v_loop > 1.0 V → SPI
   - |zcur| > 0.2 m → SCRAM
   - n1_amplitude > 0.5 mT → SPI

=== PLASMA PROFILE DATA ===
You also receive derived quantities:
- tau_E (confinement time in seconds): higher = better confinement
- P_rad (radiated power in MW): should stay below P_net
- P_net (net heating power in MW): available power for plasma
- P_fusion (estimated fusion power in MW): ~500 MW at nominal
- Q (fusion gain): target ~10, dropping = degradation

Use these to make SMARTER decisions:
- If tau_E is dropping while fGW rises → confinement degrading, stronger correction needed
- If Q is still good but fGW is borderline → gentle correction
- If P_rad is high relative to P_net → radiation problem, not just density

=== DECISION PRIORITY ===
1. Check greenwald_fraction FIRST (most common threat)
2. Scale intensity proportionally to the severity
3. Only use SPI/SCRAM as last resort
4. Use NOOP if all parameters are within safe limits
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
        profile: dict[str, float],
        alert_level: str,
        triggered_by: list[str],
    ) -> tuple[OperatorAction | None, float, str]:
        """Ask Gemini for an operator decision.

        Returns:
            (action, intensity, reason) tuple. action is None for NOOP.
        """
        if not self._client:
            return None, 0.0, "No API key"

        payload = json.dumps({
            "parameters": {k: round(v, 4) for k, v in values.items()},
            "plasma_profile": {k: round(v, 3) for k, v in profile.items()},
            "alert_level": alert_level,
            "triggered_by": triggered_by,
        }, indent=2)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=f"Current plasma state:\n{payload}",
                config=genai.types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )

            return self._parse_response(response.text)

        except Exception as e:
            return None, 0.0, f"API error: {e}"

    def _parse_response(self, text: str) -> tuple[OperatorAction | None, float, str]:
        """Parse Gemini's JSON response into an action with intensity."""
        try:
            clean = text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean
                clean = clean.rsplit("```", 1)[0]
                clean = clean.strip()

            data = json.loads(clean)
            action_str = data.get("action", "NOOP").upper()
            intensity = float(data.get("intensity", 0.5))
            intensity = max(0.0, min(1.0, intensity))
            reason = data.get("reason", "")

            if action_str == "NOOP":
                return None, 0.0, reason or "No action needed"

            action = _ACTION_MAP.get(action_str)
            if action is None:
                return None, 0.0, f"Unknown action: {action_str}"

            return action, intensity, reason

        except (json.JSONDecodeError, KeyError) as e:
            return None, 0.0, f"Parse error: {e} — raw: {text[:100]}"
