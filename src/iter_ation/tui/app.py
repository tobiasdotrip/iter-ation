from __future__ import annotations
import queue
import time
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
from iter_ation.tui.dashboard import Dashboard
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget
from iter_ation.tui.widgets.controls import ControlsBar


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


class IterApp(App):
    """ITER-ATION Disruption Monitor."""

    CSS = """
    Screen { background: #1a1a2e; }
    #header-bar { dock: top; height: 1; background: #16213e; color: #e0e0e0; text-align: center; }
    #right-panel { width: 40; }
    #gauges { height: 2fr; }
    #timeline { width: 1fr; }
    #alert-log { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_pause", "Pause"),
        ("o", "mode_observation", "Observation"),
        ("i", "mode_interactive", "Interactive"),
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
        self._paused = False
        self._action_queue: queue.Queue[OperatorAction] = queue.Queue()
        self._alert_log = AlertLog()
        self._engine = SimulationEngine()

    def compose(self) -> ComposeResult:
        yield Static(
            f"ITER-ATION -- Disruption Monitor    t=0.000s  x{self._speed}",
            id="header-bar",
        )
        yield Dashboard()
        yield ControlsBar(id="controls")

    def on_mount(self) -> None:
        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.add_series("greenwald_fraction")
        timeline.add_series("radiated_fraction")
        timeline.add_series("q95")
        self.query_one("#controls", ControlsBar).interactive_mode = self._interactive
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
            time.sleep(frame_interval)

    def on_plasma_update(self, event: PlasmaUpdate) -> None:
        self.query_one("#header-bar", Static).update(
            f"ITER-ATION -- Disruption Monitor    t={event.sim_time:.3f}s  x{self._speed}"
        )

        for name, value in event.values.items():
            try:
                gauge = self.query_one(f"#gauge-{name}", Gauge)
                gauge.update_value(value, event.param_levels.get(name, AlertLevel.NOMINAL))
            except Exception:
                pass

        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.push(event.sim_time, event.values)

        if event.new_pulse:
            timeline.mark_pulse(event.sim_time)

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
        self.query_one("#controls", ControlsBar).interactive_mode = False

    def action_mode_interactive(self) -> None:
        self._interactive = True
        self.query_one("#controls", ControlsBar).interactive_mode = True

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
