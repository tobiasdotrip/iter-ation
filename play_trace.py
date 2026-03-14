import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, RichLog, Label
from src.ui.app import StatPanel
from src.ui.components import TimeSeriesPlot

class LiseuseApp(App):
    """ITER-ATION - Liseuse de Scénario (Offline)"""
    
    CSS = """
    Grid {
        grid-size: 2 2;
        grid-columns: 2fr 1fr;
        grid-rows: 2fr 1fr;
    }
    #plot {
        border: solid green;
        height: 100%;
        row-span: 2;
    }
    #stats {
        border: solid yellow;
        height: 100%;
        padding: 1;
    }
    #ai_log {
        border: solid cyan;
        height: 100%;
    }
    #controls {
        dock: bottom;
        height: 3;
        align: center middle;
    }
    Button {
        margin-right: 2;
    }
    #stats_title {
        text-style: bold;
        margin-bottom: 1;
    }
    #lbl_progress {
        padding: 1 2;
        text-style: bold;
        color: white;
    }
    """

    def __init__(self, trace_file="scenario_trace.json"):
        super().__init__()
        self.trace_file = trace_file
        try:
            with open(trace_file, "r") as f:
                self.history = json.load(f)
        except Exception as e:
            self.history = [{"state": {"greenwald_fraction":0,"q95":0,"beta_n":0,"tau_E (s)":0, "n_e (10^20 m^-3)":0}}]
            print(f"Erreur chargement trace: {e}")
            
        self.tick_index = 0
        self.playing = False

    def compose(self) -> ComposeResult:
        with Header():
            yield Label("ITER-ATION — Liseuse (Replay Hors-Ligne)")
        
        with Grid():
            yield TimeSeriesPlot(title="Evolution Paramètre", id="plot")
            yield StatPanel(id="stats")
            yield RichLog(id="ai_log", markup=True)

        with Horizontal(id="controls"):
            yield Button("Play / Pause", id="btn_play", variant="success")
            yield Button("Reset", id="btn_reset", variant="warning")
            yield Label(f"Tick: 0/{len(self.history)}", id="lbl_progress")
            
        yield Footer()

    def on_mount(self) -> None:
        self.log_ai("[bold green]Mode LISEUSE démarré[/bold green]")
        self.log_ai(f"Fichier chargé : {self.trace_file}")
        self.log_ai("Cliquez sur [Play / Pause] pour lancer la lecture.")
        self.update_ui()
        self.set_interval(0.2, self.play_tick)

    def play_tick(self):
        if self.playing and self.tick_index < len(self.history) - 1:
            self.tick_index += 1
            self.update_ui()
        elif self.playing and self.tick_index >= len(self.history) - 1:
            self.playing = False
            self.log_ai("[dim]▶ Fin de la trace.[/dim]")

    def update_ui(self):
        record = self.history[self.tick_index]
        state_dict = record.get("state", {})
        
        lbl_progress = self.query_one("#lbl_progress", Label)
        lbl_progress.update(f"Tick: {self.tick_index}/{len(self.history)}")

        stats = self.query_one("#stats", StatPanel)
        stats.fgw = f"{state_dict.get('greenwald_fraction', 0):.2f}"
        stats.q95 = f"{state_dict.get('q95', 0):.2f}"
        stats.beta_n = f"{state_dict.get('beta_n', 0):.2f}"
        stats.tau_e = f"{state_dict.get('tau_E (s)', 0):.2f}"

        mode = record.get("mode", 0)
        plot = self.query_one("#plot", TimeSeriesPlot)
        if mode == 1:
            plot.plot_title = "Scénario 1: Greenwald Fraction (fGW)"
            plot.update_data(state_dict.get('greenwald_fraction', 0))
        elif mode == 2:
            plot.plot_title = "Scénario 2: Normalized Beta (beta_n)"
            plot.update_data(state_dict.get('beta_n', 0))
        elif mode == 3:
            plot.plot_title = "Scénario 3: Safety Factor (q95)"
            plot.update_data(state_dict.get('q95', 0))
        elif mode == 4:
            plot.plot_title = "Scénario 4: Energy Confinement (tau_E)"
            plot.update_data(state_dict.get('tau_E (s)', 0))
        else:
            plot.plot_title = "Mode Stable: Densité (n_e)"
            plot.update_data(state_dict.get('n_e (10^20 m^-3)', 0))

        ai_action = record.get("ai_action")
        ai_log_msg = record.get("ai_log")
        
        if ai_action:
            self.log_ai(f"\n[bold red]> L'IA a pris une action : {ai_action}[/bold red]")
        if ai_log_msg:
            self.log_ai(f"[bold green]> {ai_log_msg}[/bold green]")

    def log_ai(self, msg: str):
        log = self.query_one("#ai_log", RichLog)
        log.write(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_play":
            self.playing = not self.playing
            self.log_ai("[dim]▶ Lecture en cours[/dim]" if self.playing else "[dim]⏸ Pause[/dim]")
        elif event.button.id == "btn_reset":
            self.playing = False
            self.tick_index = 0
            # Reset plot data
            plot = self.query_one("#plot", TimeSeriesPlot)
            plot.data = []
            plot.refresh()
            self.update_ui()
            self.log_ai("\n[dim]--- Retour au début ---[/]")

if __name__ == "__main__":
    app = LiseuseApp()
    app.run()
