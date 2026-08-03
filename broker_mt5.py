# broker_mt5.py
#
# Broker Connector: este módulo es el único lugar del proyecto que habla
# directamente con la librería MetaTrader5. Si algún día cambiamos de bróker,
# o de forma de conectar, solo este archivo debería necesitar cambios.

import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Cargamos las variables del archivo .env apenas se importa este módulo.
load_dotenv()

MT5_LOGIN = int(os.getenv("MT5_LOGIN"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")


def asegurar_conexion():
    # Primero preguntamos si ya hay una conexión activa con la terminal MT5.
    info_terminal = mt5.terminal_info()

    if info_terminal is not None:
        # Ya estábamos conectados, no hace falta hacer nada más.
        return True

    # Si llegamos aquí, no había conexión activa. Intentamos conectar,
    # pasando las credenciales de forma explícita (no confiamos en que haya
    # una sesión guardada previamente en la terminal).
    conexion_exitosa = mt5.initialize(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
    )

    if conexion_exitosa:
        print("Conexión a MT5 establecida.")
        return True
    else:
        print(f"Error al conectar a MT5: {mt5.last_error()}")
        return False

from config import LOTE_FIJO, MAPEO_SIMBOLOS
def abrir_operacion_mt5(symbol, lot, side):
    conectado = asegurar_conexion()
    if not conectado:
        return {"exito": False, "ticket": None, "motivo": "No se pudo conectar a MT5"}

    # Traducimos el símbolo del bot ("BTCUSD") al símbolo real del bróker
    # ("BTCUSDm"). Si el símbolo no está en el mapeo, asumimos que no
    # necesita traducción y lo usamos tal cual.
    symbol_broker = MAPEO_SIMBOLOS.get(symbol, symbol)

    tick = mt5.symbol_info_tick(symbol_broker)
    if tick is None:
        motivo = f"No se pudo obtener precio para {symbol_broker}"
        return {"exito": False, "ticket": None, "motivo": motivo}

    if side == "BUY":
        tipo_orden = mt5.ORDER_TYPE_BUY
        precio = tick.ask
    else:
        tipo_orden = mt5.ORDER_TYPE_SELL
        precio = tick.bid

    solicitud = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol_broker,
        "volume": lot,
        "type": tipo_orden,
        "price": precio,
        "deviation": 20,
        "magic": 123456,
        "comment": "Apertura automatizada",
    }

    resultado = mt5.order_send(solicitud)

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Orden ejecutada: {side} {lot} lotes de {symbol_broker}, ticket {resultado.order}")
        return {"exito": True, "ticket": resultado.order, "motivo": None}
    else:
        print(f"Orden rechazada: {resultado.comment}")
        return {"exito": False, "ticket": None, "motivo": resultado.comment}

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
        "magic": 123456,
        "comment": "Cierre automatizado",
    }

    resultado = mt5.order_send(solicitud)

    if resultado.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"Posición {ticket} cerrada correctamente.")
        return {"exito": True, "motivo": None}
    else:
        print(f"Error al cerrar posición {ticket}: {resultado.comment}")
        return {"exito": False, "motivo": resultado.comment}
# Corre solo si ejecutamos este archivo directamente, no si lo importamos desde otro módulo.


if __name__ == "__main__":
    resultado = cerrar_operacion_mt5(593032011)
    print(resultado)