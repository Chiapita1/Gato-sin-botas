"""
Alerta de Favorito en Desventaja
---------------------------------
Detecta partidos EN VIVO donde un equipo muy favorito, jugando en casa,
encaja un gol tempranero (va perdiendo dentro de los primeros N minutos).
Cuando ocurre, envía una alerta por Telegram para valorar apostar a que
remonta o al menos empata (aprovechando la cuota mejorada tras el gol).

Fuente de datos: API-Football (https://www.api-football.com/)

Pensado para ejecutarse periódicamente (cron de GitHub Actions cada 3-5 min
durante las franjas horarias con partidos), igual que el resto de tu bot
Gato-sin-botas.

Variables de entorno necesarias:
  API_FOOTBALL_KEY     -> tu clave de api-football.com
  TELEGRAM_BOT_TOKEN   -> token del bot de Telegram
  TELEGRAM_CHAT_ID     -> chat/canal donde se envían las alertas

Estado:
  Se guarda un fichero JSON (alertas_enviadas.json) con los fixture_id ya
  avisados, para no mandar la misma alerta varias veces en el mismo partido.
  Si lo integras en GitHub Actions, haz commit de ese fichero al final del
  workflow (igual que probablemente ya haces con tu histórico de resultados).
"""

import os
import json
import requests
from pathlib import Path

# ----------------------- CONFIGURACIÓN -----------------------

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

# Umbral de cuota para considerar a un equipo "muy favorito" en el 1X2 (ganador del partido)
CUOTA_FAVORITO_MAX = 1.35

# Minuto límite para considerar el gol "tempranero"
MINUTO_LIMITE_GOL = 40

# Ligas a vigilar. Se cargan desde ligas_config.json, generado una sola vez
# con resolver_ligas.py (así evitamos IDs adivinados a mano). Si el fichero
# no existe o está vacío, el bot vigila TODAS las ligas en vivo disponibles.
LIGAS_CONFIG_PATH = Path("ligas_config.json")
ESTADO_PATH = Path("alertas_enviadas.json")


def cargar_ligas_vigiladas():
    if not LIGAS_CONFIG_PATH.exists():
        print("Aviso: no existe ligas_config.json -> se vigilarán TODAS las ligas en vivo.")
        return []
    datos = json.loads(LIGAS_CONFIG_PATH.read_text())
    return list(datos.values())


LIGAS_VIGILADAS = cargar_ligas_vigiladas()

# ----------------------- ESTADO LOCAL -----------------------

def cargar_estado():
    if ESTADO_PATH.exists():
        return set(json.loads(ESTADO_PATH.read_text()))
    return set()


def guardar_estado(ids_avisados):
    ESTADO_PATH.write_text(json.dumps(sorted(ids_avisados)))


# ----------------------- API-FOOTBALL -----------------------

def obtener_partidos_en_vivo():
    resp = requests.get(f"{API_BASE}/fixtures", headers=HEADERS, params={"live": "all"}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("response", [])


def obtener_cuota_local(fixture_id):
    """Devuelve la cuota 1X2 del equipo local (Match Winner) si existe, si no None."""
    resp = requests.get(
        f"{API_BASE}/odds",
        headers=HEADERS,
        params={"fixture": fixture_id, "bet": 1},  # bet 1 = Match Winner
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("response", [])
    if not data:
        return None
    try:
        bookmakers = data[0]["bookmakers"]
        for bk in bookmakers:
            for bet in bk["bets"]:
                if bet["name"] == "Match Winner":
                    for valor in bet["values"]:
                        if valor["value"] == "Home":
                            return float(valor["odd"])
    except (KeyError, IndexError, ValueError):
        return None
    return None


# ----------------------- LÓGICA DE DETECCIÓN -----------------------

def es_favorito_en_desventaja(fixture):
    liga_id = fixture["league"]["id"]
    if LIGAS_VIGILADAS and liga_id not in LIGAS_VIGILADAS:
        return None

    minuto = fixture["fixture"]["status"]["elapsed"]
    if minuto is None or minuto > MINUTO_LIMITE_GOL:
        return None

    goles_local = fixture["goals"]["home"]
    goles_visitante = fixture["goals"]["away"]

    # El local va perdiendo dentro del tramo tempranero
    if goles_local is None or goles_visitante is None or goles_local >= goles_visitante:
        return None

    fixture_id = fixture["fixture"]["id"]
    cuota_local = obtener_cuota_local(fixture_id)
    if cuota_local is None or cuota_local > CUOTA_FAVORITO_MAX:
        return None

    return {
        "fixture_id": fixture_id,
        "liga": fixture["league"]["name"],
        "pais": fixture["league"]["country"],
        "local": fixture["teams"]["home"]["name"],
        "visitante": fixture["teams"]["away"]["name"],
        "minuto": minuto,
        "marcador": f"{goles_local}-{goles_visitante}",
        "cuota_local_pre": cuota_local,
    }


# ----------------------- TELEGRAM -----------------------

def enviar_alerta_telegram(info):
    mensaje = (
        "🚨 *Favorito en desventaja* 🚨\n\n"
        f"🏆 {info['liga']} ({info['pais']})\n"
        f"🏠 {info['local']} 🆚 {info['visitante']}\n"
        f"⏱️ Minuto {info['minuto']}' | Marcador: {info['marcador']}\n"
        f"📊 Cuota pre-partido local: {info['cuota_local_pre']}\n\n"
        "El favorito va perdiendo pronto en casa. Puede ser buen momento "
        "para valorar remontada / empate con cuota mejorada."
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"},
        timeout=15,
    )


# ----------------------- MAIN -----------------------

def main():
    if not API_FOOTBALL_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise SystemExit(
            "Faltan variables de entorno: API_FOOTBALL_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
        )

    ids_avisados = cargar_estado()
    partidos = obtener_partidos_en_vivo()

    nuevas_alertas = 0
    for fixture in partidos:
        fixture_id = fixture["fixture"]["id"]
        if fixture_id in ids_avisados:
            continue

        info = es_favorito_en_desventaja(fixture)
        if info:
            enviar_alerta_telegram(info)
            ids_avisados.add(fixture_id)
            nuevas_alertas += 1

    guardar_estado(ids_avisados)
    print(f"Comprobación completada. Alertas nuevas enviadas: {nuevas_alertas}")


if __name__ == "__main__":
    main()
  
