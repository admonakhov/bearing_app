from PySide6.QtWidgets import QDialog, QVBoxLayout,QHBoxLayout, QLabel, QPushButton, QCheckBox, QLineEdit, QGridLayout, QToolButton, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

def get_data_from_plc():
    pass

def send_data_to_plc(P, I, D, SUP):
    pass

def check_plc_configure():
    pass

class PID_button(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QHBoxLayout(self)
        gear_btn = QToolButton(self)
        gear_btn.setText("⚙")
        gear_btn.setToolTip("Настройки")
        gear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gear_btn.clicked.connect(self._open_settings)
        main_layout.addWidget(gear_btn)
        self.setLayout(main_layout)
        self._settings_window = None
        self.setMaximumWidth(50)

    def _open_settings(self):
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(False)
        self.resize(400, 300)

        main_layout = QVBoxLayout(self)
        btns_layout = QHBoxLayout()
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(20)
        warning_lbl = QLabel("Изменение параметров нагружения может привести к повреждению оборудования.")
        warning_lbl.setStyleSheet("color: red; font-weight: bold;")
        self.accept = QCheckBox("Я понимаю риски и принимаю ответственность за изменения параметров.")
        
        for i, widget in enumerate(['', 'P', 'I', 'D', 'SUP']):
            param_layout.addWidget(QLabel(widget), 0, i)

        out_label = QLabel('Актуальные значения:')
        self.P_out=QLineEdit()
        self.I_out=QLineEdit()
        self.D_out=QLineEdit()
        self.SUP_out=QLineEdit()
        param_layout.addWidget(out_label, 1, 0)

        for i, widget in enumerate([self.P_out, self.I_out, self.D_out, self.SUP_out]):
   
            widget.setReadOnly(True)
            param_layout.addWidget(widget, 1, i+1)

        in_label = QLabel('Новые значения:')
        self.P_in= QLineEdit()
        self.I_in= QLineEdit()
        self.D_in= QLineEdit()
        self.SUP_in= QLineEdit()
        param_layout.addWidget(in_label, 2, 0)
        for i, widget in enumerate([self.P_in, self.I_in, self.D_in, self.SUP_in]):
            widget.setReadOnly(True)
            param_layout.addWidget(widget, 2, i+1)

        main_layout.addLayout(param_layout)
        main_layout.addSpacing(50)
        main_layout.addWidget(warning_lbl)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.accept)
        main_layout.addStretch()

        btn_close = QPushButton("Закрыть")
        self.btn_send = QPushButton("Отправить")
        btns_layout.addWidget(self.btn_send)
        btns_layout.addWidget(btn_close)
        btn_close.clicked.connect(self.close)
        self.btn_send.clicked.connect(self.send_parameters)
        self.btn_send.setEnabled(False)
        self.accept.stateChanged.connect(self.accept_changed)
        main_layout.addLayout(btns_layout)

    def send_parameters(self):
        print("Sending parameters to PLC...")
        pass

    def accept_changed(self, state):
        for widget in [self.P_in, self.I_in, self.D_in, self.SUP_in]:
            if self.accept.isChecked():
                widget.setReadOnly(False)
            else:
                widget.setReadOnly(True)
        
        if self.accept.isChecked():
            self.btn_send.setEnabled(True)
        else:
            self.btn_send.setEnabled(False)
