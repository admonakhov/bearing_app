from PySide6.QtWidgets import QDialog, QVBoxLayout,QHBoxLayout, QLabel, QPushButton, QCheckBox, QLineEdit, QGridLayout, QToolButton, QWidget
from PySide6.QtCore import Qt, QTimer 
from PySide6.QtGui import QCursor


def get_parameters(plc):
        data = plc.get_parameters()
        P = (data.get('P_', ''))
        I = (data.get('I_', ''))
        D = str(data.get('D_', ''))
        SUP = (data.get('SUP', ''))
        T2F = (data.get('T2F', ''))
        return P, I, D, SUP, T2F

def check_PID(plc):
    try:
        P, I, D, SUP, T2F = get_parameters(plc)
        if P and I and D and SUP and T2F:
            return True
        return False
    except Exception as e:
        return False

class PID_button(QWidget):
    def __init__(self, plc):
        super().__init__()
        self.plc = plc
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
        self.plc = parent.plc
        main_layout = QVBoxLayout(self)
        btns_layout = QHBoxLayout()
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(20)
        warning_lbl = QLabel("Изменение параметров нагружения может привести к повреждению оборудования.")
        warning_lbl.setStyleSheet("color: red; font-weight: bold;")
        self.accept = QCheckBox("Я понимаю риски и принимаю ответственность за изменения параметров.")
        
        for i, widget in enumerate(['', 'P', 'I', 'D', 'SUP', 'T2F']):
            param_layout.addWidget(QLabel(widget), 0, i)

        out_label = QLabel('Актуальные значения:')
        self.P_out=QLineEdit()
        self.I_out=QLineEdit()
        self.D_out=QLineEdit()
        self.SUP_out=QLineEdit()
        self.T2F_out=QLineEdit()
        param_layout.addWidget(out_label, 1, 0)

        for i, widget in enumerate([self.P_out, self.I_out, self.D_out, self.SUP_out, self.T2F_out]):
            widget.setReadOnly(True)
            param_layout.addWidget(widget, 1, i+1)

        in_label = QLabel('Новые значения:')
        self.P_in= QLineEdit()
        self.I_in= QLineEdit()
        self.D_in= QLineEdit()
        self.SUP_in= QLineEdit()
        self.T2F_in= QLineEdit()
        param_layout.addWidget(in_label, 2, 0)

        for i, widget in enumerate([self.P_in, self.I_in, self.D_in, self.SUP_in, self.T2F_in]):
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

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.fill_parameters)
        self.update_timer.start(1000) 
        self.fill_parameters()

    def send_parameters(self):
        P = float(self.P_in.text())
        I = float(self.I_in.text()) 
        D = float(self.D_in.text())
        SUP = float(self.SUP_in.text())
        T2F = float(self.T2F_in.text())
        self.plc.send_PID(P, I, D, SUP, T2F)


    def fill_parameters(self, P, I, D, SUP, T2F):
        P, I, D, SUP, T2F = get_parameters(self.plc)
        self.P_out.setText(str(P))
        self.I_out.setText(str(I))
        self.D_out.setText(str(D))
        self.SUP_out.setText(str(SUP))
        self.T2F_out.setText(str(T2F))


    def accept_changed(self, state):
        for widget in [self.P_in, self.I_in, self.D_in, self.SUP_in, self.T2F_in]:
            if self.accept.isChecked():
                widget.setReadOnly(False)
            else:
                widget.setReadOnly(True)
        
        if self.accept.isChecked():
            self.btn_send.setEnabled(True)
        else:
            self.btn_send.setEnabled(False)
    

