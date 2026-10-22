from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
)

from database import get_connection


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()

        # Виды отчётов
        self.report_type = QComboBox()

        self.report_type.addItem(
            "Рейсы за период", "trips_period"
        )
        self.report_type.addItem(
            "Количество рейсов по маршрутам", "trips_by_route"
        )
        self.report_type.addItem(
            "Автобусы на ремонте", "buses_repair"
        )
        self.report_type.addItem(
            "Свободные автобусы", "free_buses"
        )
        self.report_type.addItem(
            "Доступные водители", "available_drivers"
        )
        self.report_type.addItem(
            "Водители на маршруте", "drivers_on_route"
        )
        self.report_type.addItem(
            "Происшествия за период", "incidents_period"
        )

        # Даты для отчётов за период
        today = QDate.currentDate()

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setDate(
            QDate(today.year(), today.month(), 1)
        )

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(today)

        # Заголовок и информация
        self.title_label = QLabel("Результаты отчёта")
        self.info_label = QLabel("Выбери отчёт и нажми кнопку ниже.")

        # Таблица результатов
        self.table = QTableWidget()
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

        # Главный макет
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Верхняя панель выбора отчёта
        report_layout = QHBoxLayout()
        report_layout.setSpacing(12)

        report_layout.addWidget(QLabel("Вид отчёта:"))
        report_layout.addWidget(self.report_type, 1)

        report_layout.addWidget(QLabel("С:"))
        report_layout.addWidget(self.date_from)

        report_layout.addWidget(QLabel("По:"))
        report_layout.addWidget(self.date_to)

        layout.addLayout(report_layout)
        layout.addWidget(self.title_label)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.info_label)

        # Кнопка внизу на всю ширину
        self.generate_button = QPushButton("Сформировать отчёт")
        self.generate_button.clicked.connect(self.generate_report)

        layout.addWidget(self.generate_button)

        self.setLayout(layout)

        self.report_type.currentIndexChanged.connect(
            self.update_date_controls
        )

        self.update_date_controls()
        self.generate_report()

    # Показываем даты только там, где они нужны
    def update_date_controls(self):
        report = self.report_type.currentData()

        use_dates = report in (
            "trips_period",
            "trips_by_route",
            "incidents_period",
        )

        self.date_from.setVisible(use_dates)
        self.date_to.setVisible(use_dates)

        self.generate_button.setEnabled(
            not use_dates
            or self.date_from.date() <= self.date_to.date()
        )

    # Формирование выбранного отчёта
    def generate_report(self):
        report = self.report_type.currentData()

        date_from = self.date_from.date().toString(
            "yyyy-MM-dd"
        )
        date_to = self.date_to.date().toString(
            "yyyy-MM-dd"
        )

        if date_from > date_to:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Начальная дата не может быть позже конечной.",
            )
            return

        connection = get_connection()

        try:
            # 1. Рейсы за период
            if report == "trips_period":
                headers = [
                    "№ рейса",
                    "Маршрут",
                    "Автобус",
                    "Водитель",
                    "Дата",
                    "Отправление",
                    "Прибытие",
                    "Статус",
                ]

                rows = connection.execute(
                    """
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
                    WHERE trips.trip_date BETWEEN ? AND ?
                    ORDER BY trips.trip_date,
                             trips.departure_time
                    """,
                    (date_from, date_to),
                ).fetchall()

                self.title_label.setText("Рейсы за период")

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

                    row[7] = status_names.get(
                        row[7], row[7]
                    )

                    display_rows.append(row)

                rows = display_rows

            # 2. Количество рейсов по маршрутам
            elif report == "trips_by_route":
                headers = [
                    "Номер маршрута",
                    "Количество рейсов",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        routes.route_number,
                        COUNT(trips.trip_id) AS trip_count
                    FROM routes
                    LEFT JOIN trips
                        ON routes.route_id = trips.route_id
                        AND trips.trip_date BETWEEN ? AND ?
                    GROUP BY routes.route_id
                    ORDER BY routes.route_number
                    """,
                    (date_from, date_to),
                ).fetchall()

                self.title_label.setText(
                    "Количество рейсов по маршрутам"
                )

            # 3. Автобусы на ремонте
            elif report == "buses_repair":
                headers = [
                    "Госномер",
                    "Модель",
                    "Вместимость",
                    "Состояние",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        state_number,
                        model,
                        capacity,
                        status
                    FROM buses
                    WHERE status = 'maintenance'
                    ORDER BY state_number
                    """
                ).fetchall()

                self.title_label.setText(
                    "Автобусы на ремонте"
                )

                rows = [
                    list(row[:3]) + ["На ремонте"]
                    for row in rows
                ]

            # 4. Свободные автобусы
            elif report == "free_buses":
                headers = [
                    "Госномер",
                    "Модель",
                    "Вместимость",
                    "Состояние",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        state_number,
                        model,
                        capacity,
                        status
                    FROM buses
                    WHERE status = 'available'
                    ORDER BY state_number
                    """
                ).fetchall()

                self.title_label.setText(
                    "Свободные автобусы"
                )

                rows = [
                    list(row[:3]) + ["Свободен"]
                    for row in rows
                ]

            # 5. Доступные водители
            elif report == "available_drivers":
                headers = [
                    "ФИО",
                    "Телефон",
                    "Статус",
                    "Категории прав",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        drivers.full_name,
                        drivers.phone,
                        drivers.status,
                        GROUP_CONCAT(
                            driver_licenses.category, ', '
                        ) AS categories
                    FROM drivers
                    LEFT JOIN driver_licenses
                        ON drivers.driver_id =
                           driver_licenses.driver_id
                    WHERE drivers.status = 'available'
                    GROUP BY drivers.driver_id
                    ORDER BY drivers.full_name
                    """
                ).fetchall()

                self.title_label.setText(
                    "Доступные водители"
                )

                rows = [
                    list(row[:2])
                    + ["Доступен", row[3] or "—"]
                    for row in rows
                ]

            # 6. Водители на маршруте
            elif report == "drivers_on_route":
                headers = [
                    "ФИО",
                    "Телефон",
                    "Статус",
                    "Категории прав",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        drivers.full_name,
                        drivers.phone,
                        drivers.status,
                        GROUP_CONCAT(
                            driver_licenses.category, ', '
                        ) AS categories
                    FROM drivers
                    LEFT JOIN driver_licenses
                        ON drivers.driver_id =
                           driver_licenses.driver_id
                    WHERE drivers.status = 'on_route'
                    GROUP BY drivers.driver_id
                    ORDER BY drivers.full_name
                    """
                ).fetchall()

                self.title_label.setText(
                    "Водители на маршруте"
                )

                rows = [
                    list(row[:2])
                    + ["На маршруте", row[3] or "—"]
                    for row in rows
                ]

            # 7. Происшествия за период
            elif report == "incidents_period":
                headers = [
                    "Дата и время",
                    "№ рейса",
                    "Маршрут",
                    "Тип",
                    "Описание",
                    "Принятые меры",
                ]

                rows = connection.execute(
                    """
                    SELECT
                        incidents.incident_time,
                        trips.trip_id,
                        routes.route_number,
                        incidents.incident_type,
                        incidents.description,
                        incidents.action_taken
                    FROM incidents
                    JOIN trips
                        ON incidents.trip_id = trips.trip_id
                    JOIN routes
                        ON trips.route_id = routes.route_id
                    WHERE substr(
                        incidents.incident_time, 1, 10
                    ) BETWEEN ? AND ?
                    ORDER BY incidents.incident_time DESC
                    """,
                    (date_from, date_to),
                ).fetchall()

                self.title_label.setText(
                    "Происшествия за период"
                )

                incident_names = {
                    "breakdown": "Поломка",
                    "accident": "ДТП",
                    "delay": "Задержка",
                    "other": "Другое",
                }

                display_rows = []

                for row in rows:
                    row = list(row)

                    date_time = row[0]
                    date = QDate.fromString(
                        date_time[:10], "yyyy-MM-dd"
                    )

                    if date.isValid():
                        row[0] = (
                            date.toString("dd.MM.yyyy")
                            + " "
                            + date_time[11:16]
                        )

                    row[3] = incident_names.get(
                        row[3], row[3]
                    )

                    if not row[5]:
                        row[5] = "—"

                    display_rows.append(row)

                rows = display_rows

            else:
                headers = []
                rows = []

            self.show_rows(rows, headers)

            self.info_label.setText(
                f"Количество записей: {len(rows)}"
            )

        finally:
            connection.close()

    # Вывод результатов в таблицу
    def show_rows(self, rows, headers):
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        for row_number, row in enumerate(rows):
            for column_number, value in enumerate(row):
                if value is None:
                    value = "—"

                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter
                    | Qt.AlignmentFlag.AlignLeft
                )

                self.table.setItem(
                    row_number,
                    column_number,
                    item,
                )

        self.table.resizeRowsToContents()