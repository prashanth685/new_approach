import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import struct
import json
import logging
from datetime import datetime
import threading
import queue
from collections import defaultdict

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MQTTHandler(QObject):
    # Modified signal to include feature_name
    data_received = pyqtSignal(str, str, str, list, int)  # feature_name, tag_name, model_name, values, sample_rate
    connection_status = pyqtSignal(str)

    def __init__(self, db, project_name, broker="192.168.1.231", port=1883):
        super().__init__()
        self.db = db
        self.project_name = project_name
        self.broker = broker
        self.port = port
        self.client = None
        self.connected = False
        self.subscribed_topics = []
        self.data_queue = queue.Queue()
        self.batch_interval_ms = 100  # Batch data every 100ms
        self.processing_thread = None
        self.running = False
        self.feature_mapping = {
            "Tabular View": ["TabularView"],
            "Time View": ["TimeWave", "TimeReport"],
            "Time Report": ["TimeReport"],
            "FFT": ["FFT"],
            "Waterfall": ["WaterFall"],
            "Centerline": ["CenterLinePlot"],
            "Orbit": ["OrbitView"],
            "Trend View": ["TrendView"],
            "Multiple Trend View": ["MultiTrendView"],
            "Bode Plot": ["BodePlot"],
            "History Plot": ["HistoryPlot"],
            "Polar Plot": ["PolarPlot"],
            "Report": ["Report"]
        }
        logging.debug(f"Initializing MQTTHandler with project_name: {project_name}, broker: {broker}")

    def parse_topic(self, topic):
        try:
            tag_name = topic
            project_data = self.db.get_project_data(self.project_name)
            model_name = None
            if project_data and "models" in project_data:
                for model in project_data["models"]:
                    if model.get("tagName") == topic:
                        model_name = model.get("name")
                        break
            logging.debug(f"Parsed topic {topic}: project_name={self.project_name}, model_name={model_name}, tag_name={tag_name}")
            return self.project_name, model_name, tag_name
        except Exception as e:
            logging.error(f"Error parsing topic {topic}: {str(e)}")
            return None, None, None

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.connection_status.emit("Connected to MQTT Broker")
            logging.info("Connected to MQTT Broker")
            QTimer.singleShot(0, self.subscribe_to_topics)
        else:
            self.connected = False
            self.connection_status.emit(f"Connection failed with code {rc}")
            logging.error(f"Failed to connect to MQTT Broker with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.connection_status.emit("Disconnected from MQTT Broker")
        logging.info("Disconnected from MQTT Broker")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload
            self.data_queue.put((topic, payload))
        except Exception as e:
            logging.error(f"Error queuing MQTT message: {str(e)}")

    def process_data(self):
        batch = defaultdict(list)
        while self.running:
            try:
                # Collect messages for batch_interval_ms
                start_time = datetime.now()
                while (datetime.now() - start_time).total_seconds() * 1000 < self.batch_interval_ms:
                    try:
                        topic, payload = self.data_queue.get(timeout=0.01)
                        batch[topic].append(payload)
                    except queue.Empty:
                        continue

                # Process batched messages
                for topic, payloads in batch.items():
                    project_name, model_name, tag_name = self.parse_topic(topic)
                    if not tag_name or project_name != self.project_name or not model_name:
                        logging.warning(f"Skipping invalid topic: {topic}")
                        continue

                    for payload in payloads:
                        try:
                            # Try JSON decode first
                            try:
                                payload_str = payload.decode('utf-8')
                                data = json.loads(payload_str)
                                values = data.get("values", [])
                                sample_rate = data.get("sample_rate", 1000)
                                if not isinstance(values, list) or not values:
                                    logging.warning(f"Invalid JSON payload format: {payload_str}")
                                    continue
                                num_channels = len(values)
                                logging.debug(f"Parsed JSON payload: {num_channels} channels")
                            except (UnicodeDecodeError, json.JSONDecodeError):
                                payload_length = len(payload)
                                if payload_length < 20 or payload_length % 2 != 0:
                                    logging.warning(f"Invalid payload length: {payload_length} bytes")
                                    continue

                                num_samples = payload_length // 2
                                try:
                                    values = struct.unpack(f"<{num_samples}H", payload)
                                except struct.error as e:
                                    logging.error(f"Failed to unpack payload of {num_samples} uint16_t: {str(e)}")
                                    continue

                                if len(values) < 100:
                                    logging.warning(f"Payload too short: {len(values)} samples")
                                    continue

                                header = values[:100]
                                total_values = values[100:]
                                main_channels = header[2]
                                sample_rate = header[3]
                                tacho_channels_count = header[6]
                                total_channels = main_channels + tacho_channels_count
                                samples_per_channel = (len(total_values) // total_channels) if total_values else 0

                                if main_channels <= 0 or sample_rate <= 0 or tacho_channels_count <= 0 or samples_per_channel <= 0:
                                    logging.error(f"Invalid header values: main_channels={main_channels}, sample_rate={sample_rate}, "
                                                 f"tacho_channels_count={tacho_channels_count}, samples_per_channel={samples_per_channel}")
                                    continue

                                expected_total = samples_per_channel * total_channels
                                if len(total_values) != expected_total:
                                    logging.warning(f"Unexpected data length: got {len(total_values)}, expected {expected_total}")
                                    continue

                                main_data = total_values[:samples_per_channel * main_channels]
                                tacho_data = total_values[samples_per_channel * main_channels:]

                                channel_data = [[] for _ in range(main_channels)]
                                for i in range(0, len(main_data), main_channels):
                                    for ch in range(main_channels):
                                        channel_data[ch].append(main_data[i + ch])

                                tacho_freq_data = tacho_data[:samples_per_channel] if tacho_channels_count >= 1 else []
                                tacho_trigger_data = tacho_data[samples_per_channel:2 * samples_per_channel] if tacho_channels_count >= 2 else []

                                values = [[float(v) for v in ch] for ch in channel_data]
                                if tacho_freq_data:
                                    values.append([float(v) for v in tacho_freq_data])
                                if tacho_trigger_data:
                                    values.append([float(v) for v in tacho_trigger_data])

                                logging.debug(f"Parsed binary payload: main_channels={main_channels}, total_channels={total_channels}, "
                                             f"samples_per_channel={samples_per_channel}")

                            # Emit data for each feature
                            for feature_name, _ in self.feature_mapping.items():
                                self.data_received.emit(feature_name, tag_name, model_name, values, sample_rate)
                                logging.debug(f"Emitted data for {feature_name}/{tag_name}/{model_name}: {len(values)} channels, sample_rate={sample_rate}")

                        except Exception as e:
                            logging.error(f"Error processing payload for topic {topic}: {str(e)}")

                batch.clear()  # Clear batch for next iteration
            except Exception as e:
                logging.error(f"Error in data processing loop: {str(e)}")

    def subscribe_to_topics(self):
        try:
            project_data = self.db.get_project_data(self.project_name)
            for model in project_data.get("models", []):
                tag_name = model.get("tagName", "")
                if tag_name and tag_name not in self.subscribed_topics:
                    self.client.subscribe(tag_name)
                    self.subscribed_topics.append(tag_name)
                    logging.info(f"Subscribed to topic: {tag_name}")
        except Exception as e:
            logging.error(f"Error subscribing to topics: {str(e)}")
            self.connection_status.emit(f"Failed to subscribe to topics: {str(e)}")

    def start(self):
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            self.client.connect_async(self.broker, self.port, 60)
            self.client.loop_start()
            self.running = True
            self.processing_thread = threading.Thread(target=self.process_data, daemon=True)
            self.processing_thread.start()
            logging.info("MQTT client and processing thread started")
        except Exception as e:
            logging.error(f"Failed to start MQTT client: {str(e)}")
            self.connection_status.emit(f"Failed to start MQTT: {str(e)}")

    def stop(self):
        try:
            self.running = False
            if self.processing_thread:
                self.processing_thread.join(timeout=1.0)
                self.processing_thread = None
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                self.subscribed_topics = []
                logging.info("MQTT client and processing thread stopped")
        except Exception as e:
            logging.error(f"Error stopping MQTT client: {str(e)}")