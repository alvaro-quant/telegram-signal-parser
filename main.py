# main.py
from listener import crear_client, obtener_id_canal_senales, recuperar_historial, registrar_handler_mensajes_nuevos
from state_manager import cargar_posiciones, reconciliar_estado


def main() -> None:
    """
    Inicializa el estado local, ejecuta la recuperación de historial del canal
    y luego deja corriendo el listener de mensajes nuevos.
    """
    cargar_posiciones()
    reconciliar_estado()

    client = crear_client()
    channel_id = obtener_id_canal_senales()

    client.start()
    client.loop.run_until_complete(recuperar_historial(client, channel_id))
    registrar_handler_mensajes_nuevos(client, channel_id)

    print("Escuchando mensajes nuevos... (presiona Ctrl+C para detener)")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
