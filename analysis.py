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

MAPEO_ESTADISTICA = {
    "corners": "Corner Kicks",
    "tarjetas": "Yellow Cards",
    "tiros_puerta": "Shots on Goal",
}

MAPEO_MERCADO_ODDS = {
    "goles": {"bet_name": "Goals Over/Under", "value_busqueda": "Over 2.5"},
    "corners": {"bet_name": "Corners Over Under", "value_busqueda": "Over 9.5"},
    "tarjetas": {"bet_name": "Cards Over/Under", "value_busqueda": "Over 3.5"},
    "tiros_puerta": {"bet_name": "Total Shots on Target", "value_busqueda": "Over 7.5"},
}


def _extraer_valor_estadistica(stats_response, team_id, tipo):
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


_cache_medias_equipo = {}


def medias_equipo(team_id):
    if team_id in _cache_medias_equipo:
        return _cache_medias_equipo[team_id]

    historial = data_fetcher.historial_equipo(team_id)
    if not historial:
        _cache_medias_equipo[team_id] = None
        return None

    goles_total = 0
    acumulado = {mercado: 0.0 for mercado in MAPEO_ESTADISTICA}

    for partido in historial:
        goles = partido.get("goals", {})
        goles_total += (goles.get("home") or 0) + (goles.get("away") or 0)

        fixture_id = partido["fixture"]["id"]
        stats = data_fetcher.estadisticas_partido(fixture_id)
        if stats:
            for mercado, tipo_stat in MAPEO_ESTADISTICA.items():
                acumulado[mercado] += _extraer_valor_estadistica(stats, team_id, tipo_stat)

    n = len(historial)
    medias = {"goles": goles_total / n}
    for mercado in MAPEO_ESTADISTICA:
        medias[mercado] = acumulado[mercado] / n

    _cache_medias_equipo[team_id] = medias
    return medias


def probabilidad_implicita(cuota_decimal):
    if not cuota_decimal or cuota_decimal <= 1:
        return None
    return round((1 / cuota_decimal) * 100, 1)


def _buscar_cuota(odds_response, bet_name, value_busqueda):
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

        medias_local = medias_equipo(home["id"])
        medias_visit = medias_equipo(away["id"])

        if medias_local is None or medias_visit is None:
            continue

        media_local = medias_local[mercado]
        media_visit = medias_visit[mercado]

        expectativa = media_local + media_visit
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
