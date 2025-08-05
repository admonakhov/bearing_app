from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton
import pyqtgraph as pg
from PySide6.QtCore import QTimer
import numpy as np
from src.utils import read_json

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
        self.graphWidget.setDownsampling(auto=True)
        self.graphWidget.update()
        self.setLayout(layout)





class GraphBar(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.datasaver = parent.datasaver
        self.config = parent.config
        self.n_vals = int(self.config['values_to_view'])
        self.graph = Graph(self.config)
        self.axis = AxisChooser()
        layout = QVBoxLayout()
        layout.addWidget(self.graph)
        layout.addWidget(self.axis)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_graph)
        self.timer.start(100)



    def update_graph(self):
        x_axis = self.axis.x
        y_axis = self.axis.y

        self.graph.graphWidget.setLabel('bottom', self.axis.xlbl)
        self.graph.graphWidget.setLabel('left', self.axis.ylbl)
        if self.axis.graph_type == 'rolling':
            x = np.array(self.datasaver.data[x_axis][-self.n_vals:])
            y = np.array(self.datasaver.data[y_axis][-self.n_vals:])
        elif self.axis.graph_type == 'None':
            x = np.array(self.datasaver.data[x_axis])
            y = np.array(self.datasaver.data[y_axis])
        try:
            self.graph.curve.setData(x, y)
            self.graph.graphWidget.update()
        except ValueError:
            print('ValueError')
