# test_mt5_connection.py

import os

import pytest



def test_mt5_connection_integracion_opcional() -> None:
    """
    Verifica que sea posible inicializar una conexión a MT5 cuando el entorno
    de integración está disponible.

    Si faltan dependencias opcionales o credenciales locales, el test se omite
    para no romper la suite unitaria normal.
    """
    dotenv = pytest.importorskip("dotenv")
    mt5 = pytest.importorskip("MetaTrader5")

    dotenv.load_dotenv()

    mt5_login_texto = os.getenv("MT5_LOGIN")
    mt5_password = os.getenv("MT5_PASSWORD")
    mt5_server = os.getenv("MT5_SERVER")

    if not mt5_login_texto or not mt5_password or not mt5_server:
        pytest.skip("Entorno MT5 no configurado para la prueba de integración.")

    conexion_exitosa = mt5.initialize(
        login=int(mt5_login_texto),
        password=mt5_password,
        server=mt5_server,
    )

    try:
        assert conexion_exitosa, f"No se pudo conectar con MetaTrader 5: {mt5.last_error()}"
    finally:
        mt5.shutdown()
