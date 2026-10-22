"""Общие стили приложения. Изменять оформление можно в этом файле."""

APP_STYLE = """
QMainWindow, QWidget {
    background-color: #f4f7fb;
    color: #243247;
    font-family: Arial;
    font-size: 13px;
}

QLabel#pageTitle {
    color: #173b72;
    font-size: 20px;
    font-weight: bold;
    padding: 5px 0;
}

QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 7px;
    top: 0px;
}

QTabBar::tab {
    background-color: #e8eef7;
    color: #334761;
    padding: 12px 8px;
    margin: 0px;
    border: none;
    border-bottom: 3px solid #d9e2ef;
}

QTabBar::tab:selected {
    background-color: #2457a7;
    color: #ffffff;
    font-weight: bold;
    border-bottom: 3px solid #173b72;
}

QPushButton {
    background-color: #2457a7;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 8px 14px;
}

QPushButton:hover {
    background-color: #1b478d;
}

QPushButton:pressed {
    background-color: #15396f;
}

QLineEdit, QComboBox, QDateEdit, QTimeEdit {
    background-color: #ffffff;
    border: 1px solid #cbd6e5;
    border-radius: 5px;
    padding: 7px;
    min-height: 18px;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 1px solid #2457a7;
}

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f2f6fc;
    border: 1px solid #d9e2ef;
    border-radius: 5px;
    gridline-color: #e1e8f1;
    selection-background-color: #d8e7ff;
    selection-color: #173b72;
}

QHeaderView::section {
    background-color: #e8eef7;
    color: #173b72;
    font-weight: bold;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #cbd6e5;
}

QLabel#reportNumber {
    color: #2457a7;
    font-size: 24px;
    font-weight: bold;
}

QFrame#reportCard {
    background-color: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
"""
