from datetime import datetime, timezone
from unittest.mock import patch

import engine


def test_procesar_senal_entry_exitosa_registra_telemetria_y_abre_posicion():
    senal = {
        "type": "ENTRY",
        "symbol": "BTCUSD",
        "side": "BUY",
        "price": 81000.0,
        "position_id": "abc123",
        "strategy": "Drawdown DCA Long",
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
        mt5_ticket=111,
        side="BUY",
        strategy="Drawdown DCA Long",
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
        mt5_ticket=None,
        side="BUY",
        strategy=None,
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



def test_procesar_senal_exit_exitoso_registra_cierre_y_cierra_posicion():
    senal = {
        "type": "EXIT",
        "symbol": "BTCUSD",
        "side": "BUY",
        "price": 81030.0,
        "position_id": "abc123",
        "exit_reason": "atr_trailing_stop",
        "pnl": "+0.15%",
        "pnl_pips_or_points": 0.15,
        "duration": "12m",
        "duration_seconds": 720.0,
    }
    posicion = {
        "mt5_ticket": 111,
        "symbol": "BTCUSD",
        "lot": 0.01,
        "side": "BUY",
        "status": "OPEN",
        "sl": None,
    }
    resultado_cierre = {
        "exito": True,
        "motivo": None,
        "precio_cierre_solicitado": 81029.5,
        "closed_at_utc": "2026-09-04T12:12:01+00:00",
    }
    metricas_cierre = {
        "exito": True,
        "motivo": None,
        "exit_price": 81028.0,
        "pnl_usd": 24.0,
        "closed_at_utc": "2026-09-04T12:12:00+00:00",
        "exit_reason_broker": "tp_broker",
    }

    with patch("engine.obtener_posicion", return_value=posicion), \
         patch("engine.cerrar_operacion_mt5", return_value=resultado_cierre), \
         patch("engine.obtener_metricas_cierre_mt5", return_value=metricas_cierre), \
         patch("engine.registrar_cierre_metric") as registrar_cierre_metric_mock, \
         patch("engine.cerrar_posicion") as cerrar_posicion_mock:
        engine.procesar_senal(senal)

    registrar_cierre_metric_mock.assert_called_once_with(
        position_id="abc123",
        mt5_ticket=111,
        exit_price=81028.0,
        exit_reason="atr_trailing_stop",
        pnl_usd=24.0,
        pnl_pips_or_points=0.15,
        duration_seconds=720.0,
        closed_at_utc="2026-09-04T12:12:00+00:00",
        status="closed",
        details=None,
        reported_duration="12m",
        reported_pnl="+0.15%",
    )
    cerrar_posicion_mock.assert_called_once_with("abc123")



def test_registrar_cierre_reconciliado_usa_fallback_si_mt5_no_devuelve_metricas():
    detalle = {
        "mt5_ticket": 222,
        "symbol": "XAUUSDm",
        "lot": 0.01,
        "side": "SELL",
        "status": "OPEN",
        "sl": 2498.0,
    }

    with patch("engine.obtener_metricas_cierre_mt5", return_value={"exito": False, "motivo": "sin deals"}), \
         patch("engine.registrar_cierre_metric") as registrar_cierre_metric_mock, \
         patch("engine.datetime") as datetime_mock:
        datetime_mock.now.return_value = datetime(2026, 9, 4, 13, 5, tzinfo=timezone.utc)
        engine.registrar_cierre_reconciliado("ticket-222", detalle)

    registrar_cierre_metric_mock.assert_called_once_with(
        position_id="ticket-222",
        mt5_ticket=222,
        exit_price=None,
        exit_reason="reconciliacion_mt5",
        pnl_usd=None,
        pnl_pips_or_points=None,
        duration_seconds=None,
        closed_at_utc="2026-09-04T13:05:00+00:00",
        status="closed",
        details="sin deals",
    )
