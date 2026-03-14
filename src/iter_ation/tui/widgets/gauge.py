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


class Gauge(Widget):
    """Horizontal gauge bar for a single plasma parameter."""

    DEFAULT_CSS = """
    Gauge {
        height: 1;
        width: 1fr;
        padding: 0 1;
    }
    """

    value: reactive[float] = reactive(0.0)
    alert_level: reactive[AlertLevel] = reactive(AlertLevel.NOMINAL)

    def __init__(
        self, label: str, unit: str = "",
        min_val: float = 0.0, max_val: float = 1.0, **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._unit = unit
        self._min_val = min_val
        self._max_val = max_val

    def render(self) -> str:
        # Reserve space for label (6) + value (8) + spacing (4)
        bar_width = max(self.size.width - 18, 3)
        fill_ratio = (self.value - self._min_val) / max(self._max_val - self._min_val, 1e-9)
        fill_ratio = max(0.0, min(1.0, fill_ratio))
        filled = int(bar_width * fill_ratio)
        empty = bar_width - filled

        color = _LEVEL_COLORS.get(self.alert_level, COLORS["nominal"])
        bar = f"[{color}]{'█' * filled}[/][dim]{'░' * empty}[/]"
        return f"{self._label:<6}{bar} [{color}]{self.value:>7.3f}[/]"

    def update_value(self, value: float, level: AlertLevel) -> None:
        self.value = value
        self.alert_level = level
