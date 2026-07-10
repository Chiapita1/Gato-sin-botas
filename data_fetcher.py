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
            return resp.json().get("response", [])
        if resp.status_code == 429:  # límite de peticiones alcanzado
            time.sleep(5)
            continue
        resp.raise_for_status()
    return []


def temporada_actual():
    """API-Football numera la temporada por el año de inicio."""
    hoy = datetime.date.today()
    return hoy.year if hoy.month >= 7 else hoy.year - 1


def partidos_de_hoy(league_id):
    """Devuelve los partidos programados para hoy en una liga concreta."""
    hoy = datetime.date.today().isoformat()
    return _get(
        "fixtures",
        {"league": league_id, "season": temporada_actual(), "date": hoy},
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
