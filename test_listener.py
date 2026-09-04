import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import listener


class IteradorAsyncMensajes:
    def __init__(self, mensajes):
        self.mensajes = mensajes
        self._iterador = iter(())

    def __aiter__(self):
        self._iterador = iter(self.mensajes)
        return self

    async def __anext__(self):
        try:
            return next(self._iterador)
        except StopIteration:
            raise StopAsyncIteration



def test_recuperar_historial_procesa_mensajes_en_orden_cronologico():
    mensaje_nuevo = SimpleNamespace(id=200, text="nuevo")
    mensaje_antiguo = SimpleNamespace(id=100, text="antiguo")
    client = Mock()
    client.iter_messages.return_value = IteradorAsyncMensajes([mensaje_nuevo, mensaje_antiguo])

    parseados = {
        "antiguo": {"type": "ENTRY", "position_id": "old"},
        "nuevo": {"type": "ENTRY", "position_id": "new"},
    }
    procesador = Mock()

    with patch("listener.message_id_ya_procesado", return_value=False), \
         patch("listener.parse_message", side_effect=lambda texto: parseados[texto]), \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal"), \
         patch("listener.registrar_message_id_procesado"):
        asyncio.run(listener.recuperar_historial(client, 12345, limite=2, procesador=procesador))

    client.iter_messages.assert_called_once_with(12345, limit=2)
    assert procesador.call_args_list == [
        call({"type": "ENTRY", "position_id": "old"}),
        call({"type": "ENTRY", "position_id": "new"}),
    ]
    assert reconciliar_mock.call_count == 2



def test_procesar_mensaje_telegram_omite_ids_ya_procesados():
    mensaje = SimpleNamespace(id=321, text="mensaje repetido")
    procesador = Mock()

    with patch("listener.message_id_ya_procesado", return_value=True), \
         patch("listener.parse_message") as parse_message_mock, \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal") as guardar_senal_mock, \
         patch("listener.registrar_message_id_procesado") as registrar_id_mock:
        listener.procesar_mensaje_telegram(mensaje, procesador=procesador)

    parse_message_mock.assert_not_called()
    guardar_senal_mock.assert_not_called()
    registrar_id_mock.assert_not_called()
    procesador.assert_not_called()
    reconciliar_mock.assert_not_called()



def test_procesar_mensaje_telegram_registra_ids_de_mensajes_no_validos():
    mensaje = SimpleNamespace(id=456, text="texto irrelevante")
    procesador = Mock()

    with patch("listener.message_id_ya_procesado", return_value=False), \
         patch("listener.parse_message", return_value=None), \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal") as guardar_senal_mock, \
         patch("listener.registrar_message_id_procesado") as registrar_id_mock:
        listener.procesar_mensaje_telegram(mensaje, procesador=procesador)

    guardar_senal_mock.assert_not_called()
    procesador.assert_not_called()
    registrar_id_mock.assert_called_once_with(456)
    reconciliar_mock.assert_not_called()



def test_procesar_mensaje_telegram_procesa_y_guarda_senales_validas():
    mensaje = SimpleNamespace(id=789, text="entry")
    senal = {"type": "ENTRY", "position_id": "6bcb96ff"}
    procesador = Mock()

    with patch("listener.message_id_ya_procesado", return_value=False), \
         patch("listener.parse_message", return_value=senal), \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal") as guardar_senal_mock, \
         patch("listener.registrar_message_id_procesado") as registrar_id_mock:
        listener.procesar_mensaje_telegram(mensaje, procesador=procesador)

    procesador.assert_called_once_with(senal)
    guardar_senal_mock.assert_called_once_with(senal)
    registrar_id_mock.assert_called_once_with(789)
    reconciliar_mock.assert_called_once_with()



def test_procesar_mensaje_telegram_procesa_entry_reciente():
    ahora = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    mensaje = SimpleNamespace(
        id=790,
        text="entry reciente",
        date=ahora - timedelta(minutes=1),
    )
    senal = {"type": "ENTRY", "position_id": "recent"}
    procesador = Mock()

    with patch("listener.datetime") as datetime_mock, \
         patch("listener.message_id_ya_procesado", return_value=False), \
         patch("listener.parse_message", return_value=senal), \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal") as guardar_senal_mock, \
         patch("listener.registrar_message_id_procesado") as registrar_id_mock:
        datetime_mock.now.return_value = ahora
        listener.procesar_mensaje_telegram(mensaje, procesador=procesador)

    procesador.assert_called_once_with(senal)
    guardar_senal_mock.assert_called_once_with(senal)
    registrar_id_mock.assert_called_once_with(790)
    reconciliar_mock.assert_called_once_with()



def test_procesar_mensaje_telegram_descarta_entry_antigua_y_registra_id():
    ahora = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    mensaje = SimpleNamespace(
        id=791,
        text="entry antigua",
        date=ahora - timedelta(minutes=15),
    )
    senal = {"type": "ENTRY", "position_id": "stale"}
    procesador = Mock()

    with patch("listener.datetime") as datetime_mock, \
         patch("listener.message_id_ya_procesado", return_value=False), \
         patch("listener.parse_message", return_value=senal), \
         patch("listener.reconciliar_estado_en_caliente") as reconciliar_mock, \
         patch("listener.guardar_senal") as guardar_senal_mock, \
         patch("listener.registrar_message_id_procesado") as registrar_id_mock:
        datetime_mock.now.return_value = ahora
        listener.procesar_mensaje_telegram(mensaje, procesador=procesador)

    procesador.assert_not_called()
    guardar_senal_mock.assert_not_called()
    registrar_id_mock.assert_called_once_with(791)
    reconciliar_mock.assert_not_called()
