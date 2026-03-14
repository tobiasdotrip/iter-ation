from __future__ import annotations
import queue
import time
import threading
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.message import Message
from textual.worker import get_current_worker

from iter_ation.generator.engine import SimulationEngine
from iter_ation.generator.disruption import DisruptionPhase
from iter_ation.monitoring.thresholds import evaluate_parameter, evaluate_all, AlertLevel
from iter_ation.monitoring.alerts import AlertLog
from iter_ation.monitoring.operator import OperatorAction, ACTION_DELTAS
from iter_ation.agent.operator_ai import OperatorAI
from iter_ation.tui.dashboard import Dashboard
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget
from iter_ation.tui.widgets.ai_panel import AIPanel
from iter_ation.tui.widgets.controls import ControlsBar
from iter_ation.tui.widgets.param_section import ParamSection
from iter_ation.tui.theme import COLORS

_STATUS_DISPLAY = {
    AlertLevel.NOMINAL: f"[bold {COLORS['nominal']}]● NOMINAL[/]",
    AlertLevel.WARNING: f"[bold {COLORS['warning']}]⚠ WARNING[/]",
    AlertLevel.DANGER: f"[bold {COLORS['danger']}]✖ DANGER[/]",
    AlertLevel.DISRUPTION: f"[bold {COLORS['disruption']} blink]◉ DISRUPTION[/]",
}


class PlasmaUpdate(Message):
    def __init__(self, values: dict[str, float], sim_time: float,
                 alert_level: AlertLevel, param_levels: dict[str, AlertLevel],
                 new_pulse: bool) -> None:
        super().__init__()
        self.values = values
        self.sim_time = sim_time
        self.alert_level = alert_level
        self.param_levels = param_levels
        self.new_pulse = new_pulse


class AIDecision(Message):
    """Posted when the AI agent makes a decision."""
    def __init__(self, action: OperatorAction | None, reason: str, sim_time: float) -> None:
        super().__init__()
        self.action = action
        self.reason = reason
        self.sim_time = sim_time


class IterApp(App):
    """ITER-ATION Disruption Monitor."""

    CSS = """
    Screen { background: #1a1a2e; color: #e0e0e0; }
    #header-bar {
        dock: top;
        height: 1;
        background: #16213e;
        color: #e0e0e0;
        padding: 0 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_pause", "Pause"),
        ("o", "mode_observation", "Observation"),
        ("i", "mode_interactive", "Interactive"),
        ("a", "mode_ai", "AI"),
        ("up", "gas_up", "Gas +"),
        ("down", "gas_down", "Gas -"),
        ("+", "power_up", "Power +"),
        ("-", "power_down", "Power -"),
        ("s", "spi", "SPI"),
        ("x", "scram", "SCRAM"),
    ]

    def __init__(self, speed: int = 100, interactive: bool = False) -> None:
        super().__init__()
        self._speed = speed
        self._interactive = interactive
        self._ai_mode = not interactive  # AI mode by default
        self._paused = False
        self._action_queue: queue.Queue[OperatorAction] = queue.Queue()
        self._alert_log = AlertLog()
        self._engine = SimulationEngine()
        self._operator_ai = OperatorAI()
        self._ai_call_lock = threading.Lock()

    def compose(self) -> ComposeResult:
        yield Static(
            f"ITER-ATION -- Disruption Monitor    t=0.000s  x{self._speed}    {_STATUS_DISPLAY[AlertLevel.NOMINAL]}",
            id="header-bar",
        )
        yield Dashboard()
        yield ControlsBar(id="controls")

    def on_mount(self) -> None:
        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.add_series("greenwald_fraction")
        timeline.add_threshold(0.85, "yellow", "WARNING 0.85")
        timeline.add_threshold(1.0, "red", "DANGER 1.0")

        controls = self.query_one("#controls", ControlsBar)
        controls.interactive_mode = self._interactive
        controls.ai_mode = self._ai_mode

        # Show AI status on mount
        ai_panel = self.query_one("#ai-log", AIPanel)
        if self._operator_ai.is_available:
            ai_panel.write("[green]AI agent ready — monitoring[/]")
        else:
            ai_panel.write("[red]No GEMINI_API_KEY in .env — AI disabled[/]")
            self._ai_mode = False
            controls.ai_mode = False

        self._run_simulation()

    @work(thread=True)
    def _run_simulation(self) -> None:
        worker = get_current_worker()
        ticks_per_frame = max(1, self._speed // 10)
        frame_interval = 1.0 / 30

        while not worker.is_cancelled:
            if self._paused:
                time.sleep(0.05)
                continue

            # Process operator actions (manual or AI)
            while not self._action_queue.empty():
                self._handle_action(self._action_queue.get_nowait())

            new_pulse = False
            for _ in range(ticks_per_frame):
                state = self._engine.tick()
                if self._engine.new_pulse_triggered:
                    new_pulse = True

            values = state.values()
            param_levels = {name: evaluate_parameter(name, val) for name, val in values.items()}

            if self._engine.cascade.is_active and self._engine.cascade.phase != DisruptionPhase.RECOVERY:
                overall = AlertLevel.DISRUPTION
            else:
                overall = evaluate_all(values)

            self.post_message(PlasmaUpdate(
                values=values, sim_time=state.sim_time,
                alert_level=overall, param_levels=param_levels,
                new_pulse=new_pulse,
            ))

            # AI agent evaluation (non-blocking)
            if self._ai_mode and self._operator_ai.is_available:
                self._evaluate_ai(values, overall, param_levels, state.sim_time)

            time.sleep(frame_interval)

    def _evaluate_ai(
        self, values: dict[str, float], alert_level: AlertLevel,
        param_levels: dict[str, AlertLevel], sim_time: float,
    ) -> None:
        """Call AI agent in a separate thread to avoid blocking simulation."""
        if not self._ai_call_lock.acquire(blocking=False):
            return  # Another AI call is in progress

        def _call():
            try:
                action, reason = self._operator_ai.evaluate(
                    values=values,
                    alert_level=alert_level,
                    param_levels=param_levels,
                    sim_time=sim_time,
                )
                if reason:
                    if action is not None:
                        self._action_queue.put(action)
                    # Use call_from_thread to safely update UI from daemon thread
                    self.call_from_thread(self._display_ai_decision, action, reason, sim_time)
            finally:
                self._ai_call_lock.release()

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()

    def _display_ai_decision(self, action: OperatorAction | None, reason: str, sim_time: float) -> None:
        """Update AI panel from the main thread."""
        ai_panel = self.query_one("#ai-log", AIPanel)
        if action is not None:
            ai_panel.log_action(sim_time, action.value.upper(), reason)
        else:
            ai_panel.write(f"[dim]t={sim_time:.3f}s[/] [dim]{reason}[/]")

    def on_plasma_update(self, event: PlasmaUpdate) -> None:
        # Header with status
        status = _STATUS_DISPLAY.get(event.alert_level, _STATUS_DISPLAY[AlertLevel.NOMINAL])
        self.query_one("#header-bar", Static).update(
            f"ITER-ATION -- Disruption Monitor    "
            f"t={event.sim_time:.3f}s  x{self._speed}    {status}"
        )

        # Key metric gauges
        for name in ("greenwald_fraction", "beta_n", "q95"):
            if name in event.values:
                try:
                    gauge = self.query_one(f"#gauge-{name}", Gauge)
                    gauge.update_value(event.values[name], event.param_levels.get(name, AlertLevel.NOMINAL))
                except Exception:
                    pass

        # Parameter sections
        section_params = {
            "section-density": ["n_e", "Ip", "radiated_fraction"],
            "section-stability": ["li", "n1_amplitude"],
            "section-thermal": ["Te_core", "Wmhd", "v_loop"],
            "section-position": ["zcur", "p_input"],
        }
        for section_id, params in section_params.items():
            try:
                section = self.query_one(f"#{section_id}", ParamSection)
                for name in params:
                    if name in event.values:
                        section.update_param(
                            name, event.values[name],
                            event.param_levels.get(name, AlertLevel.NOMINAL),
                        )
            except Exception:
                pass

        # Timeline
        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.push(event.sim_time, event.values)
        if event.new_pulse:
            timeline.mark_pulse(event.sim_time)

        # Alerts
        entry = self._alert_log.update(event.sim_time, event.alert_level, event.param_levels)
        if entry:
            self.query_one("#alert-log", AlertLogWidget).add_alert(entry)

    def _handle_action(self, action: OperatorAction) -> None:
        engine = self._engine
        if action == OperatorAction.SPI:
            engine.apply_operator_adjustment("n_e", engine.current_state.n_e * 2)
            engine.apply_operator_adjustment("Te_core", -engine.current_state.Te_core * 0.8)
            engine.apply_operator_adjustment("radiated_fraction", 0.45)
            engine.apply_operator_adjustment("v_loop", 1.5)
        elif action == OperatorAction.SCRAM:
            engine.apply_operator_adjustment("Ip", -engine.current_state.Ip * 0.95)
        elif action in ACTION_DELTAS:
            for param, delta in ACTION_DELTAS[action].items():
                engine.apply_operator_adjustment(param, delta)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self.query_one("#controls", ControlsBar).paused = self._paused

    def action_mode_observation(self) -> None:
        self._interactive = False
        self._ai_mode = False
        controls = self.query_one("#controls", ControlsBar)
        controls.interactive_mode = False
        controls.ai_mode = False

    def action_mode_interactive(self) -> None:
        self._interactive = True
        self._ai_mode = False
        controls = self.query_one("#controls", ControlsBar)
        controls.interactive_mode = True
        controls.ai_mode = False

    def action_mode_ai(self) -> None:
        self._interactive = False
        self._ai_mode = True
        controls = self.query_one("#controls", ControlsBar)
        controls.interactive_mode = False
        controls.ai_mode = True

    def action_gas_up(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.GAS_UP)

    def action_gas_down(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.GAS_DOWN)

    def action_power_up(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.POWER_UP)

    def action_power_down(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.POWER_DOWN)

    def action_spi(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.SPI)

    def action_scram(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.SCRAM)
