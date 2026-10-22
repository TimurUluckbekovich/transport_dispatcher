"""Запуск приложения АРМ диспетчера городского транспорта."""

import sys

from PyQt6.QtWidgets import QApplication

from database import initialize_database
from styles import APP_STYLE
from ui.main_window import MainWindow


def main():
    initialize_database()

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
