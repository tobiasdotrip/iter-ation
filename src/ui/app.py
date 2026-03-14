import asyncio
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, RichLog, Label
from textual.reactive import reactive
from textual.worker import Worker, get_current_worker

from simulation.generator import TokamakGenerator, TokamakState, GeneratorMode
from agent.iter_agent import ITERAgent
from ui.components import TimeSeriesPlot

class StatPanel(Static):
    """Panel displaying current numerical values."""
    
    fgw = reactive("0.00")
    q95 = reactive("0.00")
    beta_n = reactive("0.00")
    tau_e = reactive("0.00")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Paramètres Temps Réel", id="stats_title")
            yield Label("", id="lbl_fgw")
            yield Label("", id="lbl_q95")
            yield Label("", id="lbl_beta_n")
            yield Label("", id="lbl_tau_e")

    def watch_fgw(self, old_val, new_val):
        try:
            bar_len = int(float(new_val) * 10)
            bar = "█" * min(bar_len, 10) + "░" * max(0, 10 - bar_len)
            self.query_one("#lbl_fgw", Label).update(f"{bar} fGW    {new_val}")
        except Exception:
            pass

    def watch_q95(self, old_val, new_val):
        try:
            bar_len = int(float(new_val) * 2)
            bar = "█" * min(bar_len, 10) + "░" * max(0, 10 - bar_len)
            self.query_one("#lbl_q95", Label).update(f"{bar} q95    {new_val}")
        except Exception:
            pass

    def watch_beta_n(self, old_val, new_val):
        try:
            bar_len = int(float(new_val) * 3)
            bar = "█" * min(bar_len, 10) + "░" * max(0, 10 - bar_len)
            self.query_one("#lbl_beta_n", Label).update(f"{bar} Beta_n {new_val}")
        except Exception:
            pass

    def watch_tau_e(self, old_val, new_val):
        try:
            bar_len = int(float(new_val) * 2)
            bar = "█" * min(bar_len, 10) + "░" * max(0, 10 - bar_len)
            self.query_one("#lbl_tau_e", Label).update(f"{bar} tau_E  {new_val} s")
        except Exception:
            pass


class IterActionApp(App):
    """ITER-ATION Main Terminal Application."""

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
    """

    def __init__(self):
        super().__init__()
        self.generator = TokamakGenerator(tick_rate_hz=10)
        self.generator.on_tick = self.on_sim_tick
        self.ai_agent = ITERAgent()
        
        self.ai_enabled = True
        self.active_scenario = GeneratorMode.STABLE
        self.tick_count = 0

    def compose(self) -> ComposeResult:
        with Header():
            yield Label("ITER-ATION — Disruption Monitor")
        
        with Grid():
            yield TimeSeriesPlot(title="Evolution Paramètre", id="plot")
            yield StatPanel(id="stats")
            yield RichLog(id="ai_log", markup=True)

        with Horizontal(id="controls"):
            yield Button("Stable", id="btn_stable", variant="success")
            yield Button("[1] fGW", id="btn_1", variant="warning")
            yield Button("[2] Beta", id="btn_2", variant="warning")
            yield Button("[3] q95", id="btn_3", variant="warning")
            yield Button("[4] tau_E", id="btn_4", variant="warning")
            yield Button("Toggle AI", id="btn_ai", variant="primary")
            
        yield Footer()

    def on_mount(self) -> None:
        self.generator.start()
        self.log_ai("[bold green]Agent IA CONNECTÉ[/bold green]")
        self.log_ai("[dim]Mode : AUTOMATIQUE[/dim]")
        
        # Start AI periodic analysis
        self.set_interval(2.0, self.trigger_ai_analysis)

    def on_unmount(self) -> None:
        self.generator.stop()

    def on_sim_tick(self, state: TokamakState):
        """Called by generator thread when a new state is computed."""
        # Use call_from_thread since this is called from the generator's thread
        self.call_from_thread(self.update_ui, state)

    def update_ui(self, state: TokamakState):
        """Updates the UI widgets with new data."""
        self.tick_count += 1
        
        # Update numeric stats
        stats = self.query_one("#stats", StatPanel)
        stats.fgw = f"{state.greenwald_fraction:.2f}"
        stats.q95 = f"{state.q95:.2f}"
        stats.beta_n = f"{state.beta_n:.2f}"
        stats.tau_e = f"{state.tau_E:.2f}"

        # Update plot based on active scenario
        plot = self.query_one("#plot", TimeSeriesPlot)
        if self.active_scenario == GeneratorMode.SCENARIO_1_GREENWALD:
            plot.plot_title = "Scénario 1: Greenwald Fraction (fGW)"
            plot.update_data(state.greenwald_fraction)
        elif self.active_scenario == GeneratorMode.SCENARIO_2_BETA:
            plot.plot_title = "Scénario 2: Normalized Beta (beta_n)"
            plot.update_data(state.beta_n)
        elif self.active_scenario == GeneratorMode.SCENARIO_3_Q95:
            plot.plot_title = "Scénario 3: Safety Factor (q95)"
            plot.update_data(state.q95)
        elif self.active_scenario == GeneratorMode.SCENARIO_4_TAUE:
            plot.plot_title = "Scénario 4: Energy Confinement (tau_E)"
            plot.update_data(state.tau_E)
        else:
            plot.plot_title = "Mode Stable: Densité (n_e)"
            plot.update_data(state.n_e)

    def trigger_ai_analysis(self):
        """Triggers the async worker to call Gemini API if not already busy."""
        if self.ai_enabled:
            # Take a snapshot of current state
            s = self.generator.state
            state_dict = {
                "n_e (10^20 m^-3)": round(s.n_e, 3),
                "Ip (MA)": round(s.Ip, 3),
                "Wmhd (MJ)": round(s.Wmhd, 3),
                "p_input (MW)": round(s.p_input, 3),
                "greenwald_fraction": round(s.greenwald_fraction, 3),
                "beta_n": round(s.beta_n, 3),
                "q95": round(s.q95, 3),
                "tau_E (s)": round(s.tau_E, 3)
            }
            self.run_worker(self.ai_worker(state_dict), thread=True)

    def ai_worker(self, state_dict: dict):
        """Worker thread to query Gemini without blocking UI."""
        worker = get_current_worker()
        
        # Ne consulte l'IA que si un seuil est approché (économie d'appels API)
        is_stable = (
            state_dict["greenwald_fraction"] < 0.82 and
            state_dict["beta_n"] < 2.5 and
            state_dict["q95"] > 2.3 and
            state_dict["tau_E (s)"] > 2.5
        )
        if is_stable:
            action = "STABLE"
        else:
            self.call_from_thread(self.log_ai, "> Analyse des signaux...")
            action = self.ai_agent.analyze_state(state_dict)

        if not worker.is_cancelled:
            self.call_from_thread(self.handle_ai_action, action)

    def handle_ai_action(self, action: str):
        if action != "STABLE" and action != "UNKNOWN_ACTION":
            self.log_ai(f"[bold red]> Action corrective IA : {action}[/bold red]")
            self.generator.apply_ai_action(action)
            # If AI fixed it, update UI tracking
            if self.generator.mode == GeneratorMode.STABLE and self.active_scenario != GeneratorMode.STABLE:
                self.log_ai("[bold green]> Plasma stabilisé avec succès ![/]")
                self.active_scenario = GeneratorMode.STABLE

    def log_ai(self, msg: str):
        log = self.query_one("#ai_log", RichLog)
        log.write(msg)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_stable":
            self.active_scenario = GeneratorMode.STABLE
            self.generator.set_scenario(GeneratorMode.STABLE)
            self.log_ai("\n[dim]--- Retour manuel mode stable ---[/]")
        elif event.button.id == "btn_1":
            self.active_scenario = GeneratorMode.SCENARIO_1_GREENWALD
            self.generator.set_scenario(GeneratorMode.SCENARIO_1_GREENWALD)
            self.log_ai("\n[bold orange3]--- Scénario 1 Déclenché (fGW) ---[/]")
        elif event.button.id == "btn_2":
            self.active_scenario = GeneratorMode.SCENARIO_2_BETA
            self.generator.set_scenario(GeneratorMode.SCENARIO_2_BETA)
            self.log_ai("\n[bold orange3]--- Scénario 2 Déclenché (Beta) ---[/]")
        elif event.button.id == "btn_3":
            self.active_scenario = GeneratorMode.SCENARIO_3_Q95
            self.generator.set_scenario(GeneratorMode.SCENARIO_3_Q95)
            self.log_ai("\n[bold orange3]--- Scénario 3 Déclenché (q95) ---[/]")
        elif event.button.id == "btn_4":
            self.active_scenario = GeneratorMode.SCENARIO_4_TAUE
            self.generator.set_scenario(GeneratorMode.SCENARIO_4_TAUE)
            self.log_ai("\n[bold orange3]--- Scénario 4 Déclenché (tau_E) ---[/]")
        elif event.button.id == "btn_ai":
            self.ai_enabled = not self.ai_enabled
            status = "ACTIVÉE" if self.ai_enabled else "DÉSACTIVÉE"
            self.log_ai(f"[bold magenta]IA {status}[/]")

if __name__ == "__main__":
    app = IterActionApp()
    app.run()
