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
    "goles_over15": {"bet_name": "Goals Over/Under", "value_busqueda": "Over 1.5"},
    "goles_1t": {"bet_name": "Goals Over/Under First Half", "value_busqueda": "Over 0.5"},
    "corners": {"bet_name": "Corners Over Under", "value_busqueda": "Over 9.5"},
    "tarjetas": {"bet_name": "Yellow Over/Under", "value_busqueda": "Over 3.5"},
    "tiros_puerta": {"bet_name": "Total Shots on Target", "value_busqueda": "Over 7.5"},
}

# Algunos mercados comparten la misma media calculada (p.ej. "goles" y
# "goles_over15" son ambos sobre el total de goles del partido completo),
# así que aquí mapeamos cada mercado a la clave real dentro de "medias".
MERCADO_A_CLAVE_MEDIA = {
    "goles": "goles",
    "goles_over15": "goles",
    "goles_1t": "goles_1t",
    "corners": "corners",
    "tarjetas": "tarjetas",
    "tiros_puerta": "tiros_puerta",
}

# Cuánto pesa cada partido anterior según su antigüedad (el más reciente
# pesa 1, el siguiente 0.85, el siguiente 0.85^2, etc.)
FACTOR_RECENCIA = 0.85

# Cuánto más pesa un partido jugado en el mismo contexto (local jugando en
# casa, visitante jugando fuera) frente a uno jugado en el contexto contrario.
FACTOR_CONTEXTO = 1.5


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


# Caché en memoria: evita volver a pedir el historial/estadísticas de un
# mismo equipo si aparece en más de un partido analizado el mismo día.
# La clave incluye si se analiza "de local" o "de visitante" porque el
# peso de cada partido pasado cambia según el contexto.
_cache_medias_equipo = {}


def medias_equipo(team_id, es_local):
    """
    Calcula las medias recientes de un equipo en los 4 mercados, ponderando:
      - más los partidos recientes que los antiguos
      - más los partidos jugados en el mismo contexto (local/visitante)
        que el partido de hoy
    """
    cache_key = (team_id, es_local)
    if cache_key in _cache_medias_equipo:
        return _cache_medias_equipo[cache_key]

    historial = data_fetcher.historial_equipo(team_id)
    if not historial:
        _cache_medias_equipo[cache_key] = None
        return None

    goles_acum = 0.0
    goles_1t_acum = 0.0
    stats_acum = {mercado: 0.0 for mercado in MAPEO_ESTADISTICA}
    peso_total = 0.0

    # La API devuelve los partidos del más reciente al más antiguo.
    for i, partido in enumerate(historial):
        peso_recencia = FACTOR_RECENCIA ** i
        jugo_de_local = partido["teams"]["home"]["id"] == team_id
        peso_contexto = FACTOR_CONTEXTO if jugo_de_local == es_local else 1.0
        peso = peso_recencia * peso_contexto

        goles = partido.get("goals", {})
        goles_acum += ((goles.get("home") or 0) + (goles.get("away") or 0)) * peso

        # Goles al descanso (para el mercado de goles en la 1ª parte)
        descanso = partido.get("score", {}).get("halftime", {})
        goles_1t_acum += ((descanso.get("home") or 0) + (descanso.get("away") or 0)) * peso

        fixture_id = partido["fixture"]["id"]
        stats = data_fetcher.estadisticas_partido(fixture_id)
        if stats:
            for mercado, tipo_stat in MAPEO_ESTADISTICA.items():
                stats_acum[mercado] += _extraer_valor_estadistica(stats, team_id, tipo_stat) * peso

        peso_total += peso

    if peso_total == 0:
        _cache_medias_equipo[cache_key] = None
        return None

    medias = {
        "goles": goles_acum / peso_total,
        "goles_1t": goles_1t_acum / peso_total,
    }
    for mercado in MAPEO_ESTADISTICA:
        medias[mercado] = stats_acum[mercado] / peso_total

    _cache_medias_equipo[cache_key] = medias
    return medias


def probabilidad_implicita(cuota_decimal):
    """Convierte una cuota decimal (ej. 1.80) en probabilidad implícita (%)."""
    if not cuota_decimal or cuota_decimal <= 1:
        return None
    return round((1 / cuota_decimal) * 100, 1)


def _parse_umbral(value_busqueda):
    """Extrae el número de un texto tipo 'Over 2.5' -> 2.5"""
    try:
        return float(value_busqueda.replace("Over ", "").replace("over ", ""))
    except (TypeError, ValueError):
        return None


def prob_poisson_mayor_que(lam, umbral):
    """
    Probabilidad de que una variable Poisson(lam) supere un umbral tipo
    "Over 2.5" (es decir, P(X >= 3) cuando umbral=2.5). Este es el método
    estándar en analítica de fútbol para mercados de over/under.
    """
    if lam is None or lam <= 0:
        return 0.0

    k_max = int(umbral)  # para 2.5 -> 2 (queremos P(X > 2) = 1 - P(X <= 2))
    prob_acumulada = 0.0
    for k in range(0, k_max + 1):
        prob_acumulada += (lam ** k) * math.exp(-lam) / math.factorial(k)

    prob = 1 - prob_acumulada
    return max(0.0, min(1.0, prob)) * 100


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


def _evaluar_mercado(fixture, mercado):
    """
    Calcula todos los datos de un mercado para un partido (cuota, probabilidad
    implícita, probabilidad estadística, diferencia), SIN aplicar ningún
    filtro de umbral. Devuelve None si falta algún dato necesario (sin cuota
    para ese mercado, sin historial suficiente, etc.).
    """
    fixture_id = fixture["fixture"]["id"]
    home = fixture["teams"]["home"]
    away = fixture["teams"]["away"]

    info_odds = MAPEO_MERCADO_ODDS.get(mercado)
    if not info_odds:
        return None

    odds = data_fetcher.cuotas_partido(fixture_id)
    cuota = _buscar_cuota(odds, info_odds["bet_name"], info_odds["value_busqueda"])
    prob_implicita = probabilidad_implicita(cuota)
    if prob_implicita is None:
        return None

    umbral = _parse_umbral(info_odds["value_busqueda"])
    if umbral is None:
        return None

    medias_local = medias_equipo(home["id"], es_local=True)
    medias_visit = medias_equipo(away["id"], es_local=False)
    if medias_local is None or medias_visit is None:
        return None

    media_local = medias_local[MERCADO_A_CLAVE_MEDIA[mercado]]
    media_visit = medias_visit[MERCADO_A_CLAVE_MEDIA[mercado]]

    # OJO: media_local y media_visit son medias de "total del partido"
    # (goles/córners/etc. de AMBOS equipos), no solo lo aportado por ese
    # equipo. Sumarlas directamente duplicaría la expectativa real del
    # partido de hoy, así que promediamos en vez de sumar.
    expectativa = (media_local + media_visit) / 2

    prob_estadistica = prob_poisson_mayor_que(expectativa, umbral)
    diferencia = prob_estadistica - prob_implicita

    return {
        "mercado": mercado,
        "seleccion": info_odds["value_busqueda"],
        "cuota": cuota,
        "prob_implicita": prob_implicita,
        "prob_estadistica": round(prob_estadistica, 1),
        "diferencia_pp": round(diferencia, 1),
    }


def analizar_partido(fixture):
    """
    Devuelve una lista de "hallazgos" (dicts) para un partido, uno por mercado
    donde la diferencia entre estadística y cuota supera el umbral configurado
    Y la probabilidad estadística llega al mínimo exigido.
    """
    hallazgos = []
    for mercado in config.MERCADOS:
        datos = _evaluar_mercado(fixture, mercado)
        if datos is None:
            continue
        if datos["diferencia_pp"] >= config.UMBRAL_DIFERENCIA_PP and \
           datos["prob_estadistica"] >= config.PROB_ESTADISTICA_MINIMA:
            hallazgos.append(datos)
    return hallazgos


def diagnostico_partido(fixture):
    """
    Igual que analizar_partido, pero devuelve TODOS los mercados evaluados,
    sin filtrar por umbral. Solo para depuración manual, no se usa en el
    funcionamiento normal del bot.
    """
    resultados = []
    for mercado in config.MERCADOS:
        datos = _evaluar_mercado(fixture, mercado)
        resultados.append(datos if datos else {"mercado": mercado, "motivo": "sin datos suficientes (sin cuota o sin historial)"})
    return resultados
                      
