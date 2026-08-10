# state_manager.py
import json
import os
import MetaTrader5 as mt5
from config import MAGIC_NUMBER

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

    # Mensaje informativo
    print(f"Posición abierta: {position_id} -> {detalles}")
    guardar_posiciones()
def obtener_posicion(position_id):
    if position_id in posiciones:
        return posiciones[position_id]
    else:
        return None

def cerrar_posicion(position_id):
    if position_id in posiciones:
        posiciones[position_id]["status"] = "CLOSED"
        print(f"Posición cerrada: {position_id} -> {posiciones[position_id]}")
        guardar_posiciones()
        return True
    else:
        print(f"No se encontró la posición: {position_id}")
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
        print("No existe posiciones.json todavía. Se parte con estado vacío.")
        return

    with open(NOMBRE_ARCHIVO_POSICIONES, "r") as archivo:
        posiciones = json.load(archivo)

    print(f"Estado cargado desde disco: {len(posiciones)} posición(es).")

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
    # Pedimos a MT5 todas las posiciones abiertas en la cuenta.
    # mt5.positions_get() no filtra por magic number directamente,
    # así que vamos a filtrar nosotros mismos después.
    posiciones_mt5 = mt5.positions_get()

    if posiciones_mt5 is None:
        # Esto pasa si hay un problema de conexión con MT5
        # (mismo patrón que ya usamos en broker_mt5.py).
        print("No se pudo obtener posiciones desde MT5. Reconciliación cancelada.")
        return

    # Filtramos: nos quedamos solo con las posiciones que tienen
    # nuestro magic number. Las demás pueden ser operaciones manuales
    # tuyas u otros bots, y no nos interesan para esta reconciliación.
    posiciones_del_bot_en_mt5 = []
    for posicion in posiciones_mt5:
        if posicion.magic == MAGIC_NUMBER:
            posiciones_del_bot_en_mt5.append(posicion)

    print(f"MT5 reporta {len(posiciones_del_bot_en_mt5)} posición(es) con nuestro magic number.")

    # Ahora armamos el conjunto de tickets que, según nuestro estado local,
    # deberían seguir abiertos. Recorremos `posiciones` (ya cargado desde
    # disco) y nos quedamos solo con los que tienen status "OPEN".
    tickets_abiertos_localmente = set()
    for position_id in posiciones:
        detalle = posiciones[position_id]
        if detalle["status"] == "OPEN":
            tickets_abiertos_localmente.add(detalle["mt5_ticket"])

    print(f"Estado local reporta {len(tickets_abiertos_localmente)} posición(es) como OPEN.")
    tickets_reales_en_mt5 = set()
    for posicion in posiciones_del_bot_en_mt5:
        tickets_reales_en_mt5.add(posicion.ticket)
    print(f"Tickets reales en MT5: {tickets_reales_en_mt5}")

    # CASO 2: tickets que el bot cree abiertos, pero que ya no existen
    # en MT5 (se cerraron manualmente, por SL, por TP, etc. mientras
    # el programa estaba apagado).
    #
    # La resta de sets "A - B" te da los elementos que están en A
    # pero no en B. Aquí: "lo que creo abierto" menos "lo que sí existe".
    tickets_a_cerrar = tickets_abiertos_localmente - tickets_reales_en_mt5
    print(f"Tickets a marcar como CLOSED (Caso 2): {tickets_a_cerrar}")

    for position_id in posiciones:
        detalle = posiciones[position_id]
        if detalle["status"] == "OPEN" and detalle["mt5_ticket"] in tickets_a_cerrar:
            detalle["status"] = "CLOSED"
            print(f"Reconciliación: {position_id} (ticket {detalle['mt5_ticket']}) marcado CLOSED — no existe en MT5.")
    # CASO 3: tickets que existen en MT5 con nuestro magic number,
    # pero que el estado local no tiene registrados en absoluto.
    # Puede pasar, por ejemplo, si order_send() se ejecutó en el bróker
    # pero el programa se cayó antes de alcanzar a llamar a abrir_posicion().
    tickets_huerfanos = tickets_reales_en_mt5 - tickets_abiertos_localmente
    print(f"Tickets huérfanos detectados (Caso 3): {tickets_huerfanos}")

    for posicion in posiciones_del_bot_en_mt5:
        if posicion.ticket in tickets_huerfanos:
            # Usamos el ticket de MT5 como position_id, convertido a texto,
            # porque no tenemos el position_id original del bot de Telegram
            # para esta operación.
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
            print(f"⚠️ Posición huérfana registrada: {position_id_generado} -> {detalles}")

    guardar_posiciones()


# --- Código que solo se ejecuta si corres este archivo directamente ---
if __name__ == "__main__":
    cargar_posiciones()
    reconciliar_estado()