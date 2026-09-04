import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import TELEMETRY_DB_PATH
from logger import logger

DB_PATH = Path(TELEMETRY_DB_PATH)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trade_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at_utc TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    telegram_price REAL,
    mt5_execution_price REAL,
    spread REAL,
    latency_seconds REAL,
    position_id TEXT,
    message_timestamp_utc TEXT,
    status TEXT NOT NULL,
    details TEXT
)
"""


def inicializar_telemetria() -> None:
    try:
        with sqlite3.connect(DB_PATH) as conexion:
            conexion.execute(SCHEMA_SQL)
    except sqlite3.Error as error:
        logger.error("No se pudo inicializar telemetría SQLite: %s", error)


def registrar_trade_metric(
    *,
    symbol: str,
    signal_type: str,
    telegram_price: float | None,
    mt5_execution_price: float | None,
    spread: float | None,
    latency_seconds: float | None,
    position_id: str | None,
    message_timestamp_utc: str | None,
    status: str,
    details: str | None,
) -> None:
    try:
        with sqlite3.connect(DB_PATH) as conexion:
            conexion.execute(SCHEMA_SQL)
            conexion.execute(
                """
                INSERT INTO trade_metrics (
                    recorded_at_utc,
                    symbol,
                    signal_type,
                    telegram_price,
                    mt5_execution_price,
                    spread,
                    latency_seconds,
                    position_id,
                    message_timestamp_utc,
                    status,
                    details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    symbol,
                    signal_type,
                    telegram_price,
                    mt5_execution_price,
                    spread,
                    latency_seconds,
                    position_id,
                    message_timestamp_utc,
                    status,
                    details,
                ),
            )
    except sqlite3.Error as error:
        logger.error("No se pudo registrar telemetría: %s", error)
