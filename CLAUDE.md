# Telegram Signal Parser & MT5 Execution Bot

## Descripción del Proyecto
Bot en Python que escucha señales de trading desde un canal de Telegram vía Telethon, parsea los mensajes (ENTRY, TRAILING_STOP_ACTIVATED, TRAILING_STOP_TIGHTENED, EXIT), gestiona el estado local de posiciones y ejecuta/reconcilia órdenes en MetaTrader 5 (MT5).

## Reglas de Arquitectura Estrictas
1. **Aislamiento MT5:** Únicamente `broker_mt5.py` puede importar y comunicarse directamente con la librería `MetaTrader5`. Ningún otro módulo debe importar `MetaTrader5`.
2. **Conexión segura:** Todas las operaciones de broker y reconciliación deben pasar por `asegurar_conexion()` antes de consultar o enviar órdenes.
3. **Operaciones manuales:** El bot SOLO gestiona órdenes con el `MAGIC_NUMBER` definido en `config.py`. Las operaciones manuales (como tickets con magic 0) se deben ignorar por completo.
4. **Modo Seguro:** Cuenta demo únicamente. Prohibido ejecutar en cuentas reales.

## Comandos de Prueba y Entorno
- Activar entorno virtual: `source venv/Scripts/activate` (Git Bash) o `.\venv\Scripts\Activate.ps1` (PowerShell)
- Ejecutar suite de pruebas: `pytest`
- Ejecutar prueba individual: `pytest test_state_manager.py`

## Convenciones de Código
- Tipado estricto con Type Hints en todas las funciones.
- Docstrings descriptivos en formato estándar de Python.
- Manejo explícito de errores con try/except y logging claro.
- No dejar credenciales ni variables de entorno escritas en el código.