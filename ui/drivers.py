import sqlite3

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QLabel,
    QDialogButtonBox,
    QPushButton,
    QMessageBox,
)

from database import get_connection
from .table_page import TablePage


# Форма добавления и изменения водителя
class DriverDialog(QDialog):
    def __init__(self, driver_id=None, parent=None):
        super().__init__(parent)

        self.driver_id = driver_id

        if driver_id is None:
            self.setWindowTitle("Добавление водителя")
        else:
            self.setWindowTitle("Изменение водителя")

        self.setMinimumWidth(400)

        # Поля водителя
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Фамилия, имя и отчество")

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+996 ...")

        # Статус водителя
        self.status = QComboBox()
        self.status.addItem("Доступен", "available")
        self.status.addItem("На маршруте", "on_route")
        self.status.addItem("Недоступен", "unavailable")

        # Категории водительских прав
        self.license_checks = {}

        license_layout = QHBoxLayout()

        for category in ["A", "B", "C", "D", "E"]:
            checkbox = QCheckBox(category)
            self.license_checks[category] = checkbox
            license_layout.addWidget(checkbox)

        # Расположение элементов формы
        layout = QVBoxLayout()
        form = QFormLayout()

        form.addRow("ФИО:", self.full_name)
        form.addRow("Телефон:", self.phone)
        form.addRow("Статус:", self.status)
        form.addRow("Категории прав:", license_layout)

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

        if driver_id is not None:
            self.load_driver()

    # Загружаем данные выбранного водителя
    def load_driver(self):
        connection = get_connection()

        try:
            driver = connection.execute(
                """
                SELECT full_name, phone, status
                FROM drivers
                WHERE driver_id = ?
                """,
                (self.driver_id,),
            ).fetchone()

            licenses = connection.execute(
                """
                SELECT category
                FROM driver_licenses
                WHERE driver_id = ?
                """,
                (self.driver_id,),
            ).fetchall()

        finally:
            connection.close()

        if driver:
            self.full_name.setText(driver["full_name"])
            self.phone.setText(driver["phone"] or "")

            index = self.status.findData(driver["status"])

            if index >= 0:
                self.status.setCurrentIndex(index)

        for license_row in licenses:
            category = license_row["category"]

            if category in self.license_checks:
                self.license_checks[category].setChecked(True)

    # Проверяем заполнение формы
    def check_fields(self):
        if not self.full_name.text().strip():
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажи ФИО водителя.",
            )
            return

        if not any(
            checkbox.isChecked()
            for checkbox in self.license_checks.values()
        ):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Выбери хотя бы одну категорию прав.",
            )
            return

        self.accept()

    # Получаем данные из формы
    def get_data(self):
        categories = []

        for category, checkbox in self.license_checks.items():
            if checkbox.isChecked():
                categories.append(category)

        return (
            self.full_name.text().strip(),
            self.phone.text().strip(),
            self.status.currentData(),
            categories,
        )


# Основная вкладка водителей
class DriversPage(TablePage):
    def __init__(self):
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Поиск по ФИО или телефону..."
        )

        # Фильтр по статусу
        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", "")
        self.status_filter.addItem("Доступен", "available")
        self.status_filter.addItem("На маршруте", "on_route")
        self.status_filter.addItem("Недоступен", "unavailable")

        # Фильтры по категориям прав
        self.category_filters = {}

        for category in ["A", "B", "C", "D", "E"]:
            checkbox = QCheckBox(category)
            self.category_filters[category] = checkbox

        query = """
            SELECT
                drivers.driver_id,
                drivers.full_name,
                drivers.phone,
                GROUP_CONCAT(
                    driver_licenses.category, ', '
                ) AS categories,
                drivers.status
            FROM drivers
            LEFT JOIN driver_licenses
                ON drivers.driver_id = driver_licenses.driver_id
            GROUP BY drivers.driver_id
            ORDER BY drivers.full_name
        """

        headers = [
            "ID",
            "ФИО",
            "Телефон",
            "Категории прав",
            "Статус",
        ]

        super().__init__(query, headers)

        # Верхняя панель: поиск и фильтр по статусу
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)

        self.search_input.textChanged.connect(self.refresh_data)
        self.status_filter.currentIndexChanged.connect(
            self.refresh_data
        )

        search_layout.addWidget(self.search_input, 3)
        search_layout.addWidget(self.status_filter, 1)

        self.layout().insertLayout(0, search_layout)

        # Вторая строка: категории прав
        category_layout = QHBoxLayout()
        category_layout.setSpacing(12)

        category_layout.addWidget(
            QLabel("Категории прав:")
        )

        for checkbox in self.category_filters.values():
            checkbox.stateChanged.connect(
                lambda state: self.refresh_data()
            )
            category_layout.addWidget(checkbox)

        category_layout.addStretch()

        self.layout().insertLayout(1, category_layout)

        # Нижняя панель: кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 8, 0, 0)

        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")

        add_button.clicked.connect(self.add_driver)
        edit_button.clicked.connect(self.edit_driver)
        delete_button.clicked.connect(self.delete_driver)

        # Одинаковая ширина кнопок
        buttons_layout.addWidget(add_button, 1)
        buttons_layout.addWidget(edit_button, 1)
        buttons_layout.addWidget(delete_button, 1)

        self.layout().addLayout(buttons_layout)

        self.refresh_data()

    # Поиск и фильтрация водителей
    def refresh_data(self):
        search = self.search_input.text().strip()
        status = self.status_filter.currentData()

        sql = """
            SELECT
                drivers.driver_id,
                drivers.full_name,
                drivers.phone,
                GROUP_CONCAT(
                    driver_licenses.category, ', '
                ) AS categories,
                drivers.status
            FROM drivers
            LEFT JOIN driver_licenses
                ON drivers.driver_id = driver_licenses.driver_id
        """

        conditions = []
        parameters = []

        # Поиск по ФИО или телефону
        if search:
            conditions.append(
                """
                (
                    drivers.full_name LIKE ?
                    OR COALESCE(drivers.phone, '') LIKE ?
                )
                """
            )

            value = f"%{search}%"
            parameters.extend([value, value])

        # Фильтр по статусу
        if status:
            conditions.append("drivers.status = ?")
            parameters.append(status)

        # Каждый выбранный фильтр категории должен выполняться
        for category, checkbox in self.category_filters.items():
            if checkbox.isChecked():
                conditions.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM driver_licenses AS selected_license
                        WHERE selected_license.driver_id =
                              drivers.driver_id
                          AND selected_license.category = ?
                    )
                    """
                )
                parameters.append(category)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += """
            GROUP BY drivers.driver_id
            ORDER BY drivers.full_name
        """

        connection = get_connection()

        try:
            rows = connection.execute(
                sql, parameters
            ).fetchall()

            # Переводим статус перед отображением
            status_names = {
                "available": "Доступен",
                "on_route": "На маршруте",
                "unavailable": "Недоступен",
            }

            display_rows = []

            for row in rows:
                row = list(row)
                row[4] = status_names.get(row[4], row[4])
                display_rows.append(row)

            self.show_rows(display_rows)

        finally:
            connection.close()

    # Добавление водителя
    def add_driver(self):
        dialog = DriverDialog(parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_driver(dialog.get_data())

    # Изменение выбранного водителя
    def edit_driver(self):
        driver_id = self.get_selected_driver_id()

        if driver_id is None:
            QMessageBox.information(
                self,
                "Изменение водителя",
                "Сначала выбери водителя в таблице.",
            )
            return

        dialog = DriverDialog(driver_id, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.save_driver(dialog.get_data(), driver_id)

    # Сохранение нового или изменённого водителя
    def save_driver(self, data, driver_id=None):
        full_name, phone, status, categories = data

        connection = get_connection()

        try:
            if driver_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO drivers
                        (full_name, phone, status)
                    VALUES (?, ?, ?)
                    """,
                    (full_name, phone, status),
                )

                driver_id = cursor.lastrowid

            else:
                connection.execute(
                    """
                    UPDATE drivers
                    SET full_name = ?,
                        phone = ?,
                        status = ?
                    WHERE driver_id = ?
                    """,
                    (full_name, phone, status, driver_id),
                )

                # Удаляем прежние категории перед заменой
                connection.execute(
                    """
                    DELETE FROM driver_licenses
                    WHERE driver_id = ?
                    """,
                    (driver_id,),
                )

            # Сохраняем все выбранные категории
            for category in categories:
                connection.execute(
                    """
                    INSERT INTO driver_licenses
                        (driver_id, category)
                    VALUES (?, ?)
                    """,
                    (driver_id, category),
                )

            connection.commit()

            QMessageBox.information(
                self,
                "Готово",
                "Данные водителя сохранены.",
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось сохранить данные водителя.",
            )

        finally:
            connection.close()

    # Удаление водителя
    def delete_driver(self):
        driver_id = self.get_selected_driver_id()

        if driver_id is None:
            QMessageBox.information(
                self,
                "Удаление водителя",
                "Сначала выбери водителя в таблице.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Ты действительно хочешь удалить этого водителя?",
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
                DELETE FROM drivers
                WHERE driver_id = ?
                """,
                (driver_id,),
            )

            connection.commit()

            QMessageBox.information(
                self,
                "Готово",
                "Водитель удалён.",
            )

            self.refresh_data()

        except sqlite3.IntegrityError:
            connection.rollback()

            QMessageBox.warning(
                self,
                "Удаление невозможно",
                "Этот водитель связан с существующими рейсами. "
                "Сначала нужно разобраться со связанными рейсами.",
            )

        finally:
            connection.close()

    # Получение ID выбранного водителя
    def get_selected_driver_id(self):
        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        return int(item.text())