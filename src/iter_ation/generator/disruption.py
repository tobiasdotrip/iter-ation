from __future__ import annotations
import math
from enum import Enum


class DisruptionPhase(Enum):
    NONE = "none"
    PRECURSORS = "precursors"
    THERMAL_QUENCH = "thermal_quench"
    CURRENT_QUENCH = "current_quench"
    RECOVERY = "recovery"


def compute_risk_score(
    greenwald_fraction: float,
    radiated_fraction: float,
    n1_amplitude: float,
    q95: float,
) -> float:
    """Compute disruption risk score in [0, 1]. Dominated by Greenwald fraction."""
    score = 0.0

    if greenwald_fraction > 0.8:
        score += min((greenwald_fraction - 0.8) / 0.2, 1.0) * 0.7

    if radiated_fraction > 0.6:
        score += min((radiated_fraction - 0.6) / 0.3, 1.0) * 0.15

    if n1_amplitude > 0.3:
        score += min((n1_amplitude - 0.3) / 0.7, 1.0) * 0.1

    if q95 < 2.5:
        score += min((2.5 - q95) / 0.5, 1.0) * 0.05

    return min(score, 1.0)


class DisruptionCascade:
    """Temporal evolution of a disruption once triggered."""

    def __init__(self) -> None:
        self.phase = DisruptionPhase.NONE
        self._elapsed: float = 0.0
        self._phase_duration: float = 0.0
        self._precursor_duration: float = 0.3
        self._tq_duration: float = 0.002
        self._cq_duration: float = 0.1
        self._recovery_duration: float = 0.5

    @property
    def is_active(self) -> bool:
        return self.phase != DisruptionPhase.NONE

    def trigger(self) -> None:
        if self.is_active:
            return
        self.phase = DisruptionPhase.PRECURSORS
        self._elapsed = 0.0
        self._phase_duration = 0.0

    def tick(self, dt: float) -> None:
        if not self.is_active:
            return
        self._elapsed += dt
        self._phase_duration += dt
        self._advance_phase()

    def _advance_phase(self) -> None:
        if self.phase == DisruptionPhase.PRECURSORS:
            if self._phase_duration >= self._precursor_duration:
                self.phase = DisruptionPhase.THERMAL_QUENCH
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.THERMAL_QUENCH:
            if self._phase_duration >= self._tq_duration:
                self.phase = DisruptionPhase.CURRENT_QUENCH
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.CURRENT_QUENCH:
            if self._phase_duration >= self._cq_duration:
                self.phase = DisruptionPhase.RECOVERY
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.RECOVERY:
            if self._phase_duration >= self._recovery_duration:
                self.phase = DisruptionPhase.NONE
                self._elapsed = 0.0
                self._phase_duration = 0.0

    def get_modifications(self) -> dict[str, float]:
        """Return modifiers for plasma parameters.

        Keys without suffix: multiplicative (value *= mod).
        Keys with '_add' suffix: additive (value += mod).
        Special key '_recovery_progress': float 0->1 for ramping back to nominal.
        """
        mods: dict[str, float] = {}
        if self.phase == DisruptionPhase.PRECURSORS:
            progress = self._phase_duration / self._precursor_duration
            growth = math.exp(10.0 * self._phase_duration)
            mods["n1_amplitude"] = growth
            mods["radiated_fraction_add"] = 0.3 * progress
            mods["li_add"] = 0.2 * progress
            # v_loop spikes in late precursors as plasma resistance rises
            # (the system pushes voltage to maintain Ip before it collapses)
            if progress > 0.7:
                late_progress = (progress - 0.7) / 0.3
                mods["v_loop_add"] = 2.0 * late_progress

        elif self.phase == DisruptionPhase.THERMAL_QUENCH:
            progress = min(self._phase_duration / self._tq_duration, 1.0)
            mods["Te_core"] = max(1.0 - 0.9 * progress, 0.1)
            mods["Wmhd"] = max(1.0 - 0.9 * progress, 0.1)

        elif self.phase == DisruptionPhase.CURRENT_QUENCH:
            progress = min(self._phase_duration / self._cq_duration, 1.0)
            mods["Ip"] = max(1.0 - progress, 0.0)
            mods["zcur_add"] = 0.3 * progress

        elif self.phase == DisruptionPhase.RECOVERY:
            mods["_recovery_progress"] = min(
                self._phase_duration / self._recovery_duration, 1.0
            )

        return mods
