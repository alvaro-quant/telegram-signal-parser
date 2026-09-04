import sqlite3
from datetime import datetime, timezone
from pathlib import Path

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
    mt5_ticket INTEGER,
    side TEXT,
    strategy TEXT,
    message_timestamp_utc TEXT,
    status TEXT NOT NULL,
    details TEXT,
    exit_price REAL,
    exit_reason TEXT,
    pnl_usd REAL,
    pnl_pips_or_points REAL,
    duration_seconds REAL,
    reported_duration TEXT,
    reported_pnl TEXT,
    closed_at_utc TEXT
)
"""

COLUMNAS_MIGRACION = {
    "mt5_ticket": "INTEGER",
    "side": "TEXT",
    "strategy": "TEXT",
    "exit_price": "REAL",
    "exit_reason": "TEXT",
    "pnl_usd": "REAL",
    "pnl_pips_or_points": "REAL",
    "duration_seconds": "REAL",
    "reported_duration": "TEXT",
    "reported_pnl": "TEXT",
    "closed_at_utc": "TEXT",
}


def _obtener_columnas_existentes(conexion: sqlite3.Connection) -> set[str]:
    filas = conexion.execute("PRAGMA table_info(trade_metrics)").fetchall()
    return {fila[1] for fila in filas}



def _asegurar_columnas_trade_metrics(conexion: sqlite3.Connection) -> None:
    columnas_existentes = _obtener_columnas_existentes(conexion)
    for nombre_columna, tipo_columna in COLUMNAS_MIGRACION.items():
        if nombre_columna not in columnas_existentes:
            conexion.execute(
                f"ALTER TABLE trade_metrics ADD COLUMN {nombre_columna} {tipo_columna}"
            )



def inicializar_telemetria() -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=1) as conexion:
            conexion.execute(SCHEMA_SQL)
            _asegurar_columnas_trade_metrics(conexion)
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
    mt5_ticket: int | None = None,
    side: str | None = None,
    strategy: str | None = None,
    message_timestamp_utc: str | None,
    status: str,
    details: str | None,
) -> None:
    try:
        with sqlite3.connect(DB_PATH, timeout=1) as conexion:
            conexion.execute(SCHEMA_SQL)
            _asegurar_columnas_trade_metrics(conexion)
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
                    mt5_ticket,
                    side,
                    strategy,
                    message_timestamp_utc,
                    status,
                    details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    mt5_ticket,
                    side,
                    strategy,
                    message_timestamp_utc,
                    status,
                    details,
                ),
            )
    except sqlite3.Error as error:
        logger.error("No se pudo registrar telemetría: %s", error)



def registrar_cierre_metric(
    *,
    position_id: str | None,
    mt5_ticket: int | None,
    exit_price: float | None,
    exit_reason: str | None,
    pnl_usd: float | None,
    pnl_pips_or_points: float | None,
    duration_seconds: float | None,
    closed_at_utc: str | None,
    status: str = "closed",
    details: str | None = None,
    reported_duration: str | None = None,
    reported_pnl: str | None = None,
) -> None:
    if position_id is None and mt5_ticket is None:
        logger.warning("No se pudo registrar cierre de telemetría: faltan position_id y mt5_ticket.")
        return

    try:
        with sqlite3.connect(DB_PATH, timeout=1) as conexion:
            conexion.execute(SCHEMA_SQL)
            _asegurar_columnas_trade_metrics(conexion)

            fila = None
            if position_id is not None:
                fila = conexion.execute(
                    """
                    SELECT id
                    FROM trade_metrics
                    WHERE position_id = ?
                      AND signal_type = 'ENTRY'
                      AND closed_at_utc IS NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (position_id,),
                ).fetchone()

            if fila is None and mt5_ticket is not None:
                fila = conexion.execute(
                    """
                    SELECT id
                    FROM trade_metrics
                    WHERE mt5_ticket = ?
                      AND signal_type = 'ENTRY'
                      AND closed_at_utc IS NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (mt5_ticket,),
                ).fetchone()

            if fila is None:
                logger.warning(
                    "No se encontró trade abierto para registrar cierre (position_id=%s, mt5_ticket=%s).",
                    position_id,
                    mt5_ticket,
                )
                return

            conexion.execute(
                """
                UPDATE trade_metrics
                SET exit_price = ?,
                    exit_reason = ?,
                    pnl_usd = ?,
                    pnl_pips_or_points = ?,
                    duration_seconds = ?,
                    closed_at_utc = ?,
                    status = ?,
                    details = COALESCE(?, details),
                    reported_duration = COALESCE(?, reported_duration),
                    reported_pnl = COALESCE(?, reported_pnl)
                WHERE id = ?
                """,
                (
                    exit_price,
                    exit_reason,
                    pnl_usd,
                    pnl_pips_or_points,
                    duration_seconds,
                    closed_at_utc,
                    status,
                    details,
                    reported_duration,
                    reported_pnl,
                    fila[0],
                ),
            )
    except sqlite3.Error as error:
        logger.error("No se pudo registrar cierre de telemetría: %s", error)
