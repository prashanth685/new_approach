import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QComboBox, QGridLayout
from PyQt5.QtCore import QObject, QEvent, Qt, QTimer
from PyQt5.QtGui import QIcon
from pyqtgraph import PlotWidget, mkPen, AxisItem, InfiniteLine, SignalProxy
from datetime import datetime
import time
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

class TimeViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, filename=None):
        super().__init__()
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.feature_name = "Time View"
        self.saved_filename = filename
        self.widget = None
        self.plot_widgets = []
        self.plots = []
        self.fifo_data = []
        self.fifo_times = []
        self.sample_rate = None
        self.main_channels = None
        self.tacho_channels_count = None
        self.total_channels = None
        self.scaling_factor = 3.3 / 65535
        self.num_plots = None
        self.samples_per_channel = None
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.active_line_idx = None
        self.window_seconds = 1
        self.fifo_window_samples = None
        self.settings_panel = None
        self.settings_button = None
        self.refresh_timer = None
        self.needs_refresh = []
        self.is_initialized = False
        self.initUI()
        if self.saved_filename:
            self.load_saved_data()

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon("settings_icon.png"))
        self.settings_button.clicked.connect(self.toggle_settings)
        top_layout.addWidget(self.settings_button)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QGridLayout()
        self.settings_panel.setLayout(settings_layout)

        settings_layout.addWidget(QLabel("Window Size (seconds)"), 0, 0)
        window_combo = QComboBox()
        window_combo.addItems([str(i) for i in range(1, 11)])
        window_combo.setCurrentText(str(self.window_seconds))
        settings_layout.addWidget(window_combo, 0, 1)
        self.settings_widgets = {"WindowSeconds": window_combo}

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_settings)
        settings_layout.addWidget(save_button, 1, 0)
        settings_layout.addWidget(close_button, 1, 1)

        main_layout.addWidget(self.settings_panel)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        self.widget.setLayout(main_layout)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plots)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in TimeViewFeature.")
        if not self.channel and self.console:
            self.console.append_to_console("No channel selected in TimeViewFeature.")
        logging.debug("UI initialized")

    def initialize_plots(self):
        if not self.main_channels or not self.tacho_channels_count or not self.total_channels:
            logging.error("Cannot initialize plots: channel counts not set")
            self.log_and_set_status("Cannot initialize plots: channel counts not set")
            return

        self.plot_widgets = []
        self.plots = []
        self.fifo_data = []
        self.fifo_times = []
        self.vlines = []
        self.proxies = []
        self.trackers = []
        self.trigger_lines = []
        self.needs_refresh = []

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        colors = ['r', 'g', 'b', 'y', 'c', 'm', 'k', 'w', '#FF4500', '#32CD32', '#00CED1', '#FFD700', '#FF69B4', '#8A2BE2', '#FF6347', '#20B2AA', '#ADFF2F', '#9932CC', '#FF7F50', '#00FA9A', '#9400D3']
        self.num_plots = self.total_channels
        for i in range(self.num_plots):
            plot_widget = PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')}, background='w')
            plot_widget.setFixedHeight(250)
            plot_widget.setMinimumWidth(0)
            if i < self.main_channels:
                plot_widget.setLabel('left', f'CH{i+1} Value')
            elif i == self.main_channels:
                plot_widget.setLabel('left', 'Tacho Frequency')
            else:
                plot_widget.setLabel('left', f'Tacho Trigger {i - self.main_channels}')
                plot_widget.setYRange(-0.5, 1.5, padding=0)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.addLegend()
            pen = mkPen(color=colors[i % len(colors)], width=2)
            plot = plot_widget.plot([], [], pen=pen)
            self.plots.append(plot)
            self.plot_widgets.append(plot_widget)
            self.fifo_data.append([])
            self.fifo_times.append([])
            self.needs_refresh.append(True)

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

            self.scroll_layout.addWidget(plot_widget)

        self.scroll_area.setWidget(self.scroll_content)
        self.initialize_buffers()

    def initialize_buffers(self):
        if not self.sample_rate or not self.num_plots or not self.samples_per_channel:
            logging.error("Cannot initialize buffers: sample_rate, num_plots, or samples_per_channel not set")
            self.log_and_set_status("Buffer initialization failed")
            return
        self.fifo_window_samples = self.sample_rate * self.window_seconds
        for i in range(self.num_plots):
            self.fifo_data[i] = np.zeros(self.fifo_window_samples)
            time_step = self.window_seconds / self.fifo_window_samples
            self.fifo_times[i] = np.array([i * time_step for i in range(self.fifo_window_samples)])
        self.is_initialized = True
        if not self.refresh_timer.isActive() and not self.saved_filename:
            self.refresh_timer.start(100)

    def load_saved_data(self):
        if not self.saved_filename:
            return
        messages = self.db.get_feature_messages(self.project_name, model_name=self.model_name, feature_name=self.feature_name, filename=self.saved_filename)
        if not messages:
            self.console.append_to_console(f"No saved data found for {self.saved_filename}")
            return

        all_data = [[] for _ in range(self.num_plots)]
        all_times = [[] for _ in range(self.num_plots)]
        self.sample_rate = messages[0].get('samplingRate', 4096)
        self.main_channels = messages[0].get('numberOfChannels', 4)
        self.tacho_channels_count = messages[0].get('tacoChannelCount', 2)
        self.total_channels = self.main_channels + self.tacho_channels_count
        self.num_plots = self.total_channels
        self.samples_per_channel = messages[0].get('samplingSize', 4096)

        self.initialize_plots()

        for msg in messages:
            created_at = datetime.fromisoformat(msg['createdAt'].replace('Z', '+00:00')).timestamp()
            values = msg['message']
            num_channels = len(values) - 2
            samples = len(values[0])
            time_step = 1.0 / self.sample_rate
            times = np.array([created_at + i * time_step for i in range(samples)])
            for ch in range(self.main_channels):
                all_data[ch].extend(values[ch])
                all_times[ch].extend(times)
            if self.tacho_channels_count >= 1:
                all_data[self.main_channels].extend(values[num_channels])
                all_times[self.main_channels].extend(times)
            if self.tacho_channels_count >= 2:
                all_data[self.main_channels + 1].extend(values[num_channels + 1])
                all_times[self.main_channels + 1].extend(times)

        for ch in range(self.num_plots):
            self.fifo_data[ch] = np.array(all_data[ch])
            self.fifo_times[ch] = np.array(all_times[ch])
            self.needs_refresh[ch] = True
        self.refresh_plots()

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.settings_button.setVisible(not self.settings_panel.isVisible())

    def save_settings(self):
        try:
            selected_seconds = int(self.settings_widgets["WindowSeconds"].currentText())
            if 1 <= selected_seconds <= 10:
                if selected_seconds != self.window_seconds:
                    self.window_seconds = selected_seconds
                    self.update_window_size()
                    if self.console:
                        self.console.append_to_console(f"Applied window size: {self.window_seconds} seconds.")
                self.settings_panel.setVisible(False)
                self.settings_button.setVisible(True)
            else:
                self.log_and_set_status(f"Invalid window seconds: {selected_seconds}")
        except Exception as e:
            self.log_and_set_status(f"Error saving settings: {str(e)}")

    def close_settings(self):
        self.settings_widgets["WindowSeconds"].setCurrentText(str(self.window_seconds))
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)

    def update_window_size(self):
        if not self.sample_rate or not self.num_plots:
            logging.error("Cannot update window size: sample_rate or num_plots not set")
            return
        new_fifo_window_samples = self.sample_rate * self.window_seconds
        for i in range(self.num_plots):
            current_data = self.fifo_data[i]
            current_length = len(current_data)
            new_data = np.zeros(new_fifo_window_samples)
            copy_length = min(current_length, new_fifo_window_samples)
            new_data[:copy_length] = current_data[:copy_length]
            self.fifo_data[i] = new_data
            time_step = self.window_seconds / new_fifo_window_samples
            self.fifo_times[i] = np.array([j * time_step for j in range(new_fifo_window_samples)])
            self.needs_refresh[i] = True
        self.fifo_window_samples = new_fifo_window_samples

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name:
            return
        try:
            if not values or not sample_rate or sample_rate <= 0:
                self.log_and_set_status(f"Invalid data: values={values}, sample_rate={sample_rate}")
                return

            self.main_channels = len(values) - 2 if len(values) >= 2 else 0
            self.tacho_channels_count = 2
            self.total_channels = self.main_channels + self.tacho_channels_count
            self.num_plots = self.total_channels
            self.sample_rate = sample_rate
            self.samples_per_channel = len(values[0]) if values else 0

            if not self.main_channels or len(values) < self.tacho_channels_count:
                self.log_and_set_status(f"Incorrect number of sublists: {len(values)}")
                return

            if not all(len(values[i]) == self.samples_per_channel for i in range(self.main_channels)):
                self.log_and_set_status(f"Channel data length mismatch")
                return

            tacho_freq_samples = len(values[self.main_channels]) if self.main_channels < len(values) else 0
            tacho_trigger_samples = len(values[self.main_channels + 1]) if self.main_channels + 1 < len(values) else 0
            if tacho_freq_samples != self.samples_per_channel or tacho_trigger_samples != self.samples_per_channel:
                self.log_and_set_status(f"Tacho data length mismatch")
                return

            if not self.fifo_data or len(self.fifo_data) != self.num_plots or not self.is_initialized:
                self.initialize_plots()

            current_time = time.time()
            time_step = 1.0 / sample_rate
            new_times = np.array([current_time - (self.samples_per_channel - 1 - i) * time_step for i in range(self.samples_per_channel)])

            for ch in range(self.main_channels):
                new_data = np.array(values[ch]) * self.scaling_factor
                self.fifo_data[ch] = np.roll(self.fifo_data[ch], -self.samples_per_channel)
                self.fifo_data[ch][-self.samples_per_channel:] = new_data
                self.needs_refresh[ch] = True

            if self.tacho_channels_count >= 1:
                self.fifo_data[self.main_channels] = np.roll(self.fifo_data[self.main_channels], -self.samples_per_channel)
                self.fifo_data[self.main_channels][-self.samples_per_channel:] = np.array(values[self.main_channels]) / 100
                self.needs_refresh[self.main_channels] = True

            if self.tacho_channels_count >= 2:
                self.fifo_data[self.main_channels + 1] = np.roll(self.fifo_data[self.main_channels + 1], -self.samples_per_channel)
                self.fifo_data[self.main_channels + 1][-self.samples_per_channel:] = np.array(values[self.main_channels + 1])
                self.needs_refresh[self.main_channels + 1] = True

            for ch in range(self.num_plots):
                self.fifo_times[ch] = np.roll(self.fifo_times[ch], -self.samples_per_channel)
                base_time = self.fifo_times[ch][-self.samples_per_channel - 1] if len(self.fifo_times[ch]) > self.samples_per_channel else 0
                self.fifo_times[ch][-self.samples_per_channel:] = base_time + np.array([(i + 1) * time_step for i in range(self.samples_per_channel)])

        except Exception as e:
            self.log_and_set_status(f"Error processing data: {str(e)}")

    def refresh_plots(self):
        if not self.is_initialized or self.fifo_window_samples is None or not self.plot_widgets or not self.plots or not self.fifo_data or not self.fifo_times:
            return

        for ch in range(self.num_plots):
            if not self.needs_refresh[ch]:
                continue

            times = self.fifo_times[ch]
            data = self.fifo_data[ch]
            if len(data) == 0 or len(times) == 0:
                continue

            if len(times) < self.fifo_window_samples:
                continue

            self.plots[ch].setData(times, data)
            self.plot_widgets[ch].setXRange(times[-self.fifo_window_samples], times[-1], padding=0)
            if ch < self.main_channels:
                self.plot_widgets[ch].enableAutoRange(axis='y')
            elif ch == self.main_channels:
                self.plot_widgets[ch].enableAutoRange(axis='y')
            else:
                self.plot_widgets[ch].setYRange(-0.5, 1.5, padding=0)

            if ch == self.num_plots - 1:
                if self.trigger_lines:
                    for line in self.trigger_lines:
                        if line:
                            self.plot_widgets[ch].removeItem(line)
                    self.trigger_lines = []

                trigger_indices = np.where(self.fifo_data[ch][-self.fifo_window_samples:] == 1)[0]
                for idx in trigger_indices:
                    if idx < len(times):
                        line = InfiniteLine(pos=times[idx], angle=90, movable=False, pen=mkPen('k', width=2, style=Qt.SolidLine))
                        self.plot_widgets[ch].addItem(line)
                        self.trigger_lines.append(line)

                self.needs_refresh[ch] = False

            if self.console:
                self.console.append_to_console(f"Time View ({self.model_name}): Refreshed {self.num_plots} plots")

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
        times = self.fifo_times[idx]
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

    def close(self):
        if self.refresh_timer:
            self.refresh_timer.stop()