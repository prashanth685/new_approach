# from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMessageBox, QWidget, QVBoxLayout, QSizePolicy
# from PyQt5.QtCore import Qt
# from PyQt5.QtGui import QColor
# import logging

# class TreeView(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.db = parent.db
#         self.project_name = parent.current_project
#         self.parent_widget = parent
#         self.selected_channel = None
#         self.selected_channel_item = None
#         self.selected_model = None
#         self.initUI()

#     def initUI(self):
#         self.tree = QTreeWidget()
#         self.tree.header().hide()
#         self.tree.setStyleSheet("""
#             QTreeWidget { background-color: #232629; color: #ecf0f1; border: none; font-size: 16px; }
#             QTreeWidget::item { padding: 8px; border-bottom: 1px solid #2c3e50; }
#             QTreeWidget::item:hover { background-color: #34495e; }
#             QTreeWidget::item:selected { background-color: #4a90e2; color: white; }
#         """)
#         self.tree.setFixedWidth(300)
#         self.setFixedWidth(300)
#         self.setMinimumWidth(300)
#         self.setMaximumWidth(300)
#         self.tree.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

#         self.tree.itemClicked.connect(self.handle_item_clicked)

#         layout = QVBoxLayout()
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.addWidget(self.tree)
#         self.setLayout(layout)

#     def add_project_to_tree(self, project_name):
#         self.project_name = project_name
#         project_item = QTreeWidgetItem(self.tree)
#         project_item.setText(0, f"📁 {project_name}")
#         project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

#         try:
#             # Fetch full project data to get models and their metadata
#             project_data = self.db.get_project_data(project_name)
#             if not project_data or "models" not in project_data:
#                 logging.warning(f"No models found for project: {project_name}")
#                 return

#             models = project_data.get("models", [])
#             if not models:
#                 logging.warning(f"Empty models list for project: {project_name}")
#                 return

#             for model in models:
#                 model_name = model.get("name", "")
#                 if not model_name:
#                     logging.warning(f"Model without name in project: {project_name}")
#                     continue

#                 model_item = QTreeWidgetItem(project_item)
#                 model_item.setExpanded(True)
#                 model_item.setText(0, f"🖥️ {model_name}")
#                 model_item.setData(0, Qt.UserRole, {
#                     "type": "model",
#                     "name": model_name,
#                     "project": project_name
#                 })

#                 # Add channels from model
#                 channels = model.get("channels", [])
#                 for channel in channels:
#                     channel_name = channel.get("channelName", f"Channel_{len(channels)+1}")
#                     tag_name = model.get("tagName", channel_name)  # Use model-level tagName
#                     channel_item = QTreeWidgetItem(model_item)
#                     channel_item.setText(0, f"📡 {channel_name}")
#                     channel_item.setData(0, Qt.UserRole, {
#                         "type": "channel",
#                         "name": tag_name,
#                         "channel_name": channel_name,
#                         "model": model_name,
#                         "project": project_name
#                     })

#         except Exception as e:
#             logging.error(f"Error adding project to tree: {str(e)}")
#             QMessageBox.warning(self, "Error", f"Error adding project to tree: {str(e)}")

#     def handle_item_clicked(self, item, column):
#         data = item.data(0, Qt.UserRole)
#         try:
#             if self.selected_channel_item and self.selected_channel_item != item:
#                 self.selected_channel_item.setBackground(0, QColor("#232629"))

#             if data["type"] == "project":
#                 self.selected_channel = None
#                 self.selected_channel_item = None
#                 self.selected_model = None
#             elif data["type"] == "model":
#                 self.selected_channel = None
#                 self.selected_channel_item = None
#                 self.selected_model = data["name"]
#             elif data["type"] == "channel":
#                 self.selected_channel = data["name"]
#                 self.selected_channel_item = item
#                 self.selected_model = data["model"]
#                 item.setBackground(0, QColor("#28a745"))

#             logging.info(f"Tree item clicked: {data['type']} - {data.get('name', 'Unknown')}, selected channel: {self.selected_channel}, selected model: {self.selected_model}")
#         except Exception as e:
#             logging.error(f"Error handling tree item click: {str(e)}")
#             QMessageBox.warning(self, "Error", f"Error handling tree item click: {str(e)}")

#     def get_selected_channel(self):
#         return self.selected_channel

#     def get_selected_model(self):
#         return self.selected_model






from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMessageBox, QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import logging

class TreeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = parent.db
        self.project_name = parent.current_project
        self.parent_widget = parent
        self.selected_channel = None
        self.selected_channel_item = None
        self.selected_model = None
        self.initUI()

    def initUI(self):
        self.tree = QTreeWidget()
        self.tree.header().hide()
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #232629; color: #ecf0f1; border: none; font-size: 16px; }
            QTreeWidget::item { padding: 8px; border-bottom: 1px solid #2c3e50; }
            QTreeWidget::item:hover { background-color: #34495e; }
            QTreeWidget::item:selected { background-color: #4a90e2; color: white; }
        """)
        self.tree.setFixedWidth(300)
        self.setFixedWidth(300)
        self.setMinimumWidth(300)
        self.setMaximumWidth(300)
        self.tree.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.tree.itemClicked.connect(self.handle_item_clicked)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def add_project_to_tree(self, project_name):
        self.project_name = project_name
        project_item = QTreeWidgetItem(self.tree)
        project_item.setText(0, f"📁 {project_name}")
        project_item.setData(0, Qt.UserRole, {"type": "project", "name": project_name})

        try:
            # Fetch full project data to get models and their metadata
            project_data = self.db.get_project_data(project_name)
            if not project_data or "models" not in project_data:
                logging.warning(f"No models found for project: {project_name}")
                return

            models = project_data.get("models", [])
            if not models:
                logging.warning(f"Empty models list for project: {project_name}")
                return

            for model in models:
                model_name = model.get("name", "")
                if not model_name:
                    logging.warning(f"Model without name in project: {project_name}")
                    continue

                model_item = QTreeWidgetItem(project_item)
                model_item.setExpanded(True)
                model_item.setText(0, f"🖥️ {model_name}")
                model_item.setData(0, Qt.UserRole, {
                    "type": "model",
                    "name": model_name,
                    "project": project_name
                })

                # Add channels from model with indexing
                channels = model.get("channels", [])
                for idx, channel in enumerate(channels):
                    channel_name = channel.get("channelName", f"Channel_{idx + 1}")
                    tag_name = model.get("tagName", channel_name)  # fallback if no tagName
                    channel_item = QTreeWidgetItem(model_item)
                    channel_item.setText(0, f"📡 {channel_name}")
                    channel_item.setData(0, Qt.UserRole, {
                        "type": "channel",
                        "index": idx,  # Index of the channel within model
                        "name": tag_name,
                        "channel_name": channel_name,
                        "model": model_name,
                        "project": project_name
                    })

        except Exception as e:
            logging.error(f"Error adding project to tree: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error adding project to tree: {str(e)}")

    def handle_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        try:
            if self.selected_channel_item and self.selected_channel_item != item:
                self.selected_channel_item.setBackground(0, QColor("#232629"))

            if data["type"] == "project":
                self.selected_channel = None
                self.selected_channel_item = None
                self.selected_model = None

            elif data["type"] == "model":
                self.selected_channel = None
                self.selected_channel_item = None
                self.selected_model = data["name"]

            elif data["type"] == "channel":
                self.selected_channel = data["name"]
                self.selected_channel_item = item
                self.selected_model = data["model"]
                item.setBackground(0, QColor("#28a745"))

                # Optional: log or use the index
                channel_index = data.get("index")
                logging.info(f"Selected channel index: {channel_index}")

            logging.info(f"Tree item clicked: {data['type']} - {data.get('name', 'Unknown')}, "
                         f"selected channel: {self.selected_channel}, selected model: {self.selected_model}")
        except Exception as e:
            logging.error(f"Error handling tree item click: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error handling tree item click: {str(e)}")

    def get_selected_channel(self):
        return self.selected_channel

    def get_selected_model(self):
        return self.selected_model
