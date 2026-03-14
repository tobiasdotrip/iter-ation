from __future__ import annotations
from dataclasses import dataclass
from iter_ation.monitoring.thresholds import AlertLevel


@dataclass(frozen=True)
class AlertEntry:
    sim_time: float
    level: AlertLevel
    triggered_by: dict[str, AlertLevel]
    message: str


def _format_message(level: AlertLevel, triggered_by: dict[str, AlertLevel]) -> str:
    if level == AlertLevel.NOMINAL:
        return "All parameters nominal"
    if level == AlertLevel.DISRUPTION:
        return "DISRUPTION CASCADE IN PROGRESS"
    params = ", ".join(f"{name} [{lvl.name}]" for name, lvl in triggered_by.items())
    return f"{level.name}: {params}"


class AlertLog:
    def __init__(self, max_entries: int = 100) -> None:
        self.entries: list[AlertEntry] = []
        self._max_entries = max_entries
        self._last_level: AlertLevel = AlertLevel.NOMINAL

    def update(
        self, sim_time: float, overall_level: AlertLevel,
        param_levels: dict[str, AlertLevel],
    ) -> AlertEntry | None:
        if overall_level == self._last_level:
            return None

        triggered = {k: v for k, v in param_levels.items() if v > AlertLevel.NOMINAL}
        entry = AlertEntry(
            sim_time=sim_time, level=overall_level,
            triggered_by=triggered, message=_format_message(overall_level, triggered),
        )
        self.entries.append(entry)
        self._last_level = overall_level

        if len(self.entries) > self._max_entries:
            self.entries = self.entries[-self._max_entries:]
        return entry

    def force_disruption(self, sim_time: float) -> AlertEntry:
        entry = AlertEntry(
            sim_time=sim_time, level=AlertLevel.DISRUPTION,
            triggered_by={}, message="DISRUPTION CASCADE IN PROGRESS",
        )
        self.entries.append(entry)
        self._last_level = AlertLevel.DISRUPTION
        return entry
