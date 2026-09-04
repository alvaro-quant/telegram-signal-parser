# engine.py
#
# El Execution Engine recibe una señal ya parseada (un diccionario, salida de
# parse_message) y decide qué hacer con ella:
#   - ENTRY -> abrir una posición
#   - EXIT -> cerrar la posición asociada
#   - TRAILING_STOP_* -> por ahora, solo registrar en consola

from datetime import datetime, timezone

from state_manager import abrir_posicion, cerrar_posicion, obtener_posicion, actualizar_sl
from config import LOTE_FIJO
from broker_mt5 import (
    abrir_operacion_mt5,
    cerrar_operacion_mt5,
    modificar_sl_mt5,
    obtener_metricas_cierre_mt5,
)
from logger import logger
from telemetry import registrar_trade_metric, registrar_cierre_metric


def _calcular_latencia_segundos(senal):
    message_timestamp_utc = senal.get("message_timestamp_utc")
    if not message_timestamp_utc:
        return None

    fecha_mensaje = datetime.fromisoformat(message_timestamp_utc)
    if fecha_mensaje.tzinfo is None:
        fecha_mensaje = fecha_mensaje.replace(tzinfo=timezone.utc)

    return (datetime.now(timezone.utc) - fecha_mensaje).total_seconds()


def _registrar_telemetria_entry(senal, resultado_broker, status):
    try:
        registrar_trade_metric(
            symbol=resultado_broker.get("symbol_broker") or senal["symbol"],
            signal_type=senal["type"],
            telegram_price=senal.get("price"),
            mt5_execution_price=resultado_broker.get("precio_ejecutado"),
            spread=resultado_broker.get("spread_actual"),
            latency_seconds=_calcular_latencia_segundos(senal),
            position_id=senal.get("position_id"),
            mt5_ticket=resultado_broker.get("ticket"),
            side=senal.get("side"),
            strategy=senal.get("strategy"),
            message_timestamp_utc=senal.get("message_timestamp_utc"),
            status=status,
            details=resultado_broker.get("motivo"),
        )
    except Exception as error:
        logger.error("No se pudo registrar telemetría de ENTRY: %s", error)



def _calcular_pnl_points(senal, posicion, exit_price):
    entry_price = senal.get("entry_price")
    if entry_price is None or exit_price is None:
        return None

    side = (posicion or {}).get("side") or senal.get("side")
    if side == "SELL":
        return entry_price - exit_price
    return exit_price - entry_price



def _registrar_telemetria_cierre(senal, posicion, resultado_cierre):
    try:
        metricas_cierre = obtener_metricas_cierre_mt5(posicion["mt5_ticket"])
        exit_price = senal.get("price")
        pnl_usd = None
        closed_at_utc = resultado_cierre.get("closed_at_utc")
        exit_reason = senal.get("exit_reason")
        details = None

        if metricas_cierre.get("exito"):
            exit_price = metricas_cierre.get("exit_price") or exit_price
            pnl_usd = metricas_cierre.get("pnl_usd")
            closed_at_utc = metricas_cierre.get("closed_at_utc") or closed_at_utc
            exit_reason = exit_reason or metricas_cierre.get("exit_reason_broker")
        else:
            details = metricas_cierre.get("motivo")

        registrar_cierre_metric(
            position_id=senal.get("position_id"),
            mt5_ticket=posicion.get("mt5_ticket"),
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_usd=pnl_usd,
            pnl_pips_or_points=senal.get("pnl_pips_or_points") or _calcular_pnl_points(senal, posicion, exit_price),
            duration_seconds=senal.get("duration_seconds"),
            closed_at_utc=closed_at_utc or datetime.now(timezone.utc).isoformat(),
            status="closed",
            details=details,
            reported_duration=senal.get("duration"),
            reported_pnl=senal.get("pnl"),
        )
    except Exception as error:
        logger.error("No se pudo registrar telemetría de cierre: %s", error)



def registrar_cierre_reconciliado(position_id, detalle):
    try:
        metricas_cierre = obtener_metricas_cierre_mt5(detalle["mt5_ticket"])
        registrar_cierre_metric(
            position_id=position_id,
            mt5_ticket=detalle.get("mt5_ticket"),
            exit_price=metricas_cierre.get("exit_price"),
            exit_reason=metricas_cierre.get("exit_reason_broker") or "reconciliacion_mt5",
            pnl_usd=metricas_cierre.get("pnl_usd"),
            pnl_pips_or_points=None,
            duration_seconds=None,
            closed_at_utc=metricas_cierre.get("closed_at_utc") or datetime.now(timezone.utc).isoformat(),
            status="closed",
            details=None if metricas_cierre.get("exito") else metricas_cierre.get("motivo"),
        )
    except Exception as error:
        logger.error("No se pudo registrar cierre reconciliado: %s", error)



def procesar_senal(senal):
    tipo = senal["type"]

    if tipo == "ENTRY":
        resultado = abrir_operacion_mt5(senal["symbol"], LOTE_FIJO, senal["side"])
        if resultado["exito"]:
            abrir_posicion(
                senal["position_id"],
                resultado["ticket"],
                senal["symbol"],
                resultado["volumen_ejecutado"],
                senal["side"],
            )
            _registrar_telemetria_entry(senal, resultado, "executed")
        else:
            logger.warning(
                "No se pudo abrir posición para %s: %s",
                senal["position_id"],
                resultado["motivo"],
            )
            if resultado.get("rechazada_por_spread"):
                _registrar_telemetria_entry(senal, resultado, "rejected_spread")
            else:
                _registrar_telemetria_entry(senal, resultado, "failed_broker")

    elif tipo == "EXIT":
        posicion = obtener_posicion(senal["position_id"])
        if posicion is None:
            logger.warning(
                "Llegó EXIT para una posición desconocida: %s",
                senal["position_id"],
            )
        else:
            resultado = cerrar_operacion_mt5(posicion["mt5_ticket"])
            if resultado["exito"]:
                _registrar_telemetria_cierre(senal, posicion, resultado)
                cerrar_posicion(senal["position_id"])
            else:
                logger.warning(
                    "No se pudo cerrar en MT5 la posición %s: %s",
                    senal["position_id"],
                    resultado["motivo"],
                )

    elif tipo in ("TRAILING_STOP_ACTIVATED", "TRAILING_STOP_TIGHTENED"):
        posicion = obtener_posicion(senal["position_id"])

        if posicion is None:
            logger.warning(
                "Trailing stop para posición desconocida: %s",
                senal["position_id"],
            )
        else:
            sl_actual = posicion["sl"]
            nuevo_sl = senal["sl"]
            side = posicion["side"]

            if sl_actual is None:
                es_mejora = True
            elif side == "BUY":
                es_mejora = nuevo_sl > sl_actual
            else:
                es_mejora = nuevo_sl < sl_actual

            if not es_mejora:
                logger.info(
                    "Trailing stop ignorado para %s: nuevo SL %s no mejora el SL actual %s",
                    senal["position_id"],
                    nuevo_sl,
                    sl_actual,
                )
            else:
                resultado = modificar_sl_mt5(posicion["mt5_ticket"], nuevo_sl)
                if resultado["exito"]:
                    actualizar_sl(senal["position_id"], nuevo_sl)
                    logger.info(
                        "Trailing stop aplicado para %s: nuevo SL %s",
                        senal["position_id"],
                        nuevo_sl,
                    )
                else:
                    logger.warning(
                        "No se pudo aplicar trailing stop en MT5 para %s: %s",
                        senal["position_id"],
                        resultado["motivo"],
                    )

    else:
        logger.warning("Tipo de señal no reconocido, se ignora: %s", tipo)
