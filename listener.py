import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from parsers import parse_message
from storage import guardar_senal

load_dotenv()

api_id_texto = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

api_id = int(api_id_texto)

client = TelegramClient("signal_listener_session", api_id, api_hash)

ID_CANAL_SENALES = int(os.getenv("ID_CANAL"))


@client.on(events.NewMessage(chats=ID_CANAL_SENALES))
async def manejar_mensaje_nuevo(evento):
    texto_mensaje = evento.message.text
    resultado = parse_message(texto_mensaje)
    if resultado is None:
        print("Mensaje recibido, pero no fue reconocido como señal:")
        print(texto_mensaje)
    else:
        print("----- Señal parseada -----")
        print(resultado)
        print("---------------------------")
        guardar_senal(resultado)    

client.start()

print("Escuchando mensajes nuevos... (presiona Ctrl+C para detener)")

client.run_until_disconnected()