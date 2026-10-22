import sqlite3

from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
)

from database import get_connection
from .table_page import TablePage


# Форма добавления и изменения автобуса
class BusDialog(QDialog):
    def __init__(self, bus_id=None, parent=None):
        super().__init__(parent)

        self.bus_id = bus_id

        if bus_id is None:
            self.setWindowTitle("Добавление автобуса")
        else:
            self.setWindowTitle("Изменение автобуса")

        self.setMinimumWidth(400)

        # Поля формы
        self.state_number = QLineEdit()
        self.state_number.setPlaceholderText("Например, A1234AA")

        self.model = QLineEdit()
        self.model.setPlaceholderText("Модель автобуса")

        self.capacity = QSpinBox()
        self.capacity.setRange(1, 200)
        self.capacity.setValue(20)
        self.capacity.setSuffix(" мест")

        self.status = QComboBox()
        self.status.addItem("Свободен", "available")
        self.status.addItem("В рейсе", "on_route")
        self.status.addItem("На ремонте", "maintenance")

        # Расположение полей
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow("Государственный номер:", self.state_number)
        form.addRow("Модель:", self.model)
        form.addRow("Вместимость:", self.capacity)
        form.addRow("Состояние:", self.status)

        layout.addLayout(form)

        # Кнопки формы
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.check_fields)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

        # Загружаем данные, если редактируем автобус
        if bus_id is not None:
            self.load_bus()

    # Загрузка данных выбранного автобуса
    def load_bus(self):
        connection = get_connection()

        try:
            bus = connection.execute(
                """
                SELECT state_number, model, capacity, status
                FROM buses
                WHERE bus_id = ?
                """,
                (self.bus_id,),
            ).fetchone()
        finally:
            connection.close()

        if bus:
            self.state_number.setText(bus["state_number"])
            self.model.setText(bus["model"])
            self.capacity.setValue(bus["capacity"])

            index = self.status.findData(bus["status"])

            if index >= 0:
                self.status.setCurrentIndex(index)

    # Проверка заполнения формы
    def check_fields(self):
        if not self.state_number.text().strip():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажи государственный номер автобуса.",
            )
            return

        if not self.model.text().strip():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажи модель автобуса.",
            )
            return

        self.accept()

    # Получение данных из формы
    def get_data(self):
        return (
            self.state_number.text().strip(),
            self.model.text().strip(),
            self.capacity.value(),
            self.status.currentData(),
        )


# Основная вкладка автобусов
class BusesPage(TablePage):
    def __init__(self):
        # Создаём элементы заранее,
        # так как TablePage загружает данные при создании
        self.search_input = QLineEdit()

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все состояния", "")
        self.status_filter.addItem("Свободен", "available")
        self.status_filter.addItem("В рейсе", "on_route")
        self.status_filter.addItem("На ремонте", "maintenance")

        query = """
            SELECT bus_id, state_number, model, capacity, status
            FROM buses
            ORDER BY state_number
        """

        headers = [
            "ID",
            "Госномер",
            "Модель",
            "Вместимость",
            "Состояние",
        ]

        super().__init__(query, headers)

        # Верхняя панель: поиск и фильтр
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)

        self.search_input.setPlaceholderText(
            "Поиск по госномеру или модели..."
        )

        self.search_input.textChanged.connect(self.refresh_data)
        self.status_filter.currentIndexChanged.connect(
            self.refresh_data
        )

        search_layout.addWidget(self.search_input, 3)
        search_layout.addWidget(self.status_filter, 1)

        self.layout().insertLayout(0, search_layout)

        # Нижняя панель: кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")

        add_button.clicked.connect(self.add_bus)
        edit_button.clicked.connect(self.edit_bus)
        delete_button.clicked.connect(self.delete_bus)

        # Кнопки одинаковой ширины
        buttons_layout.addWidget(add_button, 1)
        buttons_layout.addWidget(edit_button, 1)
        buttons_layout.addWidget(delete_button, 1)

        self.layout().addLayout(buttons_layout)

        self.refresh_data()

    # Поиск и фильтрация автобусов
    def refresh_data(self):
        search = self.search_input.text().strip()
        status = self.status_filter.currentData()

        sql = """
            SELECT bus_id, state_number, model, capacity, status
            FROM buses
        """

        conditions = []
        parameters = []

        # Поиск по государственному номеру или модели
        if search:
            conditions.append(
                "(state_number LIKE ? OR model LIKE ?)"
            )

            value = f"%{search}%"
            parameters.extend([value, value])

        # Фильтр по состоянию
        if status:
            conditions.append("status = ?")
            parameters.append(status)

        # Добавляем условия поиска и фильтрации
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY state_number"

        connection = get_connection()

        try:
            rows = connection.execute(sql, parameters).fetchall()

            status_names = {
                "available": "Свободен",
                "on_route": "В рейсе",
                "maintenance": "На ремонте",
            }

            display_rows = []

            for row in rows:
                row = list(row)
                row[4] = status_names.get(row[4], row[4])
                display_rows.append(row)

            self.show_rows(display_rows)

        finally:
            connection.close()

    # Добавление автобуса
    def add_bus(self):
        dialog = BusDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_bus(dialog.get_data())

    # Изменение выбранного автобуса
    def edit_bus(self):
        bus_id = self.get_selected_bus_id()

        if bus_id is None:
            QMessageBox.information(
                self,
                "Изменение автобуса",
                "Сначала выбери автобус в таблице.",
            )
            return

        dialog = BusDialog(bus_id, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_bus(dialog.get_data(), bus_id)

    # Сохранение нового или изменённого автобуса
    def save_bus(self, data, bus_id=None):
        connection = get_connection()

        try:
            if bus_id is None:
                connection.execute(
                    """
                    INSERT INTO buses
                        (state_number, model, capacity, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    data,
                )

                message = "Автобус успешно добавлен."

            else:
                connection.execute(
                    """
                    UPDATE buses
                    SET state_number = ?,
                        model = ?,
                        capacity = ?,
                        status = ?
                    WHERE bus_id = ?
                    """,
                    data + (bus_id,),
                )

                message = "Данные автобуса изменены."

            connection.commit()

            QMessageBox.information(
                self, "Готово", message
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось сохранить автобус. "
                "Возможно, такой госномер уже существует.",
            )

        finally:
            connection.close()

    # Удаление выбранного автобуса
    def delete_bus(self):
        bus_id = self.get_selected_bus_id()

        if bus_id is None:
            QMessageBox.information(
                self,
                "Удаление автобуса",
                "Сначала выбери автобус в таблице.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Ты действительно хочешь удалить этот автобус?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = get_connection()

        try:
            connection.execute(
                "DELETE FROM buses WHERE bus_id = ?",
                (bus_id,),
            )

            connection.commit()

            QMessageBox.information(
                self, "Готово", "Автобус удалён."
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Удаление невозможно",
                "Этот автобус связан с существующими рейсами. "
                "Удалить его нельзя.",
            )

        finally:
            connection.close()

    # Получение ID выбранного автобуса
    def get_selected_bus_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return int(item.text())