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
