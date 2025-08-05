from src.MainWindow import MainWindow, MainApp

import sys


if __name__ == '__main__':

    app = MainApp()
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
