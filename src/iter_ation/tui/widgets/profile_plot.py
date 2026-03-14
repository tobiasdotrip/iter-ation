"""Radial plasma profile widget — plotext mini-graph showing n_e(r) and Te(r)."""
from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text
from rich.ansi import AnsiDecoder
import plotext as plt

from iter_ation.physics.profiles import get_radial_data


class ProfilePlot(Widget):
    """Mini plot showing radial density and temperature profiles."""

    DEFAULT_CSS = """
    ProfilePlot {
        height: 12;
        width: 1fr;
        padding: 0 1;
    }
    """

    _data_version: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._n_e = 0.9
        self._Te_core = 20.0
        self._li = 0.85
        self._decoder = AnsiDecoder()

    def update_params(self, n_e: float, Te_core: float, li: float) -> None:
        self._n_e = n_e
        self._Te_core = Te_core
        self._li = li
        self._data_version += 1

    def render(self) -> Text:
        data = get_radial_data(
            n_e=self._n_e, Te_core=self._Te_core,
            li=self._li, points=30,
        )

        plt.clf()
        plt.theme("dark")
        plt.plotsize(self.size.width, self.size.height - 1)
        plt.xaxes(1, 0)
        plt.yaxes(1, 0)
        plt.title(f"Radial Profile (α_n={data['alpha_n']:.2f})")
        plt.xlabel("r (m)")

        r = data["r"].tolist()

        # Normalize both to 0-1 for same scale
        n_max = max(data["n_e_profile"].max(), 0.01)
        t_max = max(data["Te_profile"].max(), 0.01)

        n_norm = (data["n_e_profile"] / n_max).tolist()
        t_norm = (data["Te_profile"] / t_max).tolist()

        plt.plot(r, n_norm, label=f"n_e (peak={n_max:.2f})", color="cyan+")
        plt.plot(r, t_norm, label=f"Te (peak={t_max:.1f}keV)", color="red+")
        plt.ylim(0, 1.1)

        canvas = plt.build()
        result = Text()
        for i, line in enumerate(self._decoder.decode(canvas)):
            if i > 0:
                result.append("\n")
            result.append(line)
        return result
