from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import Qt
import logging

class FileBar(QToolBar):
    def __init__(self, parent):
        super().__init__("File", parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QToolBar {
                background: #2D2F33;
                border: none;
                padding: 0;
                spacing: 5px;
            }
            QToolBar QToolButton {
                font-size: 18px;
                font-weight: bold;
                color: #fff;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: transparent;
            }
            QToolBar QToolButton:hover {
                background-color: #4a90e2;
                color: white;
            }
        """)
        self.setFixedHeight(40)
        self.setMovable(False)
        self.setFloatable(False)

        actions = [
            ("Home", "Go to Dashboard Home", self.parent.display_dashboard),
            ("Open", "Open an Existing Project", self.parent.open_project),
            ("Edit","Edit an Existing Project",self.parent.edit_project_dialog),
            ("New", "Create a New Project", self.parent.create_project),
            ("Save", "Save Current Project Data", self.parent.save_action),
            ("Settings", "Open Application Settings", self.parent.settings_action),
            ("Refresh", "Refresh Current View", self.parent.refresh_action),
            ("Exit", "Exit Application", self.parent.close)
        ]
        for text, tooltip, func in actions:
            action = QAction(text, self)
            action.setToolTip(tooltip)
            action.triggered.connect(func)
            self.addAction(action)

    def update_file_bar(self):
        try:
            self.setStyleSheet("""
                QToolBar {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f5f5f5, stop:1 #e0e0e0);
                    border: none;
                    padding: 0;
                    spacing: 5px;
                }
                QToolBar QToolButton {
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                    padding: 8px 12px;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QToolBar QToolButton:hover {
                    background-color: #4a90e2;
                    color: white;
                }
            """)
        except Exception as e:
            logging.error(f"Error updating file bar: {str(e)}")