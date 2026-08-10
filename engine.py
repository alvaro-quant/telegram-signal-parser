# engine.py
#
# El Execution Engine recibe una señal ya parseada (un diccionario, salida de
# parse_message) y decide qué hacer con ella:
#   - ENTRY -> abrir una posición
#   - EXIT -> cerrar la posición asociada
#   - TRAILING_STOP_* -> por ahora, solo registrar en consola

from state_manager import abrir_posicion, cerrar_posicion, obtener_posicion, actualizar_sl
from config import LOTE_FIJO
from broker_mt5 import abrir_operacion_mt5, cerrar_operacion_mt5, modificar_sl_mt5


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
                senal["side"],   # <-- nuevo
            )
        else:
            print(f"Advertencia: no se pudo abrir posición para {senal['position_id']}: {resultado['motivo']}")

    elif tipo == "EXIT":
        posicion = obtener_posicion(senal["position_id"])
        if posicion is None:
            print(f"Advertencia: llegó EXIT para una posición desconocida: {senal['position_id']}")
        else:
            resultado = cerrar_operacion_mt5(posicion["mt5_ticket"])
            if resultado["exito"]:
                cerrar_posicion(senal["position_id"])
            else:
                print(f"Advertencia: no se pudo cerrar en MT5 la posición {senal['position_id']}: {resultado['motivo']}")

    elif tipo in ("TRAILING_STOP_ACTIVATED", "TRAILING_STOP_TIGHTENED"):
        posicion = obtener_posicion(senal["position_id"])

        if posicion is None:
            print(f"Advertencia: trailing stop para posición desconocida: {senal['position_id']}")
        else:
            sl_actual = posicion["sl"]
            nuevo_sl = senal["sl"]
            side = posicion["side"]

            # Decidimos si el nuevo SL representa una mejora real,
            # según la dirección de la posición.
            if sl_actual is None:
                es_mejora = True
            elif side == "BUY":
                es_mejora = nuevo_sl > sl_actual
            else:
                es_mejora = nuevo_sl < sl_actual

            if not es_mejora:
                print(f"Trailing stop ignorado para {senal['position_id']}: "
                      f"nuevo SL {nuevo_sl} no mejora el SL actual {sl_actual}")
            else:
                resultado = modificar_sl_mt5(posicion["mt5_ticket"], nuevo_sl)
                if resultado["exito"]:
                    actualizar_sl(senal["position_id"], nuevo_sl)
                    print(f"Trailing stop aplicado para {senal['position_id']}: nuevo SL {nuevo_sl}")
                else:
                    print(f"Advertencia: no se pudo aplicar trailing stop en MT5 "
                          f"para {senal['position_id']}: {resultado['motivo']}")

    else:
        print(f"Tipo de señal no reconocido, se ignora: {tipo}")

if __name__ == "__main__":
    from parsers import parse_message
    import MetaTrader5 as mt5
    from broker_mt5 import MAPEO_SIMBOLOS

    texto_entry = """🟢 Entry Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: BUY

💱 Symbol: BTCUSD

💰 Price: 64848.64

🆔 Position: 6bcb96ff

📐 Lot: 0.02"""

    senal_entry = parse_message(texto_entry)
    print(senal_entry)
    procesar_senal(senal_entry)

    from state_manager import posiciones
    print(posiciones)

    # --- Prueba de TRAILING_STOP: primer ajuste (debería aplicarse) ---
    symbol_broker = MAPEO_SIMBOLOS.get("BTCUSD", "BTCUSD")
    tick = mt5.symbol_info_tick(symbol_broker)

    sl_1 = tick.bid - 300  # distancia amplia para evitar el "stop level" del bróker

    texto_trailing_1 = f"""📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ {tick.bid}

🔒 SL: {sl_1}

📈 Best: {tick.bid}

🆔 Position: 6bcb96ff"""

    senal_trailing_1 = parse_message(texto_trailing_1)
    print(senal_trailing_1)
    procesar_senal(senal_trailing_1)
    print(posiciones)

    # --- Prueba de TRAILING_STOP: segundo ajuste, peor que el anterior (debería ignorarse) ---
    sl_2 = sl_1 - 50  # para una posición BUY, un SL más bajo es un empeoramiento

    texto_trailing_2 = f"""📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ {tick.bid}

🔒 SL: {sl_2}

📈 Best: {tick.bid}

🆔 Position: 6bcb96ff"""

    senal_trailing_2 = parse_message(texto_trailing_2)
    print(senal_trailing_2)
    procesar_senal(senal_trailing_2)
    print(posiciones)

    # --- EXIT ---
    texto_exit = """🔴 Exit Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: SELL

💱 Symbol: BTCUSD

💰 Price: 64945.92

🆔 Position: 6bcb96ff

🚪 Exit: atr_trailing_stop"""

    senal_exit = parse_message(texto_exit)
    print(senal_exit)
    procesar_senal(senal_exit)

    print(posiciones)