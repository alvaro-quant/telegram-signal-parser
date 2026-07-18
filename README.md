# Telegram Signal Parser

Proyecto de aprendizaje en Python con enfoque pedagógico. El objetivo final es leer señales de trading publicadas por un bot en un grupo de Telegram, y eventualmente replicar esas operaciones en una cuenta de Exness mediante MetaTrader 5.

Este repositorio documenta el proceso paso a paso, incluyendo el aprendizaje de Python y de Git/GitHub desde cero.

## Arquitectura general (visión a futuro)

```text
[Telegram Listener] -> [Message Parser] -> [Execution Engine] -> [MetaTrader 5 / Exness]
```

## Estado actual del proyecto: Fase 1 completa

La Fase 1 se enfoca únicamente en el **parsing de mensajes**: convertir el texto crudo de una señal de Telegram en un diccionario de Python con datos estructurados. No hay conexión real a Telegram ni a MetaTrader todavía.

### Funciones implementadas en `parser.py`

- `parse_entry_signal(text)`: extrae datos de una señal de entrada (ENTRY).
- `parse_trailing_stop(text)`: extrae datos de una activación de trailing stop.
- `parse_exit_signal(text)`: extrae datos de una señal de salida (EXIT).
- `parse_message(text)`: detecta automáticamente el tipo de señal y llama a la función correspondiente.

### Ejemplo de uso

```python
resultado = parse_message(texto_de_una_señal)
print(resultado)
```

## Cómo ejecutar el proyecto

1. Tener Python 3 instalado.
2. Clonar este repositorio.
3. Ejecutar `python parser.py` para correr la zona de pruebas incluida en el archivo.

## Próximos pasos

- Organizar el código en varios archivos (separar funciones de parsing de la zona de pruebas).
- Escribir pruebas (tests) más formales.
- Conectar con Telegram (fase futura, usando `Telethon`).
- Conectar con MetaTrader 5 / Exness (fase futura).

## Advertencia

Este proyecto es únicamente un ejercicio de programación y aprendizaje. No opera dinero real. Cualquier fase futura de ejecución de operaciones debe probarse primero en una cuenta demo.