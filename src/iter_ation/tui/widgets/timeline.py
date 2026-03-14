from __future__ import annotations
from collections import deque
from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text
from rich.ansi import AnsiDecoder
import plotext as plt


class TimelineWidget(Widget):
    """Scrolling time series plot using plotext with threshold lines."""

    DEFAULT_CSS = """
    TimelineWidget {
        height: 1fr;
        width: 1fr;
    }
    """

    _data_version: reactive[int] = reactive(0)

    def __init__(self, max_points: int = 500, **kwargs) -> None:
        super().__init__(**kwargs)
        self._max_points = max_points
        self._series: dict[str, deque[float]] = {}
        self._times: deque[float] = deque(maxlen=max_points)
        self._decoder = AnsiDecoder()
        self._pulse_markers: list[float] = []
        self._thresholds: list[tuple[float, str, str]] = []  # (value, color, label)

    def add_series(self, name: str) -> None:
        if name not in self._series:
            self._series[name] = deque(maxlen=self._max_points)

    def add_threshold(self, value: float, color: str, label: str) -> None:
        """Add a horizontal threshold line to the plot."""
        self._thresholds.append((value, color, label))

    def push(self, sim_time: float, values: dict[str, float]) -> None:
        self._times.append(sim_time)
        for name, series in self._series.items():
            series.append(values.get(name, 0.0))
        self._data_version += 1

    def mark_pulse(self, sim_time: float) -> None:
        self._pulse_markers.append(sim_time)

    def render(self) -> Text:
        if len(self._times) < 2:
            return Text("Waiting for data...")

        plt.clf()
        plt.theme("dark")
        plt.plotsize(self.size.width, self.size.height - 1)
        plt.xaxes(1, 0)
        plt.yaxes(1, 0)
        plt.title("Plasma Timeline")

        times = list(self._times)
        colors = ["cyan+", "yellow+", "red+", "green+", "magenta+"]
        for i, (name, series) in enumerate(self._series.items()):
            data = list(series)
            plt.plot(times[:len(data)], data, label=name, color=colors[i % len(colors)])

        # Threshold lines
        for value, color, label in self._thresholds:
            plt.hline(value, color)

        # Pulse markers
        for t in self._pulse_markers:
            if t >= times[0]:
                plt.vline(t, "white")

        canvas = plt.build()
        result = Text()
        for i, line in enumerate(self._decoder.decode(canvas)):
            if i > 0:
                result.append("\n")
            result.append(line)
        return result
