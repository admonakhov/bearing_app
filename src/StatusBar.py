from PySide6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtGui import QIcon
import numpy as np
from src.utils import write_conf
from PySide6.QtCore import Signal

class Parameter(QWidget):
    def __init__(self, name, units, dec=3):
        super().__init__()
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setLineWidth(2)
        frame.setMidLineWidth(0)
        frame.setStyleSheet("background-color: white;")

        self.name = name
        self.label = QLabel(name)
        self.value = QLineEdit()
        self.units = QLabel(units)
        self.dec = dec
        self.value.setReadOnly(True)
        self.label.setMaximumWidth(100)
        self.value.setMaximumWidth(150)
        self.units.setMaximumWidth(100)
        self.layout = QHBoxLayout(frame)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.value)
        self.layout.addWidget(self.units)
        self.setLayout(self.layout)

        self.value.setStyleSheet("""
            QLineEdit {
                border: 2px solid gray;  
                border-radius: 5px;       
                padding: 5px;  
            }
        """)
        self.setMaximumHeight(80)

    def round(self, val):
        val = np.round(val, self.dec)
        if self.dec:
            _int, _dec = str(val).split('.')
            return '.'.join([_int, _dec[:self.dec]])
        else:
            return str(val)

    def update_value(self, new_value):

        self.value.setText(self.round(new_value))


class ResettableParameter(Parameter):
    offset_changed = Signal(str, float)

    def __init__(self, name, units, offsets, dec=3):
        super().__init__(name, units, dec)
        self.offsets = offsets
        self.refresh_button = QPushButton()
        refresh_icon = QIcon.fromTheme("view-refresh")
        self.refresh_button.setIcon(refresh_icon)
        self.layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh_value)

    def update_value(self, new_value):
        self.value.setText(self.round(new_value-self.offsets[self.name]))

    def refresh_value(self):
        self.offsets[self.name] = float(self.value.text()) + self.offsets[self.name]
        write_conf('offsets.param', self.offsets)
        self.offset_changed.emit(self.name, self.offsets[self.name])


class MaxMinParameter(ResettableParameter):
    def __init__(self, name, units, offsets, dec=3):
        super().__init__(name, units, offsets, dec)
        min_label = QLabel('Min:')
        max_label = QLabel('Max:')
        max_min_widget = QWidget()
        self.min_value = QLineEdit()
        self.max_value = QLineEdit()
        mm_layout = QVBoxLayout()
        min_layout = QHBoxLayout()
        max_layout = QHBoxLayout()
        min_layout.addWidget(min_label)
        min_layout.addWidget(self.min_value)
        max_layout.addWidget(max_label)
        max_layout.addWidget(self.max_value)
        mm_layout.addLayout(max_layout)
        mm_layout.addLayout(min_layout)

        max_min_widget.setLayout(mm_layout)
        max_min_widget.setMaximumWidth(100)

        self.layout.addWidget(max_min_widget)
        self.max_val = 0
        self.min_val = 0


    def update_value(self, new_value):
        if new_value > self.max_val:
            self.max_val = new_value
            self.max_value.setText(self.round(self.max_val))
        if new_value  < self.min_val:
            self.min_val = new_value
            self.min_value.setText(self.round(self.min_val))
        self.value.setText(self.round(new_value))

    def reset_values(self):
        self.max_val = 0
        self.min_val = 0


class StatusBar(QWidget):
    offsets_changed = Signal()
    def __init__(self, parent):
        super().__init__()
        self.main_window = parent
        self.offsets = parent.offsets
        self.cycles = Parameter('N', 'циклов', dec=0)
        self.force = ResettableParameter('P', 'кН', self.offsets, dec=2)
        self.momentum = MaxMinParameter('M', 'Н∙м', self.offsets, dec=2)
        self.length = ResettableParameter('L', 'мм', self.offsets, dec=3)
        self.temp = Parameter('T', '°С')
        self.freq = Parameter('f', 'Гц')
        layout = QHBoxLayout()

        layout.addWidget(self.cycles)
        layout.addWidget(self.force)
        layout.addWidget(self.momentum)
        layout.addWidget(self.length)
        layout.addWidget(self.temp)
        layout.addWidget(self.freq)
        self.setMaximumHeight(100)
        self.setLayout(layout)
        self.momentum.offset_changed.connect(lambda *_: self.offsets_changed.emit())
        self.length.offset_changed.connect(lambda *_: self.offsets_changed.emit())

    def update_values(self, data):
        self.cycles.update_value(data['N'])
        self.force.update_value(data['P'])
        self.momentum.update_value(data['M'])
        self.length.update_value(data['L'])
        self.freq.update_value(data['f'])
        self.temp.update_value(data['T'])

    def reset(self):
        self.momentum.reset_values()

