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
from broker_mt5 import abrir_operacion_mt5, cerrar_operacion_mt5, modificar_sl_mt5
from logger import logger
from telemetry import registrar_trade_metric


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
            message_timestamp_utc=senal.get("message_timestamp_utc"),
            status=status,
            details=resultado_broker.get("motivo"),
        )
    except Exception as error:
        logger.error("No se pudo registrar telemetría de ENTRY: %s", error)


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
