import sqlite3
from pathlib import Path
from unittest.mock import patch

import telemetry


def test_registrar_trade_metric_inserta_fila_en_sqlite(tmp_path):
    ruta_db = tmp_path / "telemetry_test.db"

    with patch("telemetry.DB_PATH", ruta_db):
        telemetry.inicializar_telemetria()
        telemetry.registrar_trade_metric(
            symbol="BTCUSDm",
            signal_type="ENTRY",
            telegram_price=81000.0,
            mt5_execution_price=81005.0,
            spread=12.5,
            latency_seconds=3.0,
            position_id="abc123",
            mt5_ticket=111,
            side="BUY",
            strategy="Drawdown DCA Long",
            message_timestamp_utc="2026-09-04T12:00:00+00:00",
            status="executed",
            details=None,
        )

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT symbol, signal_type, telegram_price, mt5_execution_price, spread, latency_seconds, position_id, mt5_ticket, side, strategy, message_timestamp_utc, status, details FROM trade_metrics"
        ).fetchone()

    assert fila == (
        "BTCUSDm",
        "ENTRY",
        81000.0,
        81005.0,
        12.5,
        3.0,
        "abc123",
        111,
        "BUY",
        "Drawdown DCA Long",
        "2026-09-04T12:00:00+00:00",
        "executed",
        None,
    )



def test_inicializar_telemetria_migra_columnas_sin_borrar_datos(tmp_path):
    ruta_db = tmp_path / "telemetry_migracion.db"

    with sqlite3.connect(ruta_db) as conexion:
        conexion.execute(
            """
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
                message_timestamp_utc TEXT,
                status TEXT NOT NULL,
                details TEXT
            )
            """
        )
        conexion.execute(
            """
            INSERT INTO trade_metrics (
                recorded_at_utc, symbol, signal_type, telegram_price, mt5_execution_price,
                spread, latency_seconds, position_id, message_timestamp_utc, status, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-09-04T12:00:00+00:00",
                "BTCUSDm",
                "ENTRY",
                81000.0,
                81005.0,
                12.5,
                3.0,
                "abc123",
                "2026-09-04T12:00:00+00:00",
                "executed",
                None,
            ),
        )

    with patch("telemetry.DB_PATH", ruta_db):
        telemetry.inicializar_telemetria()

    with sqlite3.connect(ruta_db) as conexion:
        columnas = {
            fila[1] for fila in conexion.execute("PRAGMA table_info(trade_metrics)").fetchall()
        }
        fila = conexion.execute("SELECT position_id, status FROM trade_metrics").fetchone()

    assert "mt5_ticket" in columnas
    assert "exit_price" in columnas
    assert "closed_at_utc" in columnas
    assert fila == ("abc123", "executed")



def test_registrar_cierre_metric_actualiza_fila_por_position_id(tmp_path):
    ruta_db = tmp_path / "telemetry_close_position.db"

    with patch("telemetry.DB_PATH", ruta_db):
        telemetry.inicializar_telemetria()
        telemetry.registrar_trade_metric(
            symbol="BTCUSDm",
            signal_type="ENTRY",
            telegram_price=81000.0,
            mt5_execution_price=81005.0,
            spread=12.5,
            latency_seconds=3.0,
            position_id="abc123",
            mt5_ticket=111,
            side="BUY",
            strategy="Drawdown DCA Long",
            message_timestamp_utc="2026-09-04T12:00:00+00:00",
            status="executed",
            details=None,
        )
        telemetry.registrar_cierre_metric(
            position_id="abc123",
            mt5_ticket=111,
            exit_price=81030.0,
            exit_reason="atr_trailing_stop",
            pnl_usd=25.5,
            pnl_pips_or_points=30.0,
            duration_seconds=720.0,
            closed_at_utc="2026-09-04T12:12:00+00:00",
            status="closed",
            details=None,
            reported_duration="12m",
            reported_pnl="+0.15%",
        )

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT exit_price, exit_reason, pnl_usd, pnl_pips_or_points, duration_seconds, closed_at_utc, status, reported_duration, reported_pnl FROM trade_metrics WHERE position_id = 'abc123'"
        ).fetchone()

    assert fila == (
        81030.0,
        "atr_trailing_stop",
        25.5,
        30.0,
        720.0,
        "2026-09-04T12:12:00+00:00",
        "closed",
        "12m",
        "+0.15%",
    )



def test_registrar_cierre_metric_actualiza_fila_por_ticket_mt5(tmp_path):
    ruta_db = tmp_path / "telemetry_close_ticket.db"

    with patch("telemetry.DB_PATH", ruta_db):
        telemetry.inicializar_telemetria()
        telemetry.registrar_trade_metric(
            symbol="XAUUSDm",
            signal_type="ENTRY",
            telegram_price=2500.0,
            mt5_execution_price=2500.5,
            spread=0.5,
            latency_seconds=2.0,
            position_id=None,
            mt5_ticket=222,
            side="SELL",
            strategy=None,
            message_timestamp_utc="2026-09-04T13:00:00+00:00",
            status="executed",
            details=None,
        )
        telemetry.registrar_cierre_metric(
            position_id=None,
            mt5_ticket=222,
            exit_price=2495.0,
            exit_reason="tp_broker",
            pnl_usd=40.0,
            pnl_pips_or_points=5.5,
            duration_seconds=300.0,
            closed_at_utc="2026-09-04T13:05:00+00:00",
            status="closed",
            details=None,
        )

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT exit_price, exit_reason, pnl_usd, duration_seconds, status FROM trade_metrics WHERE mt5_ticket = 222"
        ).fetchone()

    assert fila == (2495.0, "tp_broker", 40.0, 300.0, "closed")



def test_registrar_trade_metric_no_propaga_error_sqlite():
    with patch("telemetry.sqlite3.connect", side_effect=sqlite3.Error("boom")):
        telemetry.registrar_trade_metric(
            symbol="BTCUSDm",
            signal_type="ENTRY",
            telegram_price=81000.0,
            mt5_execution_price=81005.0,
            spread=12.5,
            latency_seconds=3.0,
            position_id="abc123",
            message_timestamp_utc="2026-09-04T12:00:00+00:00",
            status="executed",
            details=None,
        )



def test_registrar_cierre_metric_no_propaga_error_sqlite():
    with patch("telemetry.sqlite3.connect", side_effect=sqlite3.Error("boom")):
        telemetry.registrar_cierre_metric(
            position_id="abc123",
            mt5_ticket=111,
            exit_price=81030.0,
            exit_reason="atr_trailing_stop",
            pnl_usd=25.5,
            pnl_pips_or_points=30.0,
            duration_seconds=720.0,
            closed_at_utc="2026-09-04T12:12:00+00:00",
        )
