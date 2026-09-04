import sqlite3
from pathlib import Path

from broker_mt5 import obtener_flotante_posiciones_abiertas
from config import TELEMETRY_DB_PATH


DB_PATH = Path(TELEMETRY_DB_PATH)



def cargar_metricas(db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as conexion:
        conexion.row_factory = sqlite3.Row
        filas = conexion.execute(
            "SELECT * FROM trade_metrics ORDER BY recorded_at_utc ASC"
        ).fetchall()
    return filas



def _promedio(valores: list[float]) -> float | None:
    if not valores:
        return None
    return sum(valores) / len(valores)



def calcular_resumen(rows: list[sqlite3.Row]) -> dict[str, float | int | None]:
    total = len(rows)
    ejecutadas_rows = [
        row
        for row in rows
        if row["mt5_execution_price"] is not None and row["signal_type"] == "ENTRY"
    ]
    ejecutadas = len(ejecutadas_rows)
    rechazadas_spread = sum(1 for row in rows if row["status"] == "rejected_spread")
    cerradas = [row for row in rows if row["closed_at_utc"] is not None]
    ganadoras = [row for row in cerradas if (row["pnl_usd"] or 0) > 0]
    pnl_total = sum((row["pnl_usd"] or 0.0) for row in cerradas)
    latencias = [row["latency_seconds"] for row in rows if row["latency_seconds"] is not None]
    slippages = [
        abs(row["mt5_execution_price"] - row["telegram_price"])
        for row in ejecutadas_rows
        if row["mt5_execution_price"] is not None
        and row["telegram_price"] is not None
    ]

    win_rate = None
    if cerradas:
        win_rate = (len(ganadoras) / len(cerradas)) * 100

    return {
        "total": total,
        "ejecutadas": ejecutadas,
        "rechazadas_spread": rechazadas_spread,
        "win_rate": win_rate,
        "pnl_total": pnl_total,
        "latencia_media": _promedio(latencias),
        "slippage_medio": _promedio(slippages),
    }



def calcular_desglose_por_simbolo(rows: list[sqlite3.Row]) -> list[dict[str, float | int | str | None]]:
    simbolos = sorted({row["symbol"] for row in rows})
    desglose = []

    for symbol in simbolos:
        filas_symbol = [row for row in rows if row["symbol"] == symbol]
        ejecutadas = [
            row
            for row in filas_symbol
            if row["signal_type"] == "ENTRY" and row["mt5_execution_price"] is not None
        ]
        cerradas = [row for row in filas_symbol if row["closed_at_utc"] is not None]
        ganancia_bruta = sum((row["pnl_usd"] or 0.0) for row in cerradas if (row["pnl_usd"] or 0.0) > 0)
        perdida_bruta = sum((row["pnl_usd"] or 0.0) for row in cerradas if (row["pnl_usd"] or 0.0) < 0)
        win_rate = None
        if cerradas:
            win_rate = (sum(1 for row in cerradas if (row["pnl_usd"] or 0.0) > 0) / len(cerradas)) * 100

        if perdida_bruta == 0:
            profit_factor = None if ganancia_bruta == 0 else float("inf")
        else:
            profit_factor = ganancia_bruta / abs(perdida_bruta)

        desglose.append(
            {
                "symbol": symbol,
                "trades": len(ejecutadas),
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "pnl_neto": sum((row["pnl_usd"] or 0.0) for row in cerradas),
            }
        )

    return desglose



def _fmt_numero(valor: float | int | None, decimales: int = 2) -> str:
    if valor is None:
        return "N/A"
    if valor == float("inf"):
        return "inf"
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



def obtener_exposicion_abierta(rows: list[sqlite3.Row]) -> dict[str, object]:
    abiertas_db = [row for row in rows if row["closed_at_utc"] is None and row["signal_type"] == "ENTRY"]
    resultado_mt5 = obtener_flotante_posiciones_abiertas()

    if not resultado_mt5["exito"]:
        return {
            "mt5_disponible": False,
            "motivo": resultado_mt5["motivo"],
            "operaciones_abiertas_db": len(abiertas_db),
            "total_tickets": len(abiertas_db),
            "flotante_total_usd": None,
            "equidad_neta_estimada": None,
            "por_simbolo": {},
        }

    return {
        "mt5_disponible": True,
        "motivo": None,
        "operaciones_abiertas_db": len(abiertas_db),
        "total_tickets": resultado_mt5["total_tickets"],
        "flotante_total_usd": resultado_mt5["flotante_total_usd"],
        "equidad_neta_estimada": resultado_mt5["flotante_total_usd"],
        "por_simbolo": resultado_mt5["por_simbolo"],
    }



def generar_reporte(db_path: Path | str = DB_PATH) -> str:
    rows = cargar_metricas(db_path)
    if not rows:
        return "No hay operaciones registradas aún en telemetría."

    resumen = calcular_resumen(rows)
    desglose = calcular_desglose_por_simbolo(rows)
    exposicion = obtener_exposicion_abierta(rows)

    tabla_resumen = formatear_tabla(
        ["Métrica", "Valor"],
        [
            ["Total señales", _fmt_numero(resumen["total"], 0)],
            ["Ejecutadas", _fmt_numero(resumen["ejecutadas"], 0)],
            ["Rechazadas spread", _fmt_numero(resumen["rechazadas_spread"], 0)],
            ["Win rate %", _fmt_numero(resumen["win_rate"])],
            ["PnL total USD", _fmt_numero(resumen["pnl_total"])],
            ["Latencia media s", _fmt_numero(resumen["latencia_media"])],
            ["Slippage medio", _fmt_numero(resumen["slippage_medio"])],
        ],
    )

    tabla_exposicion = formatear_tabla(
        ["Métrica", "Valor"],
        [
            ["Operaciones abiertas DB", _fmt_numero(exposicion["operaciones_abiertas_db"], 0)],
            ["Operaciones Abiertas", _fmt_numero(exposicion["total_tickets"], 0)],
            ["Flotante USD actual", _fmt_numero(exposicion["flotante_total_usd"])],
            [
                "Equidad neta estimada",
                _fmt_numero(
                    resumen["pnl_total"] + exposicion["flotante_total_usd"]
                    if exposicion["flotante_total_usd"] is not None
                    else None
                ),
            ],
        ],
    )

    filas_simbolo = [
        [
            item["symbol"],
            _fmt_numero(item["trades"], 0),
            _fmt_numero(item["win_rate"]),
            _fmt_numero(item["profit_factor"]),
            _fmt_numero(item["pnl_neto"]),
        ]
        for item in desglose
    ]
    tabla_simbolos = formatear_tabla(
        ["Símbolo", "Trades", "Win rate %", "Profit factor", "PnL neto USD"],
        filas_simbolo,
    )

    bloques = [
        "Resumen general",
        tabla_resumen,
        "",
        "Exposición Abierta y Flotante en Vivo",
        tabla_exposicion,
    ]

    if exposicion["mt5_disponible"]:
        filas_flotante = [
            [
                symbol,
                _fmt_numero(datos["tickets"], 0),
                _fmt_numero(datos["flotante_usd"]),
            ]
            for symbol, datos in sorted(exposicion["por_simbolo"].items())
        ]
        if filas_flotante:
            bloques.extend(
                [
                    "",
                    "Flotante por símbolo",
                    formatear_tabla(["Símbolo", "Tickets", "Flotante USD"], filas_flotante),
                ]
            )
    else:
        bloques.extend(
            [
                "",
                f"MT5 no disponible: mostrando solo PnL cerrado ({exposicion['motivo']}).",
            ]
        )

    bloques.extend(
        [
            "",
            "Desglose por símbolo",
            tabla_simbolos,
        ]
    )

    return "\n".join(bloques)



def main() -> None:
    print(generar_reporte())


if __name__ == "__main__":
    main()
