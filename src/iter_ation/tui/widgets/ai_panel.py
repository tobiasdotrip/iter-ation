"""AI Operator decision panel."""
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

    def on_mount(self) -> None:
        self.write(f"[{COLORS['text_dim']}]Idle -- no action required[/]")

    def log_action(self, sim_time: float, action: str, reason: str) -> None:
        self.write(
            f"[{COLORS['accent']}]t={sim_time:.3f}s[/] "
            f"[bold]{action}[/] -- {reason}"
        )
