# from PyQt5.QtWidgets import (
#     QToolBar, QAction, QWidget, QHBoxLayout, QSizePolicy, QLineEdit,
#     QLabel, QDialog, QVBoxLayout, QPushButton, QGridLayout, QComboBox, QMessageBox
# )
# from PyQt5.QtCore import QSize, Qt, QTimer
# from PyQt5.QtGui import QIcon
# import logging
# import re
# from datetime import datetime

# class LayoutSelectionDialog(QDialog):
#     def __init__(self, parent=None, current_layout=None):
#         super().__init__(parent)
#         self.setWindowTitle("Select Layout")
#         self.setFixedSize(300, 300)
#         self.setWindowFlags(Qt.Popup)

#         self.selected_layout = current_layout
#         self.layout_buttons = {}

#         layout = QVBoxLayout()
#         label = QLabel("Choose a layout:")
#         label.setAlignment(Qt.AlignCenter)
#         label.setStyleSheet("""
#             QLabel {
#                 font-size: 16px;
#                 font-weight: bold;
#                 color: black;
#                 margin-bottom: 10px;
#             }
#         """)
#         layout.addWidget(label)

#         grid = QGridLayout()
#         layouts = {
#             "1x2": "⬛⬛",
#             "2x2": "⬛⬛\n⬛⬛",
#             "3x3": "⬛⬛⬛\n⬛⬛⬛\n⬛⬛⬛"
#         }

#         row, col = 0, 0
#         for layout_name, icon in layouts.items():
#             btn = QPushButton(icon)
#             btn.setFixedSize(80, 80)
#             btn.setToolTip(layout_name)
#             self.layout_buttons[layout_name] = btn
#             btn.clicked.connect(lambda _, l=layout_name: self.select_layout(l))
#             grid.addWidget(btn, row, col)
#             col += 1
#             if col >= 3:
#                 row += 1
#                 col = 0

#         layout.addLayout(grid)
#         self.setLayout(layout)
#         self.update_button_styles()

#     def update_button_styles(self):
#         for layout_name, btn in self.layout_buttons.items():
#             if layout_name == self.selected_layout:
#                 btn.setStyleSheet("background-color: #4a90e2; color: white; font-weight: bold;")
#             else:
#                 btn.setStyleSheet("background-color: #cfd8dc;")

#     def select_layout(self, layout):
#         self.selected_layout = layout
#         self.update_button_styles()
#         self.accept()

# class SubToolBar(QWidget):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.parent = parent
#         self.selected_layout = "2x2"
#         self.filename_edit = None
#         self.saved_files_combo = None
#         self.is_saving = False
#         self.start_button = None
#         self.stop_button = None
#         self.blink_timer = None
#         self.blink_state = False
#         self.save_timer = None
#         self.current_feature_instance = None
#         self.current_filename = None
#         self.selected_saved_file = None
#         self.is_refreshing = False
#         self.debounce_timer = QTimer(self)
#         self.debounce_timer.setSingleShot(True)
#         self.cached_filenames = []
#         self.initUI()
#         try:
#             self.parent.mqtt_status_changed.connect(self.update_subtoolbar)
#             logging.info("SubToolBar: mqtt_status_changed signal connected")
#         except AttributeError as e:
#             logging.error(f"SubToolBar: Failed to connect signal: {e}")

#     def initUI(self):
#         self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
#         layout = QHBoxLayout()
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(10)
#         self.setLayout(layout)

#         self.toolbar = QToolBar("Controls")
#         self.toolbar.setFixedHeight(100)
#         layout.addWidget(self.toolbar)
#         self.update_subtoolbar()

#     def update_subtoolbar(self):
#         if self.is_refreshing:
#             return
#         self.is_refreshing = True
#         logging.debug(f"SubToolBar: Updating toolbar, MQTT connected: {self.parent.mqtt_connected}")
#         self.toolbar.clear()
#         self.toolbar.setStyleSheet("""
#             QToolBar { border: none; padding: 5px; spacing: 10px; }
#             QToolButton { border: none; padding: 8px; border-radius: 5px; font-size: 24px; color: white; }
#             QToolButton:hover { background-color: #4a90e2; }
#             QToolButton:pressed { background-color: #357abd; }
#             QToolButton:focus { outline: none; border: 1px solid #4a90e2; }
#             QToolButton:disabled { background-color: #546e7a; color: #b0bec5; }
#         """)
#         self.toolbar.setIconSize(QSize(25, 25))
#         self.toolbar.setMovable(False)
#         self.toolbar.setFloatable(False)

#         self.filename_edit = QLineEdit()
#         self.filename_edit.setStyleSheet("""
#             QLineEdit {
#                 background-color: #ffffff;
#                 color: #212121;
#                 border: 1px solid #90caf9;
#                 border-radius: 4px;
#                 padding: 4px 8px;
#                 font-size: 14px;
#                 font-weight: 500;
#                 min-width: 200px;
#                 max-width: 250px;
#             }
#             QLineEdit:hover {
#                 border: 1px solid #42a5f5;
#                 background-color: #f5faff;
#             }
#             QLineEdit:focus {
#                 border: 1px solid #1e88e5;
#                 background-color: #ffffff;
#             }
#         """)
#         self.filename_edit.setPlaceholderText("Enter filename (e.g., data1)")
#         self.toolbar.addWidget(self.filename_edit)

#         self.start_button = QPushButton("▶")
#         self.start_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #43a047;
#                 color: white;
#                 padding: 5px 10px;
#                 border-radius: 5px;
#                 font-size: 24px;
#             }
#             QPushButton:hover {
#                 background-color: #66bb6a;
#             }
#             QPushButton:pressed {
#                 background-color: #388e3c;
#             }
#             QPushButton:disabled {
#                 background-color: #546e7a;
#                 color: #b0bec5;
#             }
#         """)
#         self.start_button.clicked.connect(self.start_saving)
#         self.start_button.setEnabled(self.parent.mqtt_connected and not self.is_saving)
#         self.toolbar.addWidget(self.start_button)

#         self.stop_button = QPushButton("⏸")
#         self.stop_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #ef5350;
#                 color: white;
#                 padding: 5px 10px;
#                 border-radius: 5px;
#                 font-size: 24px;
#             }
#             QPushButton:hover {
#                 background-color: #f44336;
#             }
#             QPushButton:pressed {
#                 background-color: #d32f2f;
#             }
#             QPushButton:disabled {
#                 background-color: #546e7a;
#                 color: #b0bec5;
#             }
#         """)
#         self.stop_button.clicked.connect(self.stop_saving)
#         self.stop_button.setEnabled(self.is_saving)
#         self.toolbar.addWidget(self.stop_button)

#         self.saved_files_combo = QComboBox()
#         self.saved_files_combo.setStyleSheet("""
#             QComboBox {
#                 background-color: #ffffff;
#                 color: #212121;
#                 border: 1px solid #90caf9;
#                 border-radius: 4px;
#                 padding: 4px 8px;
#                 font-size: 14px;
#                 font-weight: 500;
#                 min-width: 200px;
#                 max-width: 250px;
#             }
#             QComboBox:hover {
#                 border: 1px solid #42a5f5;
#                 background-color: #f5faff;
#             }
#             QComboBox:focus {
#                 border: 1px solid #1e88e5;
#                 background-color: #ffffff;
#             }
#         """)
#         self.saved_files_combo.addItem("Select Saved File")
#         self.saved_files_combo.currentTextChanged.connect(self.on_saved_file_selected)
#         self.toolbar.addWidget(self.saved_files_combo)

#         self.toolbar.addSeparator()

#         def add_action(text_icon, color, callback, tooltip, enabled, background_color):
#             action = QAction(text_icon, self)
#             action.triggered.connect(callback)
#             action.setToolTip(tooltip)
#             action.setEnabled(enabled)
#             self.toolbar.addAction(action)
#             button = self.toolbar.widgetForAction(action)
#             if button:
#                 button.setStyleSheet(f"""
#                     QToolButton {{
#                         color: {color};
#                         font-size: 24px;
#                         border: none;
#                         padding: 8px;
#                         border-radius: 5px;
#                         background-color: {background_color if enabled else '#546e7a'};
#                     }}
#                     QToolButton:hover {{
#                         background-color: #4a90e2;
#                     }}
#                     QToolButton:pressed {{
#                         background-color: #357abd;
#                     }}
#                     QToolButton:disabled {{
#                         background-color: #546e7a;
#                         color: #b0bec5;
#                     }}
#                 """)
#                 logging.debug(f"SubToolBar: Added action '{text_icon}', enabled: {enabled}")

#         connect_enabled = not self.parent.mqtt_connected
#         disconnect_enabled = self.parent.mqtt_connected
#         connect_bg = "#43a047" if connect_enabled else "#546e7a"
#         disconnect_bg = "#ef5350" if disconnect_enabled else "#546e7a"
#         add_action("🔗", "#ffffff", self.parent.connect_mqtt, "Connect to MQTT", connect_enabled, connect_bg)
#         add_action("🔌", "#ffffff", self.parent.disconnect_mqtt, "Disconnect from MQTT", disconnect_enabled, disconnect_bg)
#         self.toolbar.addSeparator()

#         spacer = QWidget()
#         spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
#         self.toolbar.addWidget(spacer)

#         layout_action = QAction("🖼️", self)
#         layout_action.setToolTip("Select Layout")
#         layout_action.triggered.connect(self.show_layout_menu)
#         self.toolbar.addAction(layout_action)
#         layout_button = self.toolbar.widgetForAction(layout_action)
#         if layout_button:
#             layout_button.setStyleSheet("""
#                 QToolButton {
#                     color: #ffffff;
#                     font-size: 24px;
#                     border: none;
#                     padding: 8px;
#                     border-radius: 5px;
#                 }
#                 QToolButton:hover { background-color: #4a90e2; }
#                 QToolButton:pressed { background-color: #357abd; }
#             """)

#         self.toolbar.repaint()
#         self.repaint()
#         self.refresh_filename()
#         self.refresh_saved_files()
#         self.is_refreshing = False

#     def start_saving(self):
#         if not self.parent.mqtt_connected:
#             QMessageBox.warning(self, "Error", "MQTT is not connected!")
#             return
#         if not self.parent.current_project:
#             QMessageBox.warning(self, "Error", "No project selected!")
#             return
#         if not self.parent.current_feature:
#             QMessageBox.warning(self, "Error", "No feature selected!")
#             return
#         selected_model = self.parent.tree_view.get_selected_model()
#         if not selected_model:
#             QMessageBox.warning(self, "Error", "Please select a model!")
#             return
#         selected_channel = self.parent.tree_view.get_selected_channel() if self.parent.current_feature not in ["Time View", "Time Report"] else None
#         if not selected_channel and self.parent.current_feature not in ["Time View", "Time Report"]:
#             QMessageBox.warning(self, "Error", f"Please select a channel for {self.parent.current_feature}!")
#             return

#         filename = self.filename_edit.text()
#         if not filename or not re.match(r"data\d+", filename):
#             QMessageBox.warning(self, "Error", "Please enter a valid filename (e.g., data1)!")
#             return

#         try:
#             feature_name = self.parent.current_feature
#             model_name = selected_model
#             channel = selected_channel

#             feature_instance = None
#             for key, instance in self.parent.feature_instances.items():
#                 f_name, m_name, c_name, _ = key
#                 if f_name == feature_name and m_name == model_name and c_name == channel:
#                     feature_instance = instance
#                     break

#             if not feature_instance:
#                 logging.warning(f"No active feature instance found for {feature_name}/{model_name}/{channel or 'No Channel'}")
#                 self.parent.console.append_to_console(f"No active feature instance found to save for {feature_name}")
#                 QMessageBox.warning(self, "Error", "No active feature instance found to save!")
#                 return

#             self.current_feature_instance = feature_instance
#             self.current_filename = filename
#             self.is_saving = True
#             self.start_button.setEnabled(False)
#             self.stop_button.setEnabled(True)
#             self.start_blinking()

#             if not self.save_timer:
#                 self.save_timer = QTimer(self)
#                 self.save_timer.timeout.connect(self.save_data)
#             self.save_timer.start(1000)

#             self.parent.console.append_to_console(f"Started saving data to {filename} for {feature_name}")
#             self.refresh_saved_files()  # Update dropdown to include new filename
#         except Exception as e:
#             logging.error(f"SubToolBar: Error starting saving: {str(e)}")
#             self.parent.console.append_to_console(f"Error starting saving: {str(e)}")
#             QMessageBox.warning(self, "Error", f"Error starting saving: {str(e)}")

#     def stop_saving(self):
#         try:
#             if self.is_saving:
#                 self.is_saving = False
#                 self.start_button.setEnabled(self.parent.mqtt_connected)
#                 self.stop_button.setEnabled(False)
#                 self.stop_blinking()
#                 if self.save_timer:
#                     self.save_timer.stop()
#                 self.parent.console.append_to_console(f"Stopped saving data for {self.parent.current_feature}")
#                 self.current_feature_instance = None
#                 self.current_filename = None
#                 self.refresh_saved_files()
#                 self.refresh_filename()
#         except Exception as e:
#             logging.error(f"SubToolBar: Error stopping saving: {str(e)}")
#             self.parent.console.append_to_console(f"Error stopping saving: {str(e)}")
#             QMessageBox.warning(self, "Error", f"Error stopping saving: {str(e)}")

#     def start_blinking(self):
#         if not self.blink_timer:
#             self.blink_timer = QTimer(self)
#             self.blink_timer.timeout.connect(self.toggle_blink)
#         self.blink_timer.start(500)
#         self.blink_state = True
#         self.toggle_blink()

#     def stop_blinking(self):
#         if self.blink_timer:
#             self.blink_timer.stop()
#         self.start_button.setStyleSheet("""
#             QPushButton {
#                 background-color: #43a047;
#                 color: white;
#                 padding: 5px 10px;
#                 border-radius: 5px;
#                 font-size: 24px;
#             }
#             QPushButton:hover {
#                 background-color: #66bb6a;
#             }
#             QPushButton:pressed {
#                 background-color: #388e3c;
#             }
#             QPushButton:disabled {
#                 background-color: #546e7a;
#                 color: #b0bec5;
#             }
#         """)

#     def toggle_blink(self):
#         self.blink_state = not self.blink_state
#         color = "#ff0000" if self.blink_state else "#43a047"
#         self.start_button.setStyleSheet(f"""
#             QPushButton {{
#                 background-color: {color};
#                 color: white;
#                 padding: 5px 10px;
#                 border-radius: 5px;
#                 font-size: 24px;
#             }}
#             QPushButton:disabled {{
#                 background-color: #546e7a;
#                 color: #b0bec5;
#             }}
#         """)

#     def save_data(self):
#         if not self.is_saving or not self.current_feature_instance:
#             return

#         try:
#             feature_name = self.parent.current_feature
#             model_name = self.parent.tree_view.get_selected_model()
#             filename = self.current_filename

#             data = self.collect_feature_data(self.current_feature_instance, feature_name)
#             if not data:
#                 self.parent.console.append_to_console(f"No data available to save for {feature_name}")
#                 logging.warning(f"No data available to save for {feature_name}")
#                 return

#             message_data = {
#                 "topic": "dashboard_data",
#                 "filename": filename,
#                 "frameIndex": 0,
#                 "message": data,
#                 "numberOfChannels": len(data.get("channel_data", [])) if feature_name in ["Time View", "Time Report"] else 1,
#                 "samplingRate": getattr(self.current_feature_instance, 'sample_rate', 4096),
#                 "samplingSize": len(data.get("channel_data", [[]])[0]) if feature_name in ["Time View", "Time Report"] else len(data.get("data", [])),
#                 "messageFrequency": None,
#                 "tachoChannelCount": data.get("tacho_channels_count", 0) if feature_name in ["Time View", "Time Report"] else 0,
#                 "createdAt": datetime.now().isoformat(),
#                 "projectName": self.parent.current_project,
#                 "moduleName": model_name,
#                 "featureName": feature_name,
#                 "email": self.parent.email
#             }

#             success, msg = self.parent.db.save_feature_message(self.parent.current_project, model_name, feature_name, message_data)
#             if success:
#                 self.parent.console.append_to_console(f"Saved data to {filename} for {feature_name}")
#                 self.cached_filenames.append(filename)
#                 self.refresh_saved_files()
#             else:
#                 self.parent.console.append_to_console(f"Failed to save data: {msg}")
#                 logging.error(f"SubToolBar: Failed to save data: {msg}")
#         except Exception as e:
#             logging.error(f"SubToolBar: Error saving data: {str(e)}")
#             self.parent.console.append_to_console(f"Error saving data: {str(e)}")

#     def collect_feature_data(self, feature_instance, feature_name):
#         try:
#             if feature_name in ["Time View", "Time Report"]:
#                 if not hasattr(feature_instance, 'fifo_data') or not hasattr(feature_instance, 'main_channels'):
#                     logging.warning(f"Feature {feature_name} lacks required attributes for data collection")
#                     return {}
#                 data = {
#                     "channel_data": [list(data) for data in feature_instance.fifo_data[:feature_instance.main_channels]],
#                     "tacho_freq": list(feature_instance.fifo_data[feature_instance.main_channels]) if feature_instance.tacho_channels_count >= 1 else [],
#                     "tacho_trigger": list(feature_instance.fifo_data[feature_instance.main_channels + 1]) if feature_instance.tacho_channels_count >= 2 else [],
#                     "tacho_channels_count": feature_instance.tacho_channels_count
#                 }
#                 return data if any(data["channel_data"]) else {}
#             elif feature_name in [
#                 "Tabular View", "FFT", "Waterfall", "Centerline", "Orbit",
#                 "Trend View", "Multiple Trend View", "Bode Plot", "History Plot",
#                 "Polar Plot", "Report"
#             ]:
#                 if hasattr(feature_instance, 'get_current_data'):
#                     data = feature_instance.get_current_data()
#                     if data:
#                         return {"data": data}
#                 logging.warning(f"SubToolBar: No data collection implemented for {feature_name}")
#                 return {}
#             else:
#                 logging.warning(f"SubToolBar: Unknown feature {feature_name} in collect_feature_data")
#                 return {}
#         except Exception as e:
#             logging.error(f"SubToolBar: Error collecting data for {feature_name}: {str(e)}")
#             return {}

#     def refresh_filename(self):
#         if not self.filename_edit:
#             logging.warning("SubToolBar: No filename_edit initialized")
#             return
#         try:
#             model_name = self.parent.tree_view.get_selected_model() if self.parent.tree_view else None
#             filenames = self.cached_filenames or (self.parent.db.get_distinct_filenames(self.parent.current_project, model_name) if self.parent.current_project else [])
#             filename_counter = 1
#             if filenames:
#                 numbers = [int(re.match(r"data(\d+)", f).group(1)) for f in filenames if re.match(r"data(\d+)", f)]
#                 filename_counter = max(numbers, default=0) + 1 if numbers else 1
#             next_filename = f"data{filename_counter}"
#             self.filename_edit.setText(next_filename)
#             self.filename_edit.repaint()
#         except Exception as e:
#             logging.error(f"SubToolBar: Error refreshing filename: {str(e)}")
#             self.filename_edit.setText("data1")

#     def refresh_saved_files(self):
#         if self.is_refreshing:
#             return
#         self.is_refreshing = True
#         try:
#             model_name = self.parent.tree_view.get_selected_model() if self.parent.tree_view else None
#             feature_name = self.parent.current_feature
#             if not self.parent.current_project or not feature_name or not model_name:
#                 self.saved_files_combo.clear()
#                 self.saved_files_combo.addItem("Select Saved File")
#                 self.cached_filenames = []
#                 logging.debug(f"SubToolBar: No project/feature/model, cleared saved files")
#                 self.is_refreshing = False
#                 return

#             filenames = self.parent.db.get_distinct_filenames(self.parent.current_project, model_name, feature_name)
#             self.cached_filenames = sorted(set(filenames))  # Cache and sort filenames
#             self.saved_files_combo.blockSignals(True)
#             self.saved_files_combo.clear()
#             self.saved_files_combo.addItem("Select Saved File")
#             if self.cached_filenames:
#                 for filename in self.cached_filenames:
#                     self.saved_files_combo.addItem(filename)
#             logging.debug(f"SubToolBar: Refreshed saved files with {len(self.cached_filenames)} files for feature {feature_name}")
#         except Exception as e:
#             logging.error(f"SubToolBar: Error refreshing saved files: {str(e)}")
#             self.saved_files_combo.clear()
#             self.saved_files_combo.addItem("Select Saved File")
#             self.cached_filenames = []
#         finally:
#             self.saved_files_combo.blockSignals(False)
#             self.is_refreshing = False

#     def on_saved_file_selected(self, text):
#         if self.debounce_timer.isActive():
#             return
#         self.debounce_timer.start(200)  # Debounce for 200ms
#         try:
#             if text == "Select Saved File" or not text:
#                 self.selected_saved_file = None
#                 logging.debug("SubToolBar: Cleared selected saved file")
#                 return
#             if text not in self.cached_filenames:
#                 logging.warning(f"SubToolBar: Selected file {text} not in cached filenames")
#                 self.parent.console.append_to_console(f"Selected file {text} not found")
#                 return

#             self.selected_saved_file = text
#             logging.info(f"SubToolBar: Selected saved file: {text}")
#             if not self.parent.current_feature:
#                 logging.warning("SubToolBar: No feature selected for loading saved file")
#                 self.parent.console.append_to_console("No feature selected to load saved file")
#                 QMessageBox.warning(self, "Error", "Please select a feature before loading a saved file")
#                 return
#             if not self.parent.current_project:
#                 logging.warning("SubToolBar: No project selected for loading saved file")
#                 self.parent.console.append_to_console("No project selected to load saved file")
#                 QMessageBox.warning(self, "Error", "Please select a project before loading a saved file")
#                 return
#             if not self.parent.tree_view.get_selected_model():
#                 logging.warning("SubToolBar: No model selected for loading saved file")
#                 self.parent.console.append_to_console("No model selected to load saved file")
#                 QMessageBox.warning(self, "Error", "Please select a model before loading a saved file")
#                 return
#             if self.parent.current_feature not in ["Time View", "Time Report"] and not self.parent.tree_view.get_selected_channel():
#                 logging.warning(f"SubToolBar: No channel selected for {self.parent.current_feature}")
#                 self.parent.console.append_to_console(f"No channel selected for {self.parent.current_feature}")
#                 QMessageBox.warning(self, "Error", f"Please select a channel for {self.parent.current_feature}")
#                 return

#             self.parent.clear_content_layout()
#             self.parent.display_feature_content(self.parent.current_feature, self.parent.current_project, filename=text)
#             self.parent.console.append_to_console(f"Requested load of saved file: {text} for feature: {self.parent.current_feature}")
#         except Exception as e:
#             logging.error(f"SubToolBar: Error handling saved file selection {text}: {str(e)}")
#             self.parent.console.append_to_console(f"Error loading saved file {text}: {str(e)}")
#             QMessageBox.warning(self, "Error", f"Error loading saved file {text}: {str(e)}")

#     def show_layout_menu(self):
#         dialog = LayoutSelectionDialog(self, current_layout=self.selected_layout)
#         parent_geom = self.parent.geometry()
#         dialog_width = dialog.width()
#         dialog_height = dialog.height()
#         center_x = parent_geom.x() + (parent_geom.width() - dialog_width) // 2
#         center_y = parent_geom.y() + (parent_geom.height() - dialog_height) // 2
#         dialog.move(center_x, center_y)
#         if dialog.exec_() == QDialog.Accepted:
#             self.on_layout_selected(dialog.selected_layout)

#     def on_layout_selected(self, layout):
#         self.selected_layout = layout
#         self.parent.main_section.arrange_layout(layout=self.selected_layout)


from PyQt5.QtWidgets import (
    QToolBar, QAction, QWidget, QHBoxLayout, QSizePolicy, QLineEdit,
    QLabel, QDialog, QVBoxLayout, QPushButton, QGridLayout, QComboBox, QMessageBox
)
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon
import logging
import re
from datetime import datetime

class LayoutSelectionDialog(QDialog):
    def __init__(self, parent=None, current_layout=None):
        super().__init__(parent)
        self.setWindowTitle("Select Layout")
        self.setFixedSize(300, 300)
        self.setWindowFlags(Qt.Popup)

        self.selected_layout = current_layout
        self.layout_buttons = {}

        layout = QVBoxLayout()
        label = QLabel("Choose a layout:")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: black;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(label)

        grid = QGridLayout()
        layouts = {
            "1x2": "⬛⬛",
            "2x2": "⬛⬛\n⬛⬛",
            "3x3": "⬛⬛⬛\n⬛⬛⬛\n⬛⬛⬛"
        }

        row, col = 0, 0
        for layout_name, icon in layouts.items():
            btn = QPushButton(icon)
            btn.setFixedSize(80, 80)
            btn.setToolTip(layout_name)
            self.layout_buttons[layout_name] = btn
            btn.clicked.connect(lambda _, l=layout_name: self.select_layout(l))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                row += 1
                col = 0

        layout.addLayout(grid)
        self.setLayout(layout)
        self.update_button_styles()

    def update_button_styles(self):
        for layout_name, btn in self.layout_buttons.items():
            if layout_name == self.selected_layout:
                btn.setStyleSheet("background-color: #4a90e2; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #cfd8dc;")

    def select_layout(self, layout):
        self.selected_layout = layout
        self.update_button_styles()
        self.accept()

class SubToolBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.selected_layout = "2x2"
        self.filename_edit = None
        self.saved_files_combo = None
        self.is_saving = False
        self.start_button = None
        self.stop_button = None
        self.saving_label = None
        self.blink_timer = None
        self.blink_state = False
        self.save_timer = None
        self.current_feature_instance = None
        self.current_filename = None
        self.selected_saved_file = None
        self.is_refreshing = False
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.cached_filenames = []
        self.initUI()
        try:
            self.parent.mqtt_status_changed.connect(self.update_subtoolbar)
            logging.info("SubToolBar: mqtt_status_changed signal connected")
        except AttributeError as e:
            logging.error(f"SubToolBar: Failed to connect signal: {e}")

    def initUI(self):
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eceff1, stop:1 #cfd8dc);")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.toolbar = QToolBar("Controls")
        self.toolbar.setFixedHeight(100)
        layout.addWidget(self.toolbar)
        self.update_subtoolbar()

    def update_subtoolbar(self):
        if self.is_refreshing:
            return
        self.is_refreshing = True
        logging.debug(f"SubToolBar: Updating toolbar, MQTT connected: {self.parent.mqtt_connected}")
        self.toolbar.clear()
        self.toolbar.setStyleSheet("""
            QToolBar { border: none; padding: 5px; spacing: 10px; }
            QToolButton { border: none; padding: 8px; border-radius: 5px; font-size: 24px; color: white; }
            QToolButton:hover { background-color: #4a90e2; }
            QToolButton:pressed { background-color: #357abd; }
            QToolButton:focus { outline: none; border: 1px solid #4a90e2; }
            QToolButton:disabled { background-color: #546e7a; color: #b0bec5; }
        """)
        self.toolbar.setIconSize(QSize(25, 25))
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        self.filename_edit = QLineEdit()
        self.filename_edit.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                color: #212121;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
                max-width: 250px;
            }
            QLineEdit:hover {
                border: 1px solid #42a5f5;
                background-color: #f5faff;
            }
            QLineEdit:focus {
                border: 1px solid #1e88e5;
                background-color: #ffffff;
            }
        """)
        self.filename_edit.setPlaceholderText("Enter filename (e.g., data1)")
        self.toolbar.addWidget(self.filename_edit)

        self.start_button = QPushButton("▶")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #546e7a;
                color: #b0bec5;
            }
        """)
        self.start_button.clicked.connect(self.start_saving)
        self.start_button.setEnabled(self.parent.mqtt_connected and not self.is_saving)
        self.toolbar.addWidget(self.start_button)

        self.stop_button = QPushButton("⏸")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #ef5350;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 24px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #546e7a;
                color: #b0bec5;
            }
        """)
        self.stop_button.clicked.connect(self.stop_saving)
        self.stop_button.setEnabled(self.is_saving)
        self.toolbar.addWidget(self.stop_button)

        self.saving_label = QLabel("Not Saving")
        self.saving_label.setStyleSheet("color: white; font-size: 16px;")
        self.toolbar.addWidget(self.saving_label)

        self.saved_files_combo = QComboBox()
        self.saved_files_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #212121;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 500;
                min-width: 200px;
                max-width: 250px;
            }
            QComboBox:hover {
                border: 1px solid #42a5f5;
                background-color: #f5faff;
            }
            QComboBox:focus {
                border: 1px solid #1e88e5;
                background-color: #ffffff;
            }
        """)
        self.saved_files_combo.addItem("Select Saved File")
        self.saved_files_combo.currentTextChanged.connect(self.on_saved_file_selected)
        self.toolbar.addWidget(self.saved_files_combo)

        self.toolbar.addSeparator()

        def add_action(text_icon, color, callback, tooltip, enabled, background_color):
            action = QAction(text_icon, self)
            action.triggered.connect(callback)
            action.setToolTip(tooltip)
            action.setEnabled(enabled)
            self.toolbar.addAction(action)
            button = self.toolbar.widgetForAction(action)
            if button:
                button.setStyleSheet(f"""
                    QToolButton {{
                        color: {color};
                        font-size: 24px;
                        border: none;
                        padding: 8px;
                        border-radius: 5px;
                        background-color: {background_color if enabled else '#546e7a'};
                    }}
                    QToolButton:hover {{
                        background-color: #4a90e2;
                    }}
                    QToolButton:pressed {{
                        background-color: #357abd;
                    }}
                    QToolButton:disabled {{
                        background-color: #546e7a;
                        color: #b0bec5;
                    }}
                """)
                logging.debug(f"SubToolBar: Added action '{text_icon}', enabled: {enabled}")

        connect_enabled = not self.parent.mqtt_connected
        disconnect_enabled = self.parent.mqtt_connected
        connect_bg = "#43a047" if connect_enabled else "#546e7a"
        disconnect_bg = "#ef5350" if disconnect_enabled else "#546e7a"
        add_action("🔗", "#ffffff", self.parent.connect_mqtt, "Connect to MQTT", connect_enabled, connect_bg)
        add_action("🔌", "#ffffff", self.parent.disconnect_mqtt, "Disconnect from MQTT", disconnect_enabled, disconnect_bg)
        self.toolbar.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        layout_action = QAction("🖼️", self)
        layout_action.setToolTip("Select Layout")
        layout_action.triggered.connect(self.show_layout_menu)
        self.toolbar.addAction(layout_action)
        layout_button = self.toolbar.widgetForAction(layout_action)
        if layout_button:
            layout_button.setStyleSheet("""
                QToolButton {
                    color: #ffffff;
                    font-size: 24px;
                    border: none;
                    padding: 8px;
                    border-radius: 5px;
                }
                QToolButton:hover { background-color: #4a90e2; }
                QToolButton:pressed { background-color: #357abd; }
            """)

        self.toolbar.repaint()
        self.repaint()
        self.refresh_filename()
        self.refresh_saved_files()
        self.is_refreshing = False

    def start_saving(self):
        if not self.parent.mqtt_connected:
            QMessageBox.warning(self, "Error", "MQTT is not connected!")
            return
        if not self.parent.current_project:
            QMessageBox.warning(self, "Error", "No project selected!")
            return
        if not self.parent.current_feature:
            QMessageBox.warning(self, "Error", "No feature selected!")
            return
        selected_model = self.parent.tree_view.get_selected_model()
        if not selected_model:
            QMessageBox.warning(self, "Error", "Please select a model!")
            return
        selected_channel = self.parent.tree_view.get_selected_channel() if self.parent.current_feature not in ["Time View", "Time Report"] else None
        if not selected_channel and self.parent.current_feature not in ["Time View", "Time Report"]:
            QMessageBox.warning(self, "Error", f"Please select a channel for {self.parent.current_feature}!")
            return

        # Optional: Uncomment to restrict saving to Time View only
        # if self.parent.current_feature != "Time View":
        #     QMessageBox.warning(self, "Error", "Saving is only allowed for Time View feature!")
        #     return

        filename = self.filename_edit.text()
        if not filename or not re.match(r"data\d+", filename):
            QMessageBox.warning(self, "Error", "Please enter a valid filename (e.g., data1)!")
            return

        try:
            feature_name = self.parent.current_feature
            model_name = selected_model
            channel = selected_channel

            feature_instance = None
            for key, instance in self.parent.feature_instances.items():
                f_name, m_name, c_name, _ = key
                if f_name == feature_name and m_name == model_name and c_name == channel:
                    feature_instance = instance
                    break

            if not feature_instance:
                logging.warning(f"No active feature instance found for {feature_name}/{model_name}/{channel or 'No Channel'}")
                self.parent.console.append_to_console(f"No active feature instance found to save for {feature_name}")
                QMessageBox.warning(self, "Error", "No active feature instance found to save!")
                return

            self.current_feature_instance = feature_instance
            self.current_filename = filename
            self.is_saving = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.saving_label.setText("Saving...")
            self.start_blinking()

            if not self.save_timer:
                self.save_timer = QTimer(self)
                self.save_timer.timeout.connect(self.save_data)
            self.save_timer.start(1000)

            self.parent.console.append_to_console(f"Started saving data to {filename} for {feature_name}")
            self.refresh_saved_files()
        except Exception as e:
            logging.error(f"SubToolBar: Error starting saving: {str(e)}")
            self.parent.console.append_to_console(f"Error starting saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error starting saving: {str(e)}")

    def stop_saving(self):
        try:
            if self.is_saving:
                self.is_saving = False
                self.start_button.setEnabled(self.parent.mqtt_connected)
                self.stop_button.setEnabled(False)
                self.saving_label.setText("Not Saving")
                self.stop_blinking()
                if self.save_timer:
                    self.save_timer.stop()
                self.parent.console.append_to_console(f"Stopped saving data for {self.parent.current_feature}")
                self.current_feature_instance = None
                self.current_filename = None
                self.refresh_saved_files()
                self.refresh_filename()
        except Exception as e:
            logging.error(f"SubToolBar: Error stopping saving: {str(e)}")
            self.parent.console.append_to_console(f"Error stopping saving: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error stopping saving: {str(e)}")

    def start_blinking(self):
        if not self.blink_timer:
            self.blink_timer = QTimer(self)
            self.blink_timer.timeout.connect(self.toggle_blink)
        self.blink_timer.start(500)
        self.blink_state = True
        self.toggle_blink()

    def stop_blinking(self):
        if self.blink_timer:
            self.blink_timer.stop()
        self.saving_label.setStyleSheet("color: white; font-size: 16px;")

    def toggle_blink(self):
        self.blink_state = not self.blink_state
        color = "red" if self.blink_state else "green"
        self.saving_label.setStyleSheet(f"color: {color}; font-size: 16px;")

    def save_data(self):
        if not self.is_saving or not self.current_feature_instance:
            return

        try:
            feature_name = self.parent.current_feature
            model_name = self.parent.tree_view.get_selected_model()
            filename = self.current_filename

            data = self.collect_feature_data(self.current_feature_instance, feature_name)
            if not data:
                self.parent.console.append_to_console(f"No data available to save for {feature_name}")
                logging.warning(f"No data available to save for {feature_name}")
                return

            message_data = {
                "topic": "dashboard_data",
                "filename": filename,
                "frameIndex": 0,
                "message": data,
                "numberOfChannels": len(data.get("channel_data", [])) if feature_name in ["Time View", "Time Report"] else 1,
                "samplingRate": getattr(self.current_feature_instance, 'sample_rate', 4096),
                "samplingSize": len(data.get("channel_data", [[]])[0]) if feature_name in ["Time View", "Time Report"] else len(data.get("data", [])),
                "messageFrequency": None,
                "tachoChannelCount": data.get("tacho_channels_count", 0) if feature_name in ["Time View", "Time Report"] else 0,
                "createdAt": datetime.now().isoformat(),
                "projectName": self.parent.current_project,
                "moduleName": model_name,
                "featureName": feature_name,
                "email": self.parent.email
            }

            success, msg = self.parent.db.save_feature_message(self.parent.current_project, model_name, feature_name, message_data)
            if success:
                self.parent.console.append_to_console(f"Saved data to {filename} for {feature_name}")
                self.cached_filenames.append(filename)
                self.refresh_saved_files()
            else:
                self.parent.console.append_to_console(f"Failed to save data: {msg}")
                logging.error(f"SubToolBar: Failed to save data: {msg}")
        except Exception as e:
            logging.error(f"SubToolBar: Error saving data: {str(e)}")
            self.parent.console.append_to_console(f"Error saving data: {str(e)}")

    def collect_feature_data(self, feature_instance, feature_name):
        try:
            if feature_name in ["Time View", "Time Report"]:
                if not hasattr(feature_instance, 'fifo_data') or not hasattr(feature_instance, 'main_channels'):
                    logging.warning(f"Feature {feature_name} lacks required attributes for data collection")
                    return {}
                data = {
                    "channel_data": [list(data) for data in feature_instance.fifo_data[:feature_instance.main_channels]],
                    "tacho_freq": list(feature_instance.fifo_data[feature_instance.main_channels]) if feature_instance.tacho_channels_count >= 1 else [],
                    "tacho_trigger": list(feature_instance.fifo_data[feature_instance.main_channels + 1]) if feature_instance.tacho_channels_count >= 2 else [],
                    "tacho_channels_count": feature_instance.tacho_channels_count
                }
                return data if any(data["channel_data"]) else {}
            elif feature_name in [
                "Tabular View", "FFT", "Waterfall", "Centerline", "Orbit",
                "Trend View", "Multiple Trend View", "Bode Plot", "History Plot",
                "Polar Plot", "Report"
            ]:
                if hasattr(feature_instance, 'get_current_data'):
                    data = feature_instance.get_current_data()
                    if data:
                        return {"data": data}
                logging.warning(f"SubToolBar: No data collection implemented for {feature_name}")
                return {}
            else:
                logging.warning(f"SubToolBar: Unknown feature {feature_name} in collect_feature_data")
                return {}
        except Exception as e:
            logging.error(f"SubToolBar: Error collecting data for {feature_name}: {str(e)}")
            return {}

    def refresh_filename(self):
        if not self.filename_edit:
            logging.warning("SubToolBar: No filename_edit initialized")
            return
        try:
            model_name = self.parent.tree_view.get_selected_model() if self.parent.tree_view else None
            filenames = self.cached_filenames or (self.parent.db.get_distinct_filenames(self.parent.current_project, model_name) if self.parent.current_project else [])
            filename_counter = 1
            if filenames:
                numbers = [int(re.match(r"data(\d+)", f).group(1)) for f in filenames if re.match(r"data(\d+)", f)]
                filename_counter = max(numbers, default=0) + 1 if numbers else 1
            next_filename = f"data{filename_counter}"
            self.filename_edit.setText(next_filename)
            self.filename_edit.repaint()
        except Exception as e:
            logging.error(f"SubToolBar: Error refreshing filename: {str(e)}")
            self.filename_edit.setText("data1")

    def refresh_saved_files(self):
        if self.is_refreshing:
            return
        self.is_refreshing = True
        try:
            model_name = self.parent.tree_view.get_selected_model() if self.parent.tree_view else None
            feature_name = self.parent.current_feature
            if not self.parent.current_project or not feature_name or not model_name:
                self.saved_files_combo.clear()
                self.saved_files_combo.addItem("Select Saved File")
                self.cached_filenames = []
                logging.debug(f"SubToolBar: No project/feature/model, cleared saved files")
                self.is_refreshing = False
                return

            filenames = self.parent.db.get_distinct_filenames(self.parent.current_project, model_name, feature_name)
            self.cached_filenames = sorted(set(filenames))
            self.saved_files_combo.blockSignals(True)
            self.saved_files_combo.clear()
            self.saved_files_combo.addItem("Select Saved File")
            if self.cached_filenames:
                for filename in self.cached_filenames:
                    self.saved_files_combo.addItem(filename)
            logging.debug(f"SubToolBar: Refreshed saved files with {len(self.cached_filenames)} files for feature {feature_name}")
        except Exception as e:
            logging.error(f"SubToolBar: Error refreshing saved files: {str(e)}")
            self.saved_files_combo.clear()
            self.saved_files_combo.addItem("Select Saved File")
            self.cached_filenames = []
        finally:
            self.saved_files_combo.blockSignals(False)
            self.is_refreshing = False

    def on_saved_file_selected(self, text):
        if self.debounce_timer.isActive():
            return
        self.debounce_timer.start(200)
        try:
            if text == "Select Saved File" or not text:
                self.selected_saved_file = None
                logging.debug("SubToolBar: Cleared selected saved file")
                return
            if text not in self.cached_filenames:
                logging.warning(f"SubToolBar: Selected file {text} not in cached filenames")
                self.parent.console.append_to_console(f"Selected file {text} not found")
                return

            self.selected_saved_file = text
            logging.info(f"SubToolBar: Selected saved file: {text}")
            if not self.parent.current_feature:
                logging.warning("SubToolBar: No feature selected for loading saved file")
                self.parent.console.append_to_console("No feature selected to load saved file")
                QMessageBox.warning(self, "Error", "Please select a feature before loading a saved file")
                return
            if not self.parent.current_project:
                logging.warning("SubToolBar: No project selected for loading saved file")
                self.parent.console.append_to_console("No project selected to load saved file")
                QMessageBox.warning(self, "Error", "Please select a project before loading a saved file")
                return
            if not self.parent.tree_view.get_selected_model():
                logging.warning("SubToolBar: No model selected for loading saved file")
                self.parent.console.append_to_console("No model selected to load saved file")
                QMessageBox.warning(self, "Error", "Please select a model before loading a saved file")
                return
            if self.parent.current_feature != "Time Report":
                QMessageBox.information(self, "Info", "Please select 'Time Report' feature to load saved files.")
                return

            self.parent.clear_content_layout()
            self.parent.display_feature_content(self.parent.current_feature, self.parent.current_project, filename=text)
            self.parent.console.append_to_console(f"Requested load of saved file: {text} for feature: {self.parent.current_feature}")
        except Exception as e:
            logging.error(f"SubToolBar: Error handling saved file selection {text}: {str(e)}")
            self.parent.console.append_to_console(f"Error loading saved file {text}: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error loading saved file {text}: {str(e)}")

    def show_layout_menu(self):
        dialog = LayoutSelectionDialog(self, current_layout=self.selected_layout)
        parent_geom = self.parent.geometry()
        dialog_width = dialog.width()
        dialog_height = dialog.height()
        center_x = parent_geom.x() + (parent_geom.width() - dialog_width) // 2
        center_y = parent_geom.y() + (parent_geom.height() - dialog_height) // 2
        dialog.move(center_x, center_y)
        if dialog.exec_() == QDialog.Accepted:
            self.on_layout_selected(dialog.selected_layout)

    def on_layout_selected(self, layout):
        self.selected_layout = layout
        self.parent.main_section.arrange_layout(layout=self.selected_layout)