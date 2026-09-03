# storage.py
import json
import os
from typing import Any

NOMBRE_ARCHIVO = "senales.json"
NOMBRE_ARCHIVO_IDS_PROCESADOS = "message_ids_procesados.json"

message_ids_procesados: set[int] = set()


def cargar_senales() -> list[dict[str, Any]]:
    """
    Lee senales.json desde disco y devuelve la lista completa de señales.
    Si el archivo todavía no existe, devuelve una lista vacía.
    """
    if not os.path.exists(NOMBRE_ARCHIVO):
        return []

    with open(NOMBRE_ARCHIVO, "r", encoding="utf-8") as archivo:
        lista_senales: list[dict[str, Any]] = json.load(archivo)
    return lista_senales


def guardar_senal(senal: dict[str, Any]) -> None:
    """
    Agrega una nueva señal al archivo local senales.json y lo sobrescribe
    completo con el contenido actualizado.
    """
    lista_senales = cargar_senales()
    lista_senales.append(senal)

    with open(NOMBRE_ARCHIVO, "w", encoding="utf-8") as archivo:
        json.dump(lista_senales, archivo, indent=4)



def cargar_message_ids_procesados() -> set[int]:
    """
    Lee desde disco el archivo de IDs de mensajes procesados y reemplaza el
    contenido del set global `message_ids_procesados`.

    Si el archivo no existe todavía, deja el set vacío.
    """
    global message_ids_procesados

    if not os.path.exists(NOMBRE_ARCHIVO_IDS_PROCESADOS):
        message_ids_procesados = set()
        return message_ids_procesados

    with open(NOMBRE_ARCHIVO_IDS_PROCESADOS, "r", encoding="utf-8") as archivo:
        ids_guardados: list[int] = json.load(archivo)

    message_ids_procesados = set(ids_guardados)
    return message_ids_procesados



def guardar_message_ids_procesados() -> None:
    """
    Vuelca el set global `message_ids_procesados` completo a disco en formato
    JSON, sobrescribiendo el contenido anterior.
    """
    with open(NOMBRE_ARCHIVO_IDS_PROCESADOS, "w", encoding="utf-8") as archivo:
        json.dump(sorted(message_ids_procesados), archivo, indent=4)



def message_id_ya_procesado(message_id: int) -> bool:
    """
    Indica si un `message_id` de Telegram ya fue registrado previamente en el
    set cargado en memoria.
    """
    return message_id in message_ids_procesados



def registrar_message_id_procesado(message_id: int) -> bool:
    """
    Registra un `message_id` nuevo en memoria y en disco.

    Devuelve True si el ID era nuevo y False si ya había sido procesado antes.
    """
    if message_id_ya_procesado(message_id):
        return False

    message_ids_procesados.add(message_id)
    guardar_message_ids_procesados()
    return True


cargar_message_ids_procesados()
