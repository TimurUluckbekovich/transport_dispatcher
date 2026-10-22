import sqlite3

from PyQt6.QtCore import QDate, QTime
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QCheckBox,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
)

from database import get_connection
from .table_page import TablePage


# Русские названия типов происшествий
INCIDENT_TYPES = {
    "breakdown": "Поломка",
    "accident": "ДТП",
    "delay": "Задержка",
    "other": "Другое",
}


# Форма добавления и изменения происшествия
class IncidentDialog(QDialog):
    def __init__(self, incident_id=None, parent=None):
        super().__init__(parent)

        self.incident_id = incident_id
        self.setMinimumWidth(440)

        if incident_id is None:
            self.setWindowTitle("Добавление происшествия")
        else:
            self.setWindowTitle("Изменение происшествия")

        # Выбор рейса
        self.trip = QComboBox()
        self.load_trips()

        # Дата происшествия
        self.incident_date = QDateEdit()
        self.incident_date.setCalendarPopup(True)
        self.incident_date.setDisplayFormat("dd.MM.yyyy")
        self.incident_date.setDate(QDate.currentDate())

        # Время происшествия
        self.incident_time = QTimeEdit()
        self.incident_time.setDisplayFormat("HH:mm")
        self.incident_time.setTime(QTime.currentTime())

        # Тип происшествия
        self.incident_type = QComboBox()

        for code, name in INCIDENT_TYPES.items():
            self.incident_type.addItem(name, code)

        # Описание и принятые меры
        self.description = QLineEdit()
        self.description.setPlaceholderText(
            "Например, перегрев двигателя"
        )

        self.action_taken = QLineEdit()
        self.action_taken.setPlaceholderText(
            "Например, направлен резервный автобус"
        )

        # Расположение полей
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow("Рейс:", self.trip)
        form.addRow("Дата:", self.incident_date)
        form.addRow("Время:", self.incident_time)
        form.addRow("Тип происшествия:", self.incident_type)
        form.addRow("Описание:", self.description)
        form.addRow("Принятые меры:", self.action_taken)

        layout.addLayout(form)

        # Кнопки сохранения и отмены
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.check_fields)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

        if incident_id is not None:
            self.load_incident()

    # Загружаем список рейсов
    def load_trips(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT
                    trips.trip_id,
                    trips.trip_date,
                    trips.departure_time,
                    routes.route_number,
                    buses.state_number
                FROM trips
                JOIN routes
                    ON trips.route_id = routes.route_id
                JOIN buses
                    ON trips.bus_id = buses.bus_id
                ORDER BY trips.trip_date DESC,
                         trips.departure_time
                """
            ).fetchall()

        finally:
            connection.close()

        for row in rows:
            date = QDate.fromString(
                row["trip_date"], "yyyy-MM-dd"
            )

            display_date = (
                date.toString("dd.MM.yyyy")
                if date.isValid()
                else row["trip_date"]
            )

            title = (
                f"Рейс №{row['trip_id']} | "
                f"Маршрут {row['route_number']} | "
                f"{row['state_number']} | "
                f"{display_date} {row['departure_time']}"
            )

            self.trip.addItem(title, row["trip_id"])

    # Загружаем происшествие при редактировании
    def load_incident(self):
        connection = get_connection()

        try:
            incident = connection.execute(
                """
                SELECT *
                FROM incidents
                WHERE incident_id = ?
                """,
                (self.incident_id,),
            ).fetchone()

        finally:
            connection.close()

        if incident is None:
            return

        self.trip.setCurrentIndex(
            self.trip.findData(incident["trip_id"])
        )

        # В БД дата и время хранятся вместе:
        # YYYY-MM-DD HH:mm
        date_time = incident["incident_time"]

        date = QDate.fromString(
            date_time[:10], "yyyy-MM-dd"
        )

        time = QTime.fromString(
            date_time[11:16], "HH:mm"
        )

        if date.isValid():
            self.incident_date.setDate(date)

        if time.isValid():
            self.incident_time.setTime(time)

        index = self.incident_type.findData(
            incident["incident_type"]
        )

        if index >= 0:
            self.incident_type.setCurrentIndex(index)

        self.description.setText(
            incident["description"]
        )

        self.action_taken.setText(
            incident["action_taken"] or ""
        )

    # Проверяем обязательные поля
    def check_fields(self):
        if self.trip.currentData() is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала нужно создать хотя бы один рейс.",
            )
            return

        if not self.description.text().strip():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажи описание происшествия.",
            )
            return

        self.accept()

    # Получаем данные из формы
    def get_data(self):
        date = self.incident_date.date().toString(
            "yyyy-MM-dd"
        )

        time = self.incident_time.time().toString(
            "HH:mm"
        )

        return (
            self.trip.currentData(),
            f"{date} {time}",
            self.incident_type.currentData(),
            self.description.text().strip(),
            self.action_taken.text().strip(),
        )


# Основная вкладка происшествий
class IncidentsPage(TablePage):
    def __init__(self):
        # Элементы создаём до super().__init__,
        # поскольку TablePage вызывает refresh_data()
        # во время создания.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по рейсу, маршруту или описанию..."
        )

        self.type_filter = QComboBox()
        self.type_filter.addItem("Все типы", "")

        for code, name in INCIDENT_TYPES.items():
            self.type_filter.addItem(name, code)

        self.date_filter = QCheckBox("Период:")

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setEnabled(False)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)

        query = """
            SELECT
                incidents.incident_id,
                trips.trip_id,
                routes.route_number,
                incidents.incident_time,
                incidents.incident_type,
                incidents.description,
                incidents.action_taken
            FROM incidents
            JOIN trips
                ON incidents.trip_id = trips.trip_id
            JOIN routes
                ON trips.route_id = routes.route_id
            ORDER BY incidents.incident_time DESC
        """

        headers = [
            "ID",
            "Рейс",
            "Маршрут",
            "Дата и время",
            "Тип",
            "Описание",
            "Принятые меры",
        ]

        super().__init__(query, headers)

        # Верхняя панель: поиск и фильтр по типу
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)

        self.search_input.textChanged.connect(
            self.refresh_data
        )

        self.type_filter.currentIndexChanged.connect(
            self.refresh_data
        )

        search_layout.addWidget(self.search_input, 3)
        search_layout.addWidget(self.type_filter, 1)

        self.layout().insertLayout(0, search_layout)

        # Вторая панель: фильтр по периоду
        date_layout = QHBoxLayout()
        date_layout.setSpacing(12)

        self.date_filter.toggled.connect(
            self.change_date_filter
        )

        self.date_from.dateChanged.connect(
            self.refresh_data
        )

        self.date_to.dateChanged.connect(
            self.refresh_data
        )

        date_layout.addWidget(self.date_filter)
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(self.date_to)
        date_layout.addStretch()

        self.layout().insertLayout(1, date_layout)

        # Нижняя панель: кнопки одинаковой ширины
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")

        add_button.clicked.connect(self.add_incident)
        edit_button.clicked.connect(self.edit_incident)
        delete_button.clicked.connect(self.delete_incident)

        buttons_layout.addWidget(add_button, 1)
        buttons_layout.addWidget(edit_button, 1)
        buttons_layout.addWidget(delete_button, 1)

        self.layout().addLayout(buttons_layout)

        self.refresh_data()

    # Включение и выключение фильтра по датам
    def change_date_filter(self, checked):
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)

        self.refresh_data()

    # Поиск и фильтрация происшествий
    def refresh_data(self):
        search = self.search_input.text().strip()
        incident_type = self.type_filter.currentData()

        sql = """
            SELECT
                incidents.incident_id,
                trips.trip_id,
                routes.route_number,
                incidents.incident_time,
                incidents.incident_type,
                incidents.description,
                incidents.action_taken
            FROM incidents
            JOIN trips
                ON incidents.trip_id = trips.trip_id
            JOIN routes
                ON trips.route_id = routes.route_id
            JOIN buses
                ON trips.bus_id = buses.bus_id
            JOIN drivers
                ON trips.driver_id = drivers.driver_id
        """

        conditions = []
        parameters = []

        # Поиск по рейсу, маршруту, типу и описанию
        if search:
            conditions.append(
                """
                (
                    CAST(incidents.incident_id AS TEXT) LIKE ?
                    OR CAST(trips.trip_id AS TEXT) LIKE ?
                    OR routes.route_number LIKE ?
                    OR buses.state_number LIKE ?
                    OR drivers.full_name LIKE ?
                    OR incidents.incident_type LIKE ?
                    OR incidents.description LIKE ?
                    OR COALESCE(incidents.action_taken, '') LIKE ?
                )
                """
            )

            value = f"%{search}%"

            parameters.extend(
                [value, value, value, value,
                 value, value, value, value]
            )

        # Фильтр по типу происшествия
        if incident_type:
            conditions.append(
                "incidents.incident_type = ?"
            )
            parameters.append(incident_type)

        # Фильтр по периоду
        if self.date_filter.isChecked():
            date_from = self.date_from.date().toString(
                "yyyy-MM-dd"
            )

            date_to = self.date_to.date().toString(
                "yyyy-MM-dd"
            )

            if date_from > date_to:
                self.show_rows([])
                return

            conditions.append(
                "substr(incidents.incident_time, 1, 10) >= ?"
            )
            parameters.append(date_from)

            conditions.append(
                "substr(incidents.incident_time, 1, 10) <= ?"
            )
            parameters.append(date_to)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY incidents.incident_time DESC"

        connection = get_connection()

        try:
            rows = connection.execute(
                sql, parameters
            ).fetchall()

            display_rows = []

            for row in rows:
                row = list(row)

                # Перевод даты в формат дд.мм.гггг
                date_time = row[3]

                date = QDate.fromString(
                    date_time[:10], "yyyy-MM-dd"
                )

                if date.isValid():
                    display_date = date.toString(
                        "dd.MM.yyyy"
                    )
                    row[3] = (
                        f"{display_date} {date_time[11:16]}"
                    )

                # Переводим тип на русский
                row[4] = INCIDENT_TYPES.get(
                    row[4], row[4]
                )

                # Пустые принятые меры отображаем прочерком
                if not row[6]:
                    row[6] = "—"

                display_rows.append(row)

            self.show_rows(display_rows)

        finally:
            connection.close()

    # Добавление происшествия
    def add_incident(self):
        dialog = IncidentDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_incident(dialog.get_data())

    # Изменение происшествия
    def edit_incident(self):
        incident_id = self.get_selected_incident_id()

        if incident_id is None:
            QMessageBox.information(
                self,
                "Изменение происшествия",
                "Сначала выбери запись в таблице.",
            )
            return

        dialog = IncidentDialog(incident_id, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_incident(
                dialog.get_data(), incident_id
            )

    # Сохранение нового или изменённого происшествия
    def save_incident(self, data, incident_id=None):
        connection = get_connection()

        try:
            if incident_id is None:
                connection.execute(
                    """
                    INSERT INTO incidents (
                        trip_id,
                        incident_time,
                        incident_type,
                        description,
                        action_taken
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    data,
                )

                message = "Происшествие успешно добавлено."

            else:
                connection.execute(
                    """
                    UPDATE incidents
                    SET trip_id = ?,
                        incident_time = ?,
                        incident_type = ?,
                        description = ?,
                        action_taken = ?
                    WHERE incident_id = ?
                    """,
                    data + (incident_id,),
                )

                message = "Происшествие успешно изменено."

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
                "Не удалось сохранить запись. "
                "Проверь выбранный рейс и введённые данные.",
            )

        finally:
            connection.close()

    # Удаление происшествия
    def delete_incident(self):
        incident_id = self.get_selected_incident_id()

        if incident_id is None:
            QMessageBox.information(
                self,
                "Удаление происшествия",
                "Сначала выбери запись в таблице.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Ты действительно хочешь удалить это происшествие?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = get_connection()

        try:
            connection.execute(
                """
                DELETE FROM incidents
                WHERE incident_id = ?
                """,
                (incident_id,),
            )

            connection.commit()

            QMessageBox.information(
                self, "Готово", "Происшествие удалено."
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось удалить происшествие.",
            )

        finally:
            connection.close()

    # Получение ID выбранного происшествия
    def get_selected_incident_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return int(item.text())