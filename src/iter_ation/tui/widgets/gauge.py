from textual.widget import Widget
from textual.reactive import reactive
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.tui.theme import COLORS


class Gauge(Widget):
    """Horizontal gauge bar for a single plasma parameter."""

    DEFAULT_CSS = """
    Gauge {
        height: 1;
        width: 1fr;
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
        width = max(self.size.width - 22, 5)
        fill_ratio = (self.value - self._min_val) / max(self._max_val - self._min_val, 1e-9)
        fill_ratio = max(0.0, min(1.0, fill_ratio))
        filled = int(width * fill_ratio)
        empty = width - filled

        color = COLORS.get(self.alert_level.name.lower(), COLORS["nominal"])
        bar = f"[{color}]{'█' * filled}[/]{'░' * empty}"
        unit_str = f" {self._unit}" if self._unit else ""
        return f" {self._label:<8} {bar} {self.value:>8.3f}{unit_str}"

    def update_value(self, value: float, level: AlertLevel) -> None:
        self.value = value
        self.alert_level = level
