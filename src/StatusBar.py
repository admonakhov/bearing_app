from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtGui import QIcon

from src.utils import read_conf, write_conf


class Parameter(QWidget):
    def __init__(self, name, units):
        super().__init__()
        self.name = name
        self.label = QLabel(name)
        self.value = QLineEdit()
        self.units = QLabel(units)
        self.value.setReadOnly(True)
        self.label.setMaximumWidth(100)
        self.value.setMaximumWidth(150)
        self.units.setMaximumWidth(100)
        self.layout = QHBoxLayout()
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

    def update_value(self, new_value):
        new_value = round(new_value, 3)
        self.value.setText(str(new_value)[:5])


class ResettableParameter(Parameter):
    def __init__(self, name, units, offsets):
        super().__init__(name, units)
        self.offsets = offsets
        self.refresh_button = QPushButton()
        refresh_icon = QIcon.fromTheme("view-refresh")
        self.refresh_button.setIcon(refresh_icon)
        self.layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh_value)

    def update_value(self, new_value):
        new_value = round(new_value, 3)
        self.value.setText(str(new_value-self.offsets[self.name])[:5])

    def refresh_value(self):
        self.offsets[self.name] = float(self.value.text()) + self.offsets[self.name]
        write_conf('offsets.param', self.offsets)


class StatusBar(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.offsets = parent.offsets
        self.cycles = Parameter('N', 'циклов')
        self.force = ResettableParameter('P', 'кН', self.offsets)
        self.momentum = ResettableParameter('M', 'Н∙м', self.offsets)
        self.length = ResettableParameter('L', 'мм', self.offsets)
        self.temp = Parameter('T', '°С')

        # self.angle = Parameter('α', '°')
        self.freq = Parameter('f', 'Гц')
        layout = QHBoxLayout()

        layout.addWidget(self.cycles)
        layout.addWidget(self.force)
        layout.addWidget(self.momentum)
        layout.addWidget(self.length)
        layout.addWidget(self.temp)
        layout.addWidget(self.freq)

        self.setLayout(layout)

    def update_values(self, data):
        self.cycles.update_value(data['N'])
        self.force.update_value(data['P'])
        self.momentum.update_value(data['M'])
        self.length.update_value(data['L'])
        self.freq.update_value(data['f'])
        self.temp.update_value(data['T'])


