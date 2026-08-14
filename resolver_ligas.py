"""
Resolver de IDs de liga (API-Football)
---------------------------------------
Este script se ejecuta UNA VEZ (o cada vez que quieras añadir/quitar ligas)
para traducir nombres de país/competición a los league_id reales de
API-Football, y los guarda en ligas_config.json.

De esta forma alerta_favorito_desventaja.py no tiene que adivinar IDs a mano
(hay más de 1.200 competiciones y los IDs no son intuitivos) ni gastar
peticiones en resolverlos en cada ejecución.

Uso:
    export API_FOOTBALL_KEY="tu_clave"
    python resolver_ligas.py

Revisa la salida por consola: para cada liga te muestra qué encontró.
Si alguna sale como "NO ENCONTRADA" o con un resultado ambiguo, ajusta el
texto de búsqueda en LIGAS_OBJETIVO y vuelve a ejecutar.
"""

import os
import json
import time
import requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

SALIDA_PATH = "ligas_config.json"

# Cada entrada: (nombre_para_mostrar, pais_api_football, texto_busqueda)
# El texto de búsqueda se manda al parámetro "search" del endpoint /leagues.
LIGAS_OBJETIVO = [
    # Primeras divisiones
    ("España - La Liga", "Spain", "La Liga"),
    ("Inglaterra - Premier League", "England", "Premier League"),
    ("Italia - Serie A", "Italy", "Serie A"),
    ("Francia - Ligue 1", "France", "Ligue 1"),
    ("Portugal - Primeira Liga", "Portugal", "Primeira Liga"),
    ("Holanda - Eredivisie", "Netherlands", "Eredivisie"),
    ("Bélgica - Pro League", "Belgium", "Pro League"),
    ("Estonia - Meistriliiga", "Estonia", "Meistriliiga"),
    ("Austria - Bundesliga", "Austria", "Bundesliga"),
    ("Escocia - Premiership", "Scotland", "Premiership"),
    ("Dinamarca - Superliga", "Denmark", "Superliga"),
    ("Suecia - Allsvenskan", "Sweden", "Allsvenskan"),
    ("Noruega - Eliteserien", "Norway", "Eliteserien"),
    ("Rumanía - Liga I", "Romania", "Liga I"),
    ("Azerbaiyán - Premyer Liqasi", "Azerbaijan", "Premyer Liqasi"),
    ("Alemania - Bundesliga", "Germany", "Bundesliga"),
    ("Brasil - Serie A", "Brazil", "Serie A"),
    ("China - Super League", "China", "Super League"),
    ("Grecia - Super League", "Greece", "Super League"),
    ("Irlanda - Premier Division", "Ireland", "Premier Division"),
    ("México - Liga MX", "Mexico", "Liga MX"),
    ("Croacia - HNL", "Croatia", "HNL"),
    ("República Checa - Chance Liga", "Czech-Republic", "Chance"),
    ("Polonia - Ekstraklasa", "Poland", "Ekstraklasa"),
    ("Estados Unidos - MLS", "USA", "MLS"),
    ("Bulgaria - First League", "Bulgaria", "First League"),
    ("Turquía - Süper Lig", "Turkey", "Super Lig"),
    ("Hungría - NB I", "Hungary", "NB I"),
    # Segundas divisiones
    ("España - Segunda División", "Spain", "Segunda"),
    ("Alemania - 2. Bundesliga", "Germany", "2. Bundesliga"),
    ("Francia - Ligue 2", "France", "Ligue 2"),
    ("Inglaterra - Championship", "England", "Championship"),
    ("Italia - Serie B", "Italy", "Serie B"),
    # Competiciones continentales / internacionales de clubes
    ("UEFA Champions League", None, "UEFA Champions League"),
    ("UEFA Europa League", None, "UEFA Europa League"),
    ("UEFA Conference League", None, "UEFA Europa Conference League"),
    ("Copa Libertadores", None, "Copa Libertadores"),
    ("Copa Sudamericana", None, "Copa Sudamericana"),
]


def buscar_liga(pais, texto_busqueda):
    params = {"search": texto_busqueda}
    if pais:
        params["country"] = pais
    resp = requests.get(f"{API_BASE}/leagues", headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("response", [])


def main():
    if not API_FOOTBALL_KEY:
        raise SystemExit("Falta la variable de entorno API_FOOTBALL_KEY")

    resultado_final = {}
    pendientes_revision = []

    for nombre_mostrar, pais, texto_busqueda in LIGAS_OBJETIVO:
        try:
            candidatos = buscar_liga(pais, texto_busqueda)
        except requests.RequestException as e:
            print(f"[ERROR] {nombre_mostrar}: fallo de red -> {e}")
            pendientes_revision.append(nombre_mostrar)
            continue

        if not candidatos:
            print(f"[NO ENCONTRADA] {nombre_mostrar}  (búsqueda: '{texto_busqueda}', país: {pais})")
            pendientes_revision.append(nombre_mostrar)
        elif len(candidatos) == 1:
            liga = candidatos[0]["league"]
            pais_info = candidatos[0]["country"]
            resultado_final[nombre_mostrar] = liga["id"]
            print(f"[OK] {nombre_mostrar} -> id {liga['id']} ({liga['name']}, {pais_info['name']})")
        else:
            # Varios resultados: mostramos todos para que elijas a mano si hace falta
            print(f"[AMBIGUO] {nombre_mostrar} tiene {len(candidatos)} coincidencias:")
            for c in candidatos:
                print(f"    id {c['league']['id']} -> {c['league']['name']} ({c['country']['name']}, tipo: {c['league']['type']})")
            # Nos quedamos con la primera coincidencia de tipo "League" como mejor intento,
            # pero avisamos para que la revises.
            liga_tipo_league = next((c for c in candidatos if c["league"]["type"] == "League"), candidatos[0])
            resultado_final[nombre_mostrar] = liga_tipo_league["league"]["id"]
            pendientes_revision.append(nombre_mostrar)

        time.sleep(0.3)  # margen prudente entre llamadas

    with open(SALIDA_PATH, "w") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)

    print(f"\nGuardado {SALIDA_PATH} con {len(resultado_final)} ligas resueltas.")
    if pendientes_revision:
        print("\n⚠️ Revisa manualmente estas (no encontradas o ambiguas):")
        for nombre in pendientes_revision:
            print(f"  - {nombre}")
        print("Puedes corregir el id directamente en ligas_config.json.")


if __name__ == "__main__":
    main()
  
