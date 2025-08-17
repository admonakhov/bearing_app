from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import QObject, QThread, Signal, QElapsedTimer

from src.utils import *
from src.StatusBar import StatusBar
from src.TestBar import TestBar
from src.GraphBar import GraphBar
from src.ModbusClient import Client
from src.DataSaver import DataSaver
import sys

import time


class Worker(QObject):
    data_ready = Signal(dict, float)  # передаем data + rel_time
    error = Signal(str)

    def __init__(self, plc, interval_ms):
        super().__init__()
        self.plc = plc
        self.interval = interval_ms / 1000
        self._running = True
        self.init_time = time.perf_counter()  # точка отсчета времени

    def run(self):
        while self._running:
            try:
                start = time.perf_counter()
                data = self.plc()
                rel_time = (time.perf_counter() - self.init_time) * 1000
                self.data_ready.emit(data if data else {}, rel_time)

                sleep_int = time.perf_counter() - start
                if self.interval > sleep_int:
                    time.sleep(self.interval - sleep_int)
            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self._running = False



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
        # self.update_timer = QTimer(self)
        # self.update_timer.timeout.connect(self.update)
        # self.update_timer.start(int(self.config['ask_int']))

        self.timer = QElapsedTimer()
        self.thread = QThread()
        self.worker = Worker(self.plc, int(self.config['ask_int']))
        self.worker.moveToThread(self.thread)

        # сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.error.connect(self.on_error)

        self.thread.start()

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

        self.timer.start()
        self.time_offset = self.timer.elapsed()

    def update(self):
        data = self.plc()

        if data:
            stat = data["Stat"]
            self.settings_bar.update(stat)
            self.status_bar.update_values(data)
            self.datasaver.add_to_matrix(data, self.get_time())

        else:
            self.setWindowTitle(f'{self.config['name']} - Не удалось установить подключение')


    def stop(self):
        self.time_offset = self.get_time()
        self.datasaver.save_data(get_filepath(self.config['result_path'], 'stop'))
        self.plc.stop()
        self.reset()

    def start(self):
        self.datasaver.save_data(get_filepath(self.config['result_path'], 'start'))
        self.reset()

    def get_time(self):
        return self.timer.elapsed() + self.time_offset


    def closeEvent(self, event):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        self.datasaver.save_data('temp.csv')
        self.graph_bar.close()
        super().closeEvent(event)

    def reset(self):
        self.status_bar.reset()
        self.datasaver.drop_data()

    def on_data_ready(self, data, rel_time):
        if data:
            stat = data["Stat"]
            self.settings_bar.update(stat)
            self.status_bar.update_values(data)
            self.datasaver.add_to_matrix(data, round(rel_time, 1))
        else:
            self.setWindowTitle(f"{self.config['name']} - Нет данных")

    def on_error(self, msg):
        self.setWindowTitle(f"{self.config['name']} - Ошибка PLC: {msg}")