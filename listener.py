import os
from datetime import datetime, timezone
from typing import Any, Callable

from dotenv import load_dotenv
from telethon import TelegramClient, events

from parsers import parse_message
from config import MAX_ANTIGUEDAD_ENTRY_MINUTOS
from storage import (
    guardar_senal,
    message_id_ya_procesado,
    registrar_message_id_procesado,
)

ProcesadorSenal = Callable[[dict[str, Any]], None]


def _obtener_antiguedad_minutos(mensaje: Any) -> float:
    fecha_mensaje = getattr(mensaje, "date", None)
    if fecha_mensaje is None:
        return 0.0

    if fecha_mensaje.tzinfo is None:
        fecha_mensaje = fecha_mensaje.replace(tzinfo=timezone.utc)

    return (datetime.now(timezone.utc) - fecha_mensaje).total_seconds() / 60


def crear_client(nombre_sesion: str = "signal_listener_session") -> TelegramClient:
    """
    Crea y devuelve un cliente de Telethon usando las credenciales cargadas
    desde variables de entorno.
    """
    load_dotenv()

    api_id_texto = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id_texto or not api_hash:
        raise ValueError("Faltan TELEGRAM_API_ID o TELEGRAM_API_HASH en el entorno.")

    return TelegramClient(nombre_sesion, int(api_id_texto), api_hash)


def obtener_id_canal_senales() -> int:
    """
    Lee y valida el ID del canal de señales desde variables de entorno.
    """
    load_dotenv()

    channel_id_texto = os.getenv("ID_CANAL")
    if not channel_id_texto:
        raise ValueError("Falta ID_CANAL en el entorno.")

    return int(channel_id_texto)


def obtener_procesador_senal() -> ProcesadorSenal:
    """
    Resuelve de forma diferida el procesador real de señales para evitar
    dependencias innecesarias durante la importación del módulo.
    """
    from engine import procesar_senal

    return procesar_senal


def reconciliar_estado_en_caliente() -> None:
    """
    Ejecuta la reconciliación del estado local contra MT5 de forma diferida
    para no acoplar imports de broker/engine en import time.
    """
    from state_manager import reconciliar_estado

    reconciliar_estado()


def procesar_mensaje_telegram(
    mensaje: Any,
    procesador: ProcesadorSenal | None = None,
) -> None:
    """
    Procesa un mensaje individual de Telegram respetando la deduplicación por
    `message_id` y reutilizando el flujo común de parseo, ejecución y storage.
    """
    message_id = mensaje.id

    if message_id_ya_procesado(message_id):
        print(f"Mensaje {message_id} ya procesado. Se omite.")
        return

    texto_mensaje = getattr(mensaje, "text", "") or ""
    resultado = parse_message(texto_mensaje) if texto_mensaje else None

    if resultado is None:
        print("Mensaje recibido, pero no fue reconocido como señal:")
        print(texto_mensaje if texto_mensaje else "<sin texto>")
        registrar_message_id_procesado(message_id)
        return

    procesador_real = procesador or obtener_procesador_senal()

    print("----- Señal parseada -----")
    print(resultado)
    print("---------------------------")

    if resultado["type"] == "ENTRY":
        antiguedad_minutos = _obtener_antiguedad_minutos(mensaje)
        if antiguedad_minutos > MAX_ANTIGUEDAD_ENTRY_MINUTOS:
            print(
                f"ENTRY omitida por antigüedad: {antiguedad_minutos:.1f} minutos "
                f"(message_id={message_id})"
            )
            registrar_message_id_procesado(message_id)
            return

    procesador_real(resultado)
    guardar_senal(resultado)
    registrar_message_id_procesado(message_id)
    reconciliar_estado_en_caliente()


async def recuperar_historial(
    client: TelegramClient,
    channel_id: int,
    limite: int = 50,
    procesador: ProcesadorSenal | None = None,
) -> None:
    """
    Recupera mensajes históricos del canal y los procesa en orden cronológico
    real, del más antiguo al más nuevo.
    """
    mensajes = []
    async for mensaje in client.iter_messages(channel_id, limit=limite):
        mensajes.append(mensaje)

    for mensaje in reversed(mensajes):
        procesar_mensaje_telegram(mensaje, procesador=procesador)


def registrar_handler_mensajes_nuevos(
    client: TelegramClient,
    channel_id: int,
    procesador: ProcesadorSenal | None = None,
) -> None:
    """
    Registra el handler de mensajes nuevos para el canal indicado.
    """

    @client.on(events.NewMessage(chats=channel_id))
    async def manejar_mensaje_nuevo(evento: Any) -> None:
        procesar_mensaje_telegram(evento.message, procesador=procesador)
