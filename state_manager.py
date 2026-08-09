# state_manager.py
import json
import os

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


# --- Código que solo se ejecuta si corres este archivo directamente ---
if __name__ == "__main__":
    print(posiciones)

    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02, "BUY")
    abrir_posicion("6bcb96ll", 123456789, "BTCUSD", 0.02, "SELL")
    print(posiciones)

    cerrar_posicion("6bcb96ff")
    print(posiciones)

    cerrar_posicion("no-existe-este-id")

    