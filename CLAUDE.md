# Telegram Signal Parser & MT5 Execution Bot

## Descripción del Proyecto
Bot en Python que escucha señales de trading desde un canal de Telegram vía Telethon, parsea los mensajes (ENTRY, TRAILING_STOP_ACTIVATED, TRAILING_STOP_TIGHTENED, EXIT), gestiona el estado local de posiciones y ejecuta/reconcilia órdenes en MetaTrader 5 (MT5).

## Reglas de Arquitectura Estrictas
1. **Aislamiento MT5:** Únicamente `broker_mt5.py` puede importar y comunicarse directamente con la librería `MetaTrader5`. Ningún otro módulo debe importar `MetaTrader5`.
2. **Conexión segura:** Todas las operaciones de broker y reconciliación deben pasar por `asegurar_conexion()` antes de consultar o enviar órdenes.
3. **Operaciones manuales:** El bot SOLO gestiona órdenes con el `MAGIC_NUMBER` definido en `config.py`. Las operaciones manuales (como tickets con magic 0) se deben ignorar por completo.
4. **Modo Seguro:** Cuenta demo únicamente. Prohibido ejecutar en cuentas reales.
5. **Import-Safety:** Ningún módulo productivo debe tener efectos secundarios al importarse (sin conexiones activas ni clientes escuchando a nivel raíz).
6. **Aislamiento en Tests:** Las pruebas unitarias jamás deben conectarse a Telegram en vivo ni a MT5; usar siempre `unittest.mock`, `tmp_path` o `pytest.importorskip`.

## Flujo del Pipeline Principal (`main.py`)
1. Cargar posiciones locales (`state_manager.cargar_posiciones`).
2. Reconciliar estado con el broker (`state_manager.reconciliar_estado`).
3. Inicializar cliente Telethon (`listener.crear_client`).
4. Recuperar historial en orden cronológico real (`listener.recuperar_historial`).
5. Iniciar escucha de eventos en vivo (`listener.registrar_handler_mensajes_nuevos`).

## Comandos de Prueba y Entorno
- Activar entorno virtual: `source venv/Scripts/activate` (Git Bash) o `.\venv\Scripts\Activate.ps1` (PowerShell)
- Ejecutar suite completa: `pytest`
- Ejecutar suites individuales:
  - `pytest test_parsers.py`
  - `pytest test_storage.py`
  - `pytest test_state_manager.py`
  - `pytest test_listener.py`
  - `pytest test_mt5_connection.py` (requiere credenciales y MT5 abierto)

## Convenciones de Código
- Tipado estricto con Type Hints en todas las funciones.
- Docstrings descriptivos en formato estándar de Python.
- Manejo explícito de errores con try/except y logging claro.
- No dejar credenciales ni variables de entorno escritas en el código.