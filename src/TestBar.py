import time

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QMessageBox
from PySide6.QtGui import QDoubleValidator
from PySide6.QtGui import QIcon
from src.utils import read_conf, get_file_path
import os


class Parameter(QWidget):
    def __init__(self, name, units, value, max_val, min_val=0):
        super().__init__()
        self.name = QLabel(f'{name}, {units}')
        self.value = QLineEdit()
        self.validator = QDoubleValidator(bottom=min_val, top=max_val, decimals=3)
        self.value.setText(value)
        self.value.setMaximumWidth(200)
        layout = QVBoxLayout()
        layout.addWidget(self.name)
        layout.addWidget(self.value)
        self.setLayout(layout)
        self.value.editingFinished.connect(self.on_value_finished)

        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid white;  
                border-radius: 5px;       
                padding: 1px;  
            }
        """)


    def on_value_finished(self):
        text = self.value.text()
        state = self.validator.validate(text, 0)[0]

        if  state == QDoubleValidator.Acceptable:
            self.set_valid()
        else:
            self.set_invalid()
            self.value.clear()

    def __call__(self):
        return self.value.text()

    def set_invalid(self):
        self.value.setStyleSheet("QLineEdit { background-color: red}")
    def set_valid(self):
        self.value.setStyleSheet("")


class TestBar(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.main_window = parent
        self.test_params = self.get_test_parameters()
        self.force = Parameter('Уровень нагружения', 'кН', self.test_params['P_tar'], 100, -100)
        self.freq = Parameter('Частота нагружения', 'Гц', self.test_params['f_tar'], 100)
        self.force_rate = Parameter('Скорость нагружения', 'c', self.test_params['P_rate_tar'], 100)
        self.length_lim = Parameter('Значение зазора', 'мм', self.test_params['L_lim'], 10)
        self.m_max = Parameter('Верхний предел по моменту', 'Нм', self.test_params['M_max'], 50, -50)
        self.temp_lim = Parameter('Температура', '°С', self.test_params['T_max'], 1000)
        self.cycle_lim = Parameter('Значение наработки', 'цикл', self.test_params['N_max_lim'], 1e8)


        self.loading_btn = QPushButton('Нагружение')
        self.loading_btn.clicked.connect(self.apply_load)
        self.rotation_btn = QPushButton('Качение')
        self.rotation_btn.clicked.connect(self.rotate)
        self.rotation_btn.setEnabled(False)
        self.stop_btn = QPushButton('Сброс')
        self.stop_btn.clicked.connect(self.main_window.reset)
        self.save_button = QPushButton()
        self.save_button.setIcon(QIcon.fromTheme("document-save"))
        self.save_button.clicked.connect(self.save_file)

        self.save_button.setMaximumWidth(50)
        self.rotation_btn.setMaximumWidth(200)
        self.loading_btn.setMaximumWidth(200)

        data_layout = QHBoxLayout()
        container = QWidget()
        container.setLayout(data_layout)

        container.setMaximumWidth(200)

        data_layout.addWidget(self.stop_btn, 2)
        data_layout.addWidget(self.save_button, 1)

        layout = QVBoxLayout()
        layout.addWidget(self.force)
        layout.addWidget(self.freq)
        layout.addWidget(self.force_rate)
        layout.addWidget(self.length_lim)
        layout.addWidget(self.temp_lim)
        layout.addWidget(self.m_max)
        layout.addWidget(self.cycle_lim)
        layout.addWidget(self.loading_btn)
        layout.addWidget(self.rotation_btn)
        layout.addWidget(container)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.loaded = False
        self.rotating = False

    def __call__(self):
        return {"P_tar": self.force(), "f_tar": self.freq(), "P_rate_tar": self.force_rate(),
         "L_lim": self.length_lim(), "T_max": self.temp_lim(), "N_max_lim":self.cycle_lim(),
                "M_max":self.m_max()}

    def update(self, st):
        if st[2]:
            self.temp_lim.set_invalid()
        else:
            self.temp_lim.set_valid()
        if st[5]:
            self.m_max.set_invalid()
        else:
            self.m_max.set_valid()
        if st[6]:
            self.cycle_lim.set_invalid()
        else:
            self.cycle_lim.set_valid()

    def apply_load(self):
        params = self()
        self.write_test_parametrs(params)
        self.main_window.worker.enqueue_cmd('send_params', params, self.main_window.offsets)

        if self.loaded:
            self.stop()
        else:
            self.main_window.start()
            self.loaded = True
            self.loading_btn.setText('Стоп')

            self.main_window.worker.enqueue_cmd('load')

            self.rotation_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)


    def rotate(self):
        if self.rotating:
            self.rotating = False
            self.main_window.worker.enqueue_cmd('stop_rotate')
            self.rotation_btn.setText('Качение')
            self.loading_btn.setEnabled(True)
        else:
            self.rotating = True
            self.main_window.worker.enqueue_cmd('rotate')
            self.rotation_btn.setText('Стоп')
            self.loading_btn.setEnabled(False)


    def stop(self):
        self.rotating = False
        self.loaded = False

        self.main_window.worker.enqueue_cmd('stop_rotate')
        self.main_window.worker.enqueue_cmd('unload')

        self.rotation_btn.setText('Качение')
        self.loading_btn.setText('Нагружение')
        self.loading_btn.setEnabled(True)
        self.rotation_btn.setEnabled(False)

        self.main_window.stop()
        self.main_window.timer.start()

    def reset(self):
        if self.main_window.datasaver.data:
            self.main_window.datasaver.save_data('temp.csv')

        self.main_window.datasaver.drop_data()
        self.stop()

    def warning_dialog(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Внимание")
        msg_box.setText("Сброс приведет к потере записанных данных. Вы согласны удалить данные?")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg_box.exec()
        if result == QMessageBox.Ok:
            self.reset()
        self.main_window.worker.enqueue_cmd('reset')

    def get_test_parameters(self):
        if os.path.isfile('test_parameters.param'):
            return read_conf('test_parameters.param')
        else:
            self.write_test_parametrs({"P_tar": 0, "f_tar": 0, "P_rate_tar": 0,
                                       "L_lim":0,"T_max":0, 'N_max_lim':0, 'M_max':0})
            self.get_test_parameters()
            return read_conf('test_parameters.param')

    def write_test_parametrs(self, params:dict):
        with open('test_parameters.param', 'w') as file:
            for key in params.keys():
                file.write(f'{key} {params[key]}\n')

    def save_file(self):
        path = get_file_path()
        if path:
            self.main_window.datasaver.save_data(path)