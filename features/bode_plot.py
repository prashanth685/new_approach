from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import pyqtgraph as pg
import numpy as np

class BodePlotFeature:
    def __init__(self, parent, db, project_name, channel=None, model_name=None, console=None):
        self.parent = parent
        self.db = db
        self.project_name = project_name
        # self.channel = int(channel) if channel is not None else None  # Convert channel to int
        self.channel=channel
        self.model_name = model_name
        self.console = console
        self.widget = None
        self.plot_widget = None
        self.mag_plot = None
        self.phase_plot = None
        self.initUI()

    def initUI(self):
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.widget.setLayout(layout)

        label = QLabel(f"Bode Plot for Model: {self.model_name}, Channel: {self.channel}")
        layout.addWidget(label)

        # Create and add the pyqtgraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        # Set up the plot layout with two subplots (magnitude and phase)
        self.plot_widget.getPlotItem().hide()
        self.vb = self.plot_widget.getViewBox()
        self.vb.setBackgroundColor('w')  # White background
        self.layout = pg.GraphicsLayout()
        self.plot_widget.setCentralItem(self.layout)

        # Magnitude plot
        self.mag_plot = self.layout.addPlot(row=0, col=0)
        self.mag_plot.setTitle("Bode Plot - Magnitude")
        self.mag_plot.setLabel('left', "Magnitude (dB)")
        self.mag_plot.setLabel('bottom', "Frequency (Hz)")
        self.mag_plot.setLogMode(x=True, y=False)
        self.mag_plot.showGrid(x=True, y=True, alpha=0.3)

        # Phase plot
        self.layout.nextRow()
        self.phase_plot = self.layout.addPlot(row=1, col=0)
        self.phase_plot.setTitle("Bode Plot - Phase")
        self.phase_plot.setLabel('left', "Phase (degrees)")
        self.phase_plot.setLabel('bottom', "Frequency (Hz)")
        self.phase_plot.setLogMode(x=True, y=False)
        self.phase_plot.showGrid(x=True, y=True, alpha=0.3)

        if not self.model_name and self.console:
            self.console.append_to_console("No model selected in BodePlotFeature.")
        if self.channel is None and self.console:
            self.console.append_to_console("No channel selected in BodePlotFeature.")

    def get_widget(self):
        return self.widget

    def on_data_received(self, tag_name, model_name, values, sample_rate=1000):
        if self.model_name != model_name:
            return  # Ignore data for other models

        if self.console:
            self.console.append_to_console(
                f"Bode Plot ({self.model_name} - {self.channel}): Received data for {tag_name}"
            )

        try:
            # Validate channel and values
            if self.channel is None:
                if self.console:
                    self.console.append_to_console(f"No channel specified for {tag_name}")
                return

            # Convert channel to int if it isn't already
            channel_idx = int(self.channel)

            # Select the appropriate channel data
            if isinstance(values, list) and len(values) > channel_idx >= 0:
                x = np.array(values[channel_idx])
            else:
                x = np.array(values)
                if self.console:
                    self.console.append_to_console(f"Invalid channel index {channel_idx} for {tag_name}, using default data")
                return

            N = len(x)
            if N == 0:
                if self.console:
                    self.console.append_to_console(f"No data received for {tag_name}")
                return

            # Compute FFT
            fft_result = np.fft.fft(x)
            frequencies = np.fft.fftfreq(N, d=1.0/sample_rate)  # Use provided sample_rate
            frequencies = frequencies[:N//2]  # Positive frequencies only
            fft_result = fft_result[:N//2]  # Corresponding FFT values

            # Compute frequency (adjust based on sample rate)
            frequencies = frequencies / 100.0  # Hz, following provided formula

            # Compute amplitude using the formula: A = 4 * sqrt((1/N * sum(x[n] * sin(theta_n))^2 + (1/N * sum(x[n] * cos(theta_n))^2)
            theta = 2 * np.pi * frequencies * np.arange(N)[:, None] / N
            sin_sum = (1/N) * np.sum(x[:, None] * np.sin(theta), axis=0)
            cos_sum = (1/N) * np.sum(x[:, None] * np.cos(theta), axis=0)
            amplitude = 4 * np.sqrt(sin_sum**2 + cos_sum**2)

            # Convert amplitude to dB for magnitude plot
            magnitude = 20 * np.log10(np.abs(amplitude + 1e-10))  # Add small value to avoid log(0)

            # Compute phase using the formula: phi = arctan2(cos_sum / sin_sum) * 180 / pi
            phase = np.arctan2(cos_sum, sin_sum) * (180 / np.pi)

            # Clear previous plots
            self.mag_plot.clear()
            self.phase_plot.clear()

            # Plot new data
            self.mag_plot.plot(frequencies, magnitude, pen='b')
            self.phase_plot.plot(frequencies, phase, pen='b')

            # Update plot settings
            self.mag_plot.setTitle("Bode Plot - Magnitude")
            self.phase_plot.setTitle("Bode Plot - Phase")
            self.plot_widget.show()

        except Exception as e:
            if self.console:
                self.console.append_to_console(f"Error in Bode Plot for {tag_name}: {str(e)}")