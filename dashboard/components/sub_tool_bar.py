from PyQt5.QtWidgets import (
    QToolBar, QAction, QWidget, QHBoxLayout, QSizePolicy, QLineEdit,
    QLabel, QDialog, QVBoxLayout, QPushButton, QGridLayout
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
import logging
import re

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
        self.selected_layout = "2x2"  # Default layout
        self.filename_edit = None
        self.initUI()
        # Connect signal with error handling
        try:
            self.parent.mqtt_status_changed.connect(self.update_subtoolbar)
            logging.info("SubToolBar: mqtt_status_changed signal connected successfully")
        except AttributeError as e:
            logging.error(f"SubToolBar: Failed to connect mqtt_status_changed signal: {e}")

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
            QLineEdit[readOnly="true"] {
                background-color: #e0e0e0;
                color: #616161;
                border: 1px solid #b0bec5;
            }
        """)
        # Enable editing only for Time View
        is_time_view = self.parent.current_feature == "Time View"
        self.filename_edit.setReadOnly(not is_time_view)
        self.filename_edit.setEnabled(True)  # Always enabled to show filename
        self.refresh_filename()
        self.toolbar.addWidget(self.filename_edit)
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
                        transition: background-color 0.3s ease;
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
                logging.debug(f"SubToolBar: Added action '{text_icon}', enabled: {enabled}, background: {background_color}")

        # Enable save/stop actions only for Time View
        add_action("▶", "#ffffff", self.parent.start_saving, "Start Saving Data (Time View)", is_time_view and not self.parent.is_saving, "#43a047")
        add_action("⏸", "#ffffff", self.parent.stop_saving, "Stop Saving Data (Time View)", is_time_view and self.parent.is_saving, "#90a4ae")
        self.toolbar.addSeparator()

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
                    transition: background-color 0.3s ease;
                }
                QToolButton:hover { background-color: #4a90e2; }
                QToolButton:pressed { background-color: #357abd; }
            """)

        self.toolbar.repaint()
        self.repaint()
        logging.debug("SubToolBar: Toolbar updated and repainted")

    def refresh_filename(self):
        """Refresh the QLineEdit with the current or next filename."""
        if not self.filename_edit:
            logging.warning("SubToolBar: No filename_edit initialized")
            return

        try:
            # Default filename
            next_filename = "data1"
            current_filename = None
            filename_counter = 1
            is_saving = False

            # Check if in Time View and current_widget exists
            if self.parent.current_feature == "Time View" and hasattr(self.parent, 'current_widget'):
                # Get current_filename and filename_counter from TimeViewFeature
                current_filename = getattr(self.parent.current_widget, 'current_filename', None)
                filename_counter = getattr(self.parent.current_widget, 'filename_counter', 1)
                is_saving = getattr(self.parent.current_widget, 'is_saving', False)

            # Query database for existing filenames
            model_name = getattr(self.parent.current_widget, 'model_name', None) if hasattr(self.parent, 'current_widget') else None
            filenames = self.parent.db.get_distinct_filenames(self.parent.current_project, model_name) if self.parent.current_project else []
            logging.debug(f"SubToolBar: Retrieved {len(filenames)} filenames from database: {filenames}")

            # Determine the next filename based on existing filenames
            if filenames:
                numbers = [int(re.match(r"data(\d+)", f).group(1)) for f in filenames if re.match(r"data(\d+)", f)]
                filename_counter = max(numbers, default=0) + 1 if numbers else 1
                next_filename = f"data{filename_counter}"
            else:
                next_filename = f"data{filename_counter}"

            # Set the filename in QLineEdit
            if is_saving and current_filename:
                self.filename_edit.setText(current_filename)
                logging.debug(f"SubToolBar: Set filename_edit to current_filename: {current_filename}")
            else:
                self.filename_edit.setText(next_filename)
                logging.debug(f"SubToolBar: Set filename_edit to next_filename: {next_filename}")

            logging.info(f"SubToolBar: Refreshed filename, current: {self.filename_edit.text()}, "
                         f"saving: {is_saving}, counter: {filename_counter}")
            self.filename_edit.repaint()

        except Exception as e:
            logging.error(f"SubToolBar: Error refreshing filename: {e}")
            self.filename_edit.setText(f"data{filename_counter}")
            self.filename_edit.repaint()

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