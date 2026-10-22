from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from database import get_connection


class TablePage(QWidget):
    def __init__(self, sql_query, headers):
        super().__init__()

        self.sql_query = sql_query

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.info_label = QLabel("Данные из базы данных")
        layout.addWidget(self.info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        layout.addWidget(self.table)

        self.refresh_data()

    # Показывает данные в таблице
    def show_rows(self, rows):
        self.table.setRowCount(len(rows))

        for row_number, row in enumerate(rows):
            for column_number, value in enumerate(row):

                if value is None:
                    value = ""

                item = QTableWidgetItem(str(value))

                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter
                    | Qt.AlignmentFlag.AlignLeft
                )

                self.table.setItem(
                    row_number,
                    column_number,
                    item
                )

        self.info_label.setText(
            f"Количество записей: {len(rows)}"
        )

    # Загружает данные из базы
    def refresh_data(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                self.sql_query
            ).fetchall()

            self.show_rows(rows)

        finally:
            connection.close()