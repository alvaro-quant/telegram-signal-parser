# test_mt5_connection.py

import os
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Cargamos las variables del archivo .env al entorno
load_dotenv()

# Leemos las credenciales desde las variables de entorno
mt5_login_texto = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PASSWORD")
mt5_server = os.getenv("MT5_SERVER")

mt5_login = int(mt5_login_texto)

conexion_exitosa = mt5.initialize(
    login=mt5_login,
    password=mt5_password,
    server=mt5_server
)

if conexion_exitosa:
    print("Conexión exitosa con MetaTrader 5")
    print("Cuenta conectada:", mt5_login)
    print("Servidor:", mt5_server)

    simbolo = "BTCUSDm"

    # Buscamos las posiciones abiertas actualmente para este símbolo,
    # en vez de abrir una nueva o hardcodear un ticket
    posiciones_abiertas = mt5.positions_get(symbol=simbolo)

    if posiciones_abiertas is None or len(posiciones_abiertas) == 0:
        print("No hay posiciones abiertas para", simbolo)
    else:
        # Tomamos la primera posición abierta que encontremos
        posicion_a_cerrar = posiciones_abiertas[0]
        print("Posición encontrada, ticket:", posicion_a_cerrar.ticket)
        print("Volumen de esa posición:", posicion_a_cerrar.volume)

        # Necesitamos el precio actual para cerrar
        tick_para_cerrar = mt5.symbol_info_tick(simbolo)

        solicitud_cierre = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": simbolo,
            "volume": posicion_a_cerrar.volume,
            "type": mt5.ORDER_TYPE_SELL,
            "position": posicion_a_cerrar.ticket,
            "price": tick_para_cerrar.bid,
            "deviation": 20,
            "magic": 123456,
            "comment": "cierre de prueba desde Python",
        }

        resultado_cierre = mt5.order_send(solicitud_cierre)

        print("Código de retorno:", resultado_cierre.retcode)
        print("Comentario del servidor:", resultado_cierre.comment)

        if resultado_cierre.retcode == mt5.TRADE_RETCODE_DONE:
            print("¡Posición cerrada con éxito!")
        else:
            print("La posición no se pudo cerrar correctamente")

else:
    print("No se pudo conectar con MetaTrader 5")
    print("Código de error:", mt5.last_error())

mt5.shutdown()