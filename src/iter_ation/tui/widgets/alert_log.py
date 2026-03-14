from textual.widgets import RichLog
from iter_ation.monitoring.alerts import AlertEntry
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.tui.theme import COLORS

_LEVEL_ICONS = {
    AlertLevel.NOMINAL: "[green]●[/]",
    AlertLevel.WARNING: "[yellow]⚠[/]",
    AlertLevel.DANGER: "[red]✖[/]",
    AlertLevel.DISRUPTION: "[bold red blink]◉ DISRUPTION[/]",
}


class AlertLogWidget(RichLog):
    DEFAULT_CSS = """
    AlertLogWidget {
        height: 1fr;
        border: solid $surface;
    }
    """

    def add_alert(self, entry: AlertEntry) -> None:
        icon = _LEVEL_ICONS.get(entry.level, "")
        self.write(f"{icon} [{COLORS['text_dim']}]t={entry.sim_time:.3f}s[/] {entry.message}")
