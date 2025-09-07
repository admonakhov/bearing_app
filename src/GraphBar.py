from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
import pyqtgraph as pg
from PySide6.QtCore import QTimer, QThread, Signal, QObject
import numpy as np
from src.utils import read_json


class GraphWorker(QObject):
    data_ready = Signal(object, object)  # x, y
    def __init__(self, datasaver, axis, n_vals, filter_frame):
        super().__init__()
        self.datasaver = datasaver
        self.axis = axis
        self.n_vals = n_vals
        self.filter_frame = filter_frame
        self._running = True

    def run(self):
        """Запускается в отдельном QThread"""
        while self._running:
            x_axis = self.axis.x
            y_axis = self.axis.y
            x = self.datasaver.data[x_axis]
            y = self.datasaver.data[y_axis]
            self.data_ready.emit(x, y)
            QThread.msleep(100)

    def stop(self):
        self._running = False

class AxisChooser(QWidget):
    def __init__(self):
        super().__init__()
        self.axis = read_json('axis.json')
        self.graph_type_chooser = QPushButton('Скользящее окно')
        self.graph_type_chooser.clicked.connect(self.change_type)
        self.graph_type = 'rolling'
        layout = QHBoxLayout()
        x_axis = QComboBox()
        y_axis = QComboBox()

        for key in self.axis.keys():
            x_axis.addItem(key)
            y_axis.addItem(key)
        layout.addWidget(QLabel('X:'))
        layout.addWidget(x_axis)
        layout.addWidget(QLabel('Y:'))
        layout.addWidget(y_axis)
        layout.addWidget(self.graph_type_chooser)
        layout.setStretch(0, 1)
        layout.setStretch(1, 5)
        layout.setStretch(2, 1)
        layout.setStretch(3, 5)
        layout.setStretch(4, 2)
        x_axis.setCurrentIndex(0)
        y_axis.setCurrentIndex(1)

        x_axis.currentTextChanged.connect(self.on_selection_changeX)
        y_axis.currentTextChanged.connect(self.on_selection_changeY)

        self.x = "time"
        self.xlbl = x_axis.currentText()
        self.y = "N"
        self.ylbl = y_axis.currentText()
        self.setLayout(layout)

    def on_selection_changeX(self, text):
        self.x = self.axis[text]
        self.xlbl = text

    def on_selection_changeY(self, text):
        self.y = self.axis[text]
        self.ylbl = text

    def change_type(self):
        if self.graph_type == 'None':
            self.graph_type_chooser.setText('Скользящее окно')
            self.graph_type = 'rolling'
        elif self.graph_type == 'rolling':
            self.graph_type_chooser.setText('Все данные')
            self.graph_type = 'None'


class Graph(QWidget):
    def __init__(self, config):
        super().__init__()
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.showGrid(x=True, y=True)

        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget)

        self.graphWidget.setBackground('w')
        pen = pg.mkPen(config['pen_color'], width=int(config['pen_width']))
        self.curve = self.graphWidget.plot([0], [0] , pen=pen)
        self.graphWidget.update()
        self.setLayout(layout)


class GraphWindow(QWidget):
    def __init__(self, datasaver, config):
        super().__init__()
        self.datasaver = datasaver
        self.config = config
        self.n_vals = int(self.config['values_to_view'])

        self.graph = Graph(self.config)
        self.axis = AxisChooser()

        layout = QVBoxLayout()
        layout.addWidget(self.graph)
        layout.addWidget(self.axis)
        self.layout = layout
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(200)
        self.resize(600, 400)

        self.last_index = 0
        self.full_redraw = True

        self.axis.on_selection_changeX = self.wrap_axis_change(self.axis.on_selection_changeX)
        self.axis.on_selection_changeY = self.wrap_axis_change(self.axis.on_selection_changeY)
        self.axis.change_type = self.wrap_axis_change(self.axis.change_type)

    def wrap_axis_change(self, func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            self.full_redraw = True
            self.last_index = 0
        return wrapper

    def update_graph(self):
        data = self.datasaver.get_matrices()
        if not data or len(data.get("time", [])) == 0:
            return

        x_key = self.axis.x
        y_key = self.axis.y
        self.change_title()
        self.graph.graphWidget.setLabel('bottom', self.axis.xlbl)
        self.graph.graphWidget.setLabel('left', self.axis.ylbl)

        x_full = np.asarray(data.get(x_key, []), dtype=np.float32)
        y_full = np.asarray(data.get(y_key, []), dtype=np.float32)
        if x_full.size == 0 or y_full.size == 0:
            return

        n = min(len(x_full), len(y_full))
        if n <= 1:
            return
        x_full = x_full[-n:]
        y_full = y_full[-n:]

        x = x_full[-self.n_vals:]
        y = y_full[-self.n_vals:]

        mask = np.isfinite(x) & np.isfinite(y)
        if not np.any(mask):
            return
        x = x[mask]
        y = y[mask]
        if x.size <= 1:
            return

        self.graph.graphWidget.setDownsampling(auto=False)
        self.graph.curve.setData(x, y)

        self.full_redraw = False
        self.last_index = 0

    def change_title(self):
        self.setWindowTitle(self.axis.ylbl)

    def closeEvent(self, event):
        self.timer.stop()
        self.close()

class GraphBar(GraphWindow):
    def __init__(self, parent):
        super().__init__(parent.datasaver, parent.config)
        self.windows = []
        self.add_btn = QPushButton("+")
        self.add_btn.clicked.connect(self.add_graph_window)
        self.layout.addWidget(self.add_btn)

    def add_graph_window(self):
        win = GraphWindow(self.datasaver, self.config)
        self.windows.append(win)
        win.show()

    def change_title(self):
        pass

    def closeEvent(self, event):
        for win in self.windows:
            win.close()
        event.accept()
