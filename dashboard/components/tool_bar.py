from PyQt5.QtWidgets import (
    QToolBar, QToolButton, QWidget, QSizePolicy,
    QMessageBox, QLabel, QVBoxLayout
)
from PyQt5.QtCore import QSize, Qt


class ToolBar(QToolBar):
    def __init__(self, parent):
        super().__init__("Features", parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setFixedHeight(80)
        self.update_toolbar()

    def update_toolbar(self):
        self.clear()
        self.setStyleSheet("""
                        QToolBar { 
                background-color: #3C3F41;
                border: none; 
                padding: 5px; 
                spacing: 10px; 
            }
            QToolButton {
                color: white;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        self.setMovable(False)
        self.setFloatable(False)

        def add_action(feature_name, text_icon, color, tooltip):
            # Create a button
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setToolTip(tooltip)
            button.setFixedSize(64, 64)  # Consistent button size

            # Use emoji as icon via QLabel
            icon_label = QLabel(text_icon)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet(f"font-size: 24px; color: {color};")
            icon_label.setFixedSize(24, 24)  # Standard 24x24 icon size

            # Text label with proper alignment
            text_label = QLabel(feature_name)
            text_label.setWordWrap(True)
            text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  # Explicit horizontal centering
            text_label.setStyleSheet(f"font-size: 10px; color: white; font-weight: bold;")
            text_label.setFixedSize(60, 24)  # Consistent text size

            # Layout to stack icon and label
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 4, 0, 4)  # Adjusted margins for better vertical alignment
            layout.setSpacing(2)  # Tighter spacing for precise alignment
            layout.addWidget(icon_label, alignment=Qt.AlignHCenter)  # Center icon
            layout.addWidget(text_label, alignment=Qt.AlignHCenter)  # Center text
            layout.setAlignment(Qt.AlignCenter)  # Center entire layout

            # Container widget for button content
            content = QWidget()
            content.setLayout(layout)
            button.setLayout(layout)
            button.clicked.connect(lambda _, name=feature_name: self.validate_and_display(name))

            self.addWidget(button)
            spacer = QWidget()
            spacer.setFixedWidth(8)
            self.addWidget(spacer)

        feature_actions = [
            ("Time View", "⏱️", "#ffb300", "Access Time View Feature"),
            ("Tabular View", "📋", "#64b5f6", "Access Tabular View Feature"),
            ("Time Report", "📄", "#4db6ac", "Access Time Report Feature"),
            ("FFT", "📈", "#ba68c8", "Access FFT View Feature"),
            ("Waterfall", "🌊", "#4dd0e1", "Access Waterfall Feature"),
            ("Centerline", "📏", "#4dd0e1", "Access Centerline Feature"),     
            ("Orbit", "🪐", "#f06292", "Access Orbit Feature"),
            ("Trend View", "📉", "#aed581", "Access Trend View Feature"),
            ("Multiple Trend View", "📊", "#ff8a65", "Access Multiple Trend View Feature"),
            ("Bode Plot", "🔍", "#7986cb", "Access Bode Plot Feature"),
            ("Polar Plot",  "❄️", "#7986cb", "Access Polar Plot Feature"),       
            ("History Plot", "🕰️", "#ef5350", "Access History Plot Feature"),
            ("Report", "📝", "#ab47bc", "Access Report Feature"),
        ]

        for feature_name, text_icon, color, tooltip in feature_actions:
            add_action(feature_name, text_icon, color, tooltip)

        # Add a spacer to push buttons to the left
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

    def validate_and_display(self, feature_name):
        model_based_features = {"Time View", "Time Report"}

        if feature_name in model_based_features:
            if not self.parent.tree_view.get_selected_model():
                QMessageBox.warning(self, "Selection Required", "Please select a model from the tree view first.")
                return
        else:
            if not self.parent.tree_view.get_selected_channel():
                QMessageBox.warning(self, "Selection Required", "Please select a channel from the tree view first.")
                return

        # Proceed to display the feature
        self.parent.display_feature_content(feature_name, self.parent.current_project)




