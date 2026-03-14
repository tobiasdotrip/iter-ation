import asyncio
import os
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, RichLog
from textual.reactive import reactive

from plotext import plot, title, clear_figure, xlim, ylim
from textual_plotext import PlotextPlot

from simulation.generator import TokamakGenerator, TokamakState, GeneratorMode
from agent.iter_agent import ITERAgent

class TimeSeriesPlot(PlotextPlot):
    """A widget for plotting time series data using Plotext."""
    def __init__(self, title: str, id: str | None = None, **kwargs):
        super().__init__(id=id, **kwargs)
        self.plot_title = title
        self.y_data = []

    def update_data(self, new_value: float):
        self.y_data.append(new_value)
        if len(self.y_data) > 60: # Keep last 60 points
            self.y_data.pop(0)
        self._refresh_plot()

    def _refresh_plot(self):
        plt = self.plt
        plt.clear_figure()
        plt.title(self.plot_title)
        
        # Simple styling
        plt.plot(self.y_data)
        self.refresh()
