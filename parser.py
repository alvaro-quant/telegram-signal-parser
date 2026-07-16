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




# --- Zona de prueba ---

texto_trailing = """📍 Trailing Stop Activated

📋 Strategy: Drawdown DCA Long

💱 BTCUSD @ 64979.21

🔒 SL: 64940.04

📈 Best: 64979.21

🆔 Position: 6bcb96ff

🕒 2026-07-14T23:45:00+00:00
"""

resultado_trailing = parse_trailing_stop(texto_trailing)

print(resultado_trailing)