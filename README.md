# Telegram Signal Parser

Proyecto de aprendizaje en Python con enfoque pedagógico. El objetivo final es leer
señales de trading publicadas por un bot en un grupo de Telegram, y replicar esas
operaciones en una cuenta de Exness mediante MetaTrader 5.

Este repositorio documenta el proceso paso a paso, incluyendo el aprendizaje de
Python, Git/GitHub, y MetaTrader 5 desde cero.

## Arquitectura general

```text
[Telegram Listener] -> [Message Parser] -> [Execution Engine] -> [MetaTrader 5 / Exness]
```

## Estado actual del proyecto

### Fase 1 — Parser de mensajes (completa)

Convierte el texto crudo de una señal de Telegram en un diccionario de Python con
datos estructurados.

Funciones en `parsers.py`:

- `parse_entry_signal(text)`: extrae datos de una señal de entrada (ENTRY).
- `parse_trailing_stop(text)`: extrae datos de una activación de trailing stop.
- `parse_exit_signal(text)`: extrae datos de una señal de salida (EXIT).
- `parse_message(text)`: detecta automáticamente el tipo de señal y llama a la
  función correspondiente.

11 tests con pytest, todos pasando (`test_parsers.py`).

### Fase 2 — Telegram Listener (completa)

`listener.py` se conecta a un canal específico de Telegram usando `Telethon`,
escucha mensajes nuevos en tiempo real, los pasa por `parse_message()`, y guarda
el resultado en `senales.json` mediante `storage.py`. Probado con reconexión
automática ante caídas de red.

### Fase 3 — State Manager y Execution Engine (completa)

- `state_manager.py`: mantiene un diccionario de posiciones abiertas/cerradas,
  indexado por `position_id` para búsqueda eficiente. Las posiciones cerradas se
  conservan con `status: "CLOSED"` en vez de eliminarse, para distinguir señales
  tardías de señales sobre posiciones inexistentes.
- `engine.py`: función `procesar_senal(senal)` que enruta cada señal según su tipo
  (`ENTRY`, `EXIT`, `TRAILING_STOP_*`) hacia las funciones correspondientes.
  Incluye una función placeholder de ejecución
  (`abrir_operacion_mt5_simulada`), aislada deliberadamente para poder
  reemplazarla más adelante por la integración real con MT5 sin tocar el resto
  del flujo.
- `config.py`: configuración general del proyecto, incluyendo `LOTE_FIJO`
  (tamaño de posición fijo, controlado manualmente en vez de leerse de la señal).

4 tests con pytest, todos pasando (`test_state_manager.py`).

### Exploración de MetaTrader 5 (en curso)

Antes de construir el Broker Connector real, se validó manualmente la conexión
completa entre Python y MetaTrader 5 usando una cuenta demo de Exness, en el
script exploratorio `test_mt5_connection.py`. Este script no forma parte del
pipeline productivo — es una zona de pruebas para entender la librería
`MetaTrader5` antes de integrarla en `engine.py`.

Se validó:

- Conexión explícita a la cuenta demo vía credenciales en `.env`
  (`mt5.initialize()` con `login`, `password`, `server`).
- Lectura de datos de cuenta (`mt5.account_info()`): balance, equity, moneda,
  apalancamiento.
- Verificación de símbolo operable (`mt5.symbol_info()`): en esta cuenta, el
  símbolo real es `BTCUSDm` (con sufijo), no `BTCUSD` como llega en las señales
  de Telegram — este mapeo de nombres deberá resolverse en el Broker Connector.
- Lectura de precio en tiempo real (`mt5.symbol_info_tick()`): precios `bid` y
  `ask`.
- Envío de una orden de mercado (`mt5.order_send()`), verificando el
  `retcode` de la respuesta contra `mt5.TRADE_RETCODE_DONE`.
- Cierre de una posición existente, encontrada dinámicamente con
  `mt5.positions_get()` (cerrar una posición es, técnicamente, enviar una orden
  opuesta referenciando el ticket original — no existe una función de
  "eliminar" posición).

Nota importante: para que `order_send()` funcione, es necesario tener
**AutoTrading habilitado** en la terminal MT5 (botón en la barra de herramientas
y opción en Tools → Options → Expert Advisors). Sin esto, las órdenes se
rechazan con el código `10027`.

## Cómo ejecutar el proyecto

1. Tener Python 3 instalado.
2. Clonar este repositorio.
3. Crear y activar un entorno virtual (`venv`).
4. Instalar dependencias: `pip install -r requirements.txt`.
5. Crear un archivo `.env` (no incluido en el repo) con las credenciales
   necesarias: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `MT5_LOGIN`,
   `MT5_PASSWORD`, `MT5_SERVER`.
6. Correr los tests: `pytest`.
7. Para pruebas manuales, revisar `main.py` y `test_mt5_connection.py`.

## Próximos pasos

- Construir el Broker Connector real (`broker_mt5.py`), reemplazando
  `abrir_operacion_mt5_simulada` en `engine.py` con las funciones reales de MT5
  validadas en la fase exploratoria.
- Resolver el mapeo de símbolos entre el nombre que usa el bot de Telegram
  (`BTCUSD`) y el nombre real del bróker (`BTCUSDm`).
- Definir dónde vive `mt5.initialize()` dentro del flujo del programa completo.
- Manejar casos límite de ejecución real en MT5 (fills parciales, caídas de
  conexión, rechazo de órdenes).