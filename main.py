from src.MainWindow import MainWindow, MainApp
from src.hw import check_lic
import sys


if __name__ == '__main__':
    lic = check_lic()
    app = MainApp()
    window = MainWindow(lic)
    window.show()

    sys.exit(app.exec())
