"""Главное окно: собирает готовые вкладки в одном месте."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .trips import TripsPage
from .routes import RoutesPage
from .buses import BusesPage
from .drivers import DriversPage
from .incidents import IncidentsPage
from .reports import ReportsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("АРМ диспетчера городского транспорта")
        self.resize(1150, 700)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 14, 18, 18)
        main_layout.setSpacing(12)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Верхняя строка главного окна.
        top_layout = QHBoxLayout()
        title = QLabel("Диспетчерская служба городского транспорта")
        title.setObjectName("pageTitle")

        refresh_button = QPushButton("Обновить данные")
        refresh_button.clicked.connect(self.refresh_all_pages)

        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(refresh_button)
        main_layout.addLayout(top_layout)

        # Каждая вкладка находится в отдельном файле.
        self.trips_page = TripsPage()
        self.routes_page = RoutesPage()
        self.buses_page = BusesPage()
        self.drivers_page = DriversPage()
        self.incidents_page = IncidentsPage()
        self.reports_page = ReportsPage()

        self.pages = [
            self.trips_page,
            self.routes_page,
            self.buses_page,
            self.drivers_page,
            self.incidents_page,
            self.reports_page,
        ]

        self.tabs = QTabWidget()
        
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.tabBar().setUsesScrollButtons(False)
        self.tabs.addTab(self.trips_page, "Рейсы")
        self.tabs.addTab(self.routes_page, "Маршруты")
        self.tabs.addTab(self.buses_page, "Автобусы")
        self.tabs.addTab(self.drivers_page, "Водители")
        self.tabs.addTab(self.incidents_page, "Происшествия")
        self.tabs.addTab(self.reports_page, "Отчёты")
        main_layout.addWidget(self.tabs)

    def refresh_all_pages(self):
        """Обновляет данные во всех вкладках."""

        self.trips_page.refresh_data()
        self.routes_page.refresh_data()
        self.buses_page.refresh_data()
        self.drivers_page.refresh_data()
        self.incidents_page.refresh_data()

        # Обновляем отчёты
        self.reports_page.generate_report()
