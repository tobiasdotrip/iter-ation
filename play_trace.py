import json
import os
import sys
import argparse
import glob as glob_module

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, RichLog, Label
from src.ui.app import StatPanel
from src.ui.components import TimeSeriesPlot

SCENARIO_NAMES = {
    1: "Scénario 1 — Étouffement (Greenwald)",
    2: "Scénario 2 — Cocotte-minute (Beta)",
    3: "Scénario 3 — Déchirure (q95)",
    4: "Scénario 4 — Fuite de chaleur (tau_E)",
}

class LiseuseApp(App):
    """ITER-ATION - Liseuse de Scénario (Offline) — Multi-scénarios"""

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
    #lbl_scenario {
        padding: 1 2;
        text-style: bold;
        color: yellow;
    }
    """

    def __init__(self, trace_files: list):
        super().__init__()

        # Charge toutes les traces disponibles
        self.all_traces = []
        for path in trace_files:
            try:
                with open(path, "r") as f:
                    self.all_traces.append({"file": path, "history": json.load(f)})
            except Exception as e:
                print(f"Erreur chargement {path}: {e}")

        if not self.all_traces:
            empty = {"state": {"greenwald_fraction": 0, "q95": 0, "beta_n": 0, "tau_E (s)": 0, "n_e (10^20 m^-3)": 0}}
            self.all_traces = [{"file": "vide", "history": [empty]}]

        self.scenario_index = 0
        self.tick_index = 0
        self.playing = False

    @property
    def history(self):
        return self.all_traces[self.scenario_index]["history"]

    @property
    def current_file(self):
        return self.all_traces[self.scenario_index]["file"]

    @property
    def scenario_label(self):
        total = len(self.all_traces)
        idx = self.scenario_index + 1
        name = os.path.basename(self.current_file)
        # Essaie de trouver le numéro de scénario dans le nom de fichier
        for n, title in SCENARIO_NAMES.items():
            if f"_s{n}" in name:
                return f"[{idx}/{total}] {title}"
        return f"[{idx}/{total}] {name}"

    def compose(self) -> ComposeResult:
        with Header():
            yield Label("ITER-ATION — Liseuse Multi-Scénarios")

        with Grid():
            yield TimeSeriesPlot(title="Evolution Paramètre", id="plot")
            yield StatPanel(id="stats")
            yield RichLog(id="ai_log", markup=True)

        with Horizontal(id="controls"):
            yield Button("▶ Play / Pause", id="btn_play", variant="success")
            yield Button("↺ Reset", id="btn_reset", variant="warning")
            yield Button("⏭ Scénario Suivant", id="btn_next", variant="primary")
            yield Label("", id="lbl_scenario")
            yield Label("", id="lbl_progress")

        yield Footer()

    def on_mount(self) -> None:
        self.log_ai("[bold green]Mode LISEUSE multi-scénarios démarré[/bold green]")
        self.log_ai(f"{len(self.all_traces)} scénario(s) chargé(s).")
        self.log_ai("Cliquez sur [▶ Play / Pause] pour lancer.")
        self.refresh_labels()
        self.update_ui()
        self.set_interval(0.2, self.play_tick)

    def play_tick(self):
        if not self.playing:
            return
        if self.tick_index < len(self.history) - 1:
            self.tick_index += 1
            self.update_ui()
        else:
            self.playing = False
            self.log_ai("[bold yellow]▶ Fin du scénario. Cliquez sur [⏭ Scénario Suivant] ou [↺ Reset].[/bold yellow]")

    def refresh_labels(self):
        self.query_one("#lbl_scenario", Label).update(self.scenario_label)
        self.query_one("#lbl_progress", Label).update(f"Tick: {self.tick_index}/{len(self.history)}")

    def update_ui(self):
        record = self.history[self.tick_index]
        state_dict = record.get("state", {})

        self.query_one("#lbl_progress", Label).update(f"Tick: {self.tick_index}/{len(self.history)}")

        stats = self.query_one("#stats", StatPanel)
        stats.fgw    = f"{state_dict.get('greenwald_fraction', 0):.2f}"
        stats.q95    = f"{state_dict.get('q95', 0):.2f}"
        stats.beta_n = f"{state_dict.get('beta_n', 0):.2f}"
        stats.tau_e  = f"{state_dict.get('tau_E (s)', 0):.2f}"

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

    def load_scenario(self, index: int):
        """Charge un scénario par son index et remet à zéro l'affichage."""
        self.playing = False
        self.scenario_index = index
        self.tick_index = 0

        plot = self.query_one("#plot", TimeSeriesPlot)
        plot.data = []
        plot.refresh()

        log = self.query_one("#ai_log", RichLog)
        log.clear()

        self.log_ai(f"\n[bold cyan]━━━ {self.scenario_label} ━━━[/bold cyan]")
        self.log_ai(f"Fichier : {self.current_file}")
        self.log_ai("Cliquez sur [▶ Play / Pause] pour lancer.")
        self.refresh_labels()
        self.update_ui()

    def log_ai(self, msg: str):
        self.query_one("#ai_log", RichLog).write(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_play":
            self.playing = not self.playing
            self.log_ai("[dim]▶ Lecture en cours[/dim]" if self.playing else "[dim]⏸ Pause[/dim]")

        elif event.button.id == "btn_reset":
            self.load_scenario(self.scenario_index)

        elif event.button.id == "btn_next":
            next_index = self.scenario_index + 1
            if next_index < len(self.all_traces):
                self.load_scenario(next_index)
            else:
                self.log_ai("[bold yellow]⚠ Dernier scénario atteint. Retour au premier.[/bold yellow]")
                self.load_scenario(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rejoue les traces de simulation Tokamak.")
    parser.add_argument(
        "--scenario", type=int, choices=[1, 2, 3, 4], default=None,
        help="Commence par ce scénario (1-4)."
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Chemin vers un fichier de trace JSON unique."
    )
    args = parser.parse_args()

    if args.file:
        trace_files = [args.file]
    else:
        # Charge tous les fichiers disponibles, dans l'ordre 1→4
        all_found = sorted(glob_module.glob("scenario_trace_s*.json"))
        if not all_found:
            # Fallback sur l'ancien nom
            all_found = glob_module.glob("scenario_trace.json")
        trace_files = all_found if all_found else ["scenario_trace.json"]

    app = LiseuseApp(trace_files=trace_files)

    # Si --scenario N, on démarre directement sur ce scénario
    if args.scenario:
        target_file = f"scenario_trace_s{args.scenario}.json"
        if target_file in trace_files:
            app.scenario_index = trace_files.index(target_file)

    app.run()
