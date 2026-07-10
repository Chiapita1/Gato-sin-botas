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
}

# Nombres de mercado tal como aparecen en /odds (bet -> name), y el "value"
# que nos interesa dentro de ese mercado. Estos nombres pueden variar según
# la casa de apuestas que use la API; revisa la respuesta real y ajusta si hace falta.
MAPEO_MERCADO_ODDS = {
    "goles": {"bet_name": "Goals Over/Under", "value_busqueda": "Over 2.5"},
    "corners": {"bet_name": "Corners Over Under", "value_busqueda": "Over 9.5"},
    "tarjetas": {"bet_name": "Cards Over/Under", "value_busqueda": "Over 3.5"},
    "tiros_puerta": {"bet_name": "Total Shots on Target", "value_busqueda": "Over 7.5"},
}


def _extraer_valor_estadistica(stats_response, team_id, tipo):
    """Busca el valor numérico de un tipo de estadística para un equipo dado."""
    for bloque in stats_response:
        if bloque.get("team", {}).get("id") == team_id:
            for item in bloque.get("statistics", []):
                if item.get("type") == tipo:
                    valor = item.get("value")
                    if valor is None:
                        return 0
                    if isinstance(valor, str) and valor.endswith("%"):
                        valor = valor.replace("%", "")
                    try:
                        return float(valor)
                    except (TypeError, ValueError):
                        return 0
    return 0


def media_equipo_mercado(team_id, mercado):
    """Media del equipo en las últimas N partidos para un mercado dado (excepto goles)."""
    tipo_stat = MAPEO_ESTADISTICA.get(mercado)
    if not tipo_stat:
        return None

    historial = data_fetcher.historial_equipo(team_id)
    if not historial:
        return None

    valores = []
    for partido in historial:
        fixture_id = partido["fixture"]["id"]
        stats = data_fetcher.estadisticas_partido(fixture_id)
        if stats:
            valores.append(_extraer_valor_estadistica(stats, team_id, tipo_stat))

    if not valores:
        return None
    return sum(valores) / len(valores)


def media_goles_equipo(team_id):
    """Para goles usamos el historial directo (goles marcados + encajados)."""
    historial = data_fetcher.historial_equipo(team_id)
    if not historial:
        return None
    total = 0
    for partido in historial:
        goles = partido.get("goals", {})
        local_id = partido["teams"]["home"]["id"]
        if local_id == team_id:
            total += (goles.get("home") or 0) + (goles.get("away") or 0)
        else:
            total += (goles.get("home") or 0) + (goles.get("away") or 0)
    return total / len(historial)


def probabilidad_implicita(cuota_decimal):
    """Convierte una cuota decimal (ej. 1.80) en probabilidad implícita (%)."""
    if not cuota_decimal or cuota_decimal <= 1:
        return None
    return round((1 / cuota_decimal) * 100, 1)


def _buscar_cuota(odds_response, bet_name, value_busqueda):
    """Recorre la respuesta de /odds buscando la cuota de un mercado y valor concretos."""
    for bookmaker_block in odds_response:
        for bookmaker in bookmaker_block.get("bookmakers", []):
            for bet in bookmaker.get("bets", []):
                if bet.get("name") == bet_name:
                    for valor in bet.get("values", []):
                        if valor.get("value") == value_busqueda:
                            try:
                                return float(valor.get("odd"))
                            except (TypeError, ValueError):
                                continue
    return None


def analizar_partido(fixture):
    """
    Devuelve una lista de "hallazgos" (dicts) para un partido, uno por mercado
    donde la diferencia entre estadística y cuota supera el umbral configurado.
    """
    fixture_id = fixture["fixture"]["id"]
    home = fixture["teams"]["home"]
    away = fixture["teams"]["away"]

    odds = data_fetcher.cuotas_partido(fixture_id)
    hallazgos = []

    for mercado in config.MERCADOS:
        info_odds = MAPEO_MERCADO_ODDS.get(mercado)
        if not info_odds:
            continue

        cuota = _buscar_cuota(odds, info_odds["bet_name"], info_odds["value_busqueda"])
        prob_implicita = probabilidad_implicita(cuota)
        if prob_implicita is None:
            continue

        if mercado == "goles":
            media_local = media_goles_equipo(home["id"])
            media_visit = media_goles_equipo(away["id"])
        else:
            media_local = media_equipo_mercado(home["id"], mercado)
            media_visit = media_equipo_mercado(away["id"], mercado)

        if media_local is None or media_visit is None:
            continue

        # Estimación simple: media conjunta de ambos equipos como "expectativa"
        expectativa = media_local + media_visit

        # Traducimos la expectativa a una probabilidad estimada muy simplificada:
        # cuanto más por encima esté la expectativa de la línea de la cuota,
        # más alta consideramos la probabilidad estadística (heurística, no un modelo real)
        prob_estadistica = min(95, max(5, 50 + (expectativa - 2.5) * 8))

        diferencia = prob_estadistica - prob_implicita

        if diferencia >= config.UMBRAL_DIFERENCIA_PP:
            hallazgos.append({
                "mercado": mercado,
                "seleccion": info_odds["value_busqueda"],
                "cuota": cuota,
                "prob_implicita": prob_implicita,
                "prob_estadistica": round(prob_estadistica, 1),
                "diferencia_pp": round(diferencia, 1),
            })

    return hallazgos
