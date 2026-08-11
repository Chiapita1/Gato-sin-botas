"""
Configuración del bot. Todas las claves se leen de variables de entorno
para no dejar secretos escritos en el código.

Variables necesarias (ver README.md para cómo obtenerlas):
  TELEGRAM_BOT_TOKEN   -> token del bot, te lo da @BotFather
  TELEGRAM_CHAT_ID     -> tu chat_id de Telegram (o el del grupo/canal)
  API_FOOTBALL_KEY     -> clave de RapidAPI para API-Football
"""

import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

API_FOOTBALL_HOST = "v3.football.api-sports.io"
API_FOOTBALL_BASE_URL = f"https://{API_FOOTBALL_HOST}"

# Competiciones a analizar. En vez de IDs fijos (que pueden estar mal o
# cambiar), el bot busca el ID correcto por nombre + país cada vez que
# corre, usando el endpoint /leagues de la API.
LEAGUE_QUERIES = [
    # Europa - top 5
    {"nombre": "LaLiga", "search": "La Liga", "country": "Spain", "id": 140},
    {"nombre": "Premier League", "search": "Premier League", "country": "England", "id": 39},
    {"nombre": "Serie A", "search": "Serie A", "country": "Italy", "id": 135},
    {"nombre": "Bundesliga", "search": "Bundesliga", "country": "Germany", "id": 78},
    {"nombre": "Ligue 1", "search": "Ligue 1", "country": "France", "id": 61},
    # Europa - otras
    {"nombre": "Eredivisie", "search": "Eredivisie", "country": "Netherlands", "id": 88},
    {"nombre": "Primeira Liga", "search": "Primeira Liga", "country": "Portugal", "id": 94},
    {"nombre": "Eliteserien (Noruega)", "search": "Eliteserien", "country": "Norway", "id": 103},
    {"nombre": "Allsvenskan (Suecia)", "search": "Allsvenskan", "country": "Sweden", "id": 113},
    {"nombre": "Veikkausliiga (Finlandia)", "search": "Veikkausliiga", "country": "Finland", "id": 244},
    # Europa - competiciones internacionales de clubes
    {"nombre": "Champions League", "search": "Champions League", "country": "World", "id": 2},
    {"nombre": "Europa League", "search": "Europa League", "country": "World", "id": 3},
    # América
    {"nombre": "MLS", "search": "MLS", "country": "USA", "id": 866},
    {"nombre": "Liga MX", "search": "Liga MX", "country": "Mexico", "id": 262},
    # Asia
    {"nombre": "Superliga China", "search": "Super League", "country": "China", "id": 169},
    {"nombre": "J1 League (Japón)", "search": "J1 League", "country": "Japan", "id": 98},
    {"nombre": "Saudi Pro League", "search": "Pro League", "country": "Saudi Arabia"},
    # Selecciones
    {"nombre": "Mundial de Selecciones", "search": "World Cup", "country": "World", "id": 1},
    # Europa - añadidas ahora que hay plan de pago
    {"nombre": "Swiss Super League", "search": "Super League", "country": "Switzerland", "id": 207},
    {"nombre": "Austrian Bundesliga", "search": "Bundesliga", "country": "Austria", "id": 218},
    {"nombre": "Championship (Inglaterra)", "search": "Championship", "country": "England", "id": 40},
    {"nombre": "LaLiga 2", "search": "Segunda", "country": "Spain", "id": 141},
    {"nombre": "Ekstraklasa (Polonia)", "search": "Ekstraklasa", "country": "Poland", "id": 106},
    {"nombre": "Superliga (Rumanía)", "search": "Liga 1", "country": "Romania", "id": 728},
    {"nombre": "Chance Liga (Rep. Checa)", "search": "First League", "country": "Czech-Republic"},
    {"nombre": "Challenge League (Suiza)", "search": "Challenge League", "country": "Switzerland", "id": 208},
    {"nombre": "Süper Lig (Turquía)", "search": "Super Lig", "country": "Turkey", "id": 203},
    # Copas internacionales de clubes (Sudamérica)
    {"nombre": "Copa Libertadores", "search": "Libertadores", "country": "World", "id": 13},
    {"nombre": "Copa Sudamericana", "search": "Sudamericana", "country": "World", "id": 11},
    # Ampliación con suscripción de pago (7.500 peticiones/día)
    {"nombre": "Superliga (Dinamarca)", "search": "Superliga", "country": "Denmark"},
    {"nombre": "Premier Division (Irlanda)", "search": "Premier Division", "country": "Ireland"},
    {"nombre": "HNL (Croacia)", "search": "HNL", "country": "Croatia"},
    {"nombre": "Premier League (Azerbaiyán)", "search": "Premier League", "country": "Azerbaijan"},
    {"nombre": "Pro League (Bélgica)", "search": "Pro League", "country": "Belgium"},
    {"nombre": "Meistriliiga (Estonia)", "search": "Meistriliiga", "country": "Estonia"},
    {"nombre": "Serie A (Brasil)", "search": "Serie A", "country": "Brazil"},
    {"nombre": "First League (Bulgaria)", "search": "First League", "country": "Bulgaria"},
    {"nombre": "Premiership (Escocia)", "search": "Premiership", "country": "Scotland"},
    {"nombre": "Super League (Grecia)", "search": "Super League", "country": "Greece"},
    {"nombre": "NB I (Hungría)", "search": "NB I", "country": "Hungary"},
    # Segundas divisiones
    {"nombre": "2. Bundesliga (Alemania)", "search": "2. Bundesliga", "country": "Germany"},
    {"nombre": "Ligue 2 (Francia)", "search": "Ligue 2", "country": "France"},
    {"nombre": "Serie B (Italia)", "search": "Serie B", "country": "Italy"},
]

# Cuántos partidos anteriores de cada equipo se usan para calcular medias
PARTIDOS_HISTORIAL = 8

# Umbral: solo avisamos si la diferencia entre la probabilidad estadística
# y la probabilidad implícita de la cuota es igual o mayor a este valor
# (en puntos porcentuales). 15 es un valor conservador de partida.
UMBRAL_DIFERENCIA_PP = 5

# Además de la diferencia mínima, exigimos que la probabilidad estadística
# estimada sea de al menos este valor (en %) para avisar. Esto filtra
# desajustes que, aunque grandes en puntos porcentuales, sigan siendo poco
# probables en términos absolutos (ej. 30% vs 20% cumple la diferencia
# pero no llega al 80% mínimo, así que se descarta).
PROB_ESTADISTICA_MINIMA = 65

# Mercados que analizamos
MERCADOS = ["goles", "goles_over15", "goles_1t", "corners", "tarjetas", "tiros_puerta", "btts"]
