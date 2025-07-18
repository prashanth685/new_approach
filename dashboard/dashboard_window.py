import sys
import gc
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QSizePolicy, QApplication, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime
from PyQt5.QtGui import QIcon, QColor
import logging
from dashboard.components.file_bar import FileBar
from dashboard.components.tool_bar import ToolBar
from dashboard.components.sub_tool_bar import SubToolBar
from dashboard.components.main_section import MainSection
from dashboard.components.tree_view import TreeView
from dashboard.components.console import Console
from dashboard.components.mqtt_status import MQTTStatus
from mqtthandler import MQTTHandler
from features.tabular_view import TabularViewFeature
from features.polar import PolarPlotFeature
from features.time_view import TimeViewFeature
from features.fft_view import FFTViewFeature
from features.waterfall import WaterfallFeature
from features.centerline import CenterLineFeature
from features.orbit import OrbitFeature
from features.trend_view import TrendViewFeature
from features.multi_trend import MultiTrendFeature
from features.bode_plot import BodePlotFeature
from features.history_plot import HistoryPlotFeature
from features.time_report import TimeReportFeature
from features.report import ReportFeature
from select_project import SelectProjectWidget
from create_project import CreateProjectWidget
from project_structure import ProjectStructureWidget
import threading

class DashboardWindow(QWidget):
    mqtt_status_changed = pyqtSignal(bool)

    def __init__(self, db, email, auth_window=None):
        super().__init__()
        self.db = db
        self.email = email
        self.auth_window = auth_window
        self.current_project = None
        self.open_dashboards = {}
        self.current_feature = None
        self.mqtt_handler = None
        self.feature_instances = {}
        self.sub_windows = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.mqtt_connected = False
        self.select_project_widget = None
        self.create_project_widget = None
        self.project_structure_widget = None
        self.initUI()
        QTimer.singleShot(0, self.deferred_initialization)

    def initUI(self):
        self.setWindowTitle('Sarayu Desktop Application')
        self.setWindowState(Qt.WindowMaximized)

        app = QApplication.instance()
        app.setStyleSheet("""
            QInputDialog, QMessageBox {
                background-color: #1e2937;
                color: white;
                font-size: 16px;
                border: 1px solid #2c3e50;
                border-radius: 8px;
                padding: 15px;
                width:500px;
            }
            QInputDialog QLineEdit {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #4a90e2;
                padding: 8px;
                border-radius: 4px;
                font-size: 15px;
            }
            QInputDialog QLabel,
            QMessageBox QLabel {
                color: #ecf0f1;
                font-size: 16px;
                padding-bottom: 10px;
            }
            QInputDialog QPushButton,
            QMessageBox QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-size: 15px;
                min-width: 80px;
                transition: background-color 0.2s ease;
            }
            QInputDialog QPushButton:hover,
            QMessageBox QPushButton:hover {
                background-color: #357abd;
            }
            QInputDialog QPushButton:pressed,
            QMessageBox QPushButton:pressed {
                background-color: #2c5d9b;
            }
            QMdiSubWindow {
                background-color: #d1d6d9;
                border: 1px solid #d1d6d9;
                border-radius: 4px;
            }
            QMdiSubWindow > QWidget {
                background-color: #d1d6d9;
                color: #ecf0f1;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.file_bar = FileBar(self)
        main_layout.addWidget(self.file_bar)

        self.tool_bar = ToolBar(self)
        main_layout.addWidget(self.tool_bar)

        central_widget = QWidget()
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_widget.setLayout(central_layout)
        main_layout.addWidget(central_widget, 1)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setContentsMargins(0, 0, 0, 0)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #2c3e50; }")
        central_layout.addWidget(self.main_splitter)

        self.tree_view = TreeView(self)
        self.tree_view.setVisible(False)
        self.main_splitter.addWidget(self.tree_view)

        right_container = QWidget()
        right_container.setStyleSheet("background-color: #d1d6d9;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_container.setLayout(right_layout)

        self.sub_tool_bar = SubToolBar(self)
        self.sub_tool_bar.setVisible(False)
        right_layout.addWidget(self.sub_tool_bar)

        self.main_section = MainSection(self)
        right_layout.addWidget(self.main_section, 1)

        self.main_splitter.addWidget(right_container)
        window_width = self.width() if self.width() > 0 else 1200
        tree_view_width = int(window_width * 0.15)
        right_container_width = int(window_width * 0.85)
        self.main_splitter.setSizes([tree_view_width, right_container_width])

        self.console = Console(self)
        self.mqtt_status = MQTTStatus(self)
        self.console_layout = QVBoxLayout()
        self.console_layout.setContentsMargins(0, 0, 0, 0)
        self.console_layout.setSpacing(0)
        self.console_container = QWidget()
        self.console_container.setStyleSheet("background-color: black;")
        self.console_container.setFixedHeight(80)
        self.console_container.setLayout(self.console_layout)
        self.console_layout.addWidget(self.console.button_container)
        self.console_layout.addWidget(self.console.console_message_area)
        self.console_layout.addWidget(self.mqtt_status)
        main_layout.addWidget(self.console_container)

    def deferred_initialization(self):
        projects = self.db.load_projects()
        if projects and self.current_project:
            self.load_project(self.current_project)
        else:
            self.display_select_project()

    def display_select_project(self):
        self.clear_content_layout()
        self.tree_view.setVisible(False)
        self.sub_tool_bar.setVisible(False)
        self.current_project = None
        self.setWindowTitle('Sarayu Desktop Application')
        self.select_project_widget = SelectProjectWidget(self)
        self.main_section.set_widget(self.select_project_widget)
        logging.debug("Displayed SelectProjectWidget in MainSection")

    def display_create_project(self):
        self.clear_content_layout()
        self.sub_tool_bar.setVisible(False)
        self.create_project_widget = CreateProjectWidget(self)
        self.main_section.set_widget(self.create_project_widget)
        logging.debug("Displayed CreateProjectWidget in MainSection")

    def display_project_structure(self):
        self.clear_content_layout()
        self.tree_view.setVisible(False)
        self.sub_tool_bar.setVisible(False)
        self.project_structure_widget = ProjectStructureWidget(self)
        self.project_structure_widget.project_selected.connect(self.load_project)
        self.main_section.set_widget(self.project_structure_widget)
        self.main_splitter.setSizes([0, 1200])
        logging.debug("Displayed ProjectStructureWidget in MainSection")

    def load_project(self, project_name):
        self.current_project = project_name
        self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
        self.tree_view.setVisible(True)
        self.sub_tool_bar.setVisible(True)
        window_width = self.width() if self.width() > 0 else 1200
        tree_view_width = int(window_width * 0.15)
        right_container_width = int(window_width * 0.85)
        self.main_splitter.setSizes([tree_view_width, right_container_width])
        logging.debug(f"TreeView visibility: {self.tree_view.isVisible()}")
        logging.debug(f"SubToolBar visibility: {self.sub_tool_bar.isVisible()}")
        logging.debug(f"Loading project: {project_name}")
        self.clear_content_layout()
        if self.project_structure_widget:
            self.project_structure_widget.setParent(None)
            self.project_structure_widget = None
            logging.debug("ProjectStructureWidget removed from MainSection")
        self.load_project_features()
        QTimer.singleShot(0, self.setup_mqtt)

    def setup_mqtt(self):
        if not self.current_project:
            logging.warning("No project selected for MQTT setup")
            self.console.append_to_console("No project selected for MQTT setup")
            return
        self.cleanup_mqtt()
        try:
            tags = self.get_project_tags()
            if tags:
                self.mqtt_handler = MQTTHandler(self.db, self.current_project)
                self.mqtt_handler.data_received.connect(self.on_data_received)
                self.mqtt_handler.connection_status.connect(self.on_mqtt_status)
                self.mqtt_handler.start()
                logging.info(f"MQTT setup initiated for project: {self.current_project}")
                self.console.append_to_console(f"MQTT setup initiated for project: {self.current_project}")
            else:
                logging.warning(f"No tags found for project: {self.current_project}")
                self.mqtt_connected = False
                self.mqtt_status_changed.emit(False)
                self.console.append_to_console(f"No tags found for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to setup MQTT: {str(e)}")
            self.console.append_to_console(f"Failed to setup MQTT: {str(e)}")
            self.mqtt_connected = False
            self.mqtt_status_changed.emit(False)
        self.sub_tool_bar.update_subtoolbar()
        self.mqtt_status.update_mqtt_status_indicator()

    def cleanup_mqtt(self):
        if self.mqtt_handler:
            try:
                self.mqtt_handler.data_received.disconnect()
                self.mqtt_handler.connection_status.disconnect()
                self.mqtt_handler.stop()
                self.mqtt_handler.deleteLater()
                logging.info("Previous MQTT handler stopped")
            except Exception as e:
                logging.error(f"Error stopping MQTT handler: {str(e)}")
            finally:
                self.mqtt_handler = None
                self.mqtt_connected = False
                self.mqtt_status_changed.emit(False)

    def get_project_tags(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            project_data = self.db.get_project_data(self.current_project)
            if not project_data or "models" not in project_data:
                logging.warning(f"No models found for project: {self.current_project}")
                return []
            tags = []
            for model in project_data["models"]:
                model_name = model.get("name")
                tag_name = model.get("tagName", "")
                if tag_name and model_name:
                    tags.append({"tag_name": tag_name, "model_name": model_name})
            logging.debug(f"Retrieved tags for project {self.current_project}: {tags}")
            return tags
        except Exception as e:
            logging.error(f"Failed to retrieve project tags: {str(e)}")
            return []

    def connect_mqtt(self):
        if self.mqtt_connected:
            self.console.append_to_console("Already connected to MQTT")
            return
        QTimer.singleShot(0, self.setup_mqtt)

    def disconnect_mqtt(self):
        if not self.mqtt_connected:
            self.console.append_to_console("Already disconnected from MQTT")
            return
        try:
            self.cleanup_mqtt()
            self.mqtt_connected = False
            self.mqtt_status_changed.emit(False)
            self.sub_tool_bar.update_subtoolbar()
            self.mqtt_status.update_mqtt_status_indicator()
            logging.info(f"MQTT disconnected for project: {self.current_project}")
            self.console.append_to_console(f"MQTT disconnected for project: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to disconnect MQTT: {str(e)}")
            self.console.append_to_console(f"Failed to disconnect MQTT: {str(e)}")
            self.mqtt_status.update_mqtt_status_indicator()

    def on_data_received(self, feature_name, tag_name, model_name, values, sample_rate):
        try:
            # Update only the relevant feature instances
            for key, feature_instance in self.feature_instances.items():
                instance_feature, instance_model, instance_channel, _ = key
                if instance_feature == feature_name and instance_model == model_name and hasattr(feature_instance, 'on_data_received'):
                    QTimer.singleShot(0, lambda: self._update_feature(
                        instance_feature, instance_model, instance_channel, 
                        feature_instance, tag_name, values, sample_rate
                    ))
        except Exception as e:
            logging.error(f"Error in on_data_received for {feature_name}: {str(e)}")
            self.console.append_to_console(f"Error processing data for {feature_name}: {str(e)}")

    def _update_feature(self, feature_name, model_name, channel, feature_instance, tag_name, values, sample_rate):
        try:
            feature_instance.on_data_received(tag_name, model_name, values, sample_rate)
            logging.debug(f"Updated feature {feature_name}/{model_name}/{channel or 'No Channel'}")
        except Exception as e:
            logging.error(f"Error updating feature {feature_name}/{model_name}/{channel or 'No Channel'}: {str(e)}")

    def on_mqtt_status(self, message):
        self.mqtt_connected = "Connected" in message
        self.mqtt_status_changed.emit(self.mqtt_connected)
        self.console.append_to_console(f"MQTT Status: {message}")
        self.sub_tool_bar.update_subtoolbar()
        self.mqtt_status.update_mqtt_status_indicator()

    def load_project_features(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            self.tree_view.tree.clear()
            self.tree_view.add_project_to_tree(self.current_project)
            for i in range(self.tree_view.tree.topLevelItemCount()):
                item = self.tree_view.tree.topLevelItem(i)
                if item.text(0) == f"📁 {self.current_project}":
                    item.setExpanded(True)
                    self.tree_view.tree.setCurrentItem(item)
                    self.tree_view.tree.scrollToItem(item)
                    break
            logging.debug(f"Loaded project features for: {self.current_project}")
        except Exception as e:
            logging.error(f"Failed to load project features: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to load project features: {str(e)}")

    def open_project(self):
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            projects = self.db.load_projects()
            if not projects:
                QMessageBox.warning(self, "Error", "No projects available to open!")
                return
            self.display_project_structure()
        except Exception as e:
            logging.error(f"Error opening project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error opening project: {str(e)}")

    def create_project(self):
        self.display_create_project()

    def edit_project_dialog(self):
        if not self.current_project:
            QMessageBox.warning(self, "Error", "No project selected to edit!")
            return
        old_project_name = self.current_project
        new_project_name, ok = QInputDialog.getText(self, "Edit Project", "Enter new project name:", text=old_project_name)
        if not ok or not new_project_name or new_project_name == old_project_name:
            return
        try:
            if not self.db.is_connected():
                self.db.reconnect()
            success, message = self.db.edit_project(old_project_name, new_project_name)
            if success:
                self.current_project = new_project_name
                self.setWindowTitle(f'Sarayu Desktop Application - {self.current_project.upper()}')
                self.load_project_features()
                QTimer.singleShot(0, self.setup_mqtt)
                self.tool_bar.update_toolbar()
                self.sub_tool_bar.update_subtoolbar()
                if self.current_feature:
                    self.display_feature_content(self.current_feature, self.current_project)
                if old_project_name in self.open_dashboards:
                    self.open_dashboards[new_project_name] = self.open_dashboards.pop(old_project_name)
                QMessageBox.information(self, "Success", message)
                self.file_bar.update_file_bar()
            else:
                QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logging.error(f"Error editing project: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error editing project: {str(e)}")

    def delete_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "Error", "No project selected to delete!")
            return
        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {self.current_project}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                success, message = self.db.delete_project(self.current_project)
                if success:
                    if self.current_project in self.open_dashboards:
                        del self.open_dashboards[self.current_project]
                    self.display_select_project()
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.warning(self, "Error", message)
            except Exception as e:
                logging.error(f"Error deleting project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error deleting project: {str(e)}")

    def display_feature_content(self, feature_name, project_name):
        try:
            logging.debug(f"Attempting to display feature: {feature_name} for project: {project_name}")
            self.current_project = project_name
            self.current_feature = feature_name
            self.sub_tool_bar.setVisible(True)
            self.sub_tool_bar.update_subtoolbar()

            current_console_height = self.console.console_message_area.height()

            selected_model = self.tree_view.get_selected_model()
            if not selected_model:
                self.console.append_to_console(f"Please select a model to view {feature_name}.")
                logging.warning(f"No model selected for {feature_name}")
                return

            project_data = self.db.get_project_data(project_name)
            if not project_data:
                self.console.append_to_console(f"Project {project_name} not found in database.")
                logging.error(f"Project {project_name} not found!")
                return

            model = next((m for m in project_data["models"] if m["name"] == selected_model), None)
            if not model:
                self.console.append_to_console(f"Model {selected_model} not found in project {project_name}.")
                logging.error(f"Model {selected_model} not found in project {project_name}!")
                return

            selected_channel = self.tree_view.get_selected_channel() if feature_name not in ["Time View", "Time Report"] else None
            channels = [selected_channel] if selected_channel and feature_name not in ["Time View", "Time Report"] else [None]

            if not channels or (not selected_channel and feature_name not in ["Time View", "Time Report"]):
                self.console.append_to_console(f"Please select a channel for {feature_name} in model {selected_model}.")
                logging.warning(f"No channel selected for {feature_name} in model {selected_model}")
                return

            feature_classes = {
                "Tabular View": TabularViewFeature,
                "Time View": TimeViewFeature,
                "Time Report": TimeReportFeature,
                "FFT": FFTViewFeature,
                "Waterfall": WaterfallFeature,
                "Centerline": CenterLineFeature,
                "Orbit": OrbitFeature,
                "Trend View": TrendViewFeature,
                "Multiple Trend View": MultiTrendFeature,
                "Bode Plot": BodePlotFeature,
                "History Plot": HistoryPlotFeature,
                "Polar Plot": PolarPlotFeature,
                "Report": ReportFeature
            }

            if feature_name not in feature_classes:
                logging.warning(f"Unknown feature: {feature_name}")
                QMessageBox.warning(self, "Error", f"Unknown feature: {feature_name}")
                return

            for channel in channels:
                import time
                unique_id = int(time.time() * 1000)
                key = (feature_name, selected_model, channel, unique_id)

                try:
                    if not self.db.is_connected():
                        self.db.reconnect()
                    feature_instance = feature_classes[feature_name](
                        self, self.db, project_name, channel=channel, 
                        model_name=selected_model, console=self.console
                    )
                    self.feature_instances[key] = feature_instance
                    widget = feature_instance.get_widget()
                    if widget:
                        sub_window = self.main_section.add_subwindow(
                            widget,
                            feature_name,
                            channel_name=channel,
                            model_name=selected_model
                        )
                        if sub_window:
                            self.sub_windows[key] = sub_window
                            sub_window.closeEvent = lambda event, k=key: self.on_subwindow_closed(event, k)
                            sub_window.show()
                            logging.debug(f"Created new subwindow for {key}, ID: {id(sub_window)}")
                        else:
                            logging.error(f"Failed to create subwindow for {feature_name}/{selected_model}/{channel or 'No Channel'}")
                            QMessageBox.warning(self, "Error", f"Failed to create subwindow for {feature_name}")
                            del self.feature_instances[key]
                    else:
                        logging.error(f"Feature {feature_name} returned invalid widget")
                        QMessageBox.warning(self, "Error", f"Feature {feature_name} failed to initialize")
                        del self.feature_instances[key]
                    self.console.console_message_area.setFixedHeight(current_console_height)
                except Exception as e:
                    logging.error(f"Failed to load feature {feature_name} for channel {channel or 'No Channel'}: {str(e)}")
                    QMessageBox.warning(self, "Error", f"Failed to load {feature_name}: {str(e)}")
                    if key in self.feature_instances:
                        del self.feature_instances[key]

            self.main_section.arrange_layout()
            self.console.console_message_area.setFixedHeight(current_console_height)

        except Exception as e:
            logging.error(f"Error displaying feature content: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error displaying feature: {str(e)}")

    def on_subwindow_closed(self, event, key):
        try:
            feature_name, model_name, channel_name, unique_id = key
            logging.debug(f"Closing subwindow for key: {key}, ID: {id(self.sub_windows.get(key))}")

            sub_window = self.sub_windows.get(key)
            if not sub_window:
                logging.warning(f"No subwindow found for key: {key}")
                event.accept()
                return

            if sub_window.isMaximized():
                sub_window.showNormal()
                logging.debug(f"Restored maximized subwindow for {key}")

            if key in self.feature_instances:
                instance = self.feature_instances[key]
                if hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logging.error(f"Error in cleanup for {key}: {str(e)}")
                widget = instance.get_widget()
                if widget:
                    try:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    except Exception as e:
                        logging.error(f"Error cleaning up widget for {key}: {str(e)}")
                del self.feature_instances[key]
                logging.debug(f"Cleaned up feature instance for {key}")

            try:
                sub_window.close()
                self.main_section.mdi_area.removeSubWindow(sub_window)
                sub_window.setParent(None)
                sub_window.deleteLater()
                logging.debug(f"Removed subwindow from MDI area for {key}, ID: {id(sub_window)}")
            except Exception as e:
                logging.error(f"Error removing subwindow for {key}: {str(e)}")
            del self.sub_windows[key]

            if self.current_feature == feature_name:
                if not any(k[0] == feature_name for k in self.feature_instances.keys()): 
                    self.current_feature = None
                    self.sub_tool_bar.update_subtoolbar()
                    logging.debug(f"Reset current_feature as no instances of {feature_name} remain")

            self.main_section.mdi_area.update()
            self.main_section.scroll_area.viewport().update()
            self.main_section.arrange_layout()
            self.main_section.mdi_area.setMinimumSize(0, 0)
            gc.collect()
            logging.debug(f"Completed cleanup for subwindow: {key}")
        except Exception as e:
            logging.error(f"Error cleaning up subwindow for {key}: {str(e)}")
        event.accept()

    def save_action(self):
        if self.current_project:
            try:
                if not self.db.is_connected():
                    self.db.reconnect()
                project_data = self.db.get_project_data(self.current_project)
                if project_data:
                    QMessageBox.information(self, "Save", f"Data for project '{self.current_project}' saved successfully!")
                else:
                    QMessageBox.warning(self, "Save Error", "No data to save for the selected project!")
                self.file_bar.update_file_bar()
            except Exception as e:
                logging.error(f"Error saving project: {str(e)}")
                QMessageBox.warning(self, "Error", f"Error saving project: {str(e)}")
        else:
            QMessageBox.warning(self, "Save Error", "No project selected to save!")

    def refresh_action(self):
        try:
            if self.current_project and self.current_feature:
                self.display_feature_content(self.current_feature, self.current_project)
                QMessageBox.information(self, "Refresh", f"Refreshed view for '{self.current_feature}'!")
            else:
                self.display_select_project()
                QMessageBox.information(self, "Refresh", "Refreshed project selection view!")
            self.file_bar.update_file_bar()
        except Exception as e:
            logging.error(f"Error refreshing view: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error refreshing view: {str(e)}")

    def display_dashboard(self):
        if not self.current_project:
            self.display_select_project()
            return
        self.current_feature = None
        self.sub_tool_bar.update_subtoolbar()
        self.file_bar.update_file_bar()

    def clear_content_layout(self):
        try:
            logging.debug("Starting clear_content_layout")
            
            for key in list(self.sub_windows.keys()):
                sub_window = self.sub_windows.get(key)
                if sub_window:
                    try:
                        if sub_window.isMaximized():
                            sub_window.showNormal()
                        sub_window.close()
                        self.main_section.mdi_area.removeSubWindow(sub_window)
                        sub_window.setParent(None)
                        sub_window.deleteLater()
                        logging.debug(f"Closed subwindow for {key} during clear_content_layout, ID: {id(sub_window)}")
                    except Exception as e:
                        logging.error(f"Error closing subwindow {key}: {str(e)}")
            self.sub_windows.clear()
            logging.debug("Cleared all subwindows")

            for key in list(self.feature_instances.keys()):
                try:
                    instance = self.feature_instances[key]
                    if hasattr(instance, 'cleanup'):
                        instance.cleanup()
                    widget = instance.get_widget()
                    if widget:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    del self.feature_instances[key]
                    logging.debug(f"Cleaned up feature instance for {key}")
                except Exception as e:
                    logging.error(f"Error cleaning up feature instance {key}: {str(e)}")
            
            self.main_section.clear_widget()
            self.main_section.mdi_area.setMinimumSize(0, 0)
            self.main_section.mdi_area.update()
            self.main_section.scroll_area.viewport().update()
            gc.collect()
            logging.debug("Completed clear_content_layout")
            logging.debug(f"Current widget in MainSection: {self.main_section.current_widget}")
        except Exception as e:
            logging.error(f"Error clearing content layout: {str(e)}")

    def settings_action(self):
        QMessageBox.information(self, "Settings", "Settings functionality not implemented yet.")
        self.file_bar.update_file_bar()

    def back_to_login(self):
        try:
            if self.auth_window:
                self.auth_window.show()
                self.auth_window.showMaximized()
            self.close()
        except Exception as e:
            logging.error(f"Error returning to login: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to return to login: {str(e)}")

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
            self.cleanup_mqtt()
            self.clear_content_layout()
            if self.db and self.db.is_connected():
                self.db.close_connection()
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception as e:
            logging.error(f"Error during closeEvent: {str(e)}")
        finally:
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tree_view.isVisible():
            window_width = self.width()
            tree_view_width = int(window_width * 0.15)
            right_container_width = int(window_width * 0.85)
            self.main_splitter.setSizes([tree_view_width, right_container_width])
        self.main_section.arrange_layout()