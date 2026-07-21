import re

def parse_entry_signal(text):
    # --- Extraer Side ---
    resultado_side = re.search(r"Side:\s*[`*]*(\w+)", text)
    if resultado_side:
        side = resultado_side.group(1)
    else:
        side = None
    
    # --- Extraer Symbol ---
    resultado_symbol = re.search(r"Symbol:\s*[`*]*(\w+)", text)
    if resultado_symbol:
        symbol = resultado_symbol.group(1)
    else:
        symbol = None

    # --- Extraer Price ---
    resultado_price = re.search(r"Price:\s*[`*]*([\d.]+)", text)
    if resultado_price:
        price_texto = resultado_price.group(1)
        price = float(price_texto)
    else:
        price = None

    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*[`*]*(\w+)", text)
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

def parse_trailing_stop(text, tipo="TRAILING_STOP_ACTIVATED"):
    # --- Extraer Symbol y Price juntos (vienen en la misma línea, separados por @) ---
    resultado_symbol_price = re.search(r"(\w+)\s*@\s*[`*]*([\d.]+)", text)
    if resultado_symbol_price:
        symbol = resultado_symbol_price.group(1)
        price_texto = resultado_symbol_price.group(2)
        price = float(price_texto)
    else:
        symbol = None
        price = None

    # --- Extraer SL (stop loss) ---
    resultado_sl = re.search(r"SL:\s*[`*]*([\d.]+)",text)
    if resultado_sl:
        sl_texto = resultado_sl.group(1)
        sl = float(sl_texto)
    else:
        sl = None
    
    # --- Extraer Best ---
    resultado_best = re.search(r"Best:\s*[`*]*([\d.]+)",text)
    if resultado_best:
        best_texto = resultado_best.group(1)
        best = float(best_texto)
    else:
        best = None
    
    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*[`*]*(\w+)",text)
    position_id = resultado_position.group(1) if resultado_position else None

    # --- Extraer Timestamp ---
    resultado_timestamp = re.search(r"(\d{4}-\d{2}-\d{2}T[\d:]+\+\d{2}:\d{2})", text)
    if resultado_timestamp:
        timestamp = resultado_timestamp.group(1)
    else:
        timestamp = None
    
    # --- Armar el diccionario final ---
    señal_procesada = {
        "type": tipo,
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
    resultado_side = re.search(r"Side:\s*[`*]*(\w+)", text)
    if resultado_side:
        side = resultado_side.group(1)
    else:
        side = None
    # --- Extraer Symbol ---
    resultado_symbol = re.search(r"Symbol:\s*[`*]*(\w+)", text)
    if resultado_symbol:
        symbol = resultado_symbol.group(1)
    else:
        symbol = None

    # --- Extraer Price ---
    resultado_price = re.search(r"Price:\s*[`*]*([\d.]+)", text)
    if resultado_price:
        price_texto = resultado_price.group(1)
        price = float(price_texto)
    else:
        price = None

    # --- Extraer Position ---
    resultado_position = re.search(r"Position:\s*[`*]*(\w+)", text)
    if resultado_position:
        position_id = resultado_position.group(1)
    else:
        position_id = None

    # --- Extraer Exit reason ---
    resultado_exit = re.search(r"Exit:\s*[`*]*(\w+)", text)
    if resultado_exit:
        exit_reason = resultado_exit.group(1)
    else:
        exit_reason = None

    # --- Extraer PnL (incluye signo + o -, y símbolo %) ---
    resultado_pnl = re.search(r"PnL:\s*[`*]*([+-][\d.]+%)", text)
    if resultado_pnl:
        pnl = resultado_pnl.group(1)
    else:
        pnl = None

    # --- Extraer Entry price ---
    resultado_entry = re.search(r"Entry:\s*[`*]*([\d.]+)", text)
    if resultado_entry:
        entry_texto = resultado_entry.group(1)
        entry_price = float(entry_texto)
    else:
        entry_price = None

    # --- Extraer High ---
    resultado_high = re.search(r"High:\s*[`*]*([\d.]+)", text)
    if resultado_high:
        high_texto = resultado_high.group(1)
        high = float(high_texto)
    else:
        high = None

    # --- Extraer Duration ---
    resultado_duration = re.search(r"Duration:\s*[`*]*(\w+)", text)
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

def parse_message(text):
    # Buscamos pistas unicas para identificar el tipo de se;al
    if "Entry Signal" in text:
        tipo_detectado = "ENTRY"
    elif "Trailing Stop Activated" in text:
        tipo_detectado = "TRAILING_STOP_ACTIVATED"
    elif "Trailing Stop Tightened" in text:
        tipo_detectado = "TRAILING_STOP_TIGHTENED"
    elif "Exit Signal" in text:
        tipo_detectado = "EXIT"
    else:
        tipo_detectado = None

    # Segun tipo detectado llamamos a la funcion correcta
    if tipo_detectado == "ENTRY":
        resultado = parse_entry_signal(text)
    elif tipo_detectado == "TRAILING_STOP_ACTIVATED":
        resultado = parse_trailing_stop(text)
    elif tipo_detectado == "TRAILING_STOP_TIGHTENED":
        resultado = parse_trailing_stop(text, tipo = "TRAILING_STOP_TIGHTENED")
    elif tipo_detectado == "EXIT":
        resultado = parse_exit_signal(text)
    else:
        resultado = None

    return resultado