import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from config import LOTE_FIJO, TELEMETRY_DB_PATH

DB_PATH = Path(TELEMETRY_DB_PATH)
DURACION_BUCKETS = [
    ("0-2 min", 0.0, 120.0),
    ("2-5 min", 120.0, 300.0),
    ("5-15 min", 300.0, 900.0),
    (">15 min", 900.0, None),
]


def cargar_operaciones(db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as conexion:
        conexion.row_factory = sqlite3.Row
        filas = conexion.execute(
            """
            SELECT *
            FROM trade_metrics
            WHERE signal_type = ?
            ORDER BY recorded_at_utc ASC
            """,
            ("ENTRY",),
        ).fetchall()
    return filas


def _valor(row: Mapping[str, Any] | sqlite3.Row, clave: str) -> Any:
    return row[clave]


def _float_o_none(valor: Any) -> float | None:
    if valor is None:
        return None
    return float(valor)


def _promedio(valores: Sequence[float]) -> float | None:
    if not valores:
        return None
    return sum(valores) / len(valores)


def _win_rate(pnls: Sequence[float]) -> float | None:
    if not pnls:
        return None
    ganadoras = sum(1 for pnl in pnls if pnl > 0)
    return (ganadoras / len(pnls)) * 100


def _parse_datetime_utc(valor: str) -> datetime:
    fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def _bucket_duracion(duration_seconds: float) -> str | None:
    for nombre, minimo, maximo in DURACION_BUCKETS:
        if duration_seconds >= minimo and (maximo is None or duration_seconds < maximo):
            return nombre
    return None


def _operaciones_cerradas(rows: Sequence[Mapping[str, Any] | sqlite3.Row]) -> list[Mapping[str, Any] | sqlite3.Row]:
    return [
        row
        for row in rows
        if _valor(row, "closed_at_utc") is not None and _valor(row, "pnl_usd") is not None
    ]


def calcular_rentabilidad_por_duracion(
    rows: Sequence[Mapping[str, Any] | sqlite3.Row],
) -> list[dict[str, float | int | str | None]]:
    grupos: dict[str, list[float]] = {nombre: [] for nombre, _, _ in DURACION_BUCKETS}

    for row in _operaciones_cerradas(rows):
        duracion = _float_o_none(_valor(row, "duration_seconds"))
        pnl = _float_o_none(_valor(row, "pnl_usd"))
        if duracion is None or pnl is None:
            continue
        bucket = _bucket_duracion(duracion)
        if bucket is None:
            continue
        grupos[bucket].append(pnl)

    return [
        {
            "duracion": nombre,
            "trades": len(pnls),
            "win_rate": _win_rate(pnls),
            "pnl_medio": _promedio(pnls),
            "pnl_total": sum(pnls),
        }
        for nombre, _, _ in DURACION_BUCKETS
        for pnls in [grupos[nombre]]
    ]


def calcular_rendimiento_por_hora(
    rows: Sequence[Mapping[str, Any] | sqlite3.Row],
) -> list[dict[str, float | int | str | None]]:
    grupos: dict[int, list[float]] = {}

    for row in _operaciones_cerradas(rows):
        recorded_at = _valor(row, "recorded_at_utc")
        pnl = _float_o_none(_valor(row, "pnl_usd"))
        if recorded_at is None or pnl is None:
            continue
        hora = _parse_datetime_utc(str(recorded_at)).hour
        grupos.setdefault(hora, []).append(pnl)

    resultado = []
    for hora in sorted(grupos):
        pnls = grupos[hora]
        resultado.append(
            {
                "hora_utc": f"{hora:02d}:00",
                "trades": len(pnls),
                "ganadoras": sum(1 for pnl in pnls if pnl > 0),
                "perdedoras": sum(1 for pnl in pnls if pnl < 0),
                "win_rate": _win_rate(pnls),
                "pnl_total": sum(pnls),
                "pnl_medio": _promedio(pnls),
            }
        )
    return resultado


def _slippage_adverso(row: Mapping[str, Any] | sqlite3.Row) -> float | None:
    telegram_price = _float_o_none(_valor(row, "telegram_price"))
    mt5_price = _float_o_none(_valor(row, "mt5_execution_price"))
    side = _valor(row, "side")
    if telegram_price is None or mt5_price is None or side is None:
        return None

    side_normalizado = str(side).upper()
    if side_normalizado == "BUY":
        return mt5_price - telegram_price
    if side_normalizado == "SELL":
        return telegram_price - mt5_price
    return None


def calcular_slippage_por_simbolo(
    rows: Sequence[Mapping[str, Any] | sqlite3.Row],
) -> list[dict[str, float | int | str | None]]:
    grupos: dict[str, dict[str, list[float]]] = {}

    for row in rows:
        telegram_price = _float_o_none(_valor(row, "telegram_price"))
        mt5_price = _float_o_none(_valor(row, "mt5_execution_price"))
        if telegram_price is None or mt5_price is None:
            continue

        symbol = str(_valor(row, "symbol"))
        latencia = _float_o_none(_valor(row, "latency_seconds"))
        slippage = mt5_price - telegram_price
        adverso = _slippage_adverso(row)
        grupos.setdefault(symbol, {"slippage": [], "adverso": [], "latencia": []})
        grupos[symbol]["slippage"].append(slippage)
        if adverso is not None:
            grupos[symbol]["adverso"].append(adverso)
        if latencia is not None:
            grupos[symbol]["latencia"].append(latencia)

    resultado = []
    for symbol in sorted(grupos):
        datos = grupos[symbol]
        adversos = datos["adverso"]
        resultado.append(
            {
                "symbol": symbol,
                "trades": len(datos["slippage"]),
                "slippage_medio": _promedio(datos["slippage"]),
                "slippage_abs_medio": _promedio([abs(valor) for valor in datos["slippage"]]),
                "slippage_adverso_medio": _promedio(adversos),
                "peor_slippage_adverso": max(adversos) if adversos else None,
                "impacto_usd_estimado_lote_fijo": (_promedio(adversos) or 0.0) * LOTE_FIJO if adversos else None,
                "latencia_media": _promedio(datos["latencia"]),
            }
        )
    return resultado


def diagnosticar_inventario_abierto(
    rows: Sequence[Mapping[str, Any] | sqlite3.Row],
    precios_actuales: Mapping[int, Mapping[str, Any]] | None = None,
    ahora: datetime | None = None,
) -> list[dict[str, float | int | str | None]]:
    ahora_utc = ahora or datetime.now(timezone.utc)
    abiertas = [
        row
        for row in rows
        if _valor(row, "symbol") == "BTCUSDm"
        and _valor(row, "closed_at_utc") is None
        and _valor(row, "mt5_ticket") is not None
    ]
    abiertas_ordenadas = sorted(abiertas, key=lambda row: str(_valor(row, "recorded_at_utc")))[:8]

    resultado = []
    for row in abiertas_ordenadas:
        ticket = int(_valor(row, "mt5_ticket"))
        entrada = _float_o_none(_valor(row, "mt5_execution_price"))
        recorded_at_text = str(_valor(row, "recorded_at_utc"))
        recorded_at = _parse_datetime_utc(recorded_at_text)
        precio_actual = None
        if precios_actuales is not None and ticket in precios_actuales:
            precio_actual = _float_o_none(precios_actuales[ticket].get("precio_actual"))

        distancia = None
        distancia_pct = None
        if entrada is not None and precio_actual is not None:
            distancia = precio_actual - entrada
            if entrada != 0:
                distancia_pct = (distancia / entrada) * 100

        resultado.append(
            {
                "ticket": ticket,
                "entrada": entrada,
                "abierto_desde": recorded_at_text,
                "edad_min": (ahora_utc - recorded_at).total_seconds() / 60,
                "precio_actual": precio_actual,
                "distancia": distancia,
                "distancia_pct": distancia_pct,
            }
        )
    return resultado


def obtener_precios_actuales_para_inventario(rows: Sequence[Mapping[str, Any] | sqlite3.Row]) -> tuple[dict[int, Mapping[str, Any]] | None, str | None]:
    tickets = [
        int(_valor(row, "mt5_ticket"))
        for row in rows
        if _valor(row, "symbol") == "BTCUSDm"
        and _valor(row, "closed_at_utc") is None
        and _valor(row, "mt5_ticket") is not None
    ][:8]
    if not tickets:
        return {}, None

    from broker_mt5 import obtener_precios_actuales_tickets_bot

    resultado = obtener_precios_actuales_tickets_bot(tickets)
    if not resultado["exito"]:
        return None, resultado["motivo"]
    return resultado["precios"], None


def _fmt_numero(valor: float | int | None, decimales: int = 2) -> str:
    if valor is None:
        return "N/A"
    if isinstance(valor, int):
        return str(valor)
    return f"{valor:.{decimales}f}"


def formatear_tabla(headers: list[str], rows: list[list[str]]) -> str:
    anchos = [len(header) for header in headers]
    for fila in rows:
        for indice, celda in enumerate(fila):
            anchos[indice] = max(anchos[indice], len(celda))

    encabezado = " | ".join(header.ljust(anchos[i]) for i, header in enumerate(headers))
    separador = "-+-".join("-" * ancho for ancho in anchos)
    cuerpo = [" | ".join(celda.ljust(anchos[i]) for i, celda in enumerate(fila)) for fila in rows]
    return "\n".join([encabezado, separador, *cuerpo])


def generar_reporte_cuantitativo(db_path: Path | str = DB_PATH) -> str:
    rows = cargar_operaciones(db_path)
    if not rows:
        return "No hay operaciones ENTRY registradas aún en telemetría."

    precios_actuales, motivo_precios = obtener_precios_actuales_para_inventario(rows)
    rentabilidad = calcular_rentabilidad_por_duracion(rows)
    horas = calcular_rendimiento_por_hora(rows)
    slippage = calcular_slippage_por_simbolo(rows)
    inventario = diagnosticar_inventario_abierto(rows, precios_actuales)

    bloques = [
        "Análisis cuantitativo avanzado",
        "",
        "Rentabilidad por duración",
        formatear_tabla(
            ["Duración", "Trades", "Win Rate %", "PnL medio USD", "PnL total USD"],
            [
                [
                    str(item["duracion"]),
                    _fmt_numero(item["trades"], 0),
                    _fmt_numero(item["win_rate"]),
                    _fmt_numero(item["pnl_medio"]),
                    _fmt_numero(item["pnl_total"]),
                ]
                for item in rentabilidad
            ],
        ),
        "",
        "Rendimiento por hora UTC",
        formatear_tabla(
            ["Hora UTC", "Trades", "Ganadoras", "Perdedoras", "Win Rate %", "PnL total USD", "PnL medio USD"],
            [
                [
                    str(item["hora_utc"]),
                    _fmt_numero(item["trades"], 0),
                    _fmt_numero(item["ganadoras"], 0),
                    _fmt_numero(item["perdedoras"], 0),
                    _fmt_numero(item["win_rate"]),
                    _fmt_numero(item["pnl_total"]),
                    _fmt_numero(item["pnl_medio"]),
                ]
                for item in horas
            ],
        ),
        "",
        "Slippage real vs teórico por símbolo",
        formatear_tabla(
            [
                "Símbolo",
                "Trades",
                "Slippage medio",
                "Abs medio",
                "Adverso medio",
                "Peor adverso",
                "Impacto USD est.",
                "Latencia media s",
            ],
            [
                [
                    str(item["symbol"]),
                    _fmt_numero(item["trades"], 0),
                    _fmt_numero(item["slippage_medio"], 5),
                    _fmt_numero(item["slippage_abs_medio"], 5),
                    _fmt_numero(item["slippage_adverso_medio"], 5),
                    _fmt_numero(item["peor_slippage_adverso"], 5),
                    _fmt_numero(item["impacto_usd_estimado_lote_fijo"], 5),
                    _fmt_numero(item["latencia_media"]),
                ]
                for item in slippage
            ],
        ),
        "Impacto USD est. usa LOTE_FIJO porque trade_metrics no guarda volumen ni valor de tick histórico.",
        "",
        "Inventario abierto BTCUSDm",
    ]

    if motivo_precios is not None:
        bloques.append(f"MT5 no disponible para precio actual: {motivo_precios}")

    bloques.append(
        formatear_tabla(
            ["Ticket", "Entrada", "Abierto desde", "Edad min", "Precio actual", "Distancia", "Distancia %"],
            [
                [
                    _fmt_numero(item["ticket"], 0),
                    _fmt_numero(item["entrada"], 5),
                    str(item["abierto_desde"]),
                    _fmt_numero(item["edad_min"]),
                    _fmt_numero(item["precio_actual"], 5),
                    _fmt_numero(item["distancia"], 5),
                    _fmt_numero(item["distancia_pct"], 5),
                ]
                for item in inventario
            ],
        )
    )

    return "\n".join(bloques)


def main() -> None:
    print(generar_reporte_cuantitativo())


if __name__ == "__main__":
    main()
