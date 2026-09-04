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
            message_timestamp_utc="2026-09-04T12:00:00+00:00",
            status="executed",
            details=None,
        )

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT symbol, signal_type, telegram_price, mt5_execution_price, spread, latency_seconds, position_id, message_timestamp_utc, status, details FROM trade_metrics"
        ).fetchone()

    assert fila == (
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
    )



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
