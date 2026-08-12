"""
Funciones para hablar con API-Football (RapidAPI).

Documentación oficial: https://www.api-football.com/documentation-v3
Plan gratuito: 100 peticiones/día - por eso cacheamos y solo pedimos
lo estrictamente necesario cada ejecución diaria.
"""

import datetime
import time
import requests

import config


def _headers():
    return {
        "x-apisports-key": config.API_FOOTBALL_KEY,
    }


def _get(endpoint, params=None, retries=3):
    """Petición GET con reintentos simples ante fallos de red/rate limit."""
    url = f"{config.API_FOOTBALL_BASE_URL}/{endpoint}"
    for intento in range(retries):
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            errores = data.get("errors")
            # API-Football a veces devuelve 200 OK con un aviso interno
            # (parámetro mal formado, límite de plan, etc.) en vez de un
            # error HTTP. Antes lo ignorábamos en silencio; ahora lo
            # imprimimos para poder diagnosticarlo.
            if errores:
                print(f"[AVISO API] endpoint={endpoint} params={params} errores={errores}")
            return data.get("response", [])
        if resp.status_code == 429:  # límite de peticiones alcanzado
            time.sleep(5)
            continue
        resp.raise_for_status()
    return []


def temporada_actual():
    """API-Football numera la temporada por el año de inicio."""
    hoy = datetime.date.today()
    return hoy.year if hoy.month >= 7 else hoy.year - 1


def buscar_liga_id(search, country):
    """
    Busca el ID de una competición por nombre + país usando /leagues.
    Prioriza una coincidencia EXACTA de nombre; si no la hay, usa la
    primera coincidencia razonable. Devuelve None si no hay nada.
    """
    resultados = _get("leagues", {"search": search})
    if not resultados:
        return None

    if country == "World":
        # 1) coincidencia exacta de nombre entre competiciones "Cup"
        for item in resultados:
            nombre_liga = item.get("league", {}).get("name", "")
            if nombre_liga.lower() == search.lower() and item.get("league", {}).get("type") == "Cup":
                return item["league"]["id"]
        # 2) el nombre buscado aparece DENTRO del nombre de la competición (más flexible)
        for item in resultados:
            nombre_liga = item.get("league", {}).get("name", "")
            if search.lower() in nombre_liga.lower() and item.get("league", {}).get("type") == "Cup":
                return item["league"]["id"]
        # 3) cualquier "Cup" de ámbito mundial
        for item in resultados:
            if item.get("league", {}).get("type") == "Cup" and \
               item.get("country", {}).get("name") in (None, "World"):
                return item["league"]["id"]
        return resultados[0]["league"]["id"]

    # Para ligas nacionales: primero coincidencia exacta de nombre + país
    for item in resultados:
        nombre_liga = item.get("league", {}).get("name", "")
        pais = item.get("country", {}).get("name", "")
        if nombre_liga.lower() == search.lower() and pais.lower() == country.lower():
            return item["league"]["id"]

    # Si no hay coincidencia exacta, cualquier resultado de ese país
    for item in resultados:
        if item.get("country", {}).get("name", "").lower() == country.lower():
            return item["league"]["id"]

    return None


def resolver_ligas():
    """
    Recorre config.LEAGUE_QUERIES y devuelve un dict {nombre: id_liga}.

    Si una entrada de LEAGUE_QUERIES ya trae un "id" fijo (porque en una
    ejecución anterior lo encontramos y lo copiamos a config.py), NO se
    vuelve a buscar por nombre: esto ahorra 1 petición por competición
    cada día. Las que no tengan "id" se siguen buscando por nombre+país,
    y se imprime el ID encontrado para que puedas copiarlo a config.py
    y fijarlo tú mismo si quieres ahorrar esa petición a partir de mañana.
    """
    ligas_resueltas = {}
    for query in config.LEAGUE_QUERIES:
        if query.get("id"):
            ligas_resueltas[query["nombre"]] = query["id"]
            continue

        liga_id = buscar_liga_id(query["search"], query["country"])
        if liga_id:
            ligas_resueltas[query["nombre"]] = liga_id
            print(f"ID encontrado para '{query['nombre']}': {liga_id} "
                  f"(puedes fijarlo en config.py con \"id\": {liga_id})")
        else:
            print(f"Aviso: no se encontró ID para '{query['nombre']}', se omite hoy.")
    return ligas_resueltas



def partidos_de_hoy(league_id):
    """
    Devuelve los partidos programados para HOY Y MAÑANA en una liga concreta.

    Se incluye también el día siguiente porque muchas ligas sudamericanas
    juegan de madrugada en hora española; ese horario cae ya en la fecha
    siguiente en UTC (que es la que usa la API), así que si solo
    pidiéramos "hoy" esos partidos se perderían.
    """
    hoy = datetime.date.today()
    manana = hoy + datetime.timedelta(days=1)
    return _get(
        "fixtures",
        {
            "league": league_id,
            "season": temporada_actual(),
            "from": hoy.isoformat(),
            "to": manana.isoformat(),
        },
    )


def historial_equipo(team_id, n=None):
    """Últimos N partidos finalizados de un equipo (para medias estadísticas)."""
    n = n or config.PARTIDOS_HISTORIAL
    return _get("fixtures", {"team": team_id, "last": n, "status": "FT"})


def estadisticas_partido(fixture_id):
    """Estadísticas detalladas (córners, tarjetas, tiros...) de un partido ya jugado."""
    return _get("fixtures/statistics", {"fixture": fixture_id})


def cuotas_partido(fixture_id):
    """Cuotas de casas de apuestas para un partido concreto."""
    return _get("odds", {"fixture": fixture_id})
        
