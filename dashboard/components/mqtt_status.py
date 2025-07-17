from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

class MQTTStatus(QLabel):
    def __init__(self, parent):
        super().__init__("MQTT: Disconnected 🔴", parent)
        self.parent = parent
        self.initUI()
        # Connect to parent's mqtt_status_changed signal
        self.parent.mqtt_status_changed.connect(self.update_mqtt_status_indicator)

    def initUI(self):
        self.setToolTip("MQTT Connection Status")
        self.setFixedHeight(40)  # Match toolbar height
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                color: #FFFFFF;
                font-size: 14px;
                font:bold;
                padding: 2px 8px;
                border-radius: 0px;
            }
        """)
        self.update_mqtt_status_indicator()  # Initial update

    def update_mqtt_status_indicator(self):
        status_text = "MQTT:Status Connected 🟢" if self.parent.mqtt_connected else "MQTT: Status Disconnected 🔴"
        self.setText(status_text)