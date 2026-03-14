"""AI Operator decision panel."""
from rich.text import Text
from textual.widgets import RichLog
from iter_ation.tui.theme import COLORS


class AIPanel(RichLog):
    """Panel showing AI operator decisions and reasoning."""

    DEFAULT_CSS = """
    AIPanel {
        height: 1fr;
        border: solid $surface;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)

    def on_mount(self) -> None:
        self.write("[dim]Idle -- no action required[/]")

    def log_action(self, sim_time: float, action: str, reason: str) -> None:
        self.write(f"[cyan]t={sim_time:.3f}s[/] [bold]{action}[/] -- {reason}")
