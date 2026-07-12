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


def construir_resumen_rendimiento(resumen):
    """
    resumen: dict {mercado: {total_picks, aciertos, tasa_acierto, roi_pct}}
    (lo que devuelve tracker.resumen_por_mercado())
    """
    lineas = [
        "📊 <b>Resumen semanal de rendimiento (últimos 60 días)</b>",
        "<i>Basado en avisos ya resueltos. Cuantos más picks se acumulen, "
        "más fiable es este dato.</i>",
        "",
    ]

    mercados_ordenados = sorted(
        resumen.items(), key=lambda item: item[1]["roi_pct"], reverse=True
    )

    for mercado, datos in mercados_ordenados:
        signo = "+" if datos["roi_pct"] >= 0 else ""
        lineas.append(
            f"• <b>{mercado.capitalize()}</b>: {datos['total_picks']} picks, "
            f"{datos['aciertos']} aciertos ({datos['tasa_acierto']}%), "
            f"ROI {signo}{datos['roi_pct']}%"
        )

    lineas.append("")
    lineas.append(
        "Recuerda: hacen falta muchos más picks (meses) para saber si un "
        "margen es real o solo varianza a corto plazo."
    )

    return "\n".join(lineas)
