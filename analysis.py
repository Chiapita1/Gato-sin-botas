"""
Aquí está la lógica "inteligente" del bot. Importante leer esto:

NO calculamos una probabilidad de acierto real. Eso no existe de forma
fiable. Lo que hacemos es:

  1. Calcular la media reciente de un equipo en un mercado (p.ej. córners)
  2. Convertir la cuota que ofrece la casa de apuestas en una probabilidad
     implícita (fórmula estándar: prob = 1 / cuota)
  3. Avisar solo cuando la estadística reciente se aleja MUCHO de lo que
     la cuota está asumiendo (posible descuadre de precio, no garantía)

Esto es una herramienta de cribado, no un oráculo.
"""

import config
import data_fetcher

# Nombres de estadística tal como los devuelve API-Football en
# /fixtures/statistics -> cada partido tiene una lista de {"type": ..., "value": ...}
MAPEO_ESTADISTICA = {
    "corners": "Corner Kicks",
    "tarjetas": "Yellow Cards",
    "tiros_puerta": "Shots on Goal",
