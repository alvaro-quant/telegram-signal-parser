# state_manager.py
import json
import os
from broker_mt5 import obtener_posiciones_abiertas_del_bot, mt5
from config import MAGIC_NUMBER
from logger import logger

NOMBRE_ARCHIVO_POSICIONES = "posiciones.json"

def abrir_posicion(position_id, mt5_ticket, symbol, lot,side):
    detalles = {
        "mt5_ticket": mt5_ticket,
        "symbol": symbol,
        "lot": lot,
        "side": side,
        "status": "OPEN",
        "sl": None
    }

    posiciones[position_id] = detalles

    logger.info("Posición abierta: %s -> %s", position_id, detalles)
    guardar_posiciones()
def obtener_posicion(position_id):
    if position_id in posiciones:
        return posiciones[position_id]
    else:
        return None

def cerrar_posicion(position_id):
    if position_id in posiciones:
        posiciones[position_id]["status"] = "CLOSED"
        logger.info("Posición cerrada: %s -> %s", position_id, posiciones[position_id])
        guardar_posiciones()
        return True
    else:
        logger.warning("No se encontró la posición: %s", position_id)
        return False

def actualizar_sl(position_id, nuevo_sl):
    """
    Actualiza el stop loss guardado para una posición existente.
    Se usa cada vez que confirmamos (y aplicamos en MT5) un nuevo
    trailing stop reportado por el bot de Telegram.
    """
    if position_id in posiciones:
        posiciones[position_id]["sl"] = nuevo_sl
        guardar_posiciones()
def cargar_posiciones():
    """
    Lee posiciones.json desde disco y reemplaza el contenido del
    diccionario global `posiciones` con lo que encuentre ahí.
    Si el archivo no existe todavía (primera vez que corre el sistema),
    no hace nada y `posiciones` queda como estaba (vacío).
    """
    global posiciones

    if not os.path.exists(NOMBRE_ARCHIVO_POSICIONES):
        logger.info("No existe posiciones.json todavía. Se parte con estado vacío.")
        return

    with open(NOMBRE_ARCHIVO_POSICIONES, "r") as archivo:
        posiciones = json.load(archivo)

    logger.info("Estado cargado desde disco: %s posición(es).", len(posiciones))

def guardar_posiciones():
    """
    Vuelca el diccionario global `posiciones` completo a posiciones.json,
    sobrescribiendo lo que hubiera antes. Se llama automáticamente cada
    vez que el estado cambia (abrir, cerrar, actualizar SL).
    """
    with open(NOMBRE_ARCHIVO_POSICIONES, "w") as archivo:
        json.dump(posiciones, archivo, indent=4)
posiciones = {}

def reconciliar_estado():
    """
    Compara el estado local (diccionario `posiciones`, ya cargado
    desde disco) contra las posiciones reales que existen en MT5,
    y corrige el estado local si hay diferencias.
    """
    resultado_posiciones = obtener_posiciones_abiertas_del_bot()
    if not resultado_posiciones["exito"]:
        logger.warning("%s. Reconciliación cancelada.", resultado_posiciones["motivo"])
        return

    posiciones_del_bot_en_mt5 = resultado_posiciones["posiciones"]

    logger.info(
        "MT5 reporta %s posición(es) con nuestro magic number.",
        len(posiciones_del_bot_en_mt5),
    )

    tickets_abiertos_localmente = set()
    for position_id in posiciones:
        detalle = posiciones[position_id]
        if detalle["status"] == "OPEN":
            tickets_abiertos_localmente.add(detalle["mt5_ticket"])

    logger.info(
        "Estado local reporta %s posición(es) como OPEN.",
        len(tickets_abiertos_localmente),
    )
    tickets_reales_en_mt5 = set()
    for posicion in posiciones_del_bot_en_mt5:
        tickets_reales_en_mt5.add(posicion.ticket)
    logger.info("Tickets reales en MT5: %s", tickets_reales_en_mt5)

    tickets_a_cerrar = tickets_abiertos_localmente - tickets_reales_en_mt5
    logger.info("Tickets a marcar como CLOSED (Caso 2): %s", tickets_a_cerrar)

    for position_id in posiciones:
        detalle = posiciones[position_id]
        if detalle["status"] == "OPEN" and detalle["mt5_ticket"] in tickets_a_cerrar:
            from engine import registrar_cierre_reconciliado

            registrar_cierre_reconciliado(position_id, detalle)
            detalle["status"] = "CLOSED"
            logger.warning(
                "Reconciliación: %s (ticket %s) marcado CLOSED — no existe en MT5.",
                position_id,
                detalle["mt5_ticket"],
            )
    tickets_huerfanos = tickets_reales_en_mt5 - tickets_abiertos_localmente
    logger.warning("Tickets huérfanos detectados (Caso 3): %s", tickets_huerfanos)

    for posicion in posiciones_del_bot_en_mt5:
        if posicion.ticket in tickets_huerfanos:
            position_id_generado = str(posicion.ticket)

            if posicion.type == mt5.ORDER_TYPE_BUY:
                side = "BUY"
            else:
                side = "SELL"

            detalles = {
                "mt5_ticket": posicion.ticket,
                "symbol": posicion.symbol,
                "lot": posicion.volume,
                "side": side,
                "status": "OPEN",
                "sl": posicion.sl,
            }

            posiciones[position_id_generado] = detalles
            logger.warning("Posición huérfana registrada: %s -> %s", position_id_generado, detalles)

    guardar_posiciones()


# --- Código que solo se ejecuta si corres este archivo directamente ---
if __name__ == "__main__":
    cargar_posiciones()
    reconciliar_estado()