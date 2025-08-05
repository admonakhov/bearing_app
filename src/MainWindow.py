from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import QTimer, QElapsedTimer

from src.utils import *
from src.StatusBar import StatusBar
from src.TestBar import TestBar
from src.GraphBar import GraphBar
from src.ModbusClient import Client
from src.DataSaver import DataSaver
import sys



class MainApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Read app configuration
        self.config = read_conf('app.cfg')
        self.offsets = read_conf('offsets.param', float)
        # View parameters
        self.setWindowTitle(self.config['name'])
        # Logic part
        self.datasaver = DataSaver(self)
        self.plc = Client(self.config['host'])
        # self.plc = Client_em()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(int(self.config['ask_int']))
        self.timer = QElapsedTimer()


        # Main Widget
        self.status_bar = StatusBar(self)
        self.settings_bar = TestBar(self)
        self.graph_bar = GraphBar(self)

        # Layout cfg
        self.main_layout = QVBoxLayout()
        self.test_layout = QHBoxLayout()
        self.test_layout.addWidget(self.settings_bar)
        self.test_layout.addWidget(self.graph_bar)
        self.test_layout.setStretch(0, 2)
        self.test_layout.setStretch(1, 8)
        self.main_layout.addWidget(self.status_bar)
        self.main_layout.addLayout(self.test_layout)

        widget = QWidget()
        widget.setLayout(self.main_layout)
        self.setCentralWidget(widget)

        self.time_offset = 0
        self.started = False

    def update(self):
        data = self.plc()

        if data:
            stat = data["Stat"]
            self.settings_bar.update(stat)
            self.status_bar.update_values(data)
            if self.started:
                self.datasaver.add_to_matrix(data, self.get_time())
        else:
            self.setWindowTitle(f'{self.config['name']} - Не удалось установить подключение')



    def stop(self):
        self.started = False
        self.time_offset = self.get_time()
        self.plc.stop()

    def start(self):
        self.started = True
        self.timer.start()

    def get_time(self):
        return self.timer.elapsed() + self.time_offset

    def closeEvent(self, event):
        self.datasaver.save_data('temp.csv')
