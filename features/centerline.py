
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CenterLineFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, scaling_multiplier=1.0):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel  
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.plot_item = None
        self.mean_line = None
        self.ucl_line = None
        self.lcl_line = None
        self.scaling_factor = (3.3 / 65535.0)  # Adjusted scaling factor
        self.sample_rate = 4096  # Default sample rate
        self.channel_index = None
        self.latest_data = None
        self.max_samples = 4096
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_interval = 200  # ms
        self.initUI()
        self.cache_channel_index()
        logging.debug(f"Initialized CenterLineFeature with project_name: {project_name}, model_name: {model_name}, channel: {channel}, scaling_factor: {self.scaling_factor}")

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        label = QLabel(f"Centerline Plot for Model: {self.model_name or 'Unknown'}, Channel: {self.channel or 'Unknown'}")
        label.setStyleSheet("color: #ecf0f1; font-size: 16px; padding: 10px;")
        main_layout.addWidget(label)

        # Plot setup using pyqtgraph
        pg.setConfigOptions(antialias=False)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("white")
        self.plot_widget.setTitle("Centerline Control Chart", color="black", size="12pt")
        self.plot_widget.setLabel('left', 'Voltage (V)', color='#000000')
        self.plot_widget.setLabel('bottom', 'Time (s)', color='#000000')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_item = self.plot_widget.plot(pen=pg.mkPen(color='#4a90e2', width=2), name="Channel Data")
        # Initialize horizontal lines for mean, UCL, and LCL
        self.mean_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(color='#28a745', style=pg.QtCore.Qt.DashLine, width=2), label="Centerline")
        self.ucl_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(color='#e74c3c', style=pg.QtCore.Qt.DashLine, width=2), label="UCL")
        self.lcl_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(color='#e74c3c', style=pg.QtCore.Qt.DashLine, width=2), label="LCL")
        self.plot_widget.addItem(self.mean_line)
        self.plot_widget.addItem(self.ucl_line)
        self.plot_widget.addItem(self.lcl_line)
        # Enable legend
        self.plot_widget.addLegend()
        main_layout.addWidget(self.plot_widget)

        self.update_timer.start(self.update_interval)

    def cache_channel_index(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data and self.model_name in project_data["models"]:
                channels = project_data["models"][self.model_name].get("channels", [])
                for idx, ch in enumerate(channels):
                    if ch.get("tag_name") == self.channel or ch.get("channel_name") == self.channel:
                        self.channel_index = idx
                        return
            # Default to channel 0 if not found
            self.channel_index = 0
            logging.debug(f"Channel index not found in database, defaulting to {self.channel_index}")
        except Exception as e:
            logging.error(f"Error caching channel index: {e}")
            if self.console:
                self.console.append_to_console(f"Error caching channel index: {e}")
            self.channel_index = 0

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        # Validate model match
        if self.model_name != model_name:
            if self.console:
                self.console.append_to_console(f"Ignoring data for model {model_name}, expected {self.model_name}")
            logging.debug(f"Ignoring data for model {model_name}, expected {self.model_name}")
            return

        if self.console:
            self.console.append_to_console(
                f"Centerline View ({self.model_name} - {self.channel}): Received data for {tag_name} - {len(values)} channels"
            )
            logging.debug(f"Received data for {tag_name}: {len(values)} channels, sample_rate={sample_rate}")

        # Validate inputs
        if self.channel is None:
            if self.console:
                self.console.append_to_console("No channel (tag_name) selected for plotting")
            logging.error("No channel (tag_name) selected for plotting")
            return

        # Ensure the tag_name matches
        if self.channel != tag_name:
            if self.console:
                self.console.append_to_console(f"Ignoring data for tag {tag_name}, expected {self.channel}")
            logging.debug(f"Ignoring data for tag {tag_name}, expected {self.channel}")
            return

        # Since tag_name matches, use the first main channel (as done previously)
        channel_idx = 0  # Default to the first main channel
        num_channels = 4  # From mqtthandler.py and publish.py
        num_tacho_channels = 2

        # Validate channel data
        if not values or len(values) < (num_channels + num_tacho_channels):
            if self.console:
                self.console.append_to_console(f"Invalid data: expected at least {num_channels + num_tacho_channels} channels, got {len(values)}")
            logging.warning(f"Invalid data: expected at least {num_channels + num_tacho_channels} channels, got {len(values)}")
            return

        try:
            if channel_idx >= len(values):
                if self.console:
                    self.console.append_to_console(f"Channel index {channel_idx} out of range for {len(values)} channels")
                logging.warning(f"Channel index {channel_idx} out of range for {len(values)} channels")
                return

            self.sample_rate = sample_rate if sample_rate > 0 else 4096
            raw_data = np.array(values[channel_idx][:self.max_samples], dtype=np.float32)
            self.latest_data = raw_data
            logging.debug(f"Channel {channel_idx} data (first 5 samples): {self.latest_data[:5]}")
        except Exception as e:
            logging.error(f"Error in on_data_received: {e}")
            if self.console:
                self.console.append_to_console(f"Error in Centerline View: {e}")

    def update_plot(self):
        if self.latest_data is None:
            return

        try:
            # Convert to voltage with adjusted scaling factor
            voltage_data = [(v - 32768) * self.scaling_factor for v in self.latest_data]
            voltage_data = np.array(voltage_data, dtype=np.float32)
            n = len(voltage_data)
            if n < 2:
                if self.console:
                    self.console.append_to_console(f"Data too short for plotting: {n} samples")
                logging.warning(f"Data too short for plotting: {n} samples")
                return

            # Calculate centerline (mean) and control limits (same as original)
            mean = np.mean(voltage_data)
            std = np.std(voltage_data)
            ucl = mean + 3 * std
            lcl = mean - 3 * std

            # Generate time axis
            time = np.array([i / self.sample_rate for i in range(n)])

            # Update the plot
            self.plot_item.setData(time, voltage_data)
            self.mean_line.setValue(mean)
            self.ucl_line.setValue(ucl)
            self.lcl_line.setValue(lcl)

            if self.console:
                self.console.append_to_console(
                    f"Centerline Updated: Samples={n}, Mean={mean:.2f} V, UCL={ucl:.2f} V, LCL={lcl:.2f} V, Fs={self.sample_rate}Hz"
                )
                logging.debug(f"Plotted channel {self.channel_index}: Mean={mean:.2f} V, UCL={ucl:.2f} V, LCL={lcl:.2f} V")
        except Exception as e:
            logging.error(f"Error updating Centerline plot: {e}")
            if self.console:
                self.console.append_to_console(f"Error updating Centerline plot: {e}")

    def close(self):
        self.update_timer.stop()