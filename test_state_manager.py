# test_state_manager.py

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from state_manager import abrir_posicion, obtener_posicion, cerrar_posicion, posiciones, reconciliar_estado


@pytest.fixture(autouse=True)
def limpiar_posiciones():
    posiciones.clear()
    yield


def test_abrir_posicion_guarda_datos_correctos():
    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02, "BUY")
    resultado = obtener_posicion("6bcb96ff")

    assert resultado is not None
    assert resultado["mt5_ticket"] == 123456789
    assert resultado["symbol"] == "BTCUSD"
    assert resultado["lot"] == 0.02
    assert resultado["status"] == "OPEN"
    assert resultado["side"] == "BUY"



def test_cerrar_posicion_cambia_status_a_closed():
    abrir_posicion("6bcb96ff", 123456789, "BTCUSD", 0.02, "BUY")

    resultado_cierre = cerrar_posicion("6bcb96ff")
    assert resultado_cierre is True

    resultado_consulta = obtener_posicion("6bcb96ff")
    assert resultado_consulta["status"] == "CLOSED"



def test_cerrar_id_inexistente_denvuelve_false():
    resultado = cerrar_posicion("123fdsdf3")
    assert resultado is False



def test_consultar_id_inexistente_devuelve_none():
    resultado = obtener_posicion("325gdfgh34234")
    assert resultado is None



def test_reconciliar_estado_marca_closed_y_registra_cierre_reconciliado():
    posiciones["abc123"] = {
        "mt5_ticket": 111,
        "symbol": "BTCUSD",
        "lot": 0.01,
        "side": "BUY",
        "status": "OPEN",
        "sl": None,
    }
    posicion_mt5_ajena = SimpleNamespace(ticket=222, magic=123456, type=0, symbol="BTCUSDm", volume=0.01, sl=None)

    with patch("state_manager.obtener_posiciones_abiertas_del_bot", return_value={"exito": True, "motivo": None, "posiciones": [posicion_mt5_ajena]}), \
         patch("state_manager.guardar_posiciones") as guardar_mock, \
         patch("engine.registrar_cierre_reconciliado") as registrar_cierre_mock:
        reconciliar_estado()

    assert posiciones["abc123"]["status"] == "CLOSED"
    registrar_cierre_mock.assert_called_once()
    assert registrar_cierre_mock.call_args.args[0] == "abc123"
    assert registrar_cierre_mock.call_args.args[1]["mt5_ticket"] == 111
    assert registrar_cierre_mock.call_args.args[1]["symbol"] == "BTCUSD"
    assert "222" in posiciones
    guardar_mock.assert_called_once_with()
