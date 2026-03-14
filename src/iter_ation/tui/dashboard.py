from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget
from iter_ation.tui.widgets.ai_panel import AIPanel
from iter_ation.tui.widgets.param_section import ParamSection
from iter_ation.tui.widgets.plasma_profile import PlasmaProfile
from iter_ation.tui.widgets.profile_plot import ProfilePlot


class Dashboard(Static):
    DEFAULT_CSS = """
    Dashboard { height: 1fr; width: 1fr; }
    #main-area { height: 1fr; }
    #timeline { width: 1fr; min-width: 40; }
    #right-panel { width: 38; min-width: 38; }
    #key-metrics { height: auto; padding: 0 1; }
    #params-scroll { height: 1fr; }
    #bottom-area { height: 8; }
    #alerts-panel { width: 1fr; }
    #ai-panel { width: 1fr; }
    .section-title { height: 1; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        # Main area: timeline left, panels right
        with Horizontal(id="main-area"):
            yield TimelineWidget(id="timeline")

            with Vertical(id="right-panel"):
                # Key metrics with gauges
                yield Static(
                    f"[bold #00b4d8]── KEY METRICS ──[/]",
                    classes="section-title",
                )
                with Vertical(id="key-metrics"):
                    yield Gauge(
                        label="fGW", unit="",
                        min_val=0.0, max_val=1.5,
                        id="gauge-greenwald_fraction",
                    )
                    yield Gauge(
                        label="beta_n", unit="",
                        min_val=0.0, max_val=5.0,
                        id="gauge-beta_n",
                    )
                    yield Gauge(
                        label="q95", unit="",
                        min_val=0.0, max_val=6.0,
                        id="gauge-q95",
                    )

                # Parameter sections
                with Vertical(id="params-scroll"):
                    yield ParamSection(
                        title="DENSITY",
                        params=[
                            ("n_e", "n_e", "1e20m\u207b\u00b3"),
                            ("Ip", "Ip", "MA"),
                            ("radiated_fraction", "rad_frac", ""),
                        ],
                        id="section-density",
                    )
                    yield ParamSection(
                        title="STABILITY",
                        params=[
                            ("li", "li", ""),
                            ("n1_amplitude", "n1_amp", "mT"),
                        ],
                        id="section-stability",
                    )
                    yield ParamSection(
                        title="THERMAL",
                        params=[
                            ("Te_core", "Te_core", "keV"),
                            ("Wmhd", "Wmhd", "MJ"),
                            ("v_loop", "v_loop", "V"),
                        ],
                        id="section-thermal",
                    )
                    yield ParamSection(
                        title="POSITION & POWER",
                        params=[
                            ("zcur", "zcur", "m"),
                            ("p_input", "p_input", "MW"),
                        ],
                        id="section-position",
                    )
                    yield PlasmaProfile(id="plasma-profile")
                    yield ProfilePlot(id="profile-plot")

        # Bottom area: alerts + AI panel side by side
        with Horizontal(id="bottom-area"):
            with Vertical(id="alerts-panel"):
                yield Static("[bold #00b4d8]── ALERTS ──[/]", classes="section-title")
                yield AlertLogWidget(id="alert-log")
            with Vertical(id="ai-panel"):
                yield Static("[bold #00b4d8]── AI OPERATOR ──[/]", classes="section-title")
                yield AIPanel(id="ai-log")
