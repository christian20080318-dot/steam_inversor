import time
import requests
import threading
from config import TELEGRAM_BOT_TOKEN, CURRENCY_SYMBOL
from database import (
    process_user_decision, 
    get_current_capital, 
    get_connection
)
from chart_generator import generate_portfolio_chart
from notifier import send_telegram_photo

def run_telegram_listener():
    """
    Escuchador en segundo plano que procesa los clics en [SÍ] y [NO] de Telegram
    y responde a comandos del usuario como /resumen o /grafico
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[AVISO] Telegram Token no configurado. El listener interactivo no se iniciará.")
        return

    print("🤖 Iniciando escuchador interactivo de Telegram (SÍ / NO)...")
    offset = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 25}
            resp = requests.get(url, params=params, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    # 1. Manejo de botones Inline (Callback Queries)
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        cb_data = cb.get("data", "")
                        chat_id = cb["message"]["chat"]["id"]

                        # Responder al callback para quitar el icono de cargando
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})

                        if cb_data.startswith("decision:"):
                            parts = cb_data.split(":")
                            decision = parts[1] # "yes" o "no"
                            opp_id = int(parts[2])

                            user_said_yes = (decision == "yes")
                            result = process_user_decision(opp_id, user_said_yes)

                            if result:
                                if user_said_yes:
                                    msg = (
                                        f"✅ *¡REGISTRADO EN CARTERA REAL!*\n\n"
                                        f"Has confirmado la compra de *{result['item']}*.\n"
                                        f"Monto invertido: `{CURRENCY_SYMBOL} {result['spent']:.2f}`.\n"
                                        f"El bot monitoreará este activo para notificarte cuándo venderlo."
                                    )
                                else:
                                    msg = (
                                        f"ℹ️ *DESCARTADO DE CARTERA REAL*\n\n"
                                        f"No se ha descontado dinero de tu saldo real.\n"
                                        f"*{result['item']}* se registró en el *Simulador Virtual* para comparar su rendimiento."
                                    )
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
                                })

                    # 2. Manejo de mensajes de texto (Comandos o texto libre 'si' / 'no')
                    elif "message" in update and "text" in update["message"]:
                        msg_obj = update["message"]
                        chat_id = msg_obj["chat"]["id"]
                        text = msg_obj["text"].strip().lower()

                        if text in ["si", "sí", "yes", "s"]:
                            # Buscar última oportunidad pendiente
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM portfolio WHERE status = 'PENDING_CONFIRMATION' ORDER BY id DESC LIMIT 1")
                            row = cursor.fetchone()
                            conn.close()
                            if row:
                                result = process_user_decision(row["id"], True)
                                if result:
                                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                        "chat_id": chat_id,
                                        "text": f"✅ Compra de *{result['item']}* registrada en Cartera Real por `{CURRENCY_SYMBOL} {result['spent']:.2f}`.",
                                        "parse_mode": "Markdown"
                                    })
                            else:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "No hay compras pendientes de confirmar en este momento."
                                })

                        elif text in ["no", "n"]:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM portfolio WHERE status = 'PENDING_CONFIRMATION' ORDER BY id DESC LIMIT 1")
                            row = cursor.fetchone()
                            conn.close()
                            if row:
                                result = process_user_decision(row["id"], False)
                                if result:
                                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                        "chat_id": chat_id,
                                        "text": f"ℹ️ Descartada compra real de *{result['item']}*. Guardada en Simulador.",
                                        "parse_mode": "Markdown"
                                    })
                            else:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "No hay compras pendientes de confirmar en este momento."
                                })

                        elif text.startswith("/resumen") or text.startswith("/balance"):
                            real_cash, real_inv, real_eq = get_current_capital(is_real=True)
                            sim_cash, sim_inv, sim_eq = get_current_capital(is_real=False)
                            resumen_msg = (
                                f"📊 *ESTADO ACTUAL DE TU CUENTA*\n\n"
                                f"💼 *CARTERA REAL:*\n"
                                f"• Efectivo: `{CURRENCY_SYMBOL} {real_cash:.2f}`\n"
                                f"• En Activos: `{CURRENCY_SYMBOL} {real_inv:.2f}`\n"
                                f"• Total Cartera: `{CURRENCY_SYMBOL} {real_eq:.2f}`\n\n"
                                f"🎮 *CARTERA SIMULADA:*\n"
                                f"• Efectivo: `{CURRENCY_SYMBOL} {sim_cash:.2f}`\n"
                                f"• En Activos: `{CURRENCY_SYMBOL} {sim_inv:.2f}`\n"
                                f"• Total Cartera: `{CURRENCY_SYMBOL} {sim_eq:.2f}`\n"
                            )
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id, "text": resumen_msg, "parse_mode": "Markdown"
                            })

                        elif text.startswith("/grafico"):
                            days = 7
                            if "30" in text:
                                days = 30
                            elif "3" in text:
                                days = 3
                            chart_file = generate_portfolio_chart(days=days, mode="REAL")
                            if chart_file:
                                send_telegram_photo(chart_file, caption=f"Evolución de Cartera Real - {days} días")
                            else:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "Aún no hay suficiente historial para generar el gráfico."
                                })

                        elif text.startswith("/status") or text.startswith("/ping") or text.startswith("/ayuda") or text.startswith("/start"):
                            import datetime
                            import pytz
                            now_peru = datetime.datetime.now(pytz.timezone("America/Lima")).strftime('%I:%M %p')
                            is_op = (7 <= datetime.datetime.now(pytz.timezone("America/Lima")).hour < 22)
                            status_str = "🟢 EN LÍNEA Y ESCANEANDO" if is_op else "🌙 PAUSA NOCTURNA (Reanuda 7:00 AM)"
                            real_cash, real_inv, real_eq = get_current_capital(is_real=True)

                            status_msg = (
                                f"🤖 *ESTADO DE CONEXIÓN STEAM INVESTOR*\n\n"
                                f"• *Estado del Bot:* `{status_str}`\n"
                                f"• *Hora Actual Perú:* `{now_peru}`\n"
                                f"• *Cartera Real en Steam:* `{CURRENCY_SYMBOL} {real_cash:.2f}`\n"
                                f"• *En Activos/Skins:* `{CURRENCY_SYMBOL} {real_inv:.2f}`\n"
                                f"• *Total Patrimonio:* `{CURRENCY_SYMBOL} {real_eq:.2f}`\n\n"
                                f"📌 *Comandos Disponibles:*\n"
                                f"• `/status` - Comprobar que el bot está activo\n"
                                f"• `/resumen` - Ver balance detallado (Real vs Simulado)\n"
                                f"• `/grafico` - Generar gráfico de rendimiento\n"
                                f"• Responder `SI` o `NO` para confirmar compras."
                            )
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id, "text": status_msg, "parse_mode": "Markdown"
                            })

            time.sleep(1)
        except Exception as e:
            time.sleep(5)

def start_telegram_listener_thread():
    if TELEGRAM_BOT_TOKEN:
        t = threading.Thread(target=run_telegram_listener, daemon=True)
        t.start()
        return t
    return None
