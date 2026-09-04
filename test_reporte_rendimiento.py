import sqlite3
from pathlib import Path

from reporte_rendimiento import generar_reporte


SCHEMA_SQL = """
CREATE TABLE trade_metrics (
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



def _crear_db_con_datos(ruta_db: Path) -> None:
    with sqlite3.connect(ruta_db) as conexion:
        conexion.execute(SCHEMA_SQL)
        conexion.executemany(
            """
            INSERT INTO trade_metrics (
                recorded_at_utc, symbol, signal_type, telegram_price, mt5_execution_price,
                spread, latency_seconds, position_id, mt5_ticket, side, strategy,
                message_timestamp_utc, status, details, exit_price, exit_reason,
                pnl_usd, pnl_pips_or_points, duration_seconds, reported_duration,
                reported_pnl, closed_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "2026-09-04T12:00:00+00:00", "BTCUSDm", "ENTRY", 81000.0, 81005.0,
                    12.5, 3.0, "btc-win", 111, "BUY", "Drawdown DCA Long",
                    "2026-09-04T12:00:00+00:00", "closed", None, 81030.0, "atr_trailing_stop",
                    25.0, 0.15, 720.0, "12m", "+0.15%", "2026-09-04T12:12:00+00:00"
                ),
                (
                    "2026-09-04T13:00:00+00:00", "XAUUSDm", "ENTRY", 2500.0, 2499.6,
                    0.4, 5.0, "xau-loss", 222, "SELL", "Bear Scalp Short",
                    "2026-09-04T13:00:00+00:00", "closed", None, 2502.0, "sl_broker",
                    -10.0, -2.0, 300.0, "5m", "-0.08%", "2026-09-04T13:05:00+00:00"
                ),
                (
                    "2026-09-04T14:00:00+00:00", "BTCUSDm", "ENTRY", 81100.0, None,
                    30.5, 2.0, "btc-reject", None, "BUY", None,
                    "2026-09-04T14:00:00+00:00", "rejected_spread", "spread alto", None, None,
                    None, None, None, None, None, None
                ),
            ],
        )



def test_generar_reporte_muestra_metricas_clave(tmp_path):
    ruta_db = tmp_path / "report.db"
    _crear_db_con_datos(ruta_db)

    reporte = generar_reporte(ruta_db)

    assert "Resumen general" in reporte
    assert "Total señales" in reporte
    assert "3" in reporte
    assert "Rechazadas spread" in reporte
    assert "1" in reporte
    assert "Win rate %" in reporte
    assert "50.00" in reporte
    assert "PnL total USD" in reporte
    assert "15.00" in reporte
    assert "Latencia media s" in reporte
    assert "3.33" in reporte
    assert "Slippage medio" in reporte
    assert "2.70" in reporte
    assert "BTCUSDm" in reporte
    assert "XAUUSDm" in reporte
    assert "Profit factor" in reporte



def test_generar_reporte_sin_operaciones_muestra_mensaje_limpio(tmp_path):
    ruta_db = tmp_path / "empty.db"
    with sqlite3.connect(ruta_db) as conexion:
        conexion.execute(SCHEMA_SQL)

    reporte = generar_reporte(ruta_db)

    assert reporte == "No hay operaciones registradas aún en telemetría."
