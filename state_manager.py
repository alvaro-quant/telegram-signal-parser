# state_manager.py
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

def obtener_posicion(position_id):
    if position_id in posiciones:
        return posiciones[position_id]
    else:
        return None

def cerrar_posicion(position_id):
    if position_id in posiciones:
        posiciones[position_id]["status"] = "CLOSED"
        print(f"Posición cerrada: {position_id} -> {posiciones[position_id]}")
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

posiciones = {}


# --- Código que solo se ejecuta si corres este archivo directamente ---
if __name__ == "__main__":
    print(posiciones)

    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02)
    abrir_posicion("6bcb96ll", 123456789, "BTCUSD", 0.02)
    print(posiciones)

    cerrar_posicion("6bcb96ff")
    print(posiciones)

    cerrar_posicion("no-existe-este-id")

    