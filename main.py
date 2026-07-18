from parsers import parse_message

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

print(parse_message(texto_entrada))
print(parse_message(texto_trailing))
print(parse_message(texto_salida))