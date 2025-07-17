# from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QSplitter, QPushButton, QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel
# from PyQt5.QtCore import Qt
# from PyQt5.QtGui import QIcon
# import numpy as np
# import pyqtgraph as pg
# from datetime import datetime
# from pymongo import MongoClient
# from bson.objectid import ObjectId
# import scipy.signal as signal
# import logging

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# class TabularViewSettings:
#     def __init__(self, project_id):
#         self.project_id = project_id
#         self.bandpass_selection = "None"
#         self.rpm_visible = True
#         self.gap_visible = True
#         self.channel_name_visible = True
#         self.datetime_visible = True
#         self.direct_visible = True
#         self.one_x_amp_visible = True
#         self.one_x_phase_visible = True
#         self.two_x_amp_visible = True
#         self.two_x_phase_visible = True
#         self.nx_amp_visible = True
#         self.nx_phase_visible = True
#         self.vpp_visible = True
#         self.vrms_visible = True
#         self.twiddle_factor_visible = True
#         self.updated_at = datetime.utcnow()

# class TabularViewFeature:
#     def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
#         self.parent = parent
#         self.db = db
#         self.project_name = project_name
#         self.channel = channel
#         self.model_name = model_name
#         self.console = console
#         self.widget = None
#         self.data = None
#         self.sample_rate = 4096
#         self.num_channels = 1  # Default, updated in initialize_async
#         self.channel_names = ["Channel 1"]  # Default
#         self.channel_properties = {}
#         self.project_id = None
#         self.raw_data = [np.zeros(4096)]
#         self.low_pass_data = [np.zeros(4096)]
#         self.high_pass_data = [np.zeros(4096)]
#         self.band_pass_data = [np.zeros(4096)]
#         self.time_points = np.arange(4096) / self.sample_rate
#         self.band_pass_peak_to_peak_history = [[]]
#         self.band_pass_peak_to_peak_times = [[]]
#         self.average_frequency = [0.0]
#         self.band_pass_peak_to_peak = [0.0]
#         self.start_time = datetime.now()
#         self.column_visibility = {
#             "RPM": True,
#             "Gap": True,
#             "Channel Name": True,
#             "DateTime": True,
#             "Direct": True,
#             "1x Amp": True,
#             "1x Phase": True,
#             "2x Amp": True,
#             "2x Phase": True,
#             "nx Amp": True,
#             "nx Phase": True,
#             "Vpp": True,
#             "Vrms": True,
#             "Twiddle Factor": True
#         }
#         self.bandpass_selection = "None"
#         self.mongo_client = MongoClient("mongodb://localhost:27017")
#         self.plot_initialized = False
#         self.table = None
#         self.plot_widgets = []
#         self.plots = []
#         self.selected_channel_idx = 0
#         self.tag_name = ""
#         self.channel_selector = None
#         self.initUI()
#         self.initialize_async()

#     def initUI(self):
#         pg.setConfigOption('background', 'w')
#         pg.setConfigOption('foreground', 'k')

#         self.widget = QWidget()
#         layout = QVBoxLayout()
#         self.widget.setLayout(layout)

#         # Settings and channel selection
#         top_layout = QHBoxLayout()
#         self.settings_button = QPushButton("Settings")
#         self.settings_button.setIcon(QIcon("settings_icon.png"))  # Replace with your image path
#         self.settings_button.clicked.connect(self.toggle_settings)
#         top_layout.addWidget(self.settings_button)

#         top_layout.addWidget(QLabel("Select Channel for Plots:"))
#         self.channel_selector = QComboBox()
#         self.channel_selector.addItem("Select Channel")
#         self.channel_selector.addItems(self.channel_names)
#         self.channel_selector.currentIndexChanged.connect(self.update_selected_channel)
#         top_layout.addWidget(self.channel_selector)
#         top_layout.addStretch()
#         layout.addLayout(top_layout)

#         # Settings panel
#         self.settings_panel = QWidget()
#         self.settings_panel.setVisible(False)
#         settings_layout = QGridLayout()
#         self.settings_panel.setLayout(settings_layout)

#         # Bandpass selection
#         self.bandpass_combo = QComboBox()
#         self.bandpass_combo.addItems(["None", "50-200 Hz", "100-300 Hz"])
#         settings_layout.addWidget(self.bandpass_combo, 0, 0, 1, 2)

#         # Checkboxes for column visibility
#         headers = [
#             "RPM", "Gap", "Channel Name", "DateTime", "Direct",
#             "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
#             "Vpp", "Vrms", "Twiddle Factor"
#         ]
#         self.checkbox_dict = {}
#         for i, header in enumerate(headers):
#             cb = QCheckBox(header)
#             cb.setChecked(True)
#             self.checkbox_dict[header] = cb
#             settings_layout.addWidget(cb, (i // 2) + 1, i % 2)

#         # Save and Close buttons
#         self.save_settings_button = QPushButton("Save")
#         self.save_settings_button.clicked.connect(self.save_settings)
#         self.close_settings_button = QPushButton("Close")
#         self.close_settings_button.clicked.connect(self.close_settings)
#         settings_layout.addWidget(self.save_settings_button, len(headers) // 2 + 1, 0)
#         settings_layout.addWidget(self.close_settings_button, len(headers) // 2 + 1, 1)

#         layout.addWidget(self.settings_panel)

#         # Splitter for table and plots
#         splitter = QSplitter(Qt.Vertical)
#         layout.addWidget(splitter)

#         # Table setup
#         self.table = QTableWidget()
#         self.table.setRowCount(self.num_channels)
#         self.table.setColumnCount(len(headers))
#         self.table.setHorizontalHeaderLabels(headers)
#         self.table.setFixedHeight(100 * self.num_channels)  # Adjust height for rows
#         splitter.addWidget(self.table)

#         # Initialize table with default values
#         default_data = {
#             "Channel Name": "N/A",
#             "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "RPM": "0.00",
#             "Gap": "0.00",
#             "Direct": "0.00",
#             "1x Amp": "0.00",
#             "1x Phase": "0.00",
#             "2x Amp": "0.00",
#             "2x Phase": "0.00",
#             "nx Amp": "0.00",
#             "nx Phase": "0.00",
#             "Vpp": "0.00",
#             "Vrms": "0.00",
#             "Twiddle Factor": "0.00"
#         }
#         for row in range(self.num_channels):
#             default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
#             for col, header in enumerate(headers):
#                 self.table.setItem(row, col, QTableWidgetItem(default_data[header]))

#         # Plot widgets
#         plot_titles = [
#             "Raw Data",
#             "Low-Pass Filtered Data (100 Hz Cutoff)",
#             "High-Pass Filtered Data (200 Hz Cutoff)",
#             "Band-Pass Filtered Data (50-200 Hz)",
#             "Bandpass Average Peak-to-Peak Over Frequency"
#         ]
#         self.plot_widgets = []
#         self.plots = []
#         for i in range(5):
#             plot_widget = pg.PlotWidget(title=plot_titles[i])
#             plot_widget.showGrid(x=True, y=True)
#             plot_widget.setLabel('bottom', 'Time (s)' if i < 4 else 'Frequency (Hz)')
#             plot_widget.setLabel('left', 'Amplitude' if i < 4 else 'Peak-to-Peak Value')
#             splitter.addWidget(plot_widget)
#             self.plot_widgets.append(plot_widget)
#             plot = plot_widget.plot(pen='b')
#             plot.setData(np.array([0]), np.array([0]))  # Initialize empty plot
#             self.plots.append(plot)

#         splitter.setSizes([100 * self.num_channels, 600])

#         if self.console:
#             self.console.append_to_console(f"Initialized UI with {self.num_channels} channels: {self.channel_names}")

#     def get_widget(self):
#         return self.widget

#     def update_selected_channel(self, index):
#         if index > 0:  # Skip "Select Channel" option
#             self.selected_channel_idx = index - 1
#             self.update_plots()
#             if self.console:
#                 self.console.append_to_console(f"Selected channel for plots: {self.channel_names[self.selected_channel_idx]}")
#         else:
#             self.selected_channel_idx = 0
#             self.update_plots()
#             if self.console:
#                 self.console.append_to_console("No valid channel selected for plots, defaulting to first channel.")

#     def initialize_async(self):
#         try:
#             database = self.mongo_client.get_database("changed_db")
#             projects_collection = database.get_collection("projects")
#             project = projects_collection.find_one({"project_name": self.project_name, "email": self.db.email})
#             if not project:
#                 self.log_and_set_status(f"Project {self.project_name} not found for email {self.db.email}. Using default channel.")
#                 self.channel_names = ["Channel 1"]
#                 self.num_channels = 1
#                 self.table.setRowCount(1)
#                 self.channel_selector.clear()
#                 self.channel_selector.addItem("Select Channel")
#                 self.channel_selector.addItems(self.channel_names)
#                 self.channel_selector.setCurrentIndex(1)
#                 self.initialize_data_arrays()
#                 self.update_table_defaults()
#                 self.update_plots()
#                 return

#             self.project_id = project["_id"]
#             model = next((m for m in project["models"] if m["name"] == self.model_name), None)
#             if not model or not model.get("channels"):
#                 self.log_and_set_status(f"Model {self.model_name} or channels not found in project {self.project_name}. Using default channel.")
#                 self.channel_names = ["Channel 1"]
#                 self.num_channels = 1
#                 self.table.setRowCount(1)
#                 self.channel_selector.clear()
#                 self.channel_selector.addItem("Select Channel")
#                 self.channel_selector.addItems(self.channel_names)
#                 self.channel_selector.setCurrentIndex(1)
#                 self.initialize_data_arrays()
#                 self.update_table_defaults()
#                 self.update_plots()
#                 return

#             self.channel_names = [c.get("channelName", f"Channel {i+1}") for i, c in enumerate(model["channels"])]
#             self.num_channels = len(self.channel_names)
#             if not self.channel_names:
#                 self.log_and_set_status("No channels found in model. Using default channel.")
#                 self.channel_names = ["Channel 1"]
#                 self.num_channels = 1

#             # Update table and selector
#             self.table.setRowCount(self.num_channels)
#             self.channel_selector.clear()
#             self.channel_selector.addItem("Select Channel")
#             self.channel_selector.addItems(self.channel_names)
#             if self.channel in self.channel_names:
#                 self.selected_channel_idx = self.channel_names.index(self.channel)
#                 self.channel_selector.setCurrentIndex(self.selected_channel_idx + 1)
#             else:
#                 self.log_and_set_status(f"Selected channel {self.channel} not found. Defaulting to first channel.")
#                 self.selected_channel_idx = 0
#                 self.channel_selector.setCurrentIndex(1 if self.channel_names else 0)

#             # Initialize data arrays
#             self.initialize_data_arrays()

#             # Populate channel properties
#             for channel in model["channels"]:
#                 channel_name = channel.get("channelName", "Unknown")
#                 correction_value = float(channel.get("CorrectionValue", "1.0")) if channel.get("CorrectionValue") else 1.0
#                 gain = float(channel.get("Gain", "1.0")) if channel.get("Gain") else 1.0
#                 sensitivity = float(channel.get("Sensitivity", "1.0")) if channel.get("Sensitivity") and float(channel.get("Sensitivity")) != 0 else 1.0
#                 self.channel_properties[channel_name] = {
#                     "Unit": channel.get("Unit", "mil").lower(),
#                     "CorrectionValue": correction_value,
#                     "Gain": gain,
#                     "Sensitivity": sensitivity
#                 }

#             self.tag_name = model.get("tagName", "")
#             if self.console:
#                 self.console.append_to_console(f"Initialized with TagName: {self.tag_name}, Model: {self.model_name}, Channels: {self.channel_names}, Project ID: {self.project_id}")

#             self.update_table_defaults()
#             self.load_settings_from_database()
#             self.update_plots()  # Initial plot update
#         except Exception as ex:
#             self.log_and_set_status(f"Error initializing TabularView: {str(ex)}")
#             self.channel_names = ["Channel 1"]
#             self.num_channels = 1
#             self.table.setRowCount(1)
#             self.channel_selector.clear()
#             self.channel_selector.addItem("Select Channel")
#             self.channel_selector.addItems(self.channel_names)
#             self.channel_selector.setCurrentIndex(1)
#             self.initialize_data_arrays()
#             self.update_table_defaults()
#             self.update_plots()

#     def initialize_data_arrays(self):
#         self.raw_data = [np.zeros(4096) for _ in range(self.num_channels)]
#         self.low_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
#         self.high_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
#         self.band_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
#         self.band_pass_peak_to_peak_history = [[] for _ in range(self.num_channels)]
#         self.band_pass_peak_to_peak_times = [[] for _ in range(self.num_channels)]
#         self.average_frequency = [0.0 for _ in range(self.num_channels)]
#         self.band_pass_peak_to_peak = [0.0 for _ in range(self.num_channels)]
#         self.time_points = np.arange(4096) / self.sample_rate

#     def update_table_defaults(self):
#         headers = [
#             "RPM", "Gap", "Channel Name", "DateTime", "Direct",
#             "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
#             "Vpp", "Vrms", "Twiddle Factor"
#         ]
#         default_data = {
#             "Channel Name": "N/A",
#             "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "RPM": "0.00",
#             "Gap": "0.00",
#             "Direct": "0.00",
#             "1x Amp": "0.00",
#             "1x Phase": "0.00",
#             "2x Amp": "0.00",
#             "2x Phase": "0.00",
#             "nx Amp": "0.00",
#             "nx Phase": "0.00",
#             "Vpp": "0.00",
#             "Vrms": "0.00",
#             "Twiddle Factor": "0.00"
#         }
#         for row in range(self.num_channels):
#             default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
#             for col, header in enumerate(headers):
#                 self.table.setItem(row, col, QTableWidgetItem(default_data[header]))
#         self.table.setFixedHeight(100 * self.num_channels)
#         if self.console:
#             self.console.append_to_console(f"Updated table with {self.num_channels} rows for channels: {self.channel_names}")

#     def load_settings_from_database(self):
#         try:
#             database = self.mongo_client.get_database("changed_db")
#             settings_collection = database.get_collection("TabularViewSettings")
#             setting = settings_collection.find_one({"projectId": self.project_id}, sort=[("updatedAt", -1)])
            
#             if setting:
#                 self.bandpass_selection = setting.get("bandpassSelection", "None")
#                 self.column_visibility = {
#                     "RPM": setting.get("rpmVisible", True),
#                     "Gap": setting.get("gapVisible", True),
#                     "Channel Name": setting.get("channelNameVisible", True),
#                     "DateTime": setting.get("datetimeVisible", True),
#                     "Direct": setting.get("directVisible", True),
#                     "1x Amp": setting.get("oneXAmpVisible", True),
#                     "1x Phase": setting.get("oneXPhaseVisible", True),
#                     "2x Amp": setting.get("twoXAmpVisible", True),
#                     "2x Phase": setting.get("twoXPhaseVisible", True),
#                     "nx Amp": setting.get("nxAmpVisible", True),
#                     "nx Phase": setting.get("nxPhaseVisible", True),
#                     "Vpp": setting.get("vppVisible", True),
#                     "Vrms": setting.get("vrmsVisible", True),
#                     "Twiddle Factor": setting.get("twiddleFactorVisible", True)
#                 }
#                 self.bandpass_combo.setCurrentText(self.bandpass_selection)
#                 for header, cb in self.checkbox_dict.items():
#                     cb.setChecked(self.column_visibility[header])
#                 if self.console:
#                     self.console.append_to_console(f"Loaded TabularView settings for project ID: {self.project_id}")
#             else:
#                 if self.console:
#                     self.console.append_to_console(f"No TabularView settings found for project ID: {self.project_id}. Using defaults.")
#             self.update_column_visibility()
#         except Exception as ex:
#             self.log_and_set_status(f"Error loading TabularView settings: {str(ex)}")

#     def save_settings_to_database(self):
#         try:
#             database = self.mongo_client.get_database("changed_db")
#             settings_collection = database.get_collection("TabularViewSettings")
#             setting = {
#                 "projectId": self.project_id,
#                 "bandpassSelection": self.bandpass_selection,
#                 "rpmVisible": self.column_visibility["RPM"],
#                 "gapVisible": self.column_visibility["Gap"],
#                 "channelNameVisible": self.column_visibility["Channel Name"],
#                 "datetimeVisible": self.column_visibility["DateTime"],
#                 "directVisible": self.column_visibility["Direct"],
#                 "oneXAmpVisible": self.column_visibility["1x Amp"],
#                 "oneXPhaseVisible": self.column_visibility["1x Phase"],
#                 "twoXAmpVisible": self.column_visibility["2x Amp"],
#                 "twoXPhaseVisible": self.column_visibility["2x Phase"],
#                 "nxAmpVisible": self.column_visibility["nx Amp"],
#                 "nxPhaseVisible": self.column_visibility["nx Phase"],
#                 "vppVisible": self.column_visibility["Vpp"],
#                 "vrmsVisible": self.column_visibility["Vrms"],
#                 "twiddleFactorVisible": self.column_visibility["Twiddle Factor"],
#                 "updatedAt": datetime.utcnow()
#             }
#             settings_collection.update_one(
#                 {"projectId": self.project_id},
#                 {"$set": setting},
#                 upsert=True
#             )
#             if self.console:
#                 self.console.append_to_console(f"Saved TabularView settings for project ID: {self.project_id}")
#         except Exception as ex:
#             self.log_and_set_status(f"Error saving TabularView settings: {str(ex)}")

#     def toggle_settings(self):
#         self.settings_panel.setVisible(not self.settings_panel.isVisible())
#         self.settings_button.setVisible(not self.settings_panel.isVisible())

#     def save_settings(self):
#         self.bandpass_selection = self.bandpass_combo.currentText()
#         self.column_visibility = {header: cb.isChecked() for header, cb in self.checkbox_dict.items()}
#         self.save_settings_to_database()
#         self.update_column_visibility()
#         self.settings_panel.setVisible(False)
#         self.settings_button.setVisible(True)
#         if self.console:
#             self.console.append_to_console("Table settings updated and saved.")

#     def close_settings(self):
#         self.bandpass_combo.setCurrentText(self.bandpass_selection)
#         for header, cb in self.checkbox_dict.items():
#             cb.setChecked(self.column_visibility[header])
#         self.settings_panel.setVisible(False)
#         self.settings_button.setVisible(True)

#     def update_column_visibility(self):
#         headers = [
#             "RPM", "Gap", "Channel Name", "DateTime", "Direct",
#             "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
#             "Vpp", "Vrms", "Twiddle Factor"
#         ]
#         for col, header in enumerate(headers):
#             try:
#                 self.table.setColumnHidden(col, not self.column_visibility[header])
#             except KeyError as e:
#                 self.log_and_set_status(f"KeyError in update_column_visibility: {str(e)}")

#     def calculate_metrics(self, channel_data, tacho_trigger_data, channel_idx):
#         metrics = {
#             "rpm": 0.0, "gap": 0.0, "direct": 0.0, "1x Amp": 0.0, "1x Phase": 0.0,
#             "2x Amp": 0.0, "2x Phase": 0.0, "nx Amp": 0.0, "nx Phase": 0.0,
#             "vpp": 0.0, "vrms": 0.0, "twiddle_factor": 0.0
#         }

#         if len(channel_data) < 2 or len(tacho_trigger_data) < 2:
#             if self.console:
#                 self.console.append_to_console(
#                     f"Channel {channel_idx+1}: Insufficient data length: channel_data={len(channel_data)}, "
#                     f"tacho_trigger_data={len(tacho_trigger_data)}"
#                 )
#             return metrics

#         try:
#             # Basic calculations
#             metrics["vpp"] = float(np.max(channel_data) - np.min(channel_data))
#             metrics["vrms"] = float(np.sqrt(np.mean(np.square(channel_data))))
#             metrics["direct"] = float(np.mean(channel_data))

#             # Trigger detection
#             threshold = np.mean(tacho_trigger_data) + 0.5 * np.std(tacho_trigger_data)
#             trigger_indices = np.where(np.diff((tacho_trigger_data > threshold).astype(int)) > 0)[0]
#             min_distance = 5
#             filtered_trigger_indices = [trigger_indices[0]] if len(trigger_indices) > 0 else [0, len(tacho_trigger_data)-1]
#             for i in range(1, len(trigger_indices)):
#                 if trigger_indices[i] - filtered_trigger_indices[-1] >= min_distance:
#                     filtered_trigger_indices.append(trigger_indices[i])

#             # RPM calculation
#             if len(filtered_trigger_indices) >= 2:
#                 samples_per_rotation = np.mean(np.diff(filtered_trigger_indices))
#                 if samples_per_rotation > 0:
#                     metrics["rpm"] = (60 * self.sample_rate) / samples_per_rotation
#             else:
#                 if self.console:
#                     self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient trigger points for RPM.")

#             # Gap calculation
#             metrics["gap"] = float(np.mean(tacho_trigger_data))

#             # Harmonic calculations
#             if len(filtered_trigger_indices) >= 2:
#                 start_idx = filtered_trigger_indices[0]
#                 end_idx = filtered_trigger_indices[-1]
#                 segment = channel_data[start_idx:end_idx]
#                 segment_length = end_idx - start_idx
#                 if segment_length > 0:
#                     for harmonic, (amp_key, phase_key) in enumerate([
#                         ("1x Amp", "1x Phase"),
#                         ("2x Amp", "2x Phase"),
#                         ("nx Amp", "nx Phase")
#                     ], 1):
#                         sine_sum = cosine_sum = 0.0
#                         for n in range(segment_length):
#                             global_idx = start_idx + n
#                             theta = (2 * np.pi * harmonic * n) / segment_length
#                             sine_sum += channel_data[global_idx] * np.sin(theta)
#                             cosine_sum += channel_data[global_idx] * np.cos(theta)
#                         metrics[amp_key] = np.sqrt((sine_sum / segment_length) ** 2 + (cosine_sum / segment_length) ** 2) * 4
#                         metrics[phase_key] = np.arctan2(cosine_sum, sine_sum) * (180.0 / np.pi)
#                         if metrics[phase_key] < 0:
#                             metrics[phase_key] += 360
#             else:
#                 if self.console:
#                     self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient triggers for harmonic calculations.")

#             # Twiddle factor
#             if len(filtered_trigger_indices) >= 2:
#                 fft_vals = np.fft.fft(channel_data[filtered_trigger_indices[0]:filtered_trigger_indices[-1]])
#                 fft_phases = np.angle(fft_vals)
#                 phase_diffs = np.diff(fft_phases[:len(fft_phases)//2])
#                 metrics["twiddle_factor"] = float(np.std(phase_diffs)) if len(phase_diffs) > 0 else 0.0
#             else:
#                 if self.console:
#                     self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient triggers for twiddle factor.")
#         except Exception as ex:
#             self.log_and_set_status(f"Error calculating metrics for channel {channel_idx+1}: {str(ex)}")

#         return metrics

#     def process_calibrated_data(self, data, channel_idx):
#         channel_name = self.channel_names[channel_idx] if channel_idx < len(self.channel_names) else f"Channel {channel_idx+1}"
#         if channel_idx >= len(data) or not data[channel_idx]:
#             if self.console:
#                 self.console.append_to_console(f"Channel {channel_name}: No data at index {channel_idx}, using zeros.")
#             return np.zeros(4096)
#         props = self.channel_properties.get(channel_name, {"Unit": "mil", "CorrectionValue": 1.0, "Gain": 1.0, "Sensitivity": 1.0})
#         try:
#             channel_data = np.array(data[channel_idx], dtype=float) * (3.3 / 65535.0) * (props["CorrectionValue"] * props["Gain"]) / props["Sensitivity"]
#             if props["Unit"].lower() == "mil":
#                 channel_data /= 25.4
#             elif props["Unit"].lower() == "mm":
#                 channel_data /= 1000
#             return channel_data
#         except Exception as ex:
#             self.log_and_set_status(f"Error calibrating data for channel {channel_name}: {str(ex)}")
#             return np.zeros(4096)

#     def on_data_received(self, tag_name, model_name, values, sample_rate):
#         if self.console:
#             self.console.append_to_console(
#                 f"Received data: tag_name={tag_name}, model_name={model_name}, "
#                 f"channels={len(values)}, sample_counts={[len(v) for v in values]}"
#             )
#         if self.model_name != model_name or tag_name != self.tag_name:
#             if self.console:
#                 self.console.append_to_console(
#                     f"Skipped data: model_name={model_name} (expected {self.model_name}), "
#                     f"tag_name={tag_name} (expected {self.tag_name})"
#                 )
#             return

#         try:
#             # Relaxed validation: accept any non-empty values
#             if not values:
#                 if self.console:
#                     self.console.append_to_console("Empty data received, using zeros for all channels.")
#                 values = [[] for _ in range(max(self.num_channels, 6))]
#             values = values[:max(self.num_channels, 6)] + [[] for _ in range(max(self.num_channels, 6) - len(values))]
#             for i in range(len(values)):
#                 if not values[i]:
#                     values[i] = np.zeros(4096).tolist()
#                 elif len(values[i]) < 4096:
#                     values[i] = (values[i] + [0] * (4096 - len(values[i])))[:4096]
#                 elif len(values[i]) > 4096:
#                     values[i] = values[i][:4096]

#             self.sample_rate = sample_rate if sample_rate > 0 else 4096
#             self.data = values
#             main_channels = min(self.num_channels, len(values), 4)
#             if self.console:
#                 self.console.append_to_console(f"Processing {main_channels} channels for topic {tag_name}")

#             headers = [
#                 "RPM", "Gap", "Channel Name", "DateTime", "Direct",
#                 "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
#                 "Vpp", "Vrms", "Twiddle Factor"
#             ]
#             frequency_data = np.array(values[4], dtype=float) if len(values) > 4 and values[4] else np.zeros(4096)
#             trigger_data = np.array(values[5], dtype=float) if len(values) > 5 and values[5] else np.zeros(4096)

#             for ch in range(self.num_channels):
#                 try:
#                     channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
#                     self.raw_data[ch] = self.process_calibrated_data(values, ch)
#                     low_pass_cutoff = 100
#                     high_pass_cutoff = 200
#                     band_pass_low_cutoff = 50
#                     band_pass_high_cutoff = 200
#                     tap_num = 31
#                     nyquist = self.sample_rate / 2.0

#                     if low_pass_cutoff >= nyquist or high_pass_cutoff >= nyquist or band_pass_low_cutoff >= band_pass_high_cutoff or band_pass_high_cutoff >= nyquist:
#                         self.log_and_set_status(f"Invalid filter cutoff frequencies for channel {channel_name}.")
#                         self.raw_data[ch] = np.zeros(4096)
#                         self.low_pass_data[ch] = np.zeros(4096)
#                         self.high_pass_data[ch] = np.zeros(4096)
#                         self.band_pass_data[ch] = np.zeros(4096)
#                         self.update_table_row(ch, channel_name, {})
#                         continue

#                     low_pass_coeffs = signal.firwin(tap_num, low_pass_cutoff / nyquist, window='hamming')
#                     high_pass_coeffs = signal.firwin(tap_num, high_pass_cutoff / nyquist, window='hamming', pass_zero=False)
#                     band_pass_coeffs = signal.firwin(tap_num, [band_pass_low_cutoff / nyquist, band_pass_high_cutoff / nyquist], window='hamming', pass_zero=False)

#                     self.low_pass_data[ch] = signal.lfilter(low_pass_coeffs, 1.0, self.raw_data[ch])
#                     self.high_pass_data[ch] = signal.lfilter(high_pass_coeffs, 1.0, self.raw_data[ch])
#                     self.band_pass_data[ch] = signal.lfilter(band_pass_coeffs, 1.0, self.raw_data[ch])

#                     self.average_frequency[ch] = np.mean(frequency_data[frequency_data > 0]) if np.any(frequency_data > 0) else 0.0

#                     trigger_indices = np.where(trigger_data > np.mean(trigger_data) + 0.5 * np.std(trigger_data))[0]
#                     min_distance_between_triggers = 5
#                     filtered_trigger_indices = [trigger_indices[0]] if len(trigger_indices) > 0 else [0, len(trigger_data)-1]
#                     for i in range(1, len(trigger_indices)):
#                         if trigger_indices[i] - filtered_trigger_indices[-1] >= min_distance_between_triggers:
#                             filtered_trigger_indices.append(trigger_indices[i])

#                     band_pass_peak_to_peak_values = []
#                     for i in range(len(filtered_trigger_indices) - 1):
#                         start_idx = filtered_trigger_indices[i]
#                         end_idx = filtered_trigger_indices[i + 1]
#                         segment = self.band_pass_data[ch][start_idx:end_idx]
#                         if len(segment) > 0:
#                             band_pass_peak_to_peak_values.append(np.max(segment) - np.min(segment))
#                     self.band_pass_peak_to_peak[ch] = np.mean(band_pass_peak_to_peak_values) if band_pass_peak_to_peak_values else 0.0
#                     self.band_pass_peak_to_peak_history[ch].append(self.band_pass_peak_to_peak[ch])
#                     self.band_pass_peak_to_peak_times[ch].append((datetime.now() - self.start_time).total_seconds())

#                     metrics = self.calculate_metrics(self.raw_data[ch], trigger_data, ch)
#                     channel_data = {
#                         "Channel Name": channel_name,
#                         "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                         "RPM": f"{metrics['rpm']:.2f}",
#                         "Gap": f"{metrics['gap']:.2f}",
#                         "Direct": f"{metrics['direct']:.2f}",
#                         "1x Amp": f"{metrics['1x Amp']:.2f}",
#                         "1x Phase": f"{metrics['1x Phase']:.2f}",
#                         "2x Amp": f"{metrics['2x Amp']:.2f}",
#                         "2x Phase": f"{metrics['2x Phase']:.2f}",
#                         "nx Amp": f"{metrics['nx Amp']:.2f}",
#                         "nx Phase": f"{metrics['nx Phase']:.2f}",
#                         "Vpp": f"{metrics['vpp']:.2f}",
#                         "Vrms": f"{metrics['vrms']:.2f}",
#                         "Twiddle Factor": f"{metrics['twiddle_factor']:.2f}"
#                     }

#                     self.update_table_row(ch, channel_name, channel_data)
#                     if self.console:
#                         self.console.append_to_console(f"Updated table for channel {channel_name}: {channel_data}")
#                 except Exception as ex:
#                     self.log_and_set_status(f"Error processing channel {channel_name}: {str(ex)}")
#                     self.raw_data[ch] = np.zeros(4096)
#                     self.low_pass_data[ch] = np.zeros(4096)
#                     self.high_pass_data[ch] = np.zeros(4096)
#                     self.band_pass_data[ch] = np.zeros(4096)
#                     self.update_table_row(ch, channel_name, {})

#             self.update_plots()
#             if self.console:
#                 self.console.append_to_console(f"Processed data for topic {tag_name}, {main_channels} channels: Updated table and plots.")
#         except Exception as ex:
#             self.log_and_set_status(f"Error processing data: {str(ex)}")
#             for ch in range(self.num_channels):
#                 channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
#                 self.update_table_row(ch, channel_name, {})
#             self.update_plots()

#     def update_table_row(self, row, channel_name, channel_data):
#         headers = [
#             "RPM", "Gap", "Channel Name", "DateTime", "Direct",
#             "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
#             "Vpp", "Vrms", "Twiddle Factor"
#         ]
#         default_data = {
#             "Channel Name": channel_name,
#             "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "RPM": "0.00",
#             "Gap": "0.00",
#             "Direct": "0.00",
#             "1x Amp": "0.00",
#             "1x Phase": "0.00",
#             "2x Amp": "0.00",
#             "2x Phase": "0.00",
#             "nx Amp": "0.00",
#             "nx Phase": "0.00",
#             "Vpp": "0.00",
#             "Vrms": "0.00",
#             "Twiddle Factor": "0.00"
#         }
#         data = channel_data if channel_data else default_data
#         for col, header in enumerate(headers):
#             self.table.setItem(row, col, QTableWidgetItem(data[header]))

#     def update_plots(self):
#         self.plot_initialized = True

#         if self.selected_channel_idx >= self.num_channels:
#             self.selected_channel_idx = 0
#             self.channel_selector.setCurrentIndex(1 if self.channel_names else 0)
#             if self.console:
#                 self.console.append_to_console(f"Selected channel index {self.selected_channel_idx} out of range, defaulting to 0")

#         ch = self.selected_channel_idx
#         channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
#         trim_samples = 47
#         low_pass_trim = 0
#         high_pass_trim = 110
#         band_pass_trim = 110
#         raw_trim = trim_samples

#         if len(self.raw_data[ch]) <= trim_samples:
#             if self.console:
#                 self.console.append_to_console(f"Channel {channel_name}: Warning: Data length ({len(self.raw_data[ch])}) too short to trim {trim_samples} samples for plotting.")
#             low_pass_trim = high_pass_trim = band_pass_trim = raw_trim = 0

#         data_sets = [
#             (self.raw_data[ch], raw_trim, f"Channel {channel_name} Raw Data"),
#             (self.low_pass_data[ch], low_pass_trim, f"Channel {channel_name} Low-Pass Filtered Data (100 Hz Cutoff)"),
#             (self.high_pass_data[ch], high_pass_trim, f"Channel {channel_name} High-Pass Filtered Data (200 Hz Cutoff)"),
#             (self.band_pass_data[ch], band_pass_trim, f"Channel {channel_name} Band-Pass Filtered Data (50-200 Hz) ({self.average_frequency[ch]:.2f} Hz, Peak-to-Peak: {self.band_pass_peak_to_peak[ch]:.2f})")
#         ]

#         for i, (data, trim, title) in enumerate(data_sets):
#             self.plots[i].clear()
#             trimmed_data = data[trim:] if len(data) > trim else (data if len(data) > 0 else np.array([0]))
#             trimmed_time = self.time_points[trim:] if len(self.time_points) > trim else (self.time_points if len(self.time_points) > 0 else np.array([0]))
#             self.plots[i].setData(trimmed_time, trimmed_data)
#             self.plot_widgets[i].setTitle(title)
#             self.plot_widgets[i].setYRange(np.min(trimmed_data) * 1.1 if trimmed_data.size > 0 else -1, np.max(trimmed_data) * 1.1 if trimmed_data.size > 0 else 1)
#             if self.console:
#                 self.console.append_to_console(f"Updated plot {i+1} for channel {channel_name}: {len(trimmed_data)} samples")

#         self.plots[4].clear()
#         frequency_values = [self.average_frequency[ch] + (i * 0.1) for i in range(len(self.band_pass_peak_to_peak_history[ch]))]
#         if frequency_values and self.band_pass_peak_to_peak_history[ch]:
#             self.plots[4].setData(frequency_values, self.band_pass_peak_to_peak_history[ch])
#             self.plot_widgets[4].setYRange(0, max(0.01, max(self.band_pass_peak_to_peak_history[ch], default=0) * 1.1))
#             if self.console:
#                 self.console.append_to_console(f"Updated peak-to-peak plot for channel {channel_name}: {len(frequency_values)} points")
#         else:
#             self.plots[4].setData(np.array([0]), np.array([0]))
#             self.plot_widgets[4].setYRange(0, 0.01)
#             if self.console:
#                 self.console.append_to_console(f"Channel {channel_name}: No data for bandpass peak-to-peak plot")

#     def log_and_set_status(self, message):
#         if self.console:
#             self.console.append_to_console(message)

#     def close(self):
#         self.mongo_client.close()




import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QScrollArea, QPushButton, QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
from datetime import datetime
from pymongo import MongoClient
import scipy.signal as signal
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TabularViewSettings:
    def __init__(self, project_id):
        self.project_id = project_id
        self.bandpass_selection = "None"
        self.rpm_visible = True
        self.gap_visible = True
        self.channel_name_visible = True
        self.datetime_visible = True
        self.direct_visible = True
        self.one_x_amp_visible = True
        self.one_x_phase_visible = True
        self.two_x_amp_visible = True
        self.two_x_phase_visible = True
        self.nx_amp_visible = True
        self.nx_phase_visible = True
        self.vpp_visible = True
        self.vrms_visible = True
        self.twiddle_factor_visible = True
        self.updated_at = datetime.utcnow()

class TabularViewFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        self.channel = channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.data = None
        self.sample_rate = 4096
        self.num_channels = 1  # Default, updated in initialize_async
        self.channel_names = ["Channel 1"]  # Default
        self.channel_properties = {}
        self.project_id = None
        self.raw_data = [np.zeros(4096)]
        self.low_pass_data = [np.zeros(4096)]
        self.high_pass_data = [np.zeros(4096)]
        self.band_pass_data = [np.zeros(4096)]
        self.time_points = np.arange(4096) / self.sample_rate
        self.band_pass_peak_to_peak_history = [[]]
        self.band_pass_peak_to_peak_times = [[]]
        self.average_frequency = [0.0]
        self.band_pass_peak_to_peak = [0.0]
        self.start_time = datetime.now()
        self.column_visibility = {
            "RPM": True,
            "Gap": True,
            "Channel Name": True,
            "DateTime": True,
            "Direct": True,
            "1x Amp": True,
            "1x Phase": True,
            "2x Amp": True,
            "2x Phase": True,
            "nx Amp": True,
            "nx Phase": True,
            "Vpp": True,
            "Vrms": True,
            "Twiddle Factor": True
        }
        self.bandpass_selection = "None"
        self.mongo_client = MongoClient("mongodb://localhost:27017")
        self.plot_initialized = False
        self.table = None
        self.plot_widgets = []
        self.plots = []
        self.selected_channel_idx = 0
        self.tag_name = ""
        self.channel_selector = None
        self.scroll_content = None
        self.scroll_layout = None
        self.initUI()
        self.initialize_async()

    def initUI(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        # Settings and channel selection
        top_layout = QHBoxLayout()
        self.settings_button = QPushButton("Settings")
        self.settings_button.setIcon(QIcon("settings_icon.png"))  # Replace with your image path
        self.settings_button.clicked.connect(self.toggle_settings)
        top_layout.addWidget(self.settings_button)

        top_layout.addWidget(QLabel("Select Channel for Plots:"))
        self.channel_selector = QComboBox()
        self.channel_selector.addItem("Select Channel")
        self.channel_selector.addItems(self.channel_names)
        self.channel_selector.currentIndexChanged.connect(self.update_selected_channel)
        top_layout.addWidget(self.channel_selector)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Settings panel
        self.settings_panel = QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QGridLayout()
        self.settings_panel.setLayout(settings_layout)

        # Bandpass selection
        self.bandpass_combo = QComboBox()
        self.bandpass_combo.addItems(["None", "50-200 Hz", "100-300 Hz"])
        settings_layout.addWidget(self.bandpass_combo, 0, 0, 1, 2)

        # Checkboxes for column visibility
        headers = [
            "RPM", "Gap", "Channel Name", "DateTime", "Direct",
            "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
            "Vpp", "Vrms", "Twiddle Factor"
        ]
        self.checkbox_dict = {}
        for i, header in enumerate(headers):
            cb = QCheckBox(header)
            cb.setChecked(True)
            self.checkbox_dict[header] = cb
            settings_layout.addWidget(cb, (i // 2) + 1, i % 2)

        # Save and Close buttons
        self.save_settings_button = QPushButton("Save")
        self.save_settings_button.clicked.connect(self.save_settings)
        self.close_settings_button = QPushButton("Close")
        self.close_settings_button.clicked.connect(self.close_settings)
        settings_layout.addWidget(self.save_settings_button, len(headers) // 2 + 1, 0)
        settings_layout.addWidget(self.close_settings_button, len(headers) // 2 + 1, 1)

        layout.addWidget(self.settings_panel)

        # Table setup
        self.table = QTableWidget()
        self.table.setRowCount(self.num_channels)
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setFixedHeight(100 * self.num_channels)  # Adjust height for rows
        layout.addWidget(self.table)

        # Initialize table with default values
        default_data = {
            "Channel Name": "N/A",
            "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RPM": "0.00",
            "Gap": "0.00",
            "Direct": "0.00",
            "1x Amp": "0.00",
            "1x Phase": "0.00",
            "2x Amp": "0.00",
            "2x Phase": "0.00",
            "nx Amp": "0.00",
            "nx Phase": "0.00",
            "Vpp": "0.00",
            "Vrms": "0.00",
            "Twiddle Factor": "0.00"
        }
        for row in range(self.num_channels):
            default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
            for col, header in enumerate(headers):
                self.table.setItem(row, col, QTableWidgetItem(default_data[header]))

        # Scroll area for plots
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_area.setWidget(self.scroll_content)
        layout.addWidget(scroll_area)

        # Initialize plots for the selected channel
        self.initialize_plots()

        if self.console:
            self.console.append_to_console(f"Initialized UI with {self.num_channels} channels: {self.channel_names}")

    def initialize_plots(self):
        """Initialize plot widgets for the selected channel."""
        # Clear existing plots
        for widget in self.plot_widgets:
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.plot_widgets = []
        self.plots = []

        # Plot titles
        plot_titles = [
            "Raw Data",
            "Low-Pass Filtered Data (100 Hz Cutoff)",
            "High-Pass Filtered Data (200 Hz Cutoff)",
            "Band-Pass Filtered Data (50-200 Hz)",
            "Bandpass Average Peak-to-Peak Over Frequency"
        ]

        # Create plot widgets for the selected channel
        for i, title in enumerate(plot_titles):
            plot_widget = pg.PlotWidget(title=title)
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setLabel('bottom', 'Time (s)' if i < 4 else 'Frequency (Hz)')
            plot_widget.setLabel('left', 'Amplitude' if i < 4 else 'Peak-to-Peak Value')
            plot_widget.setFixedHeight(250)  # Set a fixed height for each plot
            self.scroll_layout.addWidget(plot_widget)
            self.plot_widgets.append(plot_widget)
            plot = plot_widget.plot(pen='b')
            plot.setData(np.array([0]), np.array([0]))  # Initialize empty plot
            self.plots.append(plot)

        self.scroll_layout.addStretch()  # Add stretch to keep plots at the top
        self.plot_initialized = True
        self.update_plots()

    def get_widget(self):
        return self.widget

    def update_selected_channel(self, index):
        """Update the selected channel and refresh plots."""
        if index > 0:  # Skip "Select Channel" option
            self.selected_channel_idx = index - 1
            if self.console:
                self.console.append_to_console(f"Selected channel for plots: {self.channel_names[self.selected_channel_idx]}")
        else:
            self.selected_channel_idx = 0
            if self.console:
                self.console.append_to_console("No valid channel selected for plots, defaulting to first channel.")
        self.update_plots()

    def initialize_async(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            projects_collection = database.get_collection("projects")
            project = projects_collection.find_one({"project_name": self.project_name, "email": self.db.email})
            if not project:
                self.log_and_set_status(f"Project {self.project_name} not found for email {self.db.email}. Using default channel.")
                self.channel_names = ["Channel 1"]
                self.num_channels = 1
                self.table.setRowCount(1)
                self.channel_selector.clear()
                self.channel_selector.addItem("Select Channel")
                self.channel_selector.addItems(self.channel_names)
                self.channel_selector.setCurrentIndex(1)
                self.initialize_data_arrays()
                self.update_table_defaults()
                self.initialize_plots()
                return

            self.project_id = project["_id"]
            model = next((m for m in project["models"] if m["name"] == self.model_name), None)
            if not model or not model.get("channels"):
                self.log_and_set_status(f"Model {self.model_name} or channels not found in project {self.project_name}. Using default channel.")
                self.channel_names = ["Channel 1"]
                self.num_channels = 1
                self.table.setRowCount(1)
                self.channel_selector.clear()
                self.channel_selector.addItem("Select Channel")
                self.channel_selector.addItems(self.channel_names)
                self.channel_selector.setCurrentIndex(1)
                self.initialize_data_arrays()
                self.update_table_defaults()
                self.initialize_plots()
                return

            self.channel_names = [c.get("channelName", f"Channel {i+1}") for i, c in enumerate(model["channels"])]
            self.num_channels = len(self.channel_names)
            if not self.channel_names:
                self.log_and_set_status("No channels found in model. Using default channel.")
                self.channel_names = ["Channel 1"]
                self.num_channels = 1

            # Update table and selector
            self.table.setRowCount(self.num_channels)
            self.channel_selector.clear()
            self.channel_selector.addItem("Select Channel")
            self.channel_selector.addItems(self.channel_names)
            if self.channel in self.channel_names:
                self.selected_channel_idx = self.channel_names.index(self.channel)
                self.channel_selector.setCurrentIndex(self.selected_channel_idx + 1)
            else:
                self.log_and_set_status(f"Selected channel {self.channel} not found. Defaulting to first channel.")
                self.selected_channel_idx = 0
                self.channel_selector.setCurrentIndex(1 if self.channel_names else 0)

            # Initialize data arrays
            self.initialize_data_arrays()

            # Populate channel properties
            for channel in model["channels"]:
                channel_name = channel.get("channelName", "Unknown")
                correction_value = float(channel.get("CorrectionValue", "1.0")) if channel.get("CorrectionValue") else 1.0
                gain = float(channel.get("Gain", "1.0")) if channel.get("Gain") else 1.0
                sensitivity = float(channel.get("Sensitivity", "1.0")) if channel.get("Sensitivity") and float(channel.get("Sensitivity")) != 0 else 1.0
                self.channel_properties[channel_name] = {
                    "Unit": channel.get("Unit", "mil").lower(),
                    "CorrectionValue": correction_value,
                    "Gain": gain,
                    "Sensitivity": sensitivity
                }

            self.tag_name = model.get("tagName", "")
            if self.console:
                self.console.append_to_console(f"Initialized with TagName: {self.tag_name}, Model: {self.model_name}, Channels: {self.channel_names}, Project ID: {self.project_id}")

            self.update_table_defaults()
            self.load_settings_from_database()
            self.initialize_plots()
        except Exception as ex:
            self.log_and_set_status(f"Error initializing TabularView: {str(ex)}")
            self.channel_names = ["Channel 1"]
            self.num_channels = 1
            self.table.setRowCount(1)
            self.channel_selector.clear()
            self.channel_selector.addItem("Select Channel")
            self.channel_selector.addItems(self.channel_names)
            self.channel_selector.setCurrentIndex(1)
            self.initialize_data_arrays()
            self.update_table_defaults()
            self.initialize_plots()

    def initialize_data_arrays(self):
        self.raw_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.low_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.high_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.band_pass_data = [np.zeros(4096) for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak_history = [[] for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak_times = [[] for _ in range(self.num_channels)]
        self.average_frequency = [0.0 for _ in range(self.num_channels)]
        self.band_pass_peak_to_peak = [0.0 for _ in range(self.num_channels)]
        self.time_points = np.arange(4096) / self.sample_rate

    def update_table_defaults(self):
        headers = [
            "RPM", "Gap", "Channel Name", "DateTime", "Direct",
            "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
            "Vpp", "Vrms", "Twiddle Factor"
        ]
        default_data = {
            "Channel Name": "N/A",
            "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RPM": "0.00",
            "Gap": "0.00",
            "Direct": "0.00",
            "1x Amp": "0.00",
            "1x Phase": "0.00",
            "2x Amp": "0.00",
            "2x Phase": "0.00",
            "nx Amp": "0.00",
            "nx Phase": "0.00",
            "Vpp": "0.00",
            "Vrms": "0.00",
            "Twiddle Factor": "0.00"
        }
        for row in range(self.num_channels):
            default_data["Channel Name"] = self.channel_names[row] if row < len(self.channel_names) else f"Channel {row+1}"
            for col, header in enumerate(headers):
                self.table.setItem(row, col, QTableWidgetItem(default_data[header]))
        self.table.setFixedHeight(100 * self.num_channels)
        if self.console:
            self.console.append_to_console(f"Updated table with {self.num_channels} rows for channels: {self.channel_names}")

    def load_settings_from_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("TabularViewSettings")
            setting = settings_collection.find_one({"projectId": self.project_id}, sort=[("updatedAt", -1)])
            
            if setting:
                self.bandpass_selection = setting.get("bandpassSelection", "None")
                self.column_visibility = {
                    "RPM": setting.get("rpmVisible", True),
                    "Gap": setting.get("gapVisible", True),
                    "Channel Name": setting.get("channelNameVisible", True),
                    "DateTime": setting.get("datetimeVisible", True),
                    "Direct": setting.get("directVisible", True),
                    "1x Amp": setting.get("oneXAmpVisible", True),
                    "1x Phase": setting.get("oneXPhaseVisible", True),
                    "2x Amp": setting.get("twoXAmpVisible", True),
                    "2x Phase": setting.get("twoXPhaseVisible", True),
                    "nx Amp": setting.get("nxAmpVisible", True),
                    "nx Phase": setting.get("nxPhaseVisible", True),
                    "Vpp": setting.get("vppVisible", True),
                    "Vrms": setting.get("vrmsVisible", True),
                    "Twiddle Factor": setting.get("twiddleFactorVisible", True)
                }
                self.bandpass_combo.setCurrentText(self.bandpass_selection)
                for header, cb in self.checkbox_dict.items():
                    cb.setChecked(self.column_visibility[header])
                if self.console:
                    self.console.append_to_console(f"Loaded TabularView settings for project ID: {self.project_id}")
            else:
                if self.console:
                    self.console.append_to_console(f"No TabularView settings found for project ID: {self.project_id}. Using defaults.")
            self.update_column_visibility()
        except Exception as ex:
            self.log_and_set_status(f"Error loading TabularView settings: {str(ex)}")

    def save_settings_to_database(self):
        try:
            database = self.mongo_client.get_database("changed_db")
            settings_collection = database.get_collection("TabularViewSettings")
            setting = {
                "projectId": self.project_id,
                "bandpassSelection": self.bandpass_selection,
                "rpmVisible": self.column_visibility["RPM"],
                "gapVisible": self.column_visibility["Gap"],
                "channelNameVisible": self.column_visibility["Channel Name"],
                "datetimeVisible": self.column_visibility["DateTime"],
                "directVisible": self.column_visibility["Direct"],
                "oneXAmpVisible": self.column_visibility["1x Amp"],
                "oneXPhaseVisible": self.column_visibility["1x Phase"],
                "twoXAmpVisible": self.column_visibility["2x Amp"],
                "twoXPhaseVisible": self.column_visibility["2x Phase"],
                "nxAmpVisible": self.column_visibility["nx Amp"],
                "nxPhaseVisible": self.column_visibility["nx Phase"],
                "vppVisible": self.column_visibility["Vpp"],
                "vrmsVisible": self.column_visibility["Vrms"],
                "twiddleFactorVisible": self.column_visibility["Twiddle Factor"],
                "updatedAt": datetime.utcnow()
            }
            settings_collection.update_one(
                {"projectId": self.project_id},
                {"$set": setting},
                upsert=True
            )
            if self.console:
                self.console.append_to_console(f"Saved TabularView settings for project ID: {self.project_id}")
        except Exception as ex:
            self.log_and_set_status(f"Error saving TabularView settings: {str(ex)}")

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.settings_button.setVisible(not self.settings_panel.isVisible())

    def save_settings(self):
        self.bandpass_selection = self.bandpass_combo.currentText()
        self.column_visibility = {header: cb.isChecked() for header, cb in self.checkbox_dict.items()}
        self.save_settings_to_database()
        self.update_column_visibility()
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)
        if self.console:
            self.console.append_to_console("Table settings updated and saved.")

    def close_settings(self):
        self.bandpass_combo.setCurrentText(self.bandpass_selection)
        for header, cb in self.checkbox_dict.items():
            cb.setChecked(self.column_visibility[header])
        self.settings_panel.setVisible(False)
        self.settings_button.setVisible(True)

    def update_column_visibility(self):
        headers = [
            "RPM", "Gap", "Channel Name", "DateTime", "Direct",
            "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
            "Vpp", "Vrms", "Twiddle Factor"
        ]
        for col, header in enumerate(headers):
            try:
                self.table.setColumnHidden(col, not self.column_visibility[header])
            except KeyError as e:
                self.log_and_set_status(f"KeyError in update_column_visibility: {str(e)}")

    def calculate_metrics(self, channel_data, tacho_trigger_data, channel_idx):
        metrics = {
            "rpm": 0.0, "gap": 0.0, "direct": 0.0, "1x Amp": 0.0, "1x Phase": 0.0,
            "2x Amp": 0.0, "2x Phase": 0.0, "nx Amp": 0.0, "nx Phase": 0.0,
            "vpp": 0.0, "vrms": 0.0, "twiddle_factor": 0.0
        }

        if len(channel_data) < 2 or len(tacho_trigger_data) < 2:
            if self.console:
                self.console.append_to_console(
                    f"Channel {channel_idx+1}: Insufficient data length: channel_data={len(channel_data)}, "
                    f"tacho_trigger_data={len(tacho_trigger_data)}"
                )
            return metrics

        try:
            # Basic calculations
            metrics["vpp"] = float(np.max(channel_data) - np.min(channel_data))
            metrics["vrms"] = float(np.sqrt(np.mean(np.square(channel_data))))
            metrics["direct"] = float(np.mean(channel_data))

            # Trigger detection
            threshold = np.mean(tacho_trigger_data) + 0.5 * np.std(tacho_trigger_data)
            trigger_indices = np.where(np.diff((tacho_trigger_data > threshold).astype(int)) > 0)[0]
            min_distance = 5
            filtered_trigger_indices = [trigger_indices[0]] if len(trigger_indices) > 0 else [0, len(tacho_trigger_data)-1]
            for i in range(1, len(trigger_indices)):
                if trigger_indices[i] - filtered_trigger_indices[-1] >= min_distance:
                    filtered_trigger_indices.append(trigger_indices[i])

            # RPM calculation
            if len(filtered_trigger_indices) >= 2:
                samples_per_rotation = np.mean(np.diff(filtered_trigger_indices))
                if samples_per_rotation > 0:
                    metrics["rpm"] = (60 * self.sample_rate) / samples_per_rotation
            else:
                if self.console:
                    self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient trigger points for RPM.")

            # Gap calculation
            metrics["gap"] = float(np.mean(tacho_trigger_data))

            # Harmonic calculations
            if len(filtered_trigger_indices) >= 2:
                start_idx = filtered_trigger_indices[0]
                end_idx = filtered_trigger_indices[-1]
                segment = channel_data[start_idx:end_idx]
                segment_length = end_idx - start_idx
                if segment_length > 0:
                    for harmonic, (amp_key, phase_key) in enumerate([
                        ("1x Amp", "1x Phase"),
                        ("2x Amp", "2x Phase"),
                        ("nx Amp", "nx Phase")
                    ], 1):
                        sine_sum = cosine_sum = 0.0
                        for n in range(segment_length):
                            global_idx = start_idx + n
                            theta = (2 * np.pi * harmonic * n) / segment_length
                            sine_sum += channel_data[global_idx] * np.sin(theta)
                            cosine_sum += channel_data[global_idx] * np.cos(theta)
                        metrics[amp_key] = np.sqrt((sine_sum / segment_length) ** 2 + (cosine_sum / segment_length) ** 2) * 4
                        metrics[phase_key] = np.arctan2(cosine_sum, sine_sum) * (180.0 / np.pi)
                        if metrics[phase_key] < 0:
                            metrics[phase_key] += 360
            else:
                if self.console:
                    self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient triggers for harmonic calculations.")

            # Twiddle factor
            if len(filtered_trigger_indices) >= 2:
                fft_vals = np.fft.fft(channel_data[filtered_trigger_indices[0]:filtered_trigger_indices[-1]])
                fft_phases = np.angle(fft_vals)
                phase_diffs = np.diff(fft_phases[:len(fft_phases)//2])
                metrics["twiddle_factor"] = float(np.std(phase_diffs)) if len(phase_diffs) > 0 else 0.0
            else:
                if self.console:
                    self.console.append_to_console(f"Channel {channel_idx+1}: Insufficient triggers for twiddle factor.")
        except Exception as ex:
            self.log_and_set_status(f"Error calculating metrics for channel {channel_idx+1}: {str(ex)}")

        return metrics

    def process_calibrated_data(self, data, channel_idx):
        channel_name = self.channel_names[channel_idx] if channel_idx < len(self.channel_names) else f"Channel {channel_idx+1}"
        if channel_idx >= len(data) or not data[channel_idx]:
            if self.console:
                self.console.append_to_console(f"Channel {channel_name}: No data at index {channel_idx}, using zeros.")
            return np.zeros(4096)
        props = self.channel_properties.get(channel_name, {"Unit": "mil", "CorrectionValue": 1.0, "Gain": 1.0, "Sensitivity": 1.0})
        try:
            channel_data = np.array(data[channel_idx], dtype=float) * (3.3 / 65535.0) * (props["CorrectionValue"] * props["Gain"]) / props["Sensitivity"]
            if props["Unit"].lower() == "mil":
                channel_data /= 25.4
            elif props["Unit"].lower() == "mm":
                channel_data /= 1000
            return channel_data
        except Exception as ex:
            self.log_and_set_status(f"Error calibrating data for channel {channel_name}: {str(ex)}")
            return np.zeros(4096)

    def on_data_received(self, tag_name, model_name, values, sample_rate):
        if self.console:
            self.console.append_to_console(
                f"Received data: tag_name={tag_name}, model_name={model_name}, "
                f"channels={len(values)}, sample_counts={[len(v) for v in values]}"
            )
        if self.model_name != model_name or tag_name != self.tag_name:
            if self.console:
                self.console.append_to_console(
                    f"Skipped data: model_name={model_name} (expected {self.model_name}), "
                    f"tag_name={tag_name} (expected {self.tag_name})"
                )
            return

        try:
            # Relaxed validation: accept any non-empty values
            if not values:
                if self.console:
                    self.console.append_to_console("Empty data received, using zeros for all channels.")
                values = [[] for _ in range(max(self.num_channels, 6))]
            values = values[:max(self.num_channels, 6)] + [[] for _ in range(max(self.num_channels, 6) - len(values))]
            for i in range(len(values)):
                if not values[i]:
                    values[i] = np.zeros(4096).tolist()
                elif len(values[i]) < 4096:
                    values[i] = (values[i] + [0] * (4096 - len(values[i])))[:4096]
                elif len(values[i]) > 4096:
                    values[i] = values[i][:4096]

            self.sample_rate = sample_rate if sample_rate > 0 else 4096
            self.data = values
            main_channels = min(self.num_channels, len(values), 4)
            if self.console:
                self.console.append_to_console(f"Processing {main_channels} channels for topic {tag_name}")

            headers = [
                "RPM", "Gap", "Channel Name", "DateTime", "Direct",
                "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
                "Vpp", "Vrms", "Twiddle Factor"
            ]
            frequency_data = np.array(values[4], dtype=float) if len(values) > 4 and values[4] else np.zeros(4096)
            trigger_data = np.array(values[5], dtype=float) if len(values) > 5 and values[5] else np.zeros(4096)

            for ch in range(self.num_channels):
                try:
                    channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
                    self.raw_data[ch] = self.process_calibrated_data(values, ch)
                    low_pass_cutoff = 100
                    high_pass_cutoff = 200
                    band_pass_low_cutoff = 50
                    band_pass_high_cutoff = 200
                    tap_num = 31
                    nyquist = self.sample_rate / 2.0

                    if low_pass_cutoff >= nyquist or high_pass_cutoff >= nyquist or band_pass_low_cutoff >= band_pass_high_cutoff or band_pass_high_cutoff >= nyquist:
                        self.log_and_set_status(f"Invalid filter cutoff frequencies for channel {channel_name}.")
                        self.raw_data[ch] = np.zeros(4096)
                        self.low_pass_data[ch] = np.zeros(4096)
                        self.high_pass_data[ch] = np.zeros(4096)
                        self.band_pass_data[ch] = np.zeros(4096)
                        self.update_table_row(ch, channel_name, {})
                        continue

                    low_pass_coeffs = signal.firwin(tap_num, low_pass_cutoff / nyquist, window='hamming')
                    high_pass_coeffs = signal.firwin(tap_num, high_pass_cutoff / nyquist, window='hamming', pass_zero=False)
                    band_pass_coeffs = signal.firwin(tap_num, [band_pass_low_cutoff / nyquist, band_pass_high_cutoff / nyquist], window='hamming', pass_zero=False)

                    self.low_pass_data[ch] = signal.lfilter(low_pass_coeffs, 1.0, self.raw_data[ch])
                    self.high_pass_data[ch] = signal.lfilter(high_pass_coeffs, 1.0, self.raw_data[ch])
                    self.band_pass_data[ch] = signal.lfilter(band_pass_coeffs, 1.0, self.raw_data[ch])

                    self.average_frequency[ch] = np.mean(frequency_data[frequency_data > 0]) if np.any(frequency_data > 0) else 0.0

                    trigger_indices = np.where(trigger_data > np.mean(trigger_data) + 0.5 * np.std(trigger_data))[0]
                    min_distance_between_triggers = 5
                    filtered_trigger_indices = [trigger_indices[0]] if len(trigger_indices) > 0 else [0, len(trigger_data)-1]
                    for i in range(1, len(trigger_indices)):
                        if trigger_indices[i] - filtered_trigger_indices[-1] >= min_distance_between_triggers:
                            filtered_trigger_indices.append(trigger_indices[i])

                    band_pass_peak_to_peak_values = []
                    for i in range(len(filtered_trigger_indices) - 1):
                        start_idx = filtered_trigger_indices[i]
                        end_idx = filtered_trigger_indices[i + 1]
                        segment = self.band_pass_data[ch][start_idx:end_idx]
                        if len(segment) > 0:
                            band_pass_peak_to_peak_values.append(np.max(segment) - np.min(segment))
                    self.band_pass_peak_to_peak[ch] = np.mean(band_pass_peak_to_peak_values) if band_pass_peak_to_peak_values else 0.0
                    self.band_pass_peak_to_peak_history[ch].append(self.band_pass_peak_to_peak[ch])
                    self.band_pass_peak_to_peak_times[ch].append((datetime.now() - self.start_time).total_seconds())

                    metrics = self.calculate_metrics(self.raw_data[ch], trigger_data, ch)
                    channel_data = {
                        "Channel Name": channel_name,
                        "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "RPM": f"{metrics['rpm']:.2f}",
                        "Gap": f"{metrics['gap']:.2f}",
                        "Direct": f"{metrics['direct']:.2f}",
                        "1x Amp": f"{metrics['1x Amp']:.2f}",
                        "1x Phase": f"{metrics['1x Phase']:.2f}",
                        "2x Amp": f"{metrics['2x Amp']:.2f}",
                        "2x Phase": f"{metrics['2x Phase']:.2f}",
                        "nx Amp": f"{metrics['nx Amp']:.2f}",
                        "nx Phase": f"{metrics['nx Phase']:.2f}",
                        "Vpp": f"{metrics['vpp']:.2f}",
                        "Vrms": f"{metrics['vrms']:.2f}",
                        "Twiddle Factor": f"{metrics['twiddle_factor']:.2f}"
                    }

                    self.update_table_row(ch, channel_name, channel_data)
                    if self.console:
                        self.console.append_to_console(f"Updated table for channel {channel_name}: {channel_data}")
                except Exception as ex:
                    self.log_and_set_status(f"Error processing channel {channel_name}: {str(ex)}")
                    self.raw_data[ch] = np.zeros(4096)
                    self.low_pass_data[ch] = np.zeros(4096)
                    self.high_pass_data[ch] = np.zeros(4096)
                    self.band_pass_data[ch] = np.zeros(4096)
                    self.update_table_row(ch, channel_name, {})

            self.update_plots()
            if self.console:
                self.console.append_to_console(f"Processed data for topic {tag_name}, {main_channels} channels: Updated table and plots.")
        except Exception as ex:
            self.log_and_set_status(f"Error processing data: {str(ex)}")
            for ch in range(self.num_channels):
                channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
                self.update_table_row(ch, channel_name, {})
            self.update_plots()

    def update_table_row(self, row, channel_name, channel_data):
        headers = [
            "RPM", "Gap", "Channel Name", "DateTime", "Direct",
            "1x Amp", "1x Phase", "2x Amp", "2x Phase", "nx Amp", "nx Phase",
            "Vpp", "Vrms", "Twiddle Factor"
        ]
        default_data = {
            "Channel Name": channel_name,
            "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "RPM": "0.00",
            "Gap": "0.00",
            "Direct": "0.00",
            "1x Amp": "0.00",
            "1x Phase": "0.00",
            "2x Amp": "0.00",
            "2x Phase": "0.00",
            "nx Amp": "0.00",
            "nx Phase": "0.00",
            "Vpp": "0.00",
            "Vrms": "0.00",
            "Twiddle Factor": "0.00"
        }
        data = channel_data if channel_data else default_data
        for col, header in enumerate(headers):
            self.table.setItem(row, col, QTableWidgetItem(data[header]))

    def update_plots(self):
        """Update all plots for the selected channel."""
        if not self.plot_initialized:
            self.log_and_set_status("Plots not initialized, skipping update.")
            return

        if self.selected_channel_idx >= self.num_channels:
            self.selected_channel_idx = 0
            self.channel_selector.setCurrentIndex(1 if self.channel_names else 0)
            if self.console:
                self.console.append_to_console(f"Selected channel index {self.selected_channel_idx} out of range, defaulting to 0")

        ch = self.selected_channel_idx
        channel_name = self.channel_names[ch] if ch < len(self.channel_names) else f"Channel {ch+1}"
        trim_samples = 47
        low_pass_trim = 0
        high_pass_trim = 110
        band_pass_trim = 110
        raw_trim = trim_samples

        if len(self.raw_data[ch]) <= trim_samples:
            if self.console:
                self.console.append_to_console(f"Channel {channel_name}: Warning: Data length ({len(self.raw_data[ch])}) too short to trim {trim_samples} samples for plotting.")
            low_pass_trim = high_pass_trim = band_pass_trim = raw_trim = 0

        data_sets = [
            (self.raw_data[ch], raw_trim, f"Channel {channel_name} Raw Data"),
            (self.low_pass_data[ch], low_pass_trim, f"Channel {channel_name} Low-Pass Filtered Data (100 Hz Cutoff)"),
            (self.high_pass_data[ch], high_pass_trim, f"Channel {channel_name} High-Pass Filtered Data (200 Hz Cutoff)"),
            (self.band_pass_data[ch], band_pass_trim, f"Channel {channel_name} Band-Pass Filtered Data (50-200 Hz) ({self.average_frequency[ch]:.2f} Hz, Peak-to-Peak: {self.band_pass_peak_to_peak[ch]:.2f})")
        ]

        for i, (data, trim, title) in enumerate(data_sets):
            self.plots[i].clear()
            trimmed_data = data[trim:] if len(data) > trim else (data if len(data) > 0 else np.array([0]))
            trimmed_time = self.time_points[trim:] if len(self.time_points) > trim else (self.time_points if len(self.time_points) > 0 else np.array([0]))
            self.plots[i].setData(trimmed_time, trimmed_data)
            self.plot_widgets[i].setTitle(title)
            self.plot_widgets[i].setYRange(np.min(trimmed_data) * 1.1 if trimmed_data.size > 0 else -1, np.max(trimmed_data) * 1.1 if trimmed_data.size > 0 else 1)
            if self.console:
                self.console.append_to_console(f"Updated plot {i+1} for channel {channel_name}: {len(trimmed_data)} samples")

        # Update peak-to-peak plot
        self.plots[4].clear()
        frequency_values = [self.average_frequency[ch] + (i * 0.1) for i in range(len(self.band_pass_peak_to_peak_history[ch]))]
        if frequency_values and self.band_pass_peak_to_peak_history[ch]:
            self.plots[4].setData(frequency_values, self.band_pass_peak_to_peak_history[ch])
            self.plot_widgets[4].setYRange(0, max(0.01, max(self.band_pass_peak_to_peak_history[ch], default=0) * 1.1))
            if self.console:
                self.console.append_to_console(f"Updated peak-to-peak plot for channel {channel_name}: {len(frequency_values)} points")
        else:
            self.plots[4].setData(np.array([0]), np.array([0]))
            self.plot_widgets[4].setYRange(0, 0.01)
            if self.console:
                self.console.append_to_console(f"Channel {channel_name}: No data for bandpass peak-to-peak plot")

    def log_and_set_status(self, message):
        logging.error(message)
        if self.console:
            self.console.append_to_console(message)

    def close(self):
        self.mongo_client.close()