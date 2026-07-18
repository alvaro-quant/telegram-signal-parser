import re

def parse_entry_signal(text):
    # --- Extraer Side ---
    resultado_side = re.search(r"Side:\s*(\w+)", text)
    if resultado_side:
        side = resultado_side.group(1)
    else:
        side = None
    
    # --- Extraer Symbol ---
    resultado_symbol = re.search(r"Symbol:\s*(\w+)", text)
    if resultado_symbol:
        symbol = resultado_symbol.group(1)
    else:
        symbol = None

    # --- Extraer Price ---
    resultado_price = re.search(r"Price:\s*([\d.]+)", text)
    if resultado_price:
        price_texto = resultado_price.group(1)
        price = float(price_texto)
    else:
        price = None

    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*(\w+)", text)
    if resultado_position:
        position_id = resultado_position.group(1)
    else:
        position_id = None

    # --- Armar el diccionario final ---
    señal_procesada = {
        "type": "ENTRY",
        "side": side,
        "symbol": symbol,
        "price": price,
        "position_id": position_id
    }

    return señal_procesada

def parse_trailing_stop(text):
    # --- Extraer Symbol y Price juntos (vienen en la misma línea, separados por @) ---
    resultado_symbol_price = re.search(r"(\w+)\s*@\s*([\d.]+)", text)
    if resultado_symbol_price:
        symbol = resultado_symbol_price.group(1)
        price_texto = resultado_symbol_price.group(2)
        price = float(price_texto)
    else:
        symbol = None
        price = None

    # --- Extraer SL (stop loss) ---
    resultado_sl = re.search(r"SL:\s*([\d.]+)",text)
    if resultado_sl:
        sl_texto = resultado_sl.group(1)
        sl = float(sl_texto)
    else:
        sl = None
    
    # --- Extraer Best ---
    resultado_best = re.search(r"Best:\s*([\d.]+)",text)
    if resultado_best:
        best_texto = resultado_best.group(1)
        best = float(best_texto)
    else:
        best = None
    
    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*(\w+)",text)
    position_id = resultado_position.group(1) if resultado_position else None

    # --- Extraer Timestamp ---
    resultado_timestamp = re.search(r"(\d{4}-\d{2}-\d{2}T[\d:]+\+\d{2}:\d{2})", text)
    if resultado_timestamp:
        timestamp = resultado_timestamp.group(1)
    else:
        timestamp = None
    
    # --- Armar el diccionario final ---
    señal_procesada = {
        "type": "TRAILING_STOP",
        "symbol": symbol,
        "price": price,
        "sl": sl,
        "best": best,
        "position_id": position_id,
        "timestamp": timestamp
    }
    return señal_procesada

def parse_exit_signal(text):
    # --- Extraer Side ---
    resultado_side = re.search(r"Side:\s*(\w+)", text)
    if resultado_side:
        side = resultado_side.group(1)
    else:
        side = None
    # --- Extraer Symbol ---
    resultado_symbol = re.search(r"Symbol:\s*(\w+)", text)
    if resultado_symbol:
        symbol = resultado_symbol.group(1)
    else:
        symbol = None

    # --- Extraer Price ---
    resultado_price = re.search(r"Price:\s*([\d.]+)", text)
    if resultado_price:
        price_texto = resultado_price.group(1)
        price = float(price_texto)
    else:
        price = None

    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*(\w+)", text)
    if resultado_position:
        position_id = resultado_position.group(1)
    else:
        position_id = None

    # --- Extraer Exit reason ---
    resultado_exit = re.search(r"Exit:\s*(\w+)", text)
    if resultado_exit:
        exit_reason = resultado_exit.group(1)
    else:
        exit_reason = None

    # --- Extraer PnL (incluye signo + o -, y símbolo %) ---
    resultado_pnl = re.search(r"PnL:\s*([+-][\d.]+%)", text)
    if resultado_pnl:
        pnl = resultado_pnl.group(1)
    else:
        pnl = None

    # --- Extraer Entry price ---
    resultado_entry = re.search(r"Entry:\s*([\d.]+)", text)
    if resultado_entry:
        entry_texto = resultado_entry.group(1)
        entry_price = float(entry_texto)
    else:
        entry_price = None

    # --- Extraer High ---
    resultado_high = re.search(r"High:\s*([\d.]+)", text)
    if resultado_high:
        high_texto = resultado_high.group(1)
        high = float(high_texto)
    else:
        high = None

    # --- Extraer Duration ---
    resultado_duration = re.search(r"Duration:\s*(\w+)", text)
    if resultado_duration:
        duration = resultado_duration.group(1)
    else:
        duration = None

    # --- Armar el diccionario final ---
    señal_procesada = {
        "type": "EXIT",
        "side": side,
        "symbol": symbol,
        "price": price,
        "position_id": position_id,
        "exit_reason": exit_reason,
        "pnl": pnl,
        "entry_price": entry_price,
        "high": high,
        "duration": duration
    }

    return señal_procesada

# --- Zona de prueba ---

texto_entry = """🟢 Entry Signal
📋 Strategy: Drawdown DCA Long
🏷️ Side: BUY
💱 Symbol: BTCUSD
💰 Price: 64848.64
🆔 Position: 6bcb96ff
📐 Lot: 0.02
⏱️ Analysis Timeframe: M30
📊 Candle: M1

Confluence: 3/0
❌ 📎 ob bounce (+0)
✅ 📎 fvg fill (+2)
❌ 📎 momentum (+0)
❌ 📎 volume (+0)
✅ 📎 structure bonus (+1)

Structure
🟢 M30: bullish (trending_up, 76%)

Volatility: 🟢 normal
ATR: 249.79 (ratio 0.92, P33)
Size multiplier: 1.0x

SMC Levels
📦 OB: bullish M15 64645.73-64729.74 (0.25% away)
🔳 FVG: bullish M15 64729.74-64863.49 (0.08% away)
Active: 8 OBs, 11 FVGs

Drawdown: 48.65% from cycle high
Cycle high: 126305.73
Recovery: 10.42%
"""

texto_trailing = """📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ 64979.21

🔒 SL: 64940.04

📈 Best: 64979.21

🆔 Position: 6bcb96ff

🕒 2026-07-14T23:45:00+00:00
"""

texto_exit = """"🔴 Exit Signal
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

Structure
🟢 M30: bullish (trending_up, 76%)

Volatility: 🟢 normal
ATR: 249.79 (ratio 0.92, P33)
Size multiplier: 1.0x

SMC Levels
📦 OB: bullish M15 64645.73-64729.74 (0.45% away)
🔳 FVG: bullish M15 64729.74-64863.49 (0.28% away)
Active: 8 OBs, 11 FVGs

Drawdown: 48.57% from cycle high
Cycle high: 126305.73
Recovery: 10.57%"""

resultado_entry = parse_entry_signal(texto_entry)
resultado_trailing = parse_trailing_stop(texto_trailing)
resultado_salida = parse_exit_signal(texto_exit)
print(resultado_salida)