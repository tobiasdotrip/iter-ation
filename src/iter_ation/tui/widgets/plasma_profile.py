"""Plasma profile widget — derived quantities computed from raw parameters."""
from textual.widget import Widget
from iter_ation.tui.theme import COLORS
from iter_ation.physics.constants import ITER
from iter_ation.physics.formulas import greenwald_density


class PlasmaProfile(Widget):
    """Displays derived plasma profile quantities."""

    DEFAULT_CSS = """
    PlasmaProfile {
        height: auto;
        width: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._values: dict[str, float] = {}

    def update_from_state(self, values: dict[str, float]) -> None:
        self._values = values
        self.refresh()

    def render(self) -> str:
        v = self._values
        if not v:
            return f"[bold {COLORS['accent']}]── PLASMA PROFILE ──[/]\n  [dim]Waiting...[/]"

        # tau_E: confinement time = Wmhd / P_net
        # P_net = p_input * (1 - radiated_fraction)
        p_input = v.get("p_input", 50.0)
        rad_frac = v.get("radiated_fraction", 0.5)
        wmhd = v.get("Wmhd", 350.0)
        p_net = p_input * (1.0 - rad_frac)
        tau_e = wmhd / p_net if p_net > 0.1 else 0.0

        # n_G: Greenwald density limit
        ip = v.get("Ip", 15.0)
        n_g = greenwald_density(Ip=ip, a=ITER.a) if ip > 0.01 else 0.0

        # P_rad: absolute radiated power
        p_rad = p_input * rad_frac

        # P_fusion estimate (simplified): P_fus ∝ n² * T² * V
        # At ITER nominal (Q=10): P_fus = 500 MW
        # Scale from nominal: P_fus = 500 * (n_e/0.9)² * (Te/20)² (very simplified)
        n_e = v.get("n_e", 0.9)
        te = v.get("Te_core", 20.0)
        p_fusion = 500.0 * (n_e / 0.9) ** 2 * (te / 20.0) ** 2

        # Q: fusion gain = P_fusion / P_input
        q_gain = p_fusion / p_input if p_input > 0.1 else 0.0

        # Color tau_E based on quality
        tau_color = COLORS["nominal"] if tau_e > 5.0 else (COLORS["warning"] if tau_e > 3.0 else COLORS["danger"])
        q_color = COLORS["nominal"] if q_gain > 8.0 else (COLORS["warning"] if q_gain > 5.0 else COLORS["danger"])

        lines = [
            f"[bold {COLORS['accent']}]── PLASMA PROFILE ──[/]",
            f"  [{tau_color}]tau_E       {tau_e:>9.3f} s[/]",
            f"  n_G         {n_g:>9.3f} 1e20m\u207b\u00b3",
            f"  P_rad       {p_rad:>9.3f} MW",
            f"  P_net       {p_net:>9.3f} MW",
            f"  P_fusion    {p_fusion:>9.3f} MW",
            f"  [{q_color}]Q (gain)    {q_gain:>9.3f}[/]",
        ]
        return "\n".join(lines)
