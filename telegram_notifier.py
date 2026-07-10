"""Envío de mensajes a Telegram mediante la Bot API oficial."""

import requests
import config


def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def construir_mensaje(resultados_por_liga):
    """
    resultados_por_liga: dict {nombre_liga: [(fixture, hallazgos), ...]}
    """
    hoy_hay_algo = any(hallazgos for partidos in resultados_por_liga.values()
                        for _, hallazgos in partidos)

    if not hoy_hay_algo:
        return ("⚽ <b>Resumen diario</b>\n\n"
                "Hoy no hay partidos donde la estadística reciente se aleje "
                "lo suficiente de las cuotas del mercado. Sin avisos.")

    lineas = ["⚽ <b>Resumen diario — posibles descuadres de cuota</b>",
              "<i>(esto NO es una garantía de acierto, es solo una señal a valorar)</i>", ""]

    for liga, partidos in resultados_por_liga.items():
        partidos_con_hallazgos = [(f, h) for f, h in partidos if h]
        if not partidos_con_hallazgos:
            continue

        lineas.append(f"🏆 <b>{liga}</b>")
        for fixture, hallazgos in partidos_con_hallazgos:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            hora = fixture["fixture"]["date"][11:16]
            lineas.append(f"\n🕒 {hora} — {home} vs {away}")
            for h in hallazgos:
                lineas.append(
                    f"  • {h['mercado'].capitalize()}: {h['seleccion']} "
                    f"(cuota {h['cuota']}) → estadística reciente sugiere "
                    f"~{h['prob_estadistica']}% vs {h['prob_implicita']}% implícito "
                    f"(dif. +{h['diferencia_pp']} pp)"
                )
        lineas.append("")

    return "\n".join(lineas)
