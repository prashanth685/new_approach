import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QGridLayout
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(v).strftime('%Y-%m-%d\n%H:%M:%S') for v in values]

class MouseTracker(QObject):
    def __init__(self, parent, idx, feature):
        super().__init__(parent)
        self.idx = idx
        self.feature = feature

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.feature.mouse_enter(self.idx)
        elif event.type() == QEvent.Leave:
            self.feature.mouse_leave(self.idx)
        return False

class TimeReportFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, filename=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.feature_name = "Time Report"
        self.widget = None
        self.plot_widgets = []
        self.plots = []
        self.data = []
        self.times = []
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.active_line_idx = None
        self.num_channels = 0
        self.num_plots = 0
        self.sample_rate = 4096
        self.tacho_channels_count = 0
        self.selected_filename = filename
        self.refresh_timer = None
        self.is_initialized = False
        self.init_ui_deferred()

    def init_ui_deferred(self):
        self.setup_basic_ui()
        QTimer.singleShot(0, self.load_data_async)

    def setup_basic_ui(self):
        self.widget = QWidget(self.parent)
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        header = QLabel(f"TIME REPORT FOR {self.project_name.upper()}")
        header.setStyleSheet("color: black; font-size: 26px; font-weight: bold; padding: 8px;")
        layout.addWidget(header, alignment=Qt.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plots)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeReportFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeReportFeature.")
        logging.debug("TimeReportFeature UI initialized")

    def initialize_plots(self):
        if not self.num_channels or not self.tacho_channels_count or not self.num_plots:
            logging.error("Cannot initialize plots: channel counts not set")
            self.log_and_set_status("Cannot initialize plots: channel counts not set")
            return

        self.plot_widgets = []
        self.plots = []
        self.data = []
        self.times = []
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        colors = ['r', 'g', 'b', 'y', 'c', 'm', 'k', 'w', '#FF4500', '#32CD32', '#00CED1', '#FFD700', '#FF69B4', '#8A2BE2']
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            plot_widget.setFixedHeight(250)
            plot_widget.setMinimumWidth(0)
            if i < self.num_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.num_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', f'Tacho Trigger {i - self.num_channels}')
                plot_widget.setYRange(-0.5, 1.5, padding=0)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.data.append([])
            self.times.append([])
            self.scroll_layout.addWidget(plot_widget)

            vline = InfiniteLine(angle=90, movable=False, pen=mkPen('r', width=2))
            vline.setVisible(False)
            plot_widget.addItem(vline)
            self.vlines.append(vline)

            if i == self.num_plots - 1:
                self.trigger_lines = []
            else:
                self.trigger_lines.append(None)

            proxy = SignalProxy(plot_widget.scene().sigMouseMoved, rateLimit=60, slot=lambda evt, idx=i: self.mouse_moved(evt, idx))
            self.proxies.append(proxy)

            tracker = MouseTracker(plot_widget.viewport(), i, self)
            plot_widget.viewport().installEventFilter(tracker)
            self.trackers.append(tracker)

        self.scroll_area.setWidget(self.scroll_content)
        self.is_initialized = True
        if not self.refresh_timer.isActive():
            self.refresh_timer.start(100)

    def load_data_async(self):
        if not self.selected_filename:
            self.console.append_to_console("No saved file selected for Time Report.")
            return
        try:
            messages = self.db.get_feature_messages(self.project_name, model_name=self.model_name, feature_name="Time View", filename=self.selected_filename)
            if not messages:
                self.console.append_to_console(f"No saved data found for {self.selected_filename}")
                return

            self.num_channels = messages[0].get('numberOfChannels', 4)
            self.tacho_channels_count = messages[0].get('tachoChannelCount', 2)
            self.num_plots = self.num_channels + self.tacho_channels_count
            self.sample_rate = messages[0].get('samplingRate', 4096)
            samples_per_channel = messages[0].get('samplingSize', 4096)

            self.initialize_plots()

            all_data = [[] for _ in range(self.num_plots)]
            all_times = [[] for _ in range(self.num_plots)]
            for msg in messages:
                created_at = datetime.fromisoformat(msg['createdAt'].replace('Z', '+00:00')).timestamp()
                values = msg['message']
                num_data_channels = len(values.get('channel_data', []))
                samples = len(values.get('channel_data', [[]])[0])
                time_step = 1.0 / self.sample_rate
                times = np.array([created_at + i * time_step for i in range(samples)])
                for ch in range(self.num_channels):
                    all_data[ch].extend(values['channel_data'][ch])
                    all_times[ch].extend(times)
                if self.tacho_channels_count >= 1:
                    all_data[self.num_channels].extend(values.get('tacho_freq', []))
                    all_times[self.num_channels].extend(times)
                if self.tacho_channels_count >= 2:
                    all_data[self.num_channels + 1].extend(values.get('tacho_trigger', []))
                    all_times[self.num_channels + 1].extend(times)

            for ch in range(self.num_plots):
                self.data[ch] = np.array(all_data[ch])
                self.times[ch] = np.array(all_times[ch])
            self.refresh_plots()
            self.console.append_to_console(f"Loaded saved data for {self.selected_filename} in Time Report")
        except Exception as e:
            logging.error(f"Error loading saved data: {str(e)}")
            self.console.append_to_console(f"Error loading saved data: {str(e)}")

    def refresh_plots(self):
        if not self.is_initialized or not self.plot_widgets or not self.plots or not self.data or not self.times:
            return

        for ch in range(self.num_plots):
            times = self.times[ch]
            data = self.data[ch]
            if len(data) == 0 or len(times) == 0:
                continue

            self.plots[ch].setData(times, data)
            self.plot_widgets[ch].setXRange(times[0], times[-1], padding=0)
            if ch < self.num_channels:
                self.plot_widgets[ch].enableAutoRange(axis='y')
            elif ch == self.num_channels:
                self.plot_widgets[ch].enableAutoRange(axis='y')
            else:
                self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)

            if ch == self.num_plots - 1 and self.tacho_channels_count >= 2:
                if self.trigger_lines:
                    for line in self.trigger_lines:
                        if line:
                            self.plot_widgets[ch].removeItem(line)
                    self.trigger_lines = []

                trigger_indices = np.where(self.data[ch] == 1)[0]
                for idx in trigger_indices:
                    if idx < len(times):
                        line = InfiniteLine(pos=times[idx], angle=90, movable=False, pen=mkPen('k', width=2, style=Qt.SolidLine))
                        self.plot_widgets[ch].addItem(line)
                        self.trigger_lines.append(line)

        if self.console:
            self.console.append_to_console(f"Time Report ({self.model_name}): Refreshed {self.num_plots} plots")

    def mouse_enter(self, idx):
        self.active_line_idx = idx
        self.vlines[idx].setVisible(True)

    def mouse_leave(self, idx):
        self.active_line_idx = None
        for vline in self.vlines:
            vline.setVisible(False)

    def mouse_moved(self, evt, idx):
        if self.active_line_idx is None:
            return
        pos = evt[0]
        if not self.plot_widgets[idx].sceneBoundingRect().contains(pos):
            return
        mouse_point = self.plot_widgets[idx].plotItem.vb.mapSceneToView(pos)
        x = mouse_point.x()
        times = self.times[idx]
        if len(times) > 0:
            if x < times[0]:
                x = times[0]
            elif x > times[-1]:
                x = times[-1]
        for vline in self.vlines:
            vline.setPos(x)
            vline.setVisible(True)

    def log_and_set_status(self, message):
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)

    def get_widget(self):
        return self.widget

    def cleanup(self):
        if self.refresh_timer:
            self.refresh_timer.stop()
        for tracker in self.trackers:
            tracker.parent().removeEventFilter(tracker)
        self.trackers = []
        self.proxies = []
        self.plot_widgets = []
        self.plots = []
        self.data = []
        self.times = []
        self.vlines = []
        self.trigger_lines = []
        self.widget = None