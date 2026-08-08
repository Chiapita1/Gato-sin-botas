"""
Sistema de seguimiento de resultados.

Cada vez que el bot manda un aviso, se guarda aquí con "resultado: pendiente".
Un día o más después (cuando el partido ya ha terminado), el propio bot
comprueba el resultado real y marca si acertó o no. Con el tiempo esto
permite ver, con datos reales y no con intuición, qué mercado rinde mejor.

El archivo picks_historial.json se guarda dentro del propio repositorio de
GitHub (el workflow lo hace commit automáticamente tras cada ejecución),
así que el histórico persiste de un día para otro.
"""

import json
import os
import datetime

import data_fetcher

ARCHIVO_PICKS = "picks_historial.json"


def _cargar_picks():
    if not os.path.exists(ARCHIVO_PICKS):
        return []
    try:
        with open(ARCHIVO_PICKS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _guardar_picks(picks):
    with open(ARCHIVO_PICKS, "w", encoding="utf-8") as f:
        json.dump(picks, f, ensure_ascii=False, indent=2)


def registrar_hallazgos(resultados_por_liga):
    """Añade al histórico los avisos de hoy, con resultado pendiente."""
    picks = _cargar_picks()
    hoy = datetime.date.today().isoformat()

    for liga, partidos in resultados_por_liga.items():
        for fixture, hallazgos in partidos:
            if not hallazgos:
                continue
            fixture_id = fixture["fixture"]["id"]
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            for h in hallazgos:
                picks.append({
                    "fecha": hoy,
                    "fixture_id": fixture_id,
                    "liga": liga,
                    "partido": f"{home} vs {away}",
                    "mercado": h["mercado"],
                    "seleccion": h["seleccion"],
                    "cuota": h["cuota"],
                    "prob_estadistica": h["prob_estadistica"],
                    "prob_implicita": h["prob_implicita"],
                    "resultado": None,
                    "acierto": None,
                    "ganancia": None,
                })

    _guardar_picks(picks)


def _valor_real(fixture_id, mercado):
    """Obtiene el valor real (goles/corners/tarjetas/tiros) de un partido ya finalizado."""
    if mercado in ("goles", "goles_over15"):
        partidos = data_fetcher._get("fixtures", {"id": fixture_id})
        if not partidos:
            return None
        estado = partidos[0].get("fixture", {}).get("status", {}).get("short")
        if estado not in ("FT", "AET", "PEN"):
            return None  # el partido todavía no ha terminado
        goles = partidos[0].get("goals", {})
        return (goles.get("home") or 0) + (goles.get("away") or 0)

    if mercado == "goles_1t":
        partidos = data_fetcher._get("fixtures", {"id": fixture_id})
        if not partidos:
            return None
        estado = partidos[0].get("fixture", {}).get("status", {}).get("short")
        if estado not in ("FT", "AET", "PEN"):
            return None
        descanso = partidos[0].get("score", {}).get("halftime", {})
        return (descanso.get("home") or 0) + (descanso.get("away") or 0)

    if mercado == "btts":
        partidos = data_fetcher._get("fixtures", {"id": fixture_id})
        if not partidos:
            return None
        estado = partidos[0].get("fixture", {}).get("status", {}).get("short")
        if estado not in ("FT", "AET", "PEN"):
            return None
        goles = partidos[0].get("goals", {})
        ambos_marcaron = (goles.get("home") or 0) >= 1 and (goles.get("away") or 0) >= 1
        return 1 if ambos_marcaron else 0

    tipo_stat = {
        "corners": "Corner Kicks",
        "tarjetas": "Yellow Cards",
        "tiros_puerta": "Shots on Goal",
    }.get(mercado)

    if tipo_stat is None:
        # Mercado desconocido: mejor no arriesgarnos a marcarlo mal.
        # Antes esto devolvía 0 en silencio, lo que provocaba que TODOS
        # los picks de un mercado no reconocido se marcaran como fallo
        # sin comprobar nada de verdad.
        return None

    stats = data_fetcher.estadisticas_partido(fixture_id)
    if not stats:
        return None

    total = 0.0
    for bloque in stats:
        for item in bloque.get("statistics", []):
            if item.get("type") == tipo_stat:
                valor = item.get("value")
                if valor is None:
                    continue
                if isinstance(valor, str) and valor.endswith("%"):
                    valor = valor.replace("%", "")
                try:
                    total += float(valor)
                except (TypeError, ValueError):
                    continue
    return total


def _reparar_historial_v1(picks):
    """
    Corrige un fallo de una versión anterior: los mercados "goles_over15" y
    "goles_1t" no estaban reconocidos en _valor_real, así que TODOS sus
    picks resueltos se marcaron como fallo por error, sin comprobar el
    resultado real. Esto reinicia esos picks (una sola vez, marcados con
    "_reparado_v1") para que se vuelvan a comprobar con la lógica corregida.
    """
    cambios = 0
    for pick in picks:
        if pick.get("mercado") in ("goles_over15", "goles_1t") and \
           pick.get("resultado") is not None and \
           not pick.get("_reparado_v1"):
            pick["resultado"] = None
            pick["acierto"] = None
            pick["ganancia"] = None
            pick["_reparado_v1"] = True
            cambios += 1
    return cambios


def comprobar_resultados():
    """
    Recorre los picks pendientes de hace más de 1 día (para dar tiempo a que
    el partido termine y la API actualice sus estadísticas) y comprueba si
    acertaron o no. Devuelve cuántos picks se han actualizado.
    """
    picks = _cargar_picks()
    hoy = datetime.date.today()
    cambios = _reparar_historial_v1(picks)

    for pick in picks:
        if pick["resultado"] is not None:
            continue

        fecha_pick = datetime.date.fromisoformat(pick["fecha"])
        if (hoy - fecha_pick).days < 1:
            continue

        valor_real = _valor_real(pick["fixture_id"], pick["mercado"])
        if valor_real is None:
            continue  # aún no hay datos definitivos, se reintenta otro día

        if pick["mercado"] == "btts":
            # Aquí valor_real es 1 (ambos marcaron) o 0 (no ambos)
            acierto = valor_real == 1
        else:
            try:
                umbral = float(pick["seleccion"].replace("Over ", ""))
            except (TypeError, ValueError):
                continue
            acierto = valor_real > umbral

        pick["resultado"] = valor_real
        pick["acierto"] = acierto
        pick["ganancia"] = (pick["cuota"] - 1) if acierto else -1
        cambios += 1

    if cambios:
        _guardar_picks(picks)

    return cambios


def resumen_por_mercado(dias=60):
    """
    Rendimiento por mercado de los últimos N días, contando solo picks que
    ya tienen resultado confirmado (no los pendientes).
    """
    picks = _cargar_picks()
    limite = datetime.date.today() - datetime.timedelta(days=dias)

    stats = {}
    for pick in picks:
        if pick["resultado"] is None:
            continue
        fecha_pick = datetime.date.fromisoformat(pick["fecha"])
        if fecha_pick < limite:
            continue

        mercado = pick["mercado"]
        if mercado not in stats:
            stats[mercado] = {"total": 0, "aciertos": 0, "ganancia": 0.0}

        stats[mercado]["total"] += 1
        if pick["acierto"]:
            stats[mercado]["aciertos"] += 1
        stats[mercado]["ganancia"] += pick["ganancia"]

    resumen = {}
    for mercado, datos in stats.items():
        total = datos["total"]
        resumen[mercado] = {
            "total_picks": total,
            "aciertos": datos["aciertos"],
            "tasa_acierto": round(datos["aciertos"] / total * 100, 1) if total else 0,
            "roi_pct": round(datos["ganancia"] / total * 100, 1) if total else 0,
        }

    return resumen
    
