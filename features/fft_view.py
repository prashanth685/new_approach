from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QGridLayout
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
import numpy as np
import logging
from scipy.fft import fft
from scipy.signal import get_window
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class FFTSettings:
    def __init__(self, project_id):
        self.project_id = project_id
        self.window_type = "Hamming"
        self.start_frequency = 10.0
        self.stop_frequency = 2000.0
        self.number_of_lines = 1600
        self.overlap_percentage = 0.0
        self.averaging_mode = "No Averaging"
        self.number_of_averages = 10
        self.weighting_mode = "Linear"
        self.linear_mode = "Continuous"
        self.updated_at = datetime.utcnow()

class FFTViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None, layout="vertical"):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.magnitude_plot_widget = None
        self.phase_plot_widget = None
        self.magnitude_plot_item = None
        self.phase_plot_item = None
        self.sample_rate = 1000  # Hz
        self.channel_index = None
        self.latest_data = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plot)
        self.update_interval = 200  # ms
        self.max_samples = 4096
        self.layout_type = layout
        self.mongo_client = MongoClient("mongodb://localhost:27017")
        self.project_id = None
        self.settings = FFTSettings(None)
        self.data_buffer = []  # For averaging
        self.settings_panel = None
        self.settings_button = None
        self.initUI()
        self.initialize_async()

    def initUI(self):
        self.widget = QWidget()
        main_layout = QVBoxLayout()
        self.widget.setLayout(main_layout)

        # Settings and channel selection
        top_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon("settings_icon.png"))  # Replace with your image path
        self.settings_button.clicked.connect(self.toggle_settings)
        top_layout.addWidget(self.settings_button)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # Settings panel
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QGridLayout()
        self.settings_panel.setLayout(settings_layout)

        # Settings fields
        settings_labels = [
            "Window Type", "Start Frequency (Hz)", "Stop Frequency (Hz)",
            "Number of Lines", "Overlap Percentage (%)", "Averaging Mode",
            "Number of Averages", "Weighting Mode", "Linear Mode"
        ]
        self.settings_widgets = {}

        # Window Type
        settings_layout.addWidget(QLabel("Window Type"), 0, 0)
        window_combo = QComboBox()
        window_combo.addItems(["Hamming", "Hanning", "Blackman", "Flat-top", "None"])
        window_combo.setCurrentText(self.settings.window_type)
        settings_layout.addWidget(window_combo, 0, 1)
        self.settings_widgets["WindowType"] = window_combo

        # Start Frequency
        settings_layout.addWidget(QLabel("Start Frequency (Hz)"), 1, 0)
        start_freq_edit = QLineEdit(str(self.settings.start_frequency))
        start_freq_edit.setValidator(QDoubleValidator(0.0, 10000.0, 2))
        settings_layout.addWidget(start_freq_edit, 1, 1)
        self.settings_widgets["StartFrequency"] = start_freq_edit

        # Stop Frequency
        settings_layout.addWidget(QLabel("Stop Frequency (Hz)"), 2, 0)
        stop_freq_edit = QLineEdit(str(self.settings.stop_frequency))
        stop_freq_edit.setValidator(QDoubleValidator(0.0, 10000.0, 2))
        settings_layout.addWidget(stop_freq_edit, 2, 1)
        self.settings_widgets["StopFrequency"] = stop_freq_edit

        # Number of Lines
        settings_layout.addWidget(QLabel("Number of Lines"), 3, 0)
        lines_edit = QLineEdit(str(self.settings.number_of_lines))
        lines_edit.setValidator(QIntValidator(100, 3200))
        settings_layout.addWidget(lines_edit, 3, 1)
        self.settings_widgets["NumberOfLines"] = lines_edit

        # Overlap Percentage
        settings_layout.addWidget(QLabel("Overlap Percentage (%)"), 4, 0)
        overlap_edit = QLineEdit(str(self.settings.overlap_percentage))
        overlap_edit.setValidator(QDoubleValidator(0.0, 99.9, 2))
        settings_layout.addWidget(overlap_edit, 4, 1)
        self.settings_widgets["OverlapPercentage"] = overlap_edit

        # Averaging Mode
        settings_layout.addWidget(QLabel("Averaging Mode"), 5, 0)
        avg_mode_combo = QComboBox()
        avg_mode_combo.addItems(["No Averaging", "Linear", "Exponential"])
        avg_mode_combo.setCurrentText(self.settings.averaging_mode)
        settings_layout.addWidget(avg_mode_combo, 5, 1)
        self.settings_widgets["AveragingMode"] = avg_mode_combo

        # Number of Averages
        settings_layout.addWidget(QLabel("Number of Averages"), 6, 0)
        avg_num_edit = QLineEdit(str(self.settings.number_of_averages))
        avg_num_edit.setValidator(QIntValidator(1, 100))
        settings_layout.addWidget(avg_num_edit, 6, 1)
        self.settings_widgets["NumberOfAverages"] = avg_num_edit

        # Weighting Mode
        settings_layout.addWidget(QLabel("Weighting Mode"), 7, 0)
        weight_combo = QComboBox()
        weight_combo.addItems(["Linear", "A-Weighting", "B-Weighting", "C-Weighting"])
        weight_combo.setCurrentText(self.settings.weighting_mode)
        settings_layout.addWidget(weight_combo, 7, 1)
        self.settings_widgets["WeightingMode"] = weight_combo

        # Linear Mode
        settings_layout.addWidget(QLabel("Linear Mode"), 8, 0)
        linear_combo = QComboBox()
        linear_combo.addItems(["Continuous", "Peak Hold", "Time Synchronous"])
        linear_combo.setCurrentText(self.settings.linear_mode)
        settings_layout.addWidget(linear_combo, 8, 1)
        self.settings_widgets["LinearMode"] = linear_combo

        # Save and Close buttons
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_settings)
        settings_layout.addWidget(save_button, 9, 0)
        settings_layout.addWidget(close_button, 9, 1)

        main_layout.addWidget(self.settings_panel)

        # Plot layout
        plot_layout = QHBoxLayout() if self.layout_type == "horizontal" else QVBoxLayout()
        pg.setConfigOptions(antialias=False)

        # Magnitude Plot
        self.magnitude_plot_widget = pg.PlotWidget()
        self.magnitude_plot_widget.setBackground("white")
        self.magnitude_plot_widget.setTitle("Magnitude Spectrum", color="black", size="12pt")
        self.magnitude_plot_widget.setLabel('left', 'Amplitude', color='#000000')
        self.magnitude_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#000000')
        self.magnitude_plot_widget.showGrid(x=True, y=True)
        self.magnitude_plot_item = self.magnitude_plot_widget.plot(pen=pg.mkPen(color='#4a90e2', width=2))
        plot_layout.addWidget(self.magnitude_plot_widget)

        # Phase Plot
        self.phase_plot_widget = pg.PlotWidget()
        self.phase_plot_widget.setBackground("white")
        self.phase_plot_widget.setTitle("Phase Spectrum", color="black", size="12pt")
        self.phase_plot_widget.setLabel('left', 'Phase (degrees)', color='#000000')
        self.phase_plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#000000')
        self.phase_plot_widget.showGrid(x=True, y=True)
        self.phase_plot_item = self.phase_plot_widget.plot(pen=pg.mkPen(color='#e74c3c', width=2))
        plot_layout.addWidget(self.phase_plot_widget)

        main_layout.addLayout(plot_layout)
        self.update_timer.start(self.update_interval)

        if self.console:
            self.console.append_to_console(f"Initialized FFTViewFeature with channel: {self.channel}, model: {self.model_name}")

    def initialize_async(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            projects_collection = database.get_collection("projects")
            project = projects_collection.find_one({"project_name": self.project_name, "email": self.db.email})
            if not project:
                self.log_and_set_status(f"Project {self.project_name} not found for email {self.db.email}.")
                return

            self.project_id = project["_id"]
            model = next((m for m in project["models"] if m["name"] == self.model_name), None)
            if not model:
                self.log_and_set_status(f"Model {self.model_name} not found in project {self.project_name}.")
                return

            channels = model.get("channels", [])
            for idx, ch in enumerate(channels):
                if ch.get("channelName") == self.channel or model.get("tagName") == self.channel:
                    self.channel_index = idx
                    break
            else:
                self.log_and_set_status(f"Channel {self.channel} not found for model {self.model_name}.")
                self.channel_index = 0

            self.load_settings_from_database()
            if self.console:
                self.console.append_to_console(f"Initialized FFTViewFeature with project_id: {self.project_id}, channel_index: {self.channel_index}")
        except Exception as e:
            self.log_and_set_status(f"Error initializing FFTViewFeature: {str(e)}")

    def load_settings_from_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("FFTSettings")
            setting = settings_collection.find_one({"projectId": self.project_id}, sort=[("updatedAt", -1)])
            
            if setting:
                self.settings.window_type = setting.get("windowType", "Hamming")
                self.settings.start_frequency = float(setting.get("startFrequency", 10.0))
                self.settings.stop_frequency = float(setting.get("stopFrequency", 2000.0))
                self.settings.number_of_lines = int(setting.get("numberOfLines", 1600))
                self.settings.overlap_percentage = float(setting.get("overlapPercentage", 0.0))
                self.settings.averaging_mode = setting.get("averagingMode", "No Averaging")
                self.settings.number_of_averages = int(setting.get("numberOfAverages", 10))
                self.settings.weighting_mode = setting.get("weightingMode", "Linear")
                self.settings.linear_mode = setting.get("linearMode", "Continuous")
                
                self.settings_widgets["WindowType"].setCurrentText(self.settings.window_type)
                self.settings_widgets["StartFrequency"].setText(str(self.settings.start_frequency))
                self.settings_widgets["StopFrequency"].setText(str(self.settings.stop_frequency))
                self.settings_widgets["NumberOfLines"].setText(str(self.settings.number_of_lines))
                self.settings_widgets["OverlapPercentage"].setText(str(self.settings.overlap_percentage))
                self.settings_widgets["AveragingMode"].setCurrentText(self.settings.averaging_mode)
                self.settings_widgets["NumberOfAverages"].setText(str(self.settings.number_of_averages))
                self.settings_widgets["WeightingMode"].setCurrentText(self.settings.weighting_mode)
                self.settings_widgets["LinearMode"].setCurrentText(self.settings.linear_mode)
                
                if self.console:
                    self.console.append_to_console(f"Loaded FFT settings for project ID: {self.project_id}")
            else:
                if self.console:
                    self.console.append_to_console(f"No FFT settings found for project ID: {self.project_id}. Using defaults.")
        except Exception as e:
            self.log_and_set_status(f"Error loading FFT settings: {str(e)}")

    def save_settings_to_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("FFTSettings")
            setting = {
                "projectId": self.project_id,
                "windowType": self.settings.window_type,
                "startFrequency": self.settings.start_frequency,
                "stopFrequency": self.settings.stop_frequency,
                "numberOfLines": self.settings.number_of_lines,
                "overlapPercentage": self.settings.overlap_percentage,
                "averagingMode": self.settings.averaging_mode,
                "numberOfAverages": self.settings.number_of_averages,
                "weightingMode": self.settings.weighting_mode,
                "linearMode": self.settings.linear_mode,
                "updatedAt": datetime.utcnow()
            }
            settings_collection.update_one(
                {"projectId": self.project_id},
                {"$set": setting},
                upsert=True
            )
            if self.console:
                self.console.append_to_console(f"Saved FFT settings for project ID: {self.project_id}")
        except Exception as e:
            self.log_and_set_status(f"Error saving FFT settings: {str(e)}")

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.settings_button.setVisible(not self.settings_panel.isVisible())

    def save_settings(self):
        try:
            self.settings.window_type = self.settings_widgets["WindowType"].currentText()
            self.settings.start_frequency = float(self.settings_widgets["StartFrequency"].text() or 10.0)
            self.settings.stop_frequency = float(self.settings_widgets["StopFrequency"].text() or 2000.0)
            self.settings.number_of_lines = int(self.settings_widgets["NumberOfLines"].text() or 1600)
            self.settings.overlap_percentage = float(self.settings_widgets["OverlapPercentage"].text() or 0.0)
            self.settings.averaging_mode = self.settings_widgets["AveragingMode"].currentText()
            self.settings.number_of_averages = int(self.settings_widgets["NumberOfAverages"].text() or 10)
            self.settings.weighting_mode = self.settings_widgets["WeightingMode"].currentText()
            self.settings.linear_mode = self.settings_widgets["LinearMode"].currentText()

            # Validate settings
            if self.settings.start_frequency >= self.settings.stop_frequency:
                self.settings.start_frequency = 10.0
                self.settings.stop_frequency = 2000.0
                self.settings_widgets["StartFrequency"].setText(str(self.settings.start_frequency))
                self.settings_widgets["StopFrequency"].setText(str(self.settings.stop_frequency))
                self.log_and_set_status("Invalid frequency range, reset to defaults.")
            if self.settings.number_of_lines < 100 or self.settings.number_of_lines > 3200:
                self.settings.number_of_lines = 1600
                self.settings_widgets["NumberOfLines"].setText(str(self.settings.number_of_lines))
                self.log_and_set_status("Invalid number of lines, reset to default.")
            if self.settings.overlap_percentage < 0 or self.settings.overlap_percentage > 99.9:
                self.settings.overlap_percentage = 0.0
                self.settings_widgets["OverlapPercentage"].setText(str(self.settings.overlap_percentage))
                self.log_and_set_status("Invalid overlap percentage, reset to default.")
            if self.settings.number_of_averages < 1 or self.settings.number_of_averages > 100:
                self.settings.number_of_averages = 10
                self.settings_widgets["NumberOfAverages"].setText(str(self.settings.number_of_averages))
                self.log_and_set_status("Invalid number of averages, reset to default.")

            self.save_settings_to_database()
            self.settings_panel.setVisible(False)
            self.settings_button.setVisible(True)
            if self.console:
                self.console.append_to_console("FFT settings updated and saved.")
            self.update_plot()  # Apply new settings immediately
        except Exception as e:
            self.log_and_set_status(f"Error saving FFT settings: {str(e)}")

    def close_settings(self):
        self.settings_widgets["WindowType"].setCurrentText(self.settings.window_type)
        self.settings_widgets["StartFrequency"].setText(str(self.settings.start_frequency))
        self.settings_widgets["StopFrequency"].setText(str(self.settings.stop_frequency))
        self.settings_widgets["NumberOfLines"].setText(str(self.settings.number_of_lines))
        self.settings_widgets["OverlapPercentage"].setText(str(self.settings.overlap_percentage))
        self.settings_widgets["AveragingMode"].setCurrentText(self.settings.averaging_mode)
        self.settings_widgets["NumberOfAverages"].setText(str(self.settings.number_of_averages))
        self.settings_widgets["WeightingMode"].setCurrentText(self.settings.weighting_mode)
        self.settings_widgets["LinearMode"].setCurrentText(self.settings.linear_mode)
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)

    def get_widget(self):
        return self.widget

    def cache_channel_index(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            if project_data and "models" in project_data:
                for model in project_data["models"]:
                    if model.get("name") == self.model_name:
                        channels = model.get("channels", [])
                        for idx, ch in enumerate(channels):
                            if ch.get("channelName") == self.channel or model.get("tagName") == self.channel:
                                self.channel_index = idx
                                if self.console:
                                    self.console.append_to_console(f"Cached channel index: {self.channel_index} for channel {self.channel}")
                                return
            self.channel_index = 0
            self.log_and_set_status(f"Channel {self.channel} not found for model {self.model_name}, defaulting to index 0")
        except Exception as e:
            self.log_and_set_status(f"Error caching channel index: {str(e)}")
            self.channel_index = 0

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.model_name != model_name or self.channel_index is None:
            if self.console:
                self.console.append_to_console(
                    f"FFT View: Skipped data - model_name={model_name} (expected {self.model_name}), "
                    f"channel_index={self.channel_index}"
                )
            return

        try:
            if self.channel_index >= len(values):
                self.log_and_set_status(f"Channel index {self.channel_index} out of range for {len(values)} channels")
                return

            self.sample_rate = sample_rate if sample_rate > 0 else 1000
            scaling_factor = 3.3 / 65535.0
            raw_data = np.array(values[self.channel_index][:self.max_samples], dtype=np.float32)
            self.latest_data = raw_data * scaling_factor
            self.data_buffer.append(self.latest_data.copy())

            # Trim buffer to number_of_averages
            if len(self.data_buffer) > self.settings.number_of_averages:
                self.data_buffer = self.data_buffer[-self.settings.number_of_averages:]

            if self.console:
                self.console.append_to_console(
                    f"FFT View: Received data for channel {self.channel}, "
                    f"samples={len(self.latest_data)}, Fs={self.sample_rate}Hz"
                )
        except Exception as e:
            self.log_and_set_status(f"Error in on_data_received: {str(e)}")

    def update_plot(self):
        if not self.data_buffer:
            return

        try:
            # Prepare data
            data = self.data_buffer[-1] if self.settings.averaging_mode == "No Averaging" else np.mean(self.data_buffer, axis=0)
            n = len(data)
            if n < 2:
                self.log_and_set_status(f"Insufficient data length: {n}")
                return

            # Apply window
            window_name = self.settings.window_type.lower() if self.settings.window_type != "None" else "rectangular"
            window = get_window(window_name, n)
            windowed_data = data * window

            # Compute FFT
            target_length = 2 ** int(np.ceil(np.log2(n)))
            padded_data = np.zeros(target_length)
            padded_data[:n] = windowed_data
            fft_result = fft(padded_data)
            half = target_length // 2

            # Frequency axis
            frequencies = np.linspace(0, self.sample_rate / 2, half)
            freq_mask = (frequencies >= self.settings.start_frequency) & (frequencies <= self.settings.stop_frequency)
            filtered_frequencies = frequencies[freq_mask]

            # Magnitude and phase
            magnitudes = np.abs(fft_result[:half]) / target_length
            phases = np.degrees(np.angle(fft_result[:half]))
            filtered_magnitudes = magnitudes[freq_mask]
            filtered_phases = phases[freq_mask]

            # Apply weighting
            if self.settings.weighting_mode != "Linear":
                # Simplified weighting (A, B, C-weighting curves are approximated)
                weights = np.ones_like(filtered_frequencies)
                if self.settings.weighting_mode == "A-Weighting":
                    weights = 1.0 / (1.0 + (filtered_frequencies / 1000) ** 2)  # Simplified A-weighting
                elif self.settings.weighting_mode == "B-Weighting":
                    weights = 1.0 / (1.0 + (filtered_frequencies / 500) ** 2)  # Simplified B-weighting
                elif self.settings.weighting_mode == "C-Weighting":
                    weights = 1.0 / (1.0 + (filtered_frequencies / 200) ** 2)  # Simplified C-weighting
                filtered_magnitudes *= weights

            # Apply averaging
            if self.settings.averaging_mode == "Linear" and len(self.data_buffer) > 1:
                avg_magnitudes = np.mean([np.abs(fft(np.zeros(target_length)[:n] + d * window)[:half]) / target_length for d in self.data_buffer], axis=0)
                avg_phases = np.mean([np.degrees(np.angle(fft(np.zeros(target_length)[:n] + d * window)[:half])) for d in self.data_buffer], axis=0)
                filtered_magnitudes = avg_magnitudes[freq_mask]
                filtered_phases = avg_phases[freq_mask]
            elif self.settings.averaging_mode == "Exponential" and len(self.data_buffer) > 1:
                alpha = 2.0 / (self.settings.number_of_averages + 1)
                avg_magnitudes = np.zeros(half)
                avg_phases = np.zeros(half)
                for d in self.data_buffer:
                    fft_d = fft(np.zeros(target_length)[:n] + d * window)
                    avg_magnitudes = alpha * (np.abs(fft_d[:half]) / target_length) + (1 - alpha) * avg_magnitudes
                    avg_phases = alpha * np.degrees(np.angle(fft_d[:half])) + (1 - alpha) * avg_phases
                filtered_magnitudes = avg_magnitudes[freq_mask]
                filtered_phases = avg_phases[freq_mask]

            # Adjust for number of lines
            if len(filtered_frequencies) > self.settings.number_of_lines:
                indices = np.linspace(0, len(filtered_frequencies) - 1, self.settings.number_of_lines, dtype=int)
                filtered_frequencies = filtered_frequencies[indices]
                filtered_magnitudes = filtered_magnitudes[indices]
                filtered_phases = filtered_phases[indices]

            # Update plots
            self.magnitude_plot_item.setData(filtered_frequencies, filtered_magnitudes)
            self.phase_plot_item.setData(filtered_frequencies, filtered_phases)
            self.magnitude_plot_widget.setXRange(self.settings.start_frequency, self.settings.stop_frequency)
            self.phase_plot_widget.setXRange(self.settings.start_frequency, self.settings.stop_frequency)

            if self.console:
                self.console.append_to_console(
                    f"FFT Updated: Samples={n}, FFT Size={target_length}, "
                    f"Fs={self.sample_rate}Hz, Lines={len(filtered_frequencies)}, "
                    f"Range={self.settings.start_frequency}-{self.settings.stop_frequency}Hz"
                )
        except Exception as e:
            self.log_and_set_status(f"Error updating FFT: {str(e)}")

    def log_and_set_status(self, message):
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)

    def close(self):
        self.update_timer.stop()
        self.mongo_client.close()