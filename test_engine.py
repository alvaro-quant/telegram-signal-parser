from datetime import datetime, timezone
from unittest.mock import Mock, patch

import engine


def test_procesar_senal_entry_exitosa_registra_telemetria_y_abre_posicion():
    senal = {
        "type": "ENTRY",
        "symbol": "BTCUSD",
        "side": "BUY",
        "price": 81000.0,
        "position_id": "abc123",
        "message_timestamp_utc": "2026-09-04T12:00:00+00:00",
    }
    resultado_broker = {
        "exito": True,
        "ticket": 111,
        "volumen_ejecutado": 0.01,
        "precio_ejecutado": 81005.0,
        "spread_actual": 12.5,
        "symbol_broker": "BTCUSDm",
        "motivo": None,
    }

    with patch("engine.abrir_operacion_mt5", return_value=resultado_broker), \
         patch("engine.abrir_posicion") as abrir_posicion_mock, \
         patch("engine.registrar_trade_metric") as registrar_trade_metric_mock, \
         patch("engine.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(2026, 9, 4, 12, 0, 3, tzinfo=timezone.utc)
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        engine.procesar_senal(senal)

    abrir_posicion_mock.assert_called_once_with("abc123", 111, "BTCUSD", 0.01, "BUY")
    registrar_trade_metric_mock.assert_called_once_with(
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



def test_procesar_senal_entry_rechazada_por_spread_registra_telemetria_y_no_abre_posicion():
    senal = {
        "type": "ENTRY",
        "symbol": "XAUUSD",
        "side": "BUY",
        "price": 4500.0,
        "position_id": "spread123",
        "message_timestamp_utc": "2026-09-04T12:00:00+00:00",
    }
    resultado_broker = {
        "exito": False,
        "ticket": None,
        "volumen_ejecutado": None,
        "precio_ejecutado": None,
        "spread_actual": 2.4,
        "symbol_broker": "XAUUSDm",
        "rechazada_por_spread": True,
        "motivo": "Spread actual 2.40000 excede máximo permitido 1.50000 para XAUUSDm",
    }

    with patch("engine.abrir_operacion_mt5", return_value=resultado_broker), \
         patch("engine.abrir_posicion") as abrir_posicion_mock, \
         patch("engine.registrar_trade_metric") as registrar_trade_metric_mock, \
         patch("engine.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(2026, 9, 4, 12, 0, 4, tzinfo=timezone.utc)
        datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
        engine.procesar_senal(senal)

    abrir_posicion_mock.assert_not_called()
    registrar_trade_metric_mock.assert_called_once_with(
        symbol="XAUUSDm",
        signal_type="ENTRY",
        telegram_price=4500.0,
        mt5_execution_price=None,
        spread=2.4,
        latency_seconds=4.0,
        position_id="spread123",
        message_timestamp_utc="2026-09-04T12:00:00+00:00",
        status="rejected_spread",
        details="Spread actual 2.40000 excede máximo permitido 1.50000 para XAUUSDm",
    )



def test_procesar_senal_entry_sigue_operando_si_falla_telemetria():
    senal = {
        "type": "ENTRY",
        "symbol": "BTCUSD",
        "side": "BUY",
        "price": 81000.0,
        "position_id": "telemetry-fail",
    }
    resultado_broker = {
        "exito": True,
        "ticket": 222,
        "volumen_ejecutado": 0.01,
        "precio_ejecutado": 81002.0,
        "spread_actual": 10.0,
        "symbol_broker": "BTCUSDm",
        "motivo": None,
    }

    with patch("engine.abrir_operacion_mt5", return_value=resultado_broker), \
         patch("engine.abrir_posicion") as abrir_posicion_mock, \
         patch("engine.registrar_trade_metric", side_effect=RuntimeError("db down")):
        try:
            engine.procesar_senal(senal)
        except RuntimeError as error:
            raise AssertionError(f"La telemetría no debe romper el flujo: {error}")

    abrir_posicion_mock.assert_called_once_with("telemetry-fail", 222, "BTCUSD", 0.01, "BUY")
