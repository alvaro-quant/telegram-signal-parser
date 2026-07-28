# test_state_manager.py

import pytest
from state_manager import abrir_posicion, obtener_posicion, cerrar_posicion, posiciones


@pytest.fixture(autouse=True)
def limpiar_posiciones():
    # Este código corre ANTES de cada test (todo lo que está antes del yield).
    posiciones.clear()
    yield
    # Todo lo que iría DESPUÉS del yield correría al TERMINAR cada test.

def test_abrir_posicion_guarda_datos_correctos():
    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02)
    resultado = obtener_posicion("6bcb96ff")

    assert resultado is not None
    assert resultado["mt5_ticket"] == 123456789
    assert resultado["symbol"] == "BTCUSD"
    assert resultado["lot"] == 0.02
    assert resultado["status"] == "OPEN"

# Cerrar una posición existente y verificar que su status cambia a "CLOSED".
def test_cerrar_posicion_cambia_status_a_closed():
    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02)

    resultado_cierre = cerrar_posicion("6bcb96ff")
    assert resultado_cierre is True

    resultado_consulta = obtener_posicion("6bcb96ff")
    assert resultado_consulta["status"] == "CLOSED"

# Intentar cerrar un position_id inexistente y verificar que devuelve False.
def test_cerrar_id_inexistente_denvuelve_false():
    resultado = cerrar_posicion("123fdsdf3")
    assert resultado is False

# Consultar un position_id inexistente y verificar que obtener_posicion devuelve None.
def test_consultar_id_inexistente_devuelve_none():
    resultado = obtener_posicion("325gdfgh34234")
    assert resultado is None