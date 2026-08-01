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
    {"nombre": "J1 League (Japón)", "search": "J1 League", "country": "Japan"},
    {"nombre": "Saudi Pro League", "search": "Pro League", "country": "Saudi Arabia"},
    # Selecciones
    {"nombre": "Mundial de Selecciones", "search": "World Cup", "country": "World"},
]

# Cuántos partidos anteriores de cada equipo se usan para calcular medias
PARTIDOS_HISTORIAL = 8

# Umbral: solo avisamos si la diferencia entre la probabilidad estadística
# y la probabilidad implícita de la cuota es igual o mayor a este valor
# (en puntos porcentuales). 15 es un valor conservador de partida.
UMBRAL_DIFERENCIA_PP = 5

# Mercados que analizamos
MERCADOS = ["goles", "goles_over15", "goles_1t", "corners", "tarjetas", "tiros_puerta"]
