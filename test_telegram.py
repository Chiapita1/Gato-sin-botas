"""
Prueba rápida y aislada: solo comprueba que el bot de Telegram puede
enviarte un mensaje. No toca la parte de fútbol para nada.

Uso:
    export TELEGRAM_BOT_TOKEN="tu_token"
    export TELEGRAM_CHAT_ID="tu_chat_id"
    python test_telegram.py
"""

import os
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TOKEN or not CHAT_ID:
    print("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID como variables de entorno.")
    raise SystemExit(1)

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
resp = requests.post(url, data={
    "chat_id": CHAT_ID,
    "text": "✅ Conexión correcta. Tu bot de fútbol está listo para avisarte al móvil.",
})

print("Código de respuesta:", resp.status_code)
print("Respuesta completa:", resp.json())

if resp.status_code == 200:
    print("\n¡Revisa tu Telegram! Deberías haber recibido el mensaje.")
else:
    print("\nAlgo falló. Revisa el token y el chat_id.")
