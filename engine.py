# engine.py
#
# El Execution Engine recibe una señal ya parseada (un diccionario, salida de
# parse_message) y decide qué hacer con ella:
#   - ENTRY -> abrir una posición
#   - EXIT -> cerrar la posición asociada
#   - TRAILING_STOP_* -> por ahora, solo registrar en consola

from state_manager import abrir_posicion, cerrar_posicion, obtener_posicion
from config import LOTE_FIJO

def abrir_operacion_mt5_simulada(symbol, lot, side):
    # PLACEHOLDER: esta función todavía no habla con MetaTrader 5 de verdad.
    # Cuando construyamos el Broker Connector, esta función se reemplaza por
    # la llamada real a la librería MetaTrader5, que sí devuelve un ticket
    # verdadero. Por ahora, devolvemos un número inventado para poder probar
    # el resto del sistema.
    ticket_falso = 999999
    print(f"[SIMULADO] Abriendo {side} {lot} lotes de {symbol} en MT5... ticket asignado: {ticket_falso}")
    return ticket_falso


def procesar_senal(senal):
    tipo = senal["type"]

    if tipo == "ENTRY":
        ticket = abrir_operacion_mt5_simulada(senal["symbol"], LOTE_FIJO, senal["side"])
        abrir_posicion(senal["position_id"], ticket, senal["symbol"], LOTE_FIJO)

    elif tipo == "EXIT":
        exito = cerrar_posicion(senal["position_id"])
        if not exito:
            print(f"Advertencia: llegó EXIT para una posición desconocida: {senal['position_id']}")

    elif tipo in ("TRAILING_STOP_ACTIVATED", "TRAILING_STOP_TIGHTENED"):
        posicion = obtener_posicion(senal["position_id"])
        if posicion is not None:
            print(f"Trailing stop registrado para {senal['position_id']}: nuevo SL {senal['sl']}")
        else:
            print(f"Advertencia: trailing stop para posición desconocida: {senal['position_id']}")

    else:
        print(f"Tipo de señal no reconocido, se ignora: {tipo}")


if __name__ == "__main__":
    from parsers import parse_message

    texto_entry = """🟢 Entry Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: BUY

💱 Symbol: BTCUSD

💰 Price: 64848.64

🆔 Position: 6bcb96ff

📐 Lot: 0.02"""

    senal = parse_message(texto_entry)
    print(senal)
    procesar_senal(senal)

    from state_manager import posiciones
    print(posiciones)