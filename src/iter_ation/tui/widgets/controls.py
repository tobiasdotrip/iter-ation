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
    ai_mode: reactive[bool] = reactive(False)
    paused: reactive[bool] = reactive(False)

    def render(self) -> str:
        if self.ai_mode:
            mode = "[bold magenta]AI[/]"
        elif self.interactive_mode:
            mode = "[bold cyan]INTER[/]"
        else:
            mode = "[bold green]OBS[/]"

        pause_str = " [bold yellow]PAUSED[/]" if self.paused else ""

        line1 = (
            "[dim]\\[Up/Down Gas] [+/- Power] [S SPI] [X SCRAM][/]"
            if self.interactive_mode
            else "[dim]Controls disabled -- switch to Interactive mode[/]"
        )
        line2 = (
            f"[dim]\\[O] Obs  \\[I] Inter  \\[A] AI  "
            f"\\[P] Pause  \\[Q] Quit[/]  "
            f"Mode: {mode}{pause_str}"
        )
        return f"{line1}\n{line2}"
