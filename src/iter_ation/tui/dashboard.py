from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from iter_ation.physics.parameters import PARAMETERS
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget

_GAUGE_RANGES: dict[str, tuple[float, float]] = {
    "greenwald_fraction": (0.0, 1.5),
    "n_e": (0.0, 2.0),
    "Ip": (0.0, 20.0),
    "q95": (0.0, 6.0),
    "Te_core": (0.0, 30.0),
    "Wmhd": (0.0, 500.0),
    "radiated_fraction": (0.0, 1.0),
    "li": (0.0, 2.0),
    "n1_amplitude": (0.0, 2.0),
    "v_loop": (0.0, 3.0),
    "beta_n": (0.0, 5.0),
    "zcur": (-0.5, 0.5),
    "p_input": (0.0, 80.0),
}


class Dashboard(Static):
    DEFAULT_CSS = """
    Dashboard { height: 1fr; width: 1fr; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield TimelineWidget(id="timeline")
            with Vertical(id="right-panel"):
                with Vertical(id="gauges"):
                    for p in PARAMETERS:
                        min_v, max_v = _GAUGE_RANGES.get(p.name, (0.0, 1.0))
                        yield Gauge(
                            label=p.name[:8], unit=p.unit,
                            min_val=min_v, max_val=max_v,
                            id=f"gauge-{p.name}",
                        )
                yield AlertLogWidget(id="alert-log")
