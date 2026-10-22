"""Работа с базой данных SQLite для АРМ диспетчера городского транспорта."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path


# База создаётся рядом с этим файлом, поэтому запуск работает из VS Code и Terminal.
DB_PATH = Path(__file__).resolve().parent / "transport.db"


def get_connection() -> sqlite3.Connection:
    """Открывает соединение с БД и включает проверку внешних ключей."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _create_tables(connection: sqlite3.Connection) -> None:
    """Создаёт таблицы при первом запуске. Повторный запуск безопасен."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS routes (
            route_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_number TEXT NOT NULL UNIQUE,
            start_point TEXT NOT NULL,
            end_point TEXT NOT NULL,
            distance_km REAL NOT NULL CHECK (distance_km > 0)
        );

        CREATE TABLE IF NOT EXISTS buses (
            bus_id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_number TEXT NOT NULL UNIQUE,
            model TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity > 0),
            status TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available', 'on_route', 'maintenance'))
        );

        CREATE TABLE IF NOT EXISTS drivers (
            driver_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available', 'on_route', 'unavailable'))
        );

        CREATE TABLE IF NOT EXISTS driver_licenses (
            driver_id INTEGER NOT NULL,
            category TEXT NOT NULL
                CHECK (category IN ('A', 'B', 'C', 'D', 'E')),
            PRIMARY KEY (driver_id, category),
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trips (
            trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            bus_id INTEGER NOT NULL,
            driver_id INTEGER NOT NULL,
            trip_date TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
            CHECK (length(trip_date) = 10),
            CHECK (length(departure_time) = 5),
            CHECK (length(arrival_time) = 5),
            CHECK (arrival_time > departure_time),
            FOREIGN KEY (route_id) REFERENCES routes(route_id)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (bus_id) REFERENCES buses(bus_id)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (driver_id) REFERENCES drivers(driver_id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS incidents (
            incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            incident_time TEXT NOT NULL,
            incident_type TEXT NOT NULL
                CHECK (incident_type IN ('breakdown', 'accident', 'delay', 'other')),
            description TEXT NOT NULL,
            action_taken TEXT,
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
                ON UPDATE CASCADE ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_trips_date_time
            ON trips(trip_date, departure_time);
        CREATE INDEX IF NOT EXISTS idx_trips_bus_date
            ON trips(bus_id, trip_date);
        CREATE INDEX IF NOT EXISTS idx_trips_driver_date
            ON trips(driver_id, trip_date);
        CREATE INDEX IF NOT EXISTS idx_incidents_time
            ON incidents(incident_time);
        """
    )


def _add_demo_data(connection: sqlite3.Connection) -> None:
    """Добавляет демонстрационные записи только в пустую новую БД."""
    tables = ("routes", "buses", "drivers", "trips", "incidents")
    if any(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables):
        return

    connection.executemany(
        """INSERT INTO routes (route_number, start_point, end_point, distance_km)
           VALUES (?, ?, ?, ?)""",
        [
            ("12", "Алайский рынок", "Черёмушки", 14.5),
            ("5", "Автовокзал", "Амир-Тимур", 11.2),
            ("7", "Центральный рынок", "Ошский аэропорт", 9.8),
        ],
    )

    connection.executemany(
        """INSERT INTO buses (state_number, model, capacity, status)
           VALUES (?, ?, ?, ?)""",
        [
            ("A1234AA", "Mercedes Sprinter", 18, "available"),
            ("B5678BB", "Isuzu", 25, "available"),
            ("C1111CC", "Hyundai County", 22, "maintenance"),
        ],
    )

    connection.executemany(
        """INSERT INTO drivers (full_name, phone, status)
           VALUES (?, ?, ?)""",
        [
            ("Иванов Иван Иванович", "+996 555 00-11-22", "available"),
            ("Петров Пётр Петрович", "+996 555 00-22-33", "available"),
            ("Садыков Бекжан Азаматович", "+996 555 00-33-44", "unavailable"),
        ],
    )

    # Один водитель может иметь несколько категорий; каждая хранится отдельной записью.
    connection.executemany(
        "INSERT INTO driver_licenses (driver_id, category) VALUES (?, ?)",
        [
            (1, "B"), (1, "D"),
            (2, "D"),
            (3, "C"), (3, "D"),
        ],
    )

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after_tomorrow = (date.today() + timedelta(days=2)).isoformat()

    connection.executemany(
        """INSERT INTO trips
           (route_id, bus_id, driver_id, trip_date, departure_time, arrival_time, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, 1, 1, yesterday, "08:00", "09:00", "completed"),
            (2, 2, 2, tomorrow, "09:00", "10:00", "planned"),
            (1, 1, 1, day_after_tomorrow, "11:00", "12:00", "cancelled"),
        ],
    )

    completed_trip_id = connection.execute(
        "SELECT trip_id FROM trips WHERE status = 'completed' ORDER BY trip_id LIMIT 1"
    ).fetchone()[0]
    connection.execute(
        """INSERT INTO incidents
           (trip_id, incident_time, incident_type, description, action_taken)
           VALUES (?, ?, ?, ?, ?)""",
        (
            completed_trip_id,
            f"{yesterday} 08:35",
            "breakdown",
            "Перегрев двигателя",
            "Автобус направлен в парк для проверки",
        ),
    )


def initialize_database() -> None:
    """Создаёт схему БД и заполняет новую БД демонстрационными данными."""
    connection = get_connection()
    try:
        _create_tables(connection)
        _add_demo_data(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def print_database_summary() -> None:
    """Печатает названия таблиц и количество записей для быстрой проверки."""
    connection = get_connection()
    try:
        print(f"База данных: {DB_PATH}")
        for table in ("routes", "buses", "drivers", "driver_licenses", "trips", "incidents"):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count} записей")
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print_database_summary()
