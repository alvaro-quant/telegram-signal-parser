from parsers import parse_message
from storage import guardar_senal, cargar_senales
from state_manager import cargar_posiciones, reconciliar_estado
cargar_posiciones()
reconciliar_estado()

texto_entrada = """🟢 Entry Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: BUY

💱 Symbol: BTCUSD

💰 Price: 64848.64

🆔 Position: 6bcb96ff

📐 Lot: 0.02

⏱️ Analysis Timeframe: M30
"""

texto_trailing = """📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ 64979.21

🔒 SL: 64940.04

📈 Best: 64979.21

🆔 Position: 6bcb96ff

🕒 2026-07-14T23:45:00+00:00
"""

texto_salida = """🔴 Exit Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: SELL

💱 Symbol: BTCUSD

💰 Price: 64945.92

🆔 Position: 6bcb96ff

🕒 Analysis Timeframe: M30

📊 Candle: M1

🚪 Exit: atr_trailing_stop

💚 PnL: +0.15%

Position

Entry: 64848.64

High: 64987.61

Max excursion: +0.21%

Duration: 12m
"""

# Guardamos una señal de prueba, inventada, solo para probar
señal_de_prueba = {"type": "ENTRY", "symbol": "BTCUSD", "price": 65511.05}
guardar_senal(señal_de_prueba)

# Ahora cargamos y mostramos lo que quedó guardado
print(cargar_senales())