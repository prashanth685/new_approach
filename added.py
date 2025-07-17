import sys
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

# Polar data: angles (theta in radians) and radius (r)
theta = np.linspace(0, 2 * np.pi, 360)
r = np.abs(np.sin(5 * theta))  # example function: rose curve

# Convert to Cartesian coordinates
x = r * np.cos(theta)
y = r * np.sin(theta)

# PyQtGraph setup
app = QtWidgets.QApplication([])
win = pg.plot()
win.setWindowTitle('Polar Plot (Simulated in PyQtGraph)')
win.setAspectLocked(True)  # equal aspect ratio


# Plot the curve
win.plot(x, y, pen=pg.mkPen('w', width=2))


# Show the app
if (sys.flags.interactive != 1) or not hasattr(QtWidgets, 'PYQT_VERSION'):
    QtWidgets.QApplication.instance().exec_()
