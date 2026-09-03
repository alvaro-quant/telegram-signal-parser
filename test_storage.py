# test_storage.py

import json

import pytest

import storage


@pytest.fixture(autouse=True)
def configurar_storage_temporal(tmp_path):
    nombre_archivo_original = storage.NOMBRE_ARCHIVO
    nombre_archivo_ids_original = storage.NOMBRE_ARCHIVO_IDS_PROCESADOS

    storage.NOMBRE_ARCHIVO = str(tmp_path / "senales.json")
    storage.NOMBRE_ARCHIVO_IDS_PROCESADOS = str(tmp_path / "message_ids_procesados.json")
    storage.message_ids_procesados.clear()

    yield

    storage.NOMBRE_ARCHIVO = nombre_archivo_original
    storage.NOMBRE_ARCHIVO_IDS_PROCESADOS = nombre_archivo_ids_original
    storage.message_ids_procesados.clear()



def test_registrar_message_id_procesado_guarda_ids_nuevos():
    resultado = storage.registrar_message_id_procesado(123456)

    assert resultado is True
    assert storage.message_id_ya_procesado(123456) is True

    with open(storage.NOMBRE_ARCHIVO_IDS_PROCESADOS, "r", encoding="utf-8") as archivo:
        ids_guardados = json.load(archivo)

    assert ids_guardados == [123456]



def test_registrar_message_id_procesado_detecta_duplicados():
    primer_registro = storage.registrar_message_id_procesado(987654)
    segundo_registro = storage.registrar_message_id_procesado(987654)

    assert primer_registro is True
    assert segundo_registro is False

    with open(storage.NOMBRE_ARCHIVO_IDS_PROCESADOS, "r", encoding="utf-8") as archivo:
        ids_guardados = json.load(archivo)

    assert ids_guardados == [987654]



def test_cargar_message_ids_procesados_recupera_ids_persistidos():
    storage.registrar_message_id_procesado(111)
    storage.registrar_message_id_procesado(222)

    storage.message_ids_procesados.clear()

    assert storage.message_id_ya_procesado(111) is False
    assert storage.message_id_ya_procesado(222) is False

    ids_cargados = storage.cargar_message_ids_procesados()

    assert ids_cargados == {111, 222}
    assert storage.message_id_ya_procesado(111) is True
    assert storage.message_id_ya_procesado(222) is True
