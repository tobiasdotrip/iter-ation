from textual.widgets import Static
from textual.reactive import reactive


class ControlsBar(Static):
    DEFAULT_CSS = """
    ControlsBar {
        dock: bottom;
        height: 2;
        background: $surface;
        padding: 0 1;
    }
    """

    interactive_mode: reactive[bool] = reactive(False)
    paused: reactive[bool] = reactive(False)

    def render(self) -> str:
        mode = "INTER" if self.interactive_mode else "OBS"
        pause_str = " ▶ PAUSED" if self.paused else ""

        line1 = (
            "[dim]\\[↑↓ Gas] [+- Power] [S SPI] [X SCRAM][/]"
            if self.interactive_mode
            else "[dim]Controls disabled in OBS mode[/]"
        )
        line2 = (
            f"[dim]\\[O] Observation  \\[I] Interactive  "
            f"\\[P] Pause  \\[Q] Quit[/]  "
            f"Mode: [bold]{mode}[/]{pause_str}"
        )
        return f"{line1}\n{line2}"
