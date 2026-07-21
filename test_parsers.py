from parsers import parse_entry_signal
from parsers import parse_trailing_stop
from parsers import parse_exit_signal
from parsers import parse_message


def test_parse_entry_signal_extrae_symbol_correctamente():
    texto_entrada = """🟢 Entry Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: BUY

💱 Symbol: BTCUSD

💰 Price: 64848.64

🆔 Position: 6bcb96ff

📐 Lot: 0.02
"""

    resultado = parse_entry_signal(texto_entrada)

    assert resultado["symbol"] == "BTCUSD"
    assert resultado["side"] == "BUY"
    assert resultado["price"] == 64848.64
    assert resultado["position_id"] == "6bcb96ff"


def test_parse_trailing_stop_extrae_sl_correctamente():
    texto_trailing = """📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ 64979.21

🔒 SL: 64940.04

📈 Best: 64979.21

🆔 Position: 6bcb96ff

🕒 2026-07-14T23:45:00+00:00
"""

    resultado = parse_trailing_stop(texto_trailing)

    assert resultado["sl"] == 64940.04
    assert resultado["best"] == 64979.21
    assert resultado["symbol"] == "BTCUSD"


def test_parse_exit_signal_extrae_pnl_correctamente():
    texto_salida = """🔴 Exit Signal

📋 Strategy: Drawdown DCA Long

🏷️ Side: SELL

💱 Symbol: BTCUSD

💰 Price: 64945.92

🆔 Position: 6bcb96ff

🚪 Exit: atr_trailing_stop

💚 PnL: +0.15%

Entry: 64848.64

High: 64987.61

Duration: 12m
"""

    resultado = parse_exit_signal(texto_salida)

    assert resultado["pnl"] == "+0.15%"
    assert resultado["exit_reason"] == "atr_trailing_stop"
    assert resultado["duration"] == "12m"


def test_parse_detecta_tipo_trailing_activated():
    texto_trailing = '📍 **Trailing Stop Activated**\n📋 Strategy: **Drawdown DCA Long**\n💱 BTCUSD @ `66284.21`\n🔒 SL: `66441.88`\n📈 Best: `66475.1`\n🆔 Position: `b680fdf8`\n\n🕐 2026-07-21T21:30:00+00:00'
    resultado = parse_message(texto_trailing)
    assert resultado['type'] == 'TRAILING_STOP_ACTIVATED'

def test_parse_detecta_tipo_trailing_thightened():
    texto_trailing = """📍 **Trailing Stop Tightened**\n📋 Strategy: **Bear Scalp Short**\n💱 BTCUSD @ 65334.41\n🔒 SL: 65394.14 ← 65412.8\n📈 Best: 65328.57\n🆔 Position: 1e2e54a5\n\n🕐 2026-07-20T18:43:00+00:00"""
    resultado = parse_message(texto_trailing)
    assert resultado['type'] == 'TRAILING_STOP_TIGHTENED'

def test_parse_message_detecta_tipo_entry():
    texto_entrada = "🟢 Entry Signal\n\n💱 Symbol: BTCUSD"

    resultado = parse_message(texto_entrada)

    assert resultado["type"] == "ENTRY"


def test_parse_message_con_texto_desconocido_devuelve_none():
    texto_raro = "Este mensaje no corresponde a ninguna señal conocida"

    resultado = parse_message(texto_raro)

    assert resultado is None