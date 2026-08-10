# storage.py
import json
import os

NOMBRE_ARCHIVO = "senales.json"

def cargar_senales():
    if not os.path.exists(NOMBRE_ARCHIVO):
        return []

    with open(NOMBRE_ARCHIVO, "r") as archivo:
        lista_senales = json.load(archivo)
    return lista_senales

def guardar_senal(senal):
    lista_senales = cargar_senales()
    lista_senales.append(senal)

    with open(NOMBRE_ARCHIVO, "w") as archivo:
        json.dump(lista_senales, archivo, indent=4)