# config.py
#
# Configuración general del sistema. Cualquier valor que queramos poder
# ajustar fácilmente sin tocar la lógica de otros archivos, va aquí.

# Tamaño de posición fijo, en lotes. Conservador a propósito: la estrategia
# se basa en DCA (promediar entrada) y aguantar caídas, así que preferimos
# posiciones pequeñas mientras el sistema esté en fase de pruebas.
LOTE_FIJO = 0.01
MAPEO_SIMBOLOS = {
    "BTCUSD": "BTCUSDm",
}