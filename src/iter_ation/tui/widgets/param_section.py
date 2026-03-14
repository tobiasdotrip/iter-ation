"""Compact parameter section widget with title and color-coded values."""
from textual.widget import Widget
from textual.reactive import reactive
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.tui.theme import COLORS


_LEVEL_COLORS = {
    AlertLevel.NOMINAL: COLORS["nominal"],
    AlertLevel.WARNING: COLORS["warning"],
    AlertLevel.DANGER: COLORS["danger"],
    AlertLevel.DISRUPTION: COLORS["disruption"],
}


class ParamSection(Widget):
    """A titled section displaying parameter values with alert coloring."""

    DEFAULT_CSS = """
    ParamSection {
        height: auto;
        width: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, title: str, params: list[tuple[str, str, str]], **kwargs) -> None:
        """Args:
            title: Section header (e.g. "DENSITY")
            params: List of (param_name, display_label, unit)
        """
        super().__init__(**kwargs)
        self._title = title
        self._params = params
        self._values: dict[str, float] = {p[0]: 0.0 for p in params}
        self._levels: dict[str, AlertLevel] = {p[0]: AlertLevel.NOMINAL for p in params}

    def update_param(self, name: str, value: float, level: AlertLevel) -> None:
        if name in self._values:
            self._values[name] = value
            self._levels[name] = level
            self.refresh()

    def render(self) -> str:
        lines = [f"[bold {COLORS['accent']}]── {self._title} ──[/]"]
        for name, label, unit in self._params:
            val = self._values[name]
            level = self._levels[name]
            color = _LEVEL_COLORS.get(level, COLORS["text"])
            unit_str = f" {unit}" if unit else ""
            lines.append(f"  [{color}]{label:<12} {val:>9.3f}{unit_str}[/]")
        return "\n".join(lines)
