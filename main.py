import time
import datetime
import pytz
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import (
    TIMEZONE, 
    START_HOUR, 
    END_HOUR, 
    SCAN_INTERVAL_MINUTES, 
    CURRENCY_SYMBOL
)
from database import (
    init_db, 
    record_opportunity, 
    get_active_positions, 
    mark_item_sold, 
    get_current_capital,
    is_day_closed,
    mark_day_closed,
    get_today_str
)
from steam_client import WATCHLIST, fetch_item_price, build_steam_market_url, fetch_steam_game_glitches, sync_live_steam_wallet
from steam_auth import steam_auth_mgr
from risk_engine import analyze_opportunity
from chart_generator import generate_portfolio_chart, generate_item_trend_chart
from notifier import send_telegram_alert, send_gmail_alert, send_telegram_simple_message, send_telegram_photo, send_game_glitch_alert
from telegram_handler import start_telegram_listener_thread
from ai_inspector import inspect_opportunity_with_gemini
import web_app
import threading
import requests

tz = pytz.timezone(TIMEZONE)

def is_operating_hours():
    """Verifica si la hora actual de Perú está entre las 7:00 AM y las 10:00 PM"""
    now = datetime.datetime.now(tz)
    return START_HOUR <= now.hour < END_HOUR

def execute_daily_closing():
    """
    Ejecuta el cierre del día a las 10:00 PM (Hora de Perú UTC-5):
    - Genera gráficos de 3 días, 7 días y 30 días.
    - Envía resumen final del día a Gmail y Telegram.
    - Marca el día como cerrado para evitar duplicaciones.
    """
    today_str = get_today_str()
    if is_day_closed(today_str):
        print(f"ℹ️ El cierre del día {today_str} ya fue ejecutado previamente. Se omite duplicado.")
        return

    print("\n🌙 [10:00 PM] Ejecutando cierre de día y generando reportes...")
    chart_3d = generate_portfolio_chart(days=3, mode="REAL")
    chart_7d = generate_portfolio_chart(days=7, mode="REAL")
    chart_30d = generate_portfolio_chart(days=30, mode="REAL")

    real_cash, real_inv, real_eq = get_current_capital(is_real=True)
    sim_cash, sim_inv, sim_eq = get_current_capital(is_real=False)

    summary_text = (
        f"🏁 *CIERRE DE JORNADA - STEAM INVESTOR (10:00 PM)*\n\n"
        f"💼 *Cartera Real:*\n"
        f"• Efectivo Disponible: `{CURRENCY_SYMBOL} {real_cash:.2f}`\n"
        f"• Valor en Inventario: `{CURRENCY_SYMBOL} {real_inv:.2f}`\n"
        f"• Total Patrimonio: `{CURRENCY_SYMBOL} {real_eq:.2f}`\n\n"
        f"🎮 *Cartera Simulada:*\n"
        f"• Total Simulado: `{CURRENCY_SYMBOL} {sim_eq:.2f}`\n\n"
        f"🌙 El escáner de mercado entrará en pausa nocturna y se reactivará automáticamente mañana a las 7:00 AM."
    )

    send_telegram_simple_message(summary_text)
    if chart_7d and os.path.exists(chart_7d):
        send_telegram_photo(chart_7d, caption="Rendimiento del Portafolio (Últimos 7 días)")

    # Enviar reporte por Gmail
    html_report = f"""
    <h2>Cierre de Jornada - Steam Investor Bot (10:00 PM)</h2>
    <p><strong>Cartera Real:</strong> Efectivo: {CURRENCY_SYMBOL} {real_cash:.2f} | Inventario: {CURRENCY_SYMBOL} {real_inv:.2f} | <strong>Total: {CURRENCY_SYMBOL} {real_eq:.2f}</strong></p>
    <p><strong>Cartera Simulada:</strong> Total: {CURRENCY_SYMBOL} {sim_eq:.2f}</p>
    <hr>
    <p>Se adjuntan los gráficos de tendencia a 3 días, 7 días y 30 días.</p>
    """
    send_gmail_alert("Resumen de Cierre de Día (10:00 PM) - Steam Investor Bot", html_report, attachment_image_path=chart_7d)
    
    mark_day_closed(today_str)

def check_sell_signals():
    """
    Monitorea las posiciones activas para enviar alertas de venta recomendada
    cuando se alcanza el precio meta de ganancia (Take Profit).
    """
    positions = get_active_positions()
    if not positions:
        return

    print(f"🔍 Evaluando {len(positions)} posiciones activas para señales de venta...")
    for pos in positions:
        time.sleep(2)
        price_data = fetch_item_price(pos["app_id"], pos["item_name"])
        if not price_data or not price_data.get("lowest_price"):
            continue

        current_market_price = price_data["lowest_price"]
        target_price = pos["target_sell_price"]

        if current_market_price >= target_price:
            sell_result = mark_item_sold(pos["id"], current_market_price)
            if sell_result:
                steam_url = build_steam_market_url(pos["app_id"], pos["item_name"])
                tipo = "REAL" if pos["is_real"] else "SIMULADO"
                sell_msg = (
                    f"🎯 *¡SEÑAL DE VENTA ALCANZADA! ({tipo})*\n\n"
                    f"📦 *Producto:* `{pos['item_name']}`\n"
                    f"🔢 *Cantidad a Vender:* {pos['quantity']} unidades\n"
                    f"💰 *Precio de Compra:* `{CURRENCY_SYMBOL} {pos['buy_price']:.2f}`\n"
                    f"🚀 *Precio Actual de Venta:* `{CURRENCY_SYMBOL} {current_market_price:.2f}`\n"
                    f"💵 *Ganancia Neta Realizada:* `+{CURRENCY_SYMBOL} {sell_result['net_profit']:.2f}` (*ROI: +{sell_result['roi_percent']:.1f}%*)\n\n"
                    f"ℹ️ *Acción Recomendada:*\n"
                    f"Abre tu inventario de Steam y lista las unidades a `{CURRENCY_SYMBOL} {current_market_price:.2f}` para venta rápida.\n\n"
                    f"🔗 [IR AL MERCADO DE STEAM]({steam_url})"
                )
                send_telegram_simple_message(sell_msg)
                print(f"[VENTA REALIZADA] {pos['item_name']} vendido a {current_market_price}")

def run_market_scanner():
    """
    Escanea la lista de seguimiento en busca de oportunidades de compra
    y la tienda de Steam en busca de errores de precio en juegos.
    Incorpora la validación por IA (Gemini) antes de notificar.
    """
    current_time_str = datetime.datetime.now(tz).strftime('%I:%M %p')
    print(f"\n🔎 [{current_time_str}] Iniciando escaneo de mercado de Steam...")
    
    # 1. Escaneo de Errores de Precio en Juegos de la Tienda Steam
    try:
        game_glitches = fetch_steam_game_glitches()
        if game_glitches:
            print(f"🎮 ¡{len(game_glitches)} error(es) de precio detectados en la Tienda Steam!")
            for g in game_glitches:
                send_game_glitch_alert(g)
    except Exception as e:
        print(f"[ERROR] Error al revisar tienda de juegos: {e}")

    # 2. Escaneo de la Canasta de Mercado
    opportunities_found = 0
    scanned_count = 0

    for item in WATCHLIST:
        time.sleep(2.5)
        data = fetch_item_price(item["app_id"], item["name"])
        if not data:
            continue

        scanned_count += 1
        data["strategy"] = item.get("strategy", "Oportunidad General")
        data["horizon"] = item.get("horizon", "1 a 7 días")
        opp = analyze_opportunity(data, is_real=True)
        if opp:
            # 🧠 AUDITORÍA DE INTELIGENCIA ARTIFICIAL (GEMINI)
            ai_audit = inspect_opportunity_with_gemini(opp)
            if not ai_audit["is_valid"]:
                print(f"🛡️ [IA RECHAZÓ OPORTUNIDAD] {opp['item_name']}: {ai_audit['reason']}")
                continue

            opportunities_found += 1
            print(f"✨ ¡Oportunidad Aprobada por IA! {opp['item_name']} a {CURRENCY_SYMBOL} {opp['buy_price']:.2f} (ROI: +{opp['roi_percent']:.1f}%)")
            
            opp_id = record_opportunity(
                item_name=opp["item_name"],
                app_id=opp["app_id"],
                buy_price=opp["buy_price"],
                quantity=opp["quantity"],
                target_sell_price=opp["target_sell_price"],
                is_aggressive=opp["is_aggressive"],
                notes=f"{opp['risk_level']} | Z: {opp.get('quant_info', {}).get('z_score', 0)} | Pool: {opp.get('pool_info', {}).get('category', 'NORMAL')} | IA: {ai_audit['verdict']}"
            )

            chart_path = generate_item_trend_chart(
                item_name=opp["item_name"],
                buy_price=opp["buy_price"],
                target_price=opp["target_sell_price"]
            )

            send_telegram_alert(opp, opp_id, chart_path=chart_path, ai_verdict=ai_audit)

            steam_url = build_steam_market_url(opp["app_id"], opp["item_name"])
            html_email = f"""
            <h3>Oportunidad de Inversión en Steam ({opp['risk_level']})</h3>
            <p><strong>Producto:</strong> {opp['item_name']}</p>
            <p><strong>Precio Oferta:</strong> {CURRENCY_SYMBOL} {opp['buy_price']:.2f} (Normal: {CURRENCY_SYMBOL} {opp['median_price']:.2f})</p>
            <p><strong>Cantidad Recomendada:</strong> {opp['quantity']} unidad(es)</p>
            <p><strong>Ganancia Estimada:</strong> +{CURRENCY_SYMBOL} {opp['total_net_profit']:.2f} (+{opp['roi_percent']:.1f}% neto)</p>
            <p><strong>Auditoría IA (Gemini):</strong> {ai_audit['verdict']} - {ai_audit['reason']}</p>
            <p><a href="{steam_url}">Haz clic aquí para ver el producto en Steam</a></p>
            """
            send_gmail_alert(f"Oportunidad Detectada: {opp['item_name']}", html_email, attachment_image_path=chart_path)

    # En modo silencioso, solo registramos en consola para no enviar falsos positivos ni spam cada 30 minutos
    if opportunities_found == 0 and scanned_count > 0:
        print(f"ℹ️ [{current_time_str}] Escaneo completado: {scanned_count} activos revisados. Todo en rango normal de mercado. (Modo silencioso activo - Cero spam)")

def run_keep_alive():
    """Mantiene despierto el servicio web de Render enviando un ping cada 10 minutos"""
    port = int(os.getenv("PORT", 8080))
    url = f"http://127.0.0.1:{port}/api/data"
    while True:
        try:
            time.sleep(600) # Cada 10 minutos
            requests.get(url, timeout=5)
        except Exception:
            pass

def run_steam_session_refresher():
    """
    Renueva automáticamente las cookies de sesión web cada 4 horas en segundo plano (24/7)
    usando el Refresh Token OAuth, garantizando que el bot nunca pierda la conexión.
    """
    while True:
        try:
            time.sleep(14400) # Cada 4 horas
            if steam_auth_mgr.is_authenticated():
                print("🔄 [SteamAuth] Ejecutando auto-renovación periódica de sesión 24/7...")
                steam_auth_mgr.refresh_session_if_needed()
                sync_live_steam_wallet()
        except Exception as e:
            print(f"[SteamAuth Warning] Error en auto-renovación: {e}")

def main_loop():
    print("="*60)
    print("🚀 INICIANDO STEAM INVESTOR BOT (HORARIO PERÚ 7:00 AM - 10:00 PM)")
    print("="*60)
    init_db()
    start_telegram_listener_thread()
    
    # Iniciar Panel Web en segundo plano
    web_thread = threading.Thread(target=web_app.run_web_server, daemon=True)
    web_thread.start()

    # Iniciar Keep-Alive pinger
    keep_alive_thread = threading.Thread(target=run_keep_alive, daemon=True)
    keep_alive_thread.start()

    # Iniciar Auto-Renovador de Sesión Steam 24/7
    steam_refresher = threading.Thread(target=run_steam_session_refresher, daemon=True)
    steam_refresher.start()

    # Verificación de conexión con Steam
    if steam_auth_mgr.is_authenticated():
        status = steam_auth_mgr.get_status()
        bal = sync_live_steam_wallet()
        bal_str = f"S/ {bal:.2f}" if bal is not None else "Consultando..."
        print(f"✅ [SteamAuth] Sesión 24/7 vinculada con éxito. Usuario: {status['account_name']} | Saldo Cartera: {bal_str}")
    else:
        print("📱 [SteamAuth] Cuenta no vinculada aún.")
        print("👉 Abre el Dashboard Web (http://localhost:8080) y pulsa 'Vincular Steam Móvil (24/7)' para escanear el QR desde tu celular.")

    # Notificación de arranque a Telegram para dar certeza al usuario de que el bot está vivo
    now_dt = datetime.datetime.now(tz)
    now_str = now_dt.strftime('%I:%M %p')
    op_status = "🟢 Escaneando en vivo (Horario 7:00 AM - 10:00 PM)" if is_operating_hours() else "🌙 En reposo nocturno (Se activa a las 7:00 AM)"
    real_cash, _, _ = get_current_capital(is_real=True)
    startup_msg = (
        f"🚀 *STEAM INVESTOR BOT INICIALIZADO*\n\n"
        f"• *Estado del Bot:* `{op_status}`\n"
        f"• *Hora Perú:* `{now_str}`\n"
        f"• *Efectivo en Steam:* `{CURRENCY_SYMBOL} {real_cash:.2f}`\n"
        f"• *Modo Silencioso:* Activo (Cero spam - Solo te avisará cuando haya compras reales aprobadas)\n\n"
        f"💡 *¿Quieres verificar que sigo vivo?*\n"
        f"Escribe `/status` o `/resumen` en este chat en cualquier momento y te responderé de inmediato."
    )
    send_telegram_simple_message(startup_msg)

    # Ejecutar un primer escaneo inmediato al iniciar si está en horario
    if is_operating_hours():
        run_market_scanner()
        check_sell_signals()

    while True:
        try:
            now = datetime.datetime.now(tz)
            
            if is_operating_hours():
                print(f"⏳ Esperando {SCAN_INTERVAL_MINUTES} minutos para el próximo escaneo...\n")
                time.sleep(SCAN_INTERVAL_MINUTES * 60)
                run_market_scanner()
                check_sell_signals()
            else:
                today_str = get_today_str()
                if now.hour >= END_HOUR and not is_day_closed(today_str):
                    execute_daily_closing()

                print(f"💤 Fuera de horario operativo ({now.strftime('%H:%M:%S')}). En pausa hasta las 07:00 AM...")
                time.sleep(600)

        except KeyboardInterrupt:
            print("\n🛑 Bot detenido manualmente.")
            break
        except Exception as e:
            print(f"[ERROR INESPERADO] {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
