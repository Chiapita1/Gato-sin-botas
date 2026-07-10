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

API_FOOTBALL_HOST = "api-football-v1.p.rapidapi.com"
API_FOOTBALL_BASE_URL = f"https://{API_FOOTBALL_HOST}/v3"

# IDs de ligas en API-Football (temporada se calcula automáticamente)
LEAGUES = {
    "LaLiga": 140,
    "Premier League": 39,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
}

# Cuántos partidos anteriores de cada equipo se usan para calcular medias
PARTIDOS_HISTORIAL = 8

# Umbral: solo avisamos si la diferencia entre la probabilidad estadística
# y la probabilidad implícita de la cuota es igual o mayor a este valor
# (en puntos porcentuales). 15 es un valor conservador de partida.
UMBRAL_DIFERENCIA_PP = 15

# Mercados que analizamos
MERCADOS = ["goles", "corners", "tarjetas", "tiros_puerta"]
