from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget
from PySide6.QtCore import QObject, QThread, Signal, QElapsedTimer
from queue import Queue, Empty
from src.utils import *
from src.StatusBar import StatusBar
from src.TestBar import TestBar
from src.GraphBar import GraphBar
from src.ModbusClient import Client
from src.DataSaver import DataSaver
import sys
import time


class Worker(QObject):
    data_ready = Signal(dict, float)
    error = Signal(str)

    def __init__(self, plc, interval_ms):
        super().__init__()
        self.plc = plc
        self.interval = interval_ms / 1000.0
        self._running = True
        self.init_time = time.perf_counter()
        self._cmd_q: Queue[tuple[str, tuple]] = Queue()
        self._busy = False

    def enqueue_cmd(self, name: str, *args):
        self._cmd_q.put((name, args))

    def reset_time(self):
        self.init_time = time.perf_counter()

    def _process_one_command(self):
        try:
            name, args = self._cmd_q.get_nowait()
        except Empty:
            return False

        self._busy = True
        try:
            if name == 'send_params':
                params, offsets = args
                self.plc.send_params(params, offsets)
            elif name == 'load':
                self.plc.load()
            elif name == 'unload':
                self.plc.unload()
            elif name == 'rotate':
                self.plc.rotate()
            elif name == 'stop_rotate':
                self.plc.stop_rotate()
            elif name == 'reset':
                self.plc.reset()
            elif name == 'stop_all':
                self.plc.stop()
            elif name == 'reset_time':
                self.reset_time()
            else:
                self.error.emit(f'Неизвестная команда: {name}')
        except Exception as e:
            self.error.emit(f'Команда {name} завершилась ошибкой: {e}')
        finally:
            self._busy = False
        return True

    def run(self):
        """Основной цикл: сначала выполняем накопившиеся команды, затем опрашиваем ПЛК."""
        while self._running:
            try:
                processed = 0
                while self._process_one_command():
                    processed += 1
                    if processed >= 100:
                        break

                if processed > 0 or not self._cmd_q.empty():
                    time.sleep(0.005)

                start = time.perf_counter()
                data = self.plc()
                rel_time = round((time.perf_counter() - self.init_time) * 1000.0,2)
                self.data_ready.emit(data if data else {}, rel_time)

                elapsed = time.perf_counter() - start
                if self.interval > elapsed:
                    time.sleep(self.interval - elapsed)

            except Exception as e:
                self.error.emit(str(e))

    def stop(self):
        self._running = False


class MainApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)



class MainWindow(QMainWindow):
    def __init__(self, lic):
        super().__init__()
        # Read app configuration
        self.config = read_conf('app.cfg')
        self.check_lic(lic)
        self.offsets = read_conf('offsets.param', float)

        # Logic part
        self.datasaver = DataSaver(self)
        self.plc = Client(self.config['host'])

        self.timer = QElapsedTimer()
        self.thread = QThread()
        self.worker = Worker(self.plc, int(self.config['ask_int']))
        self.worker.moveToThread(self.thread)

        # сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.error.connect(self.on_error)


        # Main Widget
        self.status_bar = StatusBar(self)
        self.settings_bar = TestBar(self)
        self.graph_bar = GraphBar(self)

        self.status_bar.offsets_changed.connect(self._resend_setpoints)

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

        self._freq_window_size = 100
        self._time_window = []
        self._cycle_window = []
        self._last_freq = None
        self.elapsed_time = 0

        if self.lic_checked:
            self.thread.start()
            self.timer.start()
            self.time_offset = self.timer.elapsed()
            self.datasaver.start_session()

    def check_lic(self, lic):
        if lic:
            self.lic_checked = True
            self.setWindowTitle(f"{self.config['name']} - {lic}")
        else:
            self.lic_checked = False
            self.setWindowTitle(f"{self.config['name']} - Версия не зарегистрирована")

    def _resend_setpoints(self):
        params = self.settings_bar()
        self.worker.enqueue_cmd('send_params', params, self.offsets)

    def stop(self):
        self.time_offset = self.get_time()
        self.datasaver.save_data(get_filepath(self.config['result_path'], 'stop'))
        self.worker.enqueue_cmd('stop_all')

    def start(self):
        self.worker.enqueue_cmd('reset_time')
        self.datasaver.save_data(get_filepath(self.config['result_path'], 'start'))
        self.datasaver.start_session()
        self.reset()

    def reset(self):
        self.status_bar.reset()
        self.worker.enqueue_cmd('reset')

    def get_time(self):
        return self.timer.elapsed() + self.time_offset

    def closeEvent(self, event):
        self.stop()
        self.settings_bar.stop()
        time.sleep(1)
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        self.datasaver.save_data('temp.csv')
        self.graph_bar.close()
        super().closeEvent(event)

    def on_data_ready(self, data, rel_time):
        if data:

            f_val = self.update_frequency_regression(data, rel_time)
            if f_val is not None:
                data['f'] = f_val

            stat = data["Stat"]
            data = self.datasaver.apply_filters(data)
            self.settings_bar.update(stat)
            self.status_bar.update_values(data)
            self.datasaver.add_to_matrix(data, round(rel_time, 1))
            if (self.elapsed_time // 10) == 1:
                self.elapsed_time = 0
                if stat[0] and self.settings_bar.loaded == False:
                    self.settings_bar.loaded = True
                    self.settings_bar.loading_btn.setText("Стоп")
                    self.settings_bar.rotation_btn.setEnabled(True)
                elif stat[0] == False and self.settings_bar.loaded == True:
                    self.settings_bar.stop()

            else:
                self.elapsed_time += 1

        else:
            self.setWindowTitle(f"{self.config['name']} - Нет данных")

    def on_error(self, msg):
        self.setWindowTitle(f"{self.config['name']} - Ошибка PLC: {msg}")

    def clean_data(self):
        self.worker.reset_time()
        self.datasaver.drop_data()
        self.datasaver.start_session()

    def update_frequency_regression(self, data, rel_time):
        """Обновляет частоту f по линейной регрессии на последних N точках."""
        N = data.get("N")
        if N is None:
            return None

        self._time_window.append(rel_time / 1000.0)  # в сек
        self._cycle_window.append(N)

        if len(self._time_window) > self._freq_window_size:
            self._time_window.pop(0)
            self._cycle_window.pop(0)

        if len(self._time_window) >= 2:
            coef = np.polyfit(self._time_window, self._cycle_window, 1)
            slope = coef[0]
            self._last_freq = slope
        return self._last_freq