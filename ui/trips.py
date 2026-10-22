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
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
)

from database import get_connection
from .table_page import TablePage


# Форма добавления и изменения рейса
class TripDialog(QDialog):
    def __init__(self, trip_id=None, parent=None):
        super().__init__(parent)

        self.trip_id = trip_id
        self.old_trip = None

        self.setMinimumWidth(440)

        if trip_id is None:
            self.setWindowTitle("Добавление рейса")
        else:
            self.setWindowTitle("Изменение рейса")

        # Загружаем старый рейс, если редактируем его
        if trip_id is not None:
            connection = get_connection()

            try:
                trip = connection.execute(
                    """
                    SELECT *
                    FROM trips
                    WHERE trip_id = ?
                    """,
                    (trip_id,),
                ).fetchone()

                if trip:
                    self.old_trip = dict(trip)

            finally:
                connection.close()

        # Выбор маршрута, автобуса и водителя
        self.route = QComboBox()
        self.bus = QComboBox()
        self.driver = QComboBox()

        self.load_routes()
        self.load_buses()
        self.load_drivers()

        # Дата рейса
        self.trip_date = QDateEdit()
        self.trip_date.setCalendarPopup(True)
        self.trip_date.setDisplayFormat("dd.MM.yyyy")
        self.trip_date.setDate(QDate.currentDate())

        # Время отправления
        self.departure_time = QTimeEdit()
        self.departure_time.setDisplayFormat("HH:mm")
        self.departure_time.setTime(QTime(8, 0))

        # Время прибытия
        self.arrival_time = QTimeEdit()
        self.arrival_time.setDisplayFormat("HH:mm")
        self.arrival_time.setTime(QTime(9, 0))

        # Статус рейса
        self.status = QComboBox()
        self.status.addItem("Запланирован", "planned")
        self.status.addItem("В рейсе", "in_progress")
        self.status.addItem("Завершён", "completed")
        self.status.addItem("Отменён", "cancelled")

        # Расположение полей
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow("Маршрут:", self.route)
        form.addRow("Автобус:", self.bus)
        form.addRow("Водитель:", self.driver)
        form.addRow("Дата:", self.trip_date)
        form.addRow("Время отправления:", self.departure_time)
        form.addRow("Время прибытия:", self.arrival_time)
        form.addRow("Статус:", self.status)

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

        if self.old_trip:
            self.load_trip_data()

    # Заполнение списка маршрутов
    def load_routes(self):
        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT route_id, route_number, start_point, end_point
                FROM routes
                ORDER BY route_number
                """
            ).fetchall()
        finally:
            connection.close()

        for row in rows:
            title = (
                f"{row['route_number']}: "
                f"{row['start_point']} — {row['end_point']}"
            )

            self.route.addItem(title, row["route_id"])

    # Заполнение списка доступных автобусов
    def load_buses(self):
        old_bus_id = (
            self.old_trip["bus_id"]
            if self.old_trip else -1
        )

        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT bus_id, state_number, model, status
                FROM buses
                WHERE status = 'available' OR bus_id = ?
                ORDER BY state_number
                """,
                (old_bus_id,),
            ).fetchall()
        finally:
            connection.close()

        for row in rows:
            status_names = {
                "available": "Свободен",
                "on_route": "В рейсе",
                "maintenance": "На ремонте",
            }

            title = (
                f"{row['state_number']} — {row['model']} "
                f"({status_names.get(row['status'], row['status'])})"
            )

            self.bus.addItem(title, row["bus_id"])

    # Заполнение списка водителей
    # Для автобуса выбираем водителей с категорией D
    def load_drivers(self):
        old_driver_id = (
            self.old_trip["driver_id"]
            if self.old_trip else -1
        )

        connection = get_connection()

        try:
            rows = connection.execute(
                """
                SELECT DISTINCT
                    drivers.driver_id,
                    drivers.full_name,
                    drivers.status
                FROM drivers
                JOIN driver_licenses
                    ON drivers.driver_id =
                       driver_licenses.driver_id
                WHERE driver_licenses.category = 'D'
                  AND (
                      drivers.status = 'available'
                      OR drivers.driver_id = ?
                  )
                ORDER BY drivers.full_name
                """,
                (old_driver_id,),
            ).fetchall()
        finally:
            connection.close()

        for row in rows:
            status_names = {
                "available": "Доступен",
                "on_route": "На маршруте",
                "unavailable": "Недоступен",
            }

            title = (
                f"{row['full_name']} "
                f"({status_names.get(row['status'], row['status'])})"
            )

            self.driver.addItem(title, row["driver_id"])

    # Загрузка данных при изменении рейса
    def load_trip_data(self):
        trip = self.old_trip

        self.route.setCurrentIndex(
            self.route.findData(trip["route_id"])
        )

        self.bus.setCurrentIndex(
            self.bus.findData(trip["bus_id"])
        )

        self.driver.setCurrentIndex(
            self.driver.findData(trip["driver_id"])
        )

        date = QDate.fromString(
            trip["trip_date"], "yyyy-MM-dd"
        )

        if date.isValid():
            self.trip_date.setDate(date)

        departure = QTime.fromString(
            trip["departure_time"], "HH:mm"
        )

        arrival = QTime.fromString(
            trip["arrival_time"], "HH:mm"
        )

        if departure.isValid():
            self.departure_time.setTime(departure)

        if arrival.isValid():
            self.arrival_time.setTime(arrival)

        index = self.status.findData(trip["status"])

        if index >= 0:
            self.status.setCurrentIndex(index)

    # Проверка заполнения формы
    def check_fields(self):
        if self.route.currentData() is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сначала добавь маршрут.",
            )
            return

        if self.bus.currentData() is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Нет доступных автобусов для выбора.",
            )
            return

        if self.driver.currentData() is None:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Нет доступных водителей с категорией D.",
            )
            return

        if (
            self.arrival_time.time()
            <= self.departure_time.time()
        ):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Время прибытия должно быть позже времени отправления.",
            )
            return

        self.accept()

    # Получение данных из формы
    def get_data(self):
        return {
            "route_id": self.route.currentData(),
            "bus_id": self.bus.currentData(),
            "driver_id": self.driver.currentData(),
            "trip_date": self.trip_date.date().toString("yyyy-MM-dd"),
            "departure_time": self.departure_time.time().toString("HH:mm"),
            "arrival_time": self.arrival_time.time().toString("HH:mm"),
            "status": self.status.currentData(),
        }


# Основная вкладка рейсов
class TripsPage(TablePage):
    def __init__(self):
        # Создаём элементы поиска и фильтрации до super().__init__
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по номеру рейса, маршруту, автобусу или водителю..."
        )

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", "")
        self.status_filter.addItem("Запланирован", "planned")
        self.status_filter.addItem("В рейсе", "in_progress")
        self.status_filter.addItem("Завершён", "completed")
        self.status_filter.addItem("Отменён", "cancelled")

        self.date_filter = QCheckBox("Фильтр по дате")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setEnabled(False)

        query = """
            SELECT
                trips.trip_id,
                routes.route_number,
                buses.state_number,
                drivers.full_name,
                trips.trip_date,
                trips.departure_time,
                trips.arrival_time,
                trips.status
            FROM trips
            JOIN routes
                ON trips.route_id = routes.route_id
            JOIN buses
                ON trips.bus_id = buses.bus_id
            JOIN drivers
                ON trips.driver_id = drivers.driver_id
            ORDER BY trips.trip_date DESC,
                     trips.departure_time
        """

        headers = [
            "ID",
            "Маршрут",
            "Автобус",
            "Водитель",
            "Дата",
            "Отправление",
            "Прибытие",
            "Статус",
        ]

        super().__init__(query, headers)

        # Верхняя панель: поиск и фильтры
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)

        self.search_input.textChanged.connect(self.refresh_data)
        self.status_filter.currentIndexChanged.connect(
            self.refresh_data
        )

        self.date_filter.toggled.connect(
            lambda checked: (
                self.date_edit.setEnabled(checked),
                self.refresh_data(),
            )
        )

        self.date_edit.dateChanged.connect(
            lambda date: self.refresh_data()
        )

        search_layout.addWidget(self.search_input, 3)
        search_layout.addWidget(self.status_filter, 1)
        search_layout.addWidget(self.date_filter)
        search_layout.addWidget(self.date_edit)

        self.layout().insertLayout(0, search_layout)

        # Нижняя панель кнопок
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")

        add_button.clicked.connect(self.add_trip)
        edit_button.clicked.connect(self.edit_trip)
        delete_button.clicked.connect(self.delete_trip)

        buttons_layout.addWidget(add_button, 1)
        buttons_layout.addWidget(edit_button, 1)
        buttons_layout.addWidget(delete_button, 1)

        self.layout().addLayout(buttons_layout)

        self.refresh_data()

    # Поиск, фильтрация и отображение рейсов
    def refresh_data(self):
        search = self.search_input.text().strip()
        status = self.status_filter.currentData()

        sql = """
            SELECT
                trips.trip_id,
                routes.route_number,
                buses.state_number,
                drivers.full_name,
                trips.trip_date,
                trips.departure_time,
                trips.arrival_time,
                trips.status
            FROM trips
            JOIN routes
                ON trips.route_id = routes.route_id
            JOIN buses
                ON trips.bus_id = buses.bus_id
            JOIN drivers
                ON trips.driver_id = drivers.driver_id
        """

        conditions = []
        parameters = []

        # Поиск по разным полям
        if search:
            conditions.append(
                """
                (
                    CAST(trips.trip_id AS TEXT) LIKE ?
                    OR routes.route_number LIKE ?
                    OR buses.state_number LIKE ?
                    OR drivers.full_name LIKE ?
                )
                """
            )

            value = f"%{search}%"
            parameters.extend([value, value, value, value])

        # Фильтр по статусу
        if status:
            conditions.append("trips.status = ?")
            parameters.append(status)

        # Фильтр по выбранной дате
        if self.date_filter.isChecked():
            conditions.append("trips.trip_date = ?")

            parameters.append(
                self.date_edit.date().toString("yyyy-MM-dd")
            )

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += """
            ORDER BY trips.trip_date DESC,
                     trips.departure_time
        """

        connection = get_connection()

        try:
            rows = connection.execute(
                sql, parameters
            ).fetchall()

            # Переводим дату и статус для интерфейса
            status_names = {
                "planned": "Запланирован",
                "in_progress": "В рейсе",
                "completed": "Завершён",
                "cancelled": "Отменён",
            }

            display_rows = []

            for row in rows:
                row = list(row)

                date = QDate.fromString(
                    row[4], "yyyy-MM-dd"
                )

                if date.isValid():
                    row[4] = date.toString("dd.MM.yyyy")

                row[7] = status_names.get(row[7], row[7])

                display_rows.append(row)

            self.show_rows(display_rows)

        finally:
            connection.close()

    # Добавление рейса
    def add_trip(self):
        dialog = TripDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_trip(dialog.get_data())

    # Изменение выбранного рейса
    def edit_trip(self):
        trip_id = self.get_selected_trip_id()

        if trip_id is None:
            QMessageBox.information(
                self,
                "Изменение рейса",
                "Сначала выбери рейс в таблице.",
            )
            return

        dialog = TripDialog(trip_id, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_trip(dialog.get_data(), trip_id)

    # Проверка доступности автобуса и водителя
    def check_availability(
        self, connection, data, old_trip
    ):
        bus = connection.execute(
            "SELECT status FROM buses WHERE bus_id = ?",
            (data["bus_id"],),
        ).fetchone()

        driver = connection.execute(
            "SELECT status FROM drivers WHERE driver_id = ?",
            (data["driver_id"],),
        ).fetchone()

        # Проверка автобуса
        bus_is_available = (
            bus is not None
            and bus["status"] == "available"
        )

        if (
            old_trip
            and data["bus_id"] == old_trip["bus_id"]
        ):
            bus_is_available = True

        if not bus_is_available:
            QMessageBox.warning(
                self,
                "Автобус недоступен",
                "Выбери свободный автобус, "
                "который не находится на ремонте.",
            )
            return False

        # Проверка водителя
        driver_is_available = (
            driver is not None
            and driver["status"] == "available"
        )

        if (
            old_trip
            and data["driver_id"] == old_trip["driver_id"]
        ):
            driver_is_available = True

        if not driver_is_available:
            QMessageBox.warning(
                self,
                "Водитель недоступен",
                "Выбери доступного водителя.",
            )
            return False

        # Проверяем наличие категории D
        license_row = connection.execute(
            """
            SELECT 1
            FROM driver_licenses
            WHERE driver_id = ?
              AND category = 'D'
            """,
            (data["driver_id"],),
        ).fetchone()

        if license_row is None:
            QMessageBox.warning(
                self,
                "Нет необходимой категории",
                "Для работы на автобусе у водителя "
                "должна быть категория D.",
            )
            return False

        return True

    # Проверяем, не пересекается ли рейс с другим рейсом
    def check_trip_overlap(
        self, connection, data, trip_id=None
    ):
        sql = """
            SELECT trip_id
            FROM trips
            WHERE trip_date = ?
              AND status != 'cancelled'
              AND (bus_id = ? OR driver_id = ?)
              AND departure_time < ?
              AND arrival_time > ?
        """

        parameters = [
            data["trip_date"],
            data["bus_id"],
            data["driver_id"],
            data["arrival_time"],
            data["departure_time"],
        ]

        if trip_id is not None:
            sql += " AND trip_id != ?"
            parameters.append(trip_id)

        conflict = connection.execute(
            sql, parameters
        ).fetchone()

        if conflict:
            QMessageBox.warning(
                self,
                "Конфликт расписания",
                "Этот автобус или водитель уже назначен "
                "на другой рейс в пересекающееся время.",
            )
            return False

        return True

    # Сохранение нового или изменённого рейса
    def save_trip(self, data, trip_id=None):
        connection = get_connection()

        try:
            old_trip = None

            if trip_id is not None:
                row = connection.execute(
                    """
                    SELECT bus_id, driver_id, status
                    FROM trips
                    WHERE trip_id = ?
                    """,
                    (trip_id,),
                ).fetchone()

                if row:
                    old_trip = dict(row)

            # Проверяем доступность ресурсов
            if data["status"] in ("planned", "in_progress"):
                if not self.check_availability(
                    connection, data, old_trip
                ):
                    return

            # Проверяем пересечения по времени
            if data["status"] != "cancelled":
                if not self.check_trip_overlap(
                    connection, data, trip_id
                ):
                    return

            if trip_id is None:
                connection.execute(
                    """
                    INSERT INTO trips (
                        route_id,
                        bus_id,
                        driver_id,
                        trip_date,
                        departure_time,
                        arrival_time,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["route_id"],
                        data["bus_id"],
                        data["driver_id"],
                        data["trip_date"],
                        data["departure_time"],
                        data["arrival_time"],
                        data["status"],
                    ),
                )

            else:
                connection.execute(
                    """
                    UPDATE trips
                    SET route_id = ?,
                        bus_id = ?,
                        driver_id = ?,
                        trip_date = ?,
                        departure_time = ?,
                        arrival_time = ?,
                        status = ?
                    WHERE trip_id = ?
                    """,
                    (
                        data["route_id"],
                        data["bus_id"],
                        data["driver_id"],
                        data["trip_date"],
                        data["departure_time"],
                        data["arrival_time"],
                        data["status"],
                        trip_id,
                    ),
                )

            # Если прежний рейс был активным,
            # освобождаем прежний автобус и водителя
            if old_trip and old_trip["status"] == "in_progress":
                if (
                    data["status"] != "in_progress"
                    or data["bus_id"] != old_trip["bus_id"]
                ):
                    bus_busy = connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM trips
                        WHERE bus_id = ?
                          AND status = 'in_progress'
                        """,
                        (old_trip["bus_id"],),
                    ).fetchone()[0]

                    if bus_busy == 0:
                        connection.execute(
                            """
                            UPDATE buses
                            SET status = 'available'
                            WHERE bus_id = ?
                              AND status = 'on_route'
                            """,
                            (old_trip["bus_id"],),
                        )

                if (
                    data["status"] != "in_progress"
                    or data["driver_id"] != old_trip["driver_id"]
                ):
                    driver_busy = connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM trips
                        WHERE driver_id = ?
                          AND status = 'in_progress'
                        """,
                        (old_trip["driver_id"],),
                    ).fetchone()[0]

                    if driver_busy == 0:
                        connection.execute(
                            """
                            UPDATE drivers
                            SET status = 'available'
                            WHERE driver_id = ?
                              AND status = 'on_route'
                            """,
                            (old_trip["driver_id"],),
                        )

            # При начале рейса меняем состояние автобуса и водителя
            if data["status"] == "in_progress":
                connection.execute(
                    """
                    UPDATE buses
                    SET status = 'on_route'
                    WHERE bus_id = ?
                      AND status = 'available'
                    """,
                    (data["bus_id"],),
                )

                connection.execute(
                    """
                    UPDATE drivers
                    SET status = 'on_route'
                    WHERE driver_id = ?
                      AND status = 'available'
                    """,
                    (data["driver_id"],),
                )

            connection.commit()

            QMessageBox.information(
                self,
                "Готово",
                "Рейс успешно сохранён.",
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Ошибка базы данных",
                "Не удалось сохранить рейс. "
                "Проверь маршрут, автобус, водителя и время.",
            )

        finally:
            connection.close()

    # Удаление выбранного рейса
    def delete_trip(self):
        trip_id = self.get_selected_trip_id()

        if trip_id is None:
            QMessageBox.information(
                self,
                "Удаление рейса",
                "Сначала выбери рейс в таблице.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Ты действительно хочешь удалить этот рейс?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        connection = get_connection()

        try:
            trip = connection.execute(
                """
                SELECT bus_id, driver_id, status
                FROM trips
                WHERE trip_id = ?
                """,
                (trip_id,),
            ).fetchone()

            if trip is None:
                return

            connection.execute(
                "DELETE FROM trips WHERE trip_id = ?",
                (trip_id,),
            )

            # Освобождаем ресурсы, если удалили активный рейс
            if trip["status"] == "in_progress":
                bus_busy = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM trips
                    WHERE bus_id = ?
                      AND status = 'in_progress'
                    """,
                    (trip["bus_id"],),
                ).fetchone()[0]

                if bus_busy == 0:
                    connection.execute(
                        """
                        UPDATE buses
                        SET status = 'available'
                        WHERE bus_id = ?
                          AND status = 'on_route'
                        """,
                        (trip["bus_id"],),
                    )

                driver_busy = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM trips
                    WHERE driver_id = ?
                      AND status = 'in_progress'
                    """,
                    (trip["driver_id"],),
                ).fetchone()[0]

                if driver_busy == 0:
                    connection.execute(
                        """
                        UPDATE drivers
                        SET status = 'available'
                        WHERE driver_id = ?
                          AND status = 'on_route'
                        """,
                        (trip["driver_id"],),
                    )

            connection.commit()

            QMessageBox.information(
                self,
                "Готово",
                "Рейс удалён.",
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Удаление невозможно",
                "С этим рейсом связаны происшествия. "
                "Сначала нужно разобраться с ними.",
            )

        finally:
            connection.close()

    # Получение ID выбранного рейса
    def get_selected_trip_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return int(item.text())