"""
Resolver de IDs de liga (API-Football) - v2
----------------------------------------------
Trae el listado COMPLETO de ligas/copas de API-Football en una sola llamada
y busca dentro de ese listado (en Python) las competiciones que nos
interesan. Esto evita depender de adivinar el nombre exacto de {country} o
si el parámetro {search} funciona bien combinado con {country}, que fue lo
que falló en la primera versión.

Uso:
    export API_FOOTBALL_KEY="tu_clave"
    python resolver_ligas.py

Revisa la salida por consola: para cada liga te muestra qué encontró.
Si alguna sale como "NO ENCONTRADA" o "AMBIGUO", ajusta el texto de
búsqueda en LIGAS_OBJETIVO (o el nombre de país) y vuelve a ejecutar.
"""

import os
import json
import requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

SALIDA_PATH = "ligas_config.json"

# Cada entrada: (nombre_para_mostrar, texto_pais_o_None, texto_nombre_liga)
# Ambos textos se buscan como subcadena, sin distinguir mayúsculas/minúsculas,
# dentro de los campos "country" y "league.name" que devuelve la API.
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
    ("Azerbaiyán - Premyer Liqasi", "Azerbaijan", "Premyer"),
    ("Alemania - Bundesliga", "Germany", "Bundesliga"),
    ("Brasil - Serie A", "Brazil", "Serie A"),
    ("China - Super League", "China", "Super League"),
    ("Grecia - Super League", "Greece", "Super League"),
    ("Irlanda - Premier Division", "Ireland", "Premier Division"),
    ("México - Liga MX", "Mexico", "Liga MX"),
    ("Croacia - HNL", "Croatia", "HNL"),
    ("República Checa - Chance Liga", "Czech", "Chance"),
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
    ("UEFA Champions League", "World", "Champions League"),
    ("UEFA Europa League", "World", "Europa League"),
    ("UEFA Conference League", "World", "Conference League"),
    ("Copa Libertadores", "World", "Libertadores"),
    ("Copa Sudamericana", "World", "Sudamericana"),
]


def obtener_todas_las_ligas():
    """Una sola llamada: trae el listado completo de ligas/copas de la API."""
    resp = requests.get(f"{API_BASE}/leagues", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise SystemExit(f"La API devolvió un error: {data['errors']}")
    return data.get("response", [])


def buscar_en_listado(listado, texto_pais, texto_nombre):
    texto_nombre_low = texto_nombre.lower()
    candidatos = []
    for item in listado:
        nombre_liga = item["league"]["name"]
        nombre_pais = item["country"]["name"] or ""
        if texto_nombre_low not in nombre_liga.lower():
            continue
        if texto_pais and texto_pais != "World":
            if texto_pais.lower() not in nombre_pais.lower():
                continue
        if texto_pais == "World" and nombre_pais.lower() != "world":
            continue
        candidatos.append(item)
    return candidatos


def elegir_mejor_candidato(candidatos, texto_nombre):
    # Prioriza coincidencia exacta de nombre (sin distinguir mayúsculas)
    for c in candidatos:
        if c["league"]["name"].lower() == texto_nombre.lower():
            return c, False
    return candidatos[0], True


def main():
    if not API_FOOTBALL_KEY:
        raise SystemExit("Falta la variable de entorno API_FOOTBALL_KEY")

    print("Descargando listado completo de ligas (1 sola llamada)...")
    listado = obtener_todas_las_ligas()
    print(f"Listado recibido: {len(listado)} competiciones en total.\n")

    resultado_final = {}
    pendientes_revision = []

    for nombre_mostrar, texto_pais, texto_nombre in LIGAS_OBJETIVO:
        candidatos = buscar_en_listado(listado, texto_pais, texto_nombre)

        if not candidatos:
            print(f"[NO ENCONTRADA] {nombre_mostrar}  (buscado: pais='{texto_pais}', nombre~'{texto_nombre}')")
            pendientes_revision.append(nombre_mostrar)
            continue

        elegido, es_ambiguo = elegir_mejor_candidato(candidatos, texto_nombre)
        liga = elegido["league"]
        pais_info = elegido["country"]
        resultado_final[nombre_mostrar] = liga["id"]

        if es_ambiguo and len(candidatos) > 1:
            print(f"[AMBIGUO] {nombre_mostrar} -> eligiendo id {liga['id']} ({liga['name']}, {pais_info['name']}) entre {len(candidatos)} opciones:")
            for c in candidatos:
                print(f"    id {c['league']['id']} -> {c['league']['name']} ({c['country']['name']}, tipo: {c['league']['type']})")
            pendientes_revision.append(nombre_mostrar)
        else:
            print(f"[OK] {nombre_mostrar} -> id {liga['id']} ({liga['name']}, {pais_info['name']})")

    with open(SALIDA_PATH, "w") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)

    print(f"\nGuardado {SALIDA_PATH} con {len(resultado_final)} de {len(LIGAS_OBJETIVO)} ligas resueltas.")
    if pendientes_revision:
        print("\n⚠️ Revisa manualmente estas (no encontradas o ambiguas):")
        for nombre in pendientes_revision:
            print(f"  - {nombre}")
        print("Puedes corregir el id directamente en ligas_config.json.")


if __name__ == "__main__":
    main()
    
