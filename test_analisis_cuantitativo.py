import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from analisis_cuantitativo import (
    calcular_rendimiento_por_hora,
    calcular_rentabilidad_por_duracion,
    calcular_slippage_por_simbolo,
    diagnosticar_inventario_abierto,
    generar_reporte_cuantitativo,
)

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


def _row(
    *,
    recorded_at_utc: str = "2026-09-04T12:00:00+00:00",
    symbol: str = "BTCUSDm",
    telegram_price: float | None = 100.0,
    mt5_execution_price: float | None = 101.0,
    latency_seconds: float | None = 2.0,
    mt5_ticket: int | None = 1,
    side: str | None = "BUY",
    pnl_usd: float | None = None,
    duration_seconds: float | None = None,
    closed_at_utc: str | None = None,
) -> dict[str, object]:
    return {
        "recorded_at_utc": recorded_at_utc,
        "symbol": symbol,
        "signal_type": "ENTRY",
        "telegram_price": telegram_price,
        "mt5_execution_price": mt5_execution_price,
        "spread": None,
        "latency_seconds": latency_seconds,
        "position_id": None,
        "mt5_ticket": mt5_ticket,
        "side": side,
        "strategy": None,
        "message_timestamp_utc": recorded_at_utc,
        "status": "closed" if closed_at_utc else "executed",
        "details": None,
        "exit_price": None,
        "exit_reason": None,
        "pnl_usd": pnl_usd,
        "pnl_pips_or_points": None,
        "duration_seconds": duration_seconds,
        "reported_duration": None,
        "reported_pnl": None,
        "closed_at_utc": closed_at_utc,
    }


def _crear_db(ruta_db: Path) -> None:
    filas = [
        (
            "2026-09-04T00:05:00+00:00", "BTCUSDm", "ENTRY", 100.0, 101.0,
            1.0, 2.0, "a", 1, "BUY", None,
            "2026-09-04T00:05:00+00:00", "closed", None, 102.0, "tp",
            10.0, 2.0, 60.0, None, None, "2026-09-04T00:06:00+00:00"
        ),
        (
            "2026-09-04T01:05:00+00:00", "BTCUSDm", "ENTRY", 110.0, 111.0,
            1.0, 4.0, "b", 2, "BUY", None,
            "2026-09-04T01:05:00+00:00", "executed", None, None, None,
            None, None, None, None, None, None
        ),
    ]
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
            filas,
        )


def test_calcular_rentabilidad_por_duracion_agrupa_win_rate_y_pnl_medio():
    rows = [
        _row(pnl_usd=10.0, duration_seconds=60.0, closed_at_utc="2026-09-04T12:01:00+00:00"),
        _row(pnl_usd=-5.0, duration_seconds=180.0, closed_at_utc="2026-09-04T12:03:00+00:00"),
        _row(pnl_usd=20.0, duration_seconds=600.0, closed_at_utc="2026-09-04T12:10:00+00:00"),
        _row(pnl_usd=-10.0, duration_seconds=1200.0, closed_at_utc="2026-09-04T12:20:00+00:00"),
    ]

    resultado = calcular_rentabilidad_por_duracion(rows)

    assert resultado[0] == {
        "duracion": "0-2 min",
        "trades": 1,
        "win_rate": 100.0,
        "pnl_medio": 10.0,
        "pnl_total": 10.0,
    }
    assert resultado[1]["duracion"] == "2-5 min"
    assert resultado[1]["win_rate"] == 0.0
    assert resultado[2]["pnl_medio"] == 20.0
    assert resultado[3]["pnl_total"] == -10.0


def test_calcular_rendimiento_por_hora_identifica_horas_ganadoras_y_perdedoras():
    rows = [
        _row(recorded_at_utc="2026-09-04T09:15:00+00:00", pnl_usd=12.0, duration_seconds=60.0, closed_at_utc="2026-09-04T09:16:00+00:00"),
        _row(recorded_at_utc="2026-09-04T09:45:00+00:00", pnl_usd=-6.0, duration_seconds=60.0, closed_at_utc="2026-09-04T09:46:00+00:00"),
        _row(recorded_at_utc="2026-09-04T15:00:00+00:00", pnl_usd=-8.0, duration_seconds=60.0, closed_at_utc="2026-09-04T15:01:00+00:00"),
    ]

    resultado = calcular_rendimiento_por_hora(rows)

    assert resultado[0]["hora_utc"] == "09:00"
    assert resultado[0]["trades"] == 2
    assert resultado[0]["ganadoras"] == 1
    assert resultado[0]["perdedoras"] == 1
    assert resultado[0]["pnl_total"] == 6.0
    assert resultado[1]["hora_utc"] == "15:00"
    assert resultado[1]["win_rate"] == 0.0


def test_calcular_slippage_por_simbolo_respeta_sentido_buy_y_sell():
    rows = [
        _row(symbol="BTCUSDm", telegram_price=100.0, mt5_execution_price=103.0, side="BUY", latency_seconds=2.0),
        _row(symbol="BTCUSDm", telegram_price=100.0, mt5_execution_price=98.0, side="SELL", latency_seconds=4.0),
        _row(symbol="XAUUSDm", telegram_price=2000.0, mt5_execution_price=1999.5, side="BUY", latency_seconds=6.0),
    ]

    resultado = calcular_slippage_por_simbolo(rows)

    btc = resultado[0]
    xau = resultado[1]
    assert btc["symbol"] == "BTCUSDm"
    assert btc["trades"] == 2
    assert btc["slippage_adverso_medio"] == 2.5
    assert btc["peor_slippage_adverso"] == 3.0
    assert btc["latencia_media"] == 3.0
    assert xau["symbol"] == "XAUUSDm"
    assert xau["slippage_adverso_medio"] == -0.5


def test_diagnosticar_inventario_abierto_limita_ocho_tickets_y_calcula_distancia():
    rows = [
        _row(
            recorded_at_utc=f"2026-09-04T00:0{indice}:00+00:00",
            mt5_ticket=100 + indice,
            mt5_execution_price=100.0 + indice,
        )
        for indice in range(9)
    ]
    precios = {100: {"precio_actual": 110.0}}

    resultado = diagnosticar_inventario_abierto(
        rows,
        precios,
        ahora=datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc),
    )

    assert len(resultado) == 8
    assert resultado[0]["ticket"] == 100
    assert resultado[0]["distancia"] == 10.0
    assert resultado[0]["distancia_pct"] == 10.0
    assert resultado[1]["precio_actual"] is None
    assert resultado[-1]["ticket"] == 107


def test_generar_reporte_cuantitativo_usa_sqlite_y_degrada_precio_actual(tmp_path):
    ruta_db = tmp_path / "quant.db"
    _crear_db(ruta_db)

    with patch(
        "analisis_cuantitativo.obtener_precios_actuales_para_inventario",
        return_value=(None, "No se pudo conectar a MT5"),
    ):
        reporte = generar_reporte_cuantitativo(ruta_db)

    assert "Análisis cuantitativo avanzado" in reporte
    assert "Rentabilidad por duración" in reporte
    assert "Rendimiento por hora UTC" in reporte
    assert "Slippage real vs teórico por símbolo" in reporte
    assert "Inventario abierto BTCUSDm" in reporte
    assert "MT5 no disponible para precio actual" in reporte
    assert "100.00" in reporte
