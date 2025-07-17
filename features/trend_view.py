from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Format x-axis ticks as hh:mm:ss"""
        return [datetime.fromtimestamp(val).strftime('%H:%M:%S') for val in values]

class TrendViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.model_name = model_name
        self.console = console
        self.num_channels = 4
        self.scaling_factor = 3.3 / 65535.0
        self.channel = self.resolve_channel_index(channel) if channel is not None else 0
        self.widget = None
        self.plot_data = []  # (timestamp, average) tuples
        self.display_window_seconds = 1.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)
        self.initUI()

    def resolve_channel_index(self, channel):
        try:
            if isinstance(channel, str):
                project_data = self.db.get_project_data(self.project_name) if self.db else {}
                models = project_data.get("models", {})
                for m_data in models.values():
                    channels = m_data.get("channels", [])
                    for idx, ch in enumerate(channels):
                        if ch.get("tag_name") == channel:
                            return idx
            elif isinstance(channel, int):
                return channel
        except Exception as e:
            logging.warning(f"Failed to resolve channel index: {e}")
        return 0

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        self.label = QLabel(f"Trend View for Model: {self.model_name}, Channel: {self.channel}")
        layout.addWidget(self.label)

        self.data_display = QListWidget()
        layout.addWidget(self.data_display)

        # Use custom TimeAxisItem for x-axis
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot_widget.setTitle(f"Trend for {self.model_name} - Channel {self.channel}")
        self.plot_widget.setLabel('left', 'Voltage (V)')
        self.plot_widget.setLabel('bottom', 'Time (hh:mm:ss)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('w')
        layout.addWidget(self.plot_widget)

        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2))

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return

        if self.channel >= len(values):
            return

        raw_values = values[self.channel]
        if not raw_values:
            return

        try:
            scaled = np.array(raw_values, dtype=np.float32) * self.scaling_factor
            avg_voltage = float(np.mean(scaled))
            timestamp = datetime.now().timestamp()
            self.plot_data.append((timestamp, avg_voltage))
            self.data_display.addItem(f"{tag_name}: Avg={avg_voltage:.3f} V at {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")
            self.trim_old_data()
        except Exception as e:
            logging.error(f"Data processing error: {e}")

    def trim_old_data(self):
        now = datetime.now().timestamp()
        self.plot_data = [(t, v) for t, v in self.plot_data if (now - t) <= self.display_window_seconds]

    def update_plot(self):
        if not self.plot_data:
            return

        timestamps, voltages = zip(*self.plot_data)
        now = datetime.now().timestamp()

        # Padding logic for x-axis: 40px / width * timespan
        try:
            plot_width = self.plot_widget.width()
            timespan = self.display_window_seconds
            padding_time = (40.0 / plot_width) * timespan if plot_width > 0 else 1.0
            self.plot_widget.setXRange(now - timespan - padding_time, now + padding_time)
        except Exception as e:
            logging.warning(f"Padding calculation error: {e}")

        self.curve.setData(timestamps, voltages)