# broker_mt5.py
#
# Broker Connector: este módulo es el único lugar del proyecto que habla
# directamente con la librería MetaTrader5. Si algún día cambiamos de bróker,
# o de forma de conectar, solo este archivo debería necesitar cambios.

import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import MetaTrader5 as mt5
from logger import logger

# Cargamos las variables del archivo .env apenas se importa este módulo.
load_dotenv()

MT5_LOGIN = int(os.getenv("MT5_LOGIN"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")


def asegurar_conexion():
    info_terminal = mt5.terminal_info()

    if info_terminal is not None:
        return True

    conexion_exitosa = mt5.initialize(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
    )

    if conexion_exitosa:
        logger.info("Conexión a MT5 establecida.")
        return True
    else:
        logger.error("Error al conectar a MT5: %s", mt5.last_error())
        return False

from config import LOTE_FIJO, MAPEO_SIMBOLOS, MAGIC_NUMBER, SPREAD_MAXIMO_PERMITIDO

def resolver_simbolo_broker(symbol):
    return MAPEO_SIMBOLOS.get(symbol, symbol)



def obtener_posiciones_abiertas_del_bot():
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "motivo": "No se pudo conectar a MT5", "posiciones": []}

    posiciones_mt5 = mt5.positions_get()
    if posiciones_mt5 is None:
        return {
            "exito": False,
            "motivo": "No se pudo obtener posiciones desde MT5",
            "posiciones": [],
        }

    posiciones_del_bot = [
        posicion for posicion in posiciones_mt5 if posicion.magic == MAGIC_NUMBER
    ]
    return {"exito": True, "motivo": None, "posiciones": posiciones_del_bot}



def _inferir_motivo_cierre_broker(deal) -> str | None:
    reason = getattr(deal, "reason", None)
    if reason == getattr(mt5, "DEAL_REASON_SL", object()):
        return "sl_broker"
    if reason == getattr(mt5, "DEAL_REASON_TP", object()):
        return "tp_broker"
    if reason == getattr(mt5, "DEAL_REASON_EXPERT", object()):
        return "expert_broker"
    if reason == getattr(mt5, "DEAL_REASON_CLIENT", object()):
        return "manual_client"
    return None



def obtener_metricas_cierre_mt5(ticket):
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "motivo": "No se pudo conectar a MT5"}

    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=7)

    try:
        deals = mt5.history_deals_get(desde, ahora)
    except Exception as error:
        logger.error("Excepción consultando histórico de deals para %s: %s", ticket, error)
        deals = None

    if deals is None:
        return {
            "exito": False,
            "motivo": f"No se pudo obtener histórico de deals para ticket {ticket}",
        }

    deals_ticket = [deal for deal in deals if getattr(deal, "position_id", None) == ticket]
    if not deals_ticket:
        deals_ticket = [deal for deal in deals if getattr(deal, "order", None) == ticket]

    if not deals_ticket:
        return {
            "exito": False,
            "motivo": f"No se encontraron deals históricos para ticket {ticket}",
        }

    deal_cierre = sorted(deals_ticket, key=lambda deal: getattr(deal, "time", 0))[-1]
    timestamp = getattr(deal_cierre, "time", None)
    closed_at_utc = None
    if timestamp is not None:
        closed_at_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    return {
        "exito": True,
        "motivo": None,
        "exit_price": getattr(deal_cierre, "price", None),
        "pnl_usd": getattr(deal_cierre, "profit", None),
        "closed_at_utc": closed_at_utc,
        "exit_reason_broker": _inferir_motivo_cierre_broker(deal_cierre),
    }



def obtener_spread_actual(symbol):
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "motivo": "No se pudo conectar a MT5"}

    symbol_broker = resolver_simbolo_broker(symbol)
    seleccion_exitosa = mt5.symbol_select(symbol_broker, True)
    if not seleccion_exitosa:
        motivo = f"No se pudo habilitar el símbolo {symbol_broker} en Market Watch"
        return {"exito": False, "motivo": motivo, "symbol_broker": symbol_broker}

    symbol_info = mt5.symbol_info(symbol_broker)
    if symbol_info is None:
        motivo = f"No se pudo obtener información del símbolo {symbol_broker}"
        return {"exito": False, "motivo": motivo, "symbol_broker": symbol_broker}

    tick = mt5.symbol_info_tick(symbol_broker)
    if tick is None:
        motivo = f"No se pudo obtener precio para {symbol_broker}"
        return {"exito": False, "motivo": motivo, "symbol_broker": symbol_broker}

    spread = tick.ask - tick.bid
    return {
        "exito": True,
        "motivo": None,
        "symbol_broker": symbol_broker,
        "spread_actual": spread,
        "bid": tick.bid,
        "ask": tick.ask,
        "digits": getattr(symbol_info, "digits", None),
    }


def abrir_operacion_mt5(symbol, lot, side):
    info_spread = obtener_spread_actual(symbol)
    if not info_spread["exito"]:
        return {
            "exito": False,
            "ticket": None,
            "volumen_ejecutado": None,
            "precio_ejecutado": None,
            "spread_actual": None,
            "symbol_broker": info_spread.get("symbol_broker"),
            "rechazada_por_spread": False,
            "codigo_motivo": "MT5_DATA_ERROR",
            "motivo": info_spread["motivo"],
        }

    symbol_broker = info_spread["symbol_broker"]
    spread_actual = info_spread["spread_actual"]
    spread_maximo = SPREAD_MAXIMO_PERMITIDO.get(symbol_broker)
    if spread_maximo is not None and spread_actual > spread_maximo:
        logger.warning(
            "ENTRY rechazada por spread alto en %s: spread actual %.5f, máximo permitido %.5f",
            symbol_broker,
            spread_actual,
            spread_maximo,
        )
        return {
            "exito": False,
            "ticket": None,
            "volumen_ejecutado": None,
            "precio_ejecutado": None,
            "spread_actual": spread_actual,
            "symbol_broker": symbol_broker,
            "rechazada_por_spread": True,
            "codigo_motivo": "SPREAD_TOO_HIGH",
            "motivo": (
                f"Spread actual {spread_actual:.5f} excede máximo permitido "
                f"{spread_maximo:.5f} para {symbol_broker}"
            ),
        }

    if side == "BUY":
        tipo_orden = mt5.ORDER_TYPE_BUY
        precio = info_spread["ask"]
    else:
        tipo_orden = mt5.ORDER_TYPE_SELL
        precio = info_spread["bid"]

    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol_broker,
        "volume": lot,
        "type": tipo_orden,
        "price": precio,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Apertura automatizada",
    }

    try:
        resultado = mt5.order_send(solicitud)
    except Exception as error:
        logger.error("Excepción al enviar la orden de apertura para %s: %s", symbol_broker, error)
        resultado = None

    if resultado is None:
        motivo = "Sin respuesta del servidor al enviar la orden de apertura (posible caída de conexión)"
        logger.warning("Orden rechazada: %s", motivo)
        return {
            "exito": False,
            "ticket": None,
            "volumen_ejecutado": None,
            "precio_ejecutado": None,
            "spread_actual": spread_actual,
            "symbol_broker": symbol_broker,
            "rechazada_por_spread": False,
            "codigo_motivo": "ORDER_SEND_NO_RESPONSE",
            "motivo": motivo,
        }

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
            volumen_ejecutado = resultado.volume

            if volumen_ejecutado < lot:
                logger.warning(
                    "Fill parcial. Solicitado %s, ejecutado %s",
                    lot,
                    volumen_ejecutado,
                )

            logger.info(
                "Orden ejecutada: %s %s lotes de %s, ticket %s",
                side,
                volumen_ejecutado,
                symbol_broker,
                resultado.order,
            )
            return {
                "exito": True,
                "ticket": resultado.order,
                "volumen_ejecutado": volumen_ejecutado,
                "precio_ejecutado": precio,
                "spread_actual": spread_actual,
                "symbol_broker": symbol_broker,
                "rechazada_por_spread": False,
                "codigo_motivo": None,
                "motivo": None,
            }
    else:
        logger.warning("Orden rechazada: %s", resultado.comment)
        return {
            "exito": False,
            "ticket": None,
            "volumen_ejecutado": None,
            "precio_ejecutado": None,
            "spread_actual": spread_actual,
            "symbol_broker": symbol_broker,
            "rechazada_por_spread": False,
            "codigo_motivo": "ORDER_REJECTED",
            "motivo": resultado.comment,
        }

def cerrar_operacion_mt5(ticket):
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "motivo": "No se pudo conectar a MT5"}

    posiciones = mt5.positions_get(ticket=ticket)

    if len(posiciones) == 0:
        motivo = f"No se encontró una posición abierta con ticket {ticket}"
        return {"exito": False, "motivo": motivo}

    # positions_get devuelve una tupla; como filtramos por un ticket
    # específico, esperamos como máximo un solo resultado.
    posicion = posiciones[0]

    symbol_broker = posicion.symbol
    volumen = posicion.volume

    # Si la posición original era BUY, la cerramos con una orden SELL,
    # y usamos el precio bid actual. Si era SELL, la cerramos con BUY,
    # usando el precio ask actual.
    tick = mt5.symbol_info_tick(symbol_broker)

    if posicion.type == mt5.ORDER_TYPE_BUY:
        tipo_orden_cierre = mt5.ORDER_TYPE_SELL
        precio = tick.bid
    else:
        tipo_orden_cierre = mt5.ORDER_TYPE_BUY
        precio = tick.ask

    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol_broker,
        "volume": volumen,
        "type": tipo_orden_cierre,
        "position": ticket,
        "price": precio,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Cierre automatizado",
    }

    try:
        resultado = mt5.order_send(solicitud)
    except Exception as error:
        logger.error("Excepción al enviar la orden de cierre para %s: %s", ticket, error)
        resultado = None

    if resultado is None:
        motivo = "Sin respuesta del servidor al enviar la orden de cierre (posible caída de conexión)"
        logger.warning("Error al cerrar posición %s: %s", ticket, motivo)
        return {"exito": False, "motivo": motivo}

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info("Posición %s cerrada correctamente.", ticket)
        return {
            "exito": True,
            "motivo": None,
            "precio_cierre_solicitado": precio,
            "closed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    else:
        logger.warning("Error al cerrar posición %s: %s", ticket, resultado.comment)
        return {"exito": False, "motivo": resultado.comment}
# Corre solo si ejecutamos este archivo directamente, no si lo importamos desde otro módulo.
def modificar_sl_mt5(ticket, nuevo_sl):
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "motivo": "No se pudo conectar a MT5"}

    posiciones = mt5.positions_get(ticket=ticket)

    if len(posiciones) == 0:
        motivo = f"No se encontró una posición abierta con ticket {ticket}"
        return {"exito": False, "motivo": motivo}

    posicion = posiciones[0]

    solicitud = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": posicion.symbol,
        "position": ticket,
        "sl": nuevo_sl,
        "tp": posicion.tp,  # reenviamos el TP actual para no borrarlo
        "magic": MAGIC_NUMBER,
        "comment": "Trailing stop automatizado",
    }

    try:
        resultado = mt5.order_send(solicitud)
    except Exception as error:
        logger.error("Excepción al enviar la orden de modificación de SL para %s: %s", ticket, error)
        resultado = None

    if resultado is None:
        motivo = "Sin respuesta del servidor al enviar la orden de modificación de SL (posible caída de conexión)"
        logger.warning("Error al modificar SL de posición %s: %s", ticket, motivo)
        return {"exito": False, "motivo": motivo}
    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info("SL actualizado para posición %s: nuevo SL %s", ticket, nuevo_sl)
        return {"exito": True, "motivo": None}
    else:
        logger.warning("Error al modificar SL de posición %s: %s", ticket, resultado.comment)
        return {"exito": False, "motivo": resultado.comment}

if __name__ == "__main__":
    # --- Prueba manual de modificar_sl_mt5 ---
    # Abrimos una posición de prueba, le asignamos un SL, y la cerramos.
    # No necesitamos que el precio se mueva: solo probamos que la función
    # logre comunicarse con MT5 y aplicar el cambio.

    resultado_apertura = abrir_operacion_mt5("BTCUSD", 0.01, "BUY")
    print(resultado_apertura)

    if resultado_apertura["exito"]:
        ticket = resultado_apertura["ticket"]

        # Necesitamos el precio actual para calcular un SL válido.
        # Para una posición BUY, el SL debe quedar por debajo del precio.
        symbol_broker = MAPEO_SIMBOLOS.get("BTCUSD", "BTCUSD")
        tick = mt5.symbol_info_tick(symbol_broker)

        # Restamos una distancia razonable (por ejemplo, 100 puntos de precio)
        # para asegurarnos de que el SL sea válido y no quede pegado al precio.
        sl_de_prueba = tick.bid - 100

        resultado_sl = modificar_sl_mt5(ticket, sl_de_prueba)
        print(resultado_sl)

        # Cerramos la posición de prueba para no dejarla abierta.
        resultado_cierre = cerrar_operacion_mt5(ticket)
        print(resultado_cierre)