"""
Punto de entrada. Ejecuta el análisis diario, registra los avisos para
seguimiento, comprueba resultados pasados, y envía el resumen por Telegram.

Uso manual:
    python main.py

Uso programado: ver README.md (cron, GitHub Actions, o similar) para que
se ejecute solo una vez al día sin que tengas que abrir nada.
"""

import datetime
import sys
import time

import config
import data_fetcher
import analysis
import telegram_notifier
import tracker


def validar_configuracion():
    faltantes = [
        nombre for nombre, valor in [
            ("TELEGRAM_BOT_TOKEN", config.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID", config.TELEGRAM_CHAT_ID),
            ("API_FOOTBALL_KEY", config.API_FOOTBALL_KEY),
        ] if not valor
    ]
    if faltantes:
        print(f"Faltan variables de entorno: {', '.join(faltantes)}")
        print("Revisa el README.md para configurarlas.")
        sys.exit(1)


def main():
    validar_configuracion()

    print("Buscando IDs de las competiciones configuradas...")
    ligas = data_fetcher.resolver_ligas()

    resultados_por_liga = {}
    ya_se_ha_depurado = False

    for nombre_liga, league_id in ligas.items():
        print(f"Analizando {nombre_liga}...")
        partidos = data_fetcher.partidos_de_hoy(league_id)
        print(f"  Partidos encontrados: {len(partidos)}")

        resultados_liga = []
        for fixture in partidos:
            # DEPURACIÓN TEMPORAL: imprime los nombres de mercado reales del
            # primer partido con cuotas que encontremos, para comprobar si
            # coinciden con los que busca analysis.MAPEO_MERCADO_ODDS.
            if not ya_se_ha_depurado:
                fixture_id = fixture["fixture"]["id"]
                odds_debug = data_fetcher.cuotas_partido(fixture_id)
                if odds_debug:
                    nombres_mercado = set()
                    for bloque in odds_debug:
                        for bookmaker in bloque.get("bookmakers", []):
                            for bet in bookmaker.get("bets", []):
                                nombres_mercado.add(bet.get("name"))
                    print(f"[DEPURACIÓN] Mercados disponibles en {fixture['teams']['home']['name']} "
                          f"vs {fixture['teams']['away']['name']}: {sorted(nombres_mercado)}")
                    ya_se_ha_depurado = True

            hallazgos = analysis.analizar_partido(fixture)
            resultados_liga.append((fixture, hallazgos))
            time.sleep(1)  # pequeño respiro para no saturar el límite de la API

        resultados_por_liga[nombre_liga] = resultados_liga

    # Guarda los avisos de hoy para poder comprobar más adelante si aciertan
    tracker.registrar_hallazgos(resultados_por_liga)

    # Comprueba resultados de avisos de días anteriores
    actualizados = tracker.comprobar_resultados()
    print(f"Resultados actualizados hoy: {actualizados}")

    mensaje = telegram_notifier.construir_mensaje(resultados_por_liga)
    telegram_notifier.enviar_mensaje(mensaje)
    print("Resumen enviado por Telegram.")

    # Los domingos, además, se manda un resumen de rendimiento acumulado
    if datetime.date.today().weekday() == 6:
        resumen = tracker.resumen_por_mercado(dias=60)
        if resumen:
            mensaje_resumen = telegram_notifier.construir_resumen_rendimiento(resumen)
            telegram_notifier.enviar_mensaje(mensaje_resumen)
            print("Resumen de rendimiento enviado por Telegram.")


if __name__ == "__main__":
    main()
