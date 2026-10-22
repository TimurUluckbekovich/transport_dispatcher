import sqlite3

from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
)

from database import get_connection
from .table_page import TablePage


# Форма добавления и изменения маршрута
class RouteDialog(QDialog):
    def __init__(self, route_id=None, parent=None):
        super().__init__(parent)

        self.route_id = route_id

        if route_id is None:
            self.setWindowTitle("Добавление маршрута")
        else:
            self.setWindowTitle("Изменение маршрута")

        self.setMinimumWidth(380)

        # Поля формы
        self.route_number = QLineEdit()
        self.start_point = QLineEdit()
        self.end_point = QLineEdit()

        self.distance = QDoubleSpinBox()
        self.distance.setRange(0.1, 10000)
        self.distance.setDecimals(1)
        self.distance.setSuffix(" км")

        # Размещение полей
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow("Номер маршрута:", self.route_number)
        form.addRow("Начальная точка:", self.start_point)
        form.addRow("Конечная точка:", self.end_point)
        form.addRow("Длина маршрута:", self.distance)

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

        if route_id is not None:
            self.load_route()

    # Загрузка данных выбранного маршрута
    def load_route(self):
        connection = get_connection()

        try:
            route = connection.execute(
                """
                SELECT route_number, start_point,
                       end_point, distance_km
                FROM routes
                WHERE route_id = ?
                """,
                (self.route_id,),
            ).fetchone()
        finally:
            connection.close()

        if route:
            self.route_number.setText(route["route_number"])
            self.start_point.setText(route["start_point"])
            self.end_point.setText(route["end_point"])
            self.distance.setValue(route["distance_km"])

    # Проверка заполнения формы
    def check_fields(self):
        if not self.route_number.text().strip():
            QMessageBox.warning(
                self, "Ошибка", "Укажи номер маршрута."
            )
            return

        if not self.start_point.text().strip():
            QMessageBox.warning(
                self, "Ошибка", "Укажи начальную точку."
            )
            return

        if not self.end_point.text().strip():
            QMessageBox.warning(
                self, "Ошибка", "Укажи конечную точку."
            )
            return

        self.accept()

    # Получение введённых данных
    def get_data(self):
        return (
            self.route_number.text().strip(),
            self.start_point.text().strip(),
            self.end_point.text().strip(),
            self.distance.value(),
        )


# Основная вкладка маршрутов
class RoutesPage(TablePage):
    def __init__(self):
        self.search_input = None

        query = """
            SELECT route_id, route_number, start_point,
                   end_point, distance_km
            FROM routes
            ORDER BY route_number
        """

        headers = [
            "ID",
            "№ маршрута",
            "Начальная точка",
            "Конечная точка",
            "Длина (км)",
        ]

        super().__init__(query, headers)

        # Верхняя часть — только поиск
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по номеру или точкам маршрута..."
        )

        self.search_input.textChanged.connect(self.refresh_data)

        search_layout.addWidget(self.search_input)

        self.layout().insertLayout(0, search_layout)

        # Нижняя часть — кнопки управления
# Нижняя панель кнопок
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")

        add_button.clicked.connect(self.add_route)
        edit_button.clicked.connect(self.edit_route)
        delete_button.clicked.connect(self.delete_route)

        # Все три кнопки одинаковой ширины
        buttons_layout.addWidget(add_button, 1)
        buttons_layout.addWidget(edit_button, 1)
        buttons_layout.addWidget(delete_button, 1)

        self.layout().addLayout(buttons_layout)
        self.refresh_data()

    # Поиск и отображение маршрутов
    def refresh_data(self):
        search = (
            self.search_input.text().strip()
            if self.search_input is not None
            else ""
        )

        sql = """
            SELECT route_id, route_number, start_point,
                   end_point, distance_km
            FROM routes
        """

        parameters = ()

        if search:
            sql += """
                WHERE route_number LIKE ?
                   OR start_point LIKE ?
                   OR end_point LIKE ?
            """

            value = f"%{search}%"
            parameters = (value, value, value)

        sql += " ORDER BY route_number"

        connection = get_connection()

        try:
            rows = connection.execute(
                sql, parameters
            ).fetchall()

            self.show_rows(rows)

        finally:
            connection.close()

    # Добавление маршрута
    def add_route(self):
        dialog = RouteDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_route(dialog.get_data())

    # Изменение маршрута
    def edit_route(self):
        route_id = self.get_selected_route_id()

        if route_id is None:
            QMessageBox.information(
                self,
                "Изменение маршрута",
                "Сначала выбери маршрут в таблице.",
            )
            return

        dialog = RouteDialog(route_id, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_route(dialog.get_data(), route_id)

    # Сохранение нового или изменённого маршрута
    def save_route(self, data, route_id=None):
        connection = get_connection()

        try:
            if route_id is None:
                connection.execute(
                    """
                    INSERT INTO routes
                    (route_number, start_point,
                     end_point, distance_km)
                    VALUES (?, ?, ?, ?)
                    """,
                    data,
                )
                message = "Маршрут успешно добавлен."

            else:
                connection.execute(
                    """
                    UPDATE routes
                    SET route_number = ?,
                        start_point = ?,
                        end_point = ?,
                        distance_km = ?
                    WHERE route_id = ?
                    """,
                    data + (route_id,),
                )
                message = "Маршрут успешно изменён."

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
                "Не удалось сохранить маршрут. "
                "Возможно, такой номер уже существует.",
            )

        finally:
            connection.close()

    # Удаление маршрута
    def delete_route(self):
        route_id = self.get_selected_route_id()

        if route_id is None:
            QMessageBox.information(
                self,
                "Удаление маршрута",
                "Сначала выбери маршрут в таблице.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            "Ты действительно хочешь удалить этот маршрут?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = get_connection()

        try:
            connection.execute(
                "DELETE FROM routes WHERE route_id = ?",
                (route_id,),
            )

            connection.commit()

            QMessageBox.information(
                self, "Готово", "Маршрут удалён."
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Нельзя удалить маршрут",
                "Этот маршрут используется в рейсах. "
                "Удаление невозможно, пока существуют "
                "связанные записи.",
            )

        finally:
            connection.close()

    # Получение ID выбранного маршрута
    def get_selected_route_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return int(item.text())