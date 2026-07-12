"""
Aquí está la lógica "inteligente" del bot. Importante leer esto:

NO calculamos una probabilidad de acierto real garantizada. Eso no existe de
forma fiable. Lo que hacemos es un modelo estadístico razonable:

  1. Calcular la media reciente de un equipo en un mercado, dando más peso
     a los partidos más recientes y a si jugó en casa o fuera (según el
     contexto del partido de hoy).
  2. Usar esa media como "lambda" de una distribución de Poisson (el
     método estándar en analítica de fútbol para mercados de over/under)
     y calcular la probabilidad real de superar la línea de la cuota.
  3. Convertir la cuota que ofrece la casa de apuestas en una probabilidad
     implícita (fórmula estándar: prob = 1 / cuota).
  4. Avisar solo cuando la probabilidad estadística se aleja MUCHO de la
     probabilidad implícita (posible descuadre de precio, no garantía).

Esto sigue siendo una herramienta de cribado, no un oráculo. Ningún modelo
puede garantizar un % de beneficio a largo plazo.
"""

import math

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

FACTOR_RECENCIA = 0.85
FACTOR_CONTEXTO = 1.5


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


def medias_equipo(team_id, es_local):
    cache_key = (team_id, es_local)
    if cache_key in _cache_medias_equipo:
        return _cache_medias_equipo[cache_key]

    historial = data_fetcher.historial_equipo(team_id)
    if not historial:
        _cache_medias_equipo[cache_key] = None
        return None

    goles_acum = 0.0
    stats_acum = {mercado: 0.0 for mercado in MAPEO_ESTADISTICA}
    peso_total = 0.0

    for i, partido in enumerate(historial):
        peso_recencia = FACTOR_RECENCIA ** i
        jugo_de_local = partido["teams"]["home"]["id"] == team_id
        peso_contexto = FACTOR_CONTEXTO if jugo_de_local == es_local else 1.0
        peso = peso_recencia * peso_contexto

        goles = partido.get("goals", {})
        goles_acum += ((goles.get("home") or 0) + (goles.get("away") or 0)) * peso

        fixture_id = partido["fixture"]["id"]
        stats = data_fetcher.estadisticas_partido(fixture_id)
        if stats:
            for mercado, tipo_stat in MAPEO_ESTADISTICA.items():
                stats_acum[mercado] += _extraer_valor_estadistica(stats, team_id, tipo_stat) * peso

        peso_total += peso

    if peso_total == 0:
        _cache_medias_equipo[cache_key] = None
        return None

    medias = {"goles": goles_acum / peso_total}
    for mercado in MAPEO_ESTADISTICA:
        medias[mercado] = stats_acum[mercado] / peso_total

    _cache_medias_equipo[cache_key] = medias
    return medias


def probabilidad_implicita(cuota_decimal):
    if not cuota_decimal or cuota_decimal <= 1:
        return None
    return round((1 / cuota_decimal) * 100, 1)


def _parse_umbral(value_busqueda):
    try:
        return float(value_busqueda.replace("Over ", "").replace("over ", ""))
    except (TypeError, ValueError):
        return None


def prob_poisson_mayor_que(lam, umbral):
    if lam is None or lam <= 0:
        return 0.0

    k_max = int(umbral)
    prob_acumulada = 0.0
    for k in range(0, k_max + 1):
        prob_acumulada += (lam ** k) * math.exp(-lam) / math.factorial(k)

    prob = 1 - prob_acumulada
    return max(0.0, min(1.0, prob)) * 100


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

        umbral = _parse_umbral(info_odds["value_busqueda"])
        if umbral is None:
            continue

        medias_local = medias_equipo(home["id"], es_local=True)
        medias_visit = medias_equipo(away["id"], es_local=False)

        if medias_local is None or medias_visit is None:
            continue

        media_local = medias_local[mercado]
        media_visit = medias_visit[mercado]

        expectativa = media_local + media_visit

        prob_estadistica = prob_poisson_mayor_que(expectativa, umbral)
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
