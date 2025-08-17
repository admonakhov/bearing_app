from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
import pyqtgraph as pg
from PySide6.QtCore import QTimer, QThread, Signal, QObject
import numpy as np
from src.utils import read_json, moving_average


def adaptive_downsample(x, y, max_points: int = 5000):
    """
    Адаптивный даунсэмплинг: уменьшает количество точек до max_points.

    :param x: numpy-массив X
    :param y: numpy-массив Y
    :param max_points: максимально допустимое количество точек
    :return: (x_ds, y_ds) - уменьшенные массивы
    """
    n_points = len(x)
    if n_points <= max_points:
        return x, y

    step = int(np.ceil(n_points / max_points))
    return np.array(x[::step]), np.array(y[::step])

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

            if self.filter_frame:
                x = moving_average(x, self.filter_frame)
                y = moving_average(y, self.filter_frame)

            if self.axis.graph_type == 'rolling':
                x = x[-self.n_vals:]
                y = y[-self.n_vals:]
            else:
                x, y = adaptive_downsample(x, y)

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
        # self.graphWidget.setDownsampling(auto=True)
        self.graphWidget.update()
        self.setLayout(layout)


# class GraphWindow(QWidget):
#     def __init__(self, datasaver, config):
#         super().__init__()
#         self.datasaver = datasaver
#         self.config = config
#         self.n_vals = int(self.config['values_to_view'])
#         self.filter_frame = int(self.config['graph_filter_frame'])
#
#         self.graph = Graph(self.config)
#         self.axis = AxisChooser()
#
#         layout = QVBoxLayout()
#         layout.addWidget(self.graph)
#         layout.addWidget(self.axis)
#         self._layout = layout
#         self.setLayout(layout)
#
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.update_graph)
#         self.timer.start(100)
#         self.resize(600, 400)
#
#     def update_graph(self):
#         x_axis = self.axis.x
#         y_axis = self.axis.y
#         self.change_title()
#         self.graph.graphWidget.setLabel('bottom', self.axis.xlbl)
#         self.graph.graphWidget.setLabel('left', self.axis.ylbl)
#
#         if self.axis.graph_type == 'rolling':
#             x = np.array(self.datasaver.data[x_axis][-self.n_vals:])
#             y = np.array(self.datasaver.data[y_axis][-self.n_vals:])
#             self.graph.graphWidget.setDownsampling(auto=False)
#         else:
#             x = np.array(self.datasaver.data[x_axis])
#             y = np.array(self.datasaver.data[y_axis])
#             self.graph.graphWidget.setDownsampling(auto=True)
#
#         if self.filter_frame:
#             x = moving_average(x, self.filter_frame)
#             y = moving_average(y, self.filter_frame)
#
#         try:
#             self.graph.curve.setData(x, y)
#             self.graph.graphWidget.update()
#         except ValueError:
#             print('ValueError')
#
#     def change_title(self):
#         self.setWindowTitle(self.axis.ylbl)
#
#     def closeEvent(self, event):
#         self.timer.stop()
#         self.close()

class GraphWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.datasaver = parent.datasaver
        self.config = parent.config
        self.n_vals = int(self.config['values_to_view'])
        self.filter_frame = int(self.config['graph_filter_frame'])

        self.graph = Graph(self.config)
        self.axis = AxisChooser()

        layout = QVBoxLayout()
        layout.addWidget(self.graph)
        layout.addWidget(self.axis)
        self._layout = layout
        self.setLayout(layout)

        self.worker = GraphWorker(self.datasaver, self.axis, self.n_vals, self.filter_frame)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.data_ready.connect(self.update_plot)
        self.thread.start()

        self.resize(600, 400)

    def change_title(self):
        self.setWindowTitle(self.axis.ylbl)

    def update_plot(self, x, y):
        """В GUI-потоке"""
        self.change_title()
        try:
            # if self.axis.graph_type == 'rolling':
            #     self.graph.graphWidget.setDownsampling(auto=False)
            # else:
            #     self.graph.graphWidget.setDownsampling(auto=True)

            self.graph.curve.setData(x, y)
            self.graph.graphWidget.update()
        except ValueError:
            print("ValueError")



    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()

        self.parent.windows.remove(self)
        if len(self.parent.windows) < 3:
            self.parent.add_btn.setEnabled(True)

        event.accept()

class GraphBar(GraphWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.windows = []
        self.add_btn = QPushButton("+")
        self.add_btn.clicked.connect(self.add_graph_window)
        self._layout.addWidget(self.add_btn)

    def add_graph_window(self):
        win = GraphWindow(self)
        self.windows.append(win)
        if len(self.windows) >= 3:
            self.add_btn.setEnabled(False)
        win.show()

    def change_title(self):
        pass

    def closeEvent(self, event):
        for win in self.windows:
            win.close()
        event.accept()


