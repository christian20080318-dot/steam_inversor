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

                        if cb_data.startswith("prompt_qty:") or cb_data.startswith("decision:yes:"):
                            opp_id = int(cb_data.split(":")[2]) if cb_data.startswith("decision:yes:") else int(cb_data.split(":")[1])
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM portfolio WHERE id = ?", (opp_id,))
                            item = cursor.fetchone()
                            conn.close()

                            if not item:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "Esta oportunidad ya no está pendiente o ya fue procesada."
                                })
                            else:
                                opp_qty = item["quantity"]
                                buy_price = item["buy_price"]
                                item_name = item["item_name"]
                                kb = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "1", "callback_data": f"qty:{opp_id}:1"},
                                            {"text": "2", "callback_data": f"qty:{opp_id}:2"},
                                            {"text": "3", "callback_data": f"qty:{opp_id}:3"},
                                            {"text": "4", "callback_data": f"qty:{opp_id}:4"},
                                            {"text": "5", "callback_data": f"qty:{opp_id}:5"}
                                        ],
                                        [
                                            {"text": "6", "callback_data": f"qty:{opp_id}:6"},
                                            {"text": "7", "callback_data": f"qty:{opp_id}:7"},
                                            {"text": "8", "callback_data": f"qty:{opp_id}:8"},
                                            {"text": "9", "callback_data": f"qty:{opp_id}:9"},
                                            {"text": "10", "callback_data": f"qty:{opp_id}:10"}
                                        ]
                                    ]
                                }
                                if opp_qty > 10:
                                    kb["inline_keyboard"].append([
                                        {"text": f"📦 Comprar recomendadas ({opp_qty} u.)", "callback_data": f"qty:{opp_id}:{opp_qty}"}
                                    ])
                                kb["inline_keyboard"].append([
                                    {"text": "✍️ Escribir otra cantidad en el chat", "callback_data": f"prompt_custom:{opp_id}"}
                                ])

                                prompt_msg = (
                                    f"🔢 *¿CUÁNTAS UNIDADES COMPRASTE?*\n\n"
                                    f"📦 *Ítem:* `{item_name}`\n"
                                    f"💰 *Precio Unitario:* `{CURRENCY_SYMBOL} {buy_price:.2f}`\n\n"
                                    f"👉 *Toca un botón del 1 al 10* abajo, o escribe cualquier número directamente en este chat (ejemplo: `15`, `25`, `50`)."
                                )
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id,
                                    "text": prompt_msg,
                                    "parse_mode": "Markdown",
                                    "reply_markup": kb
                                })

                        elif cb_data.startswith("qty:"):
                            parts = cb_data.split(":")
                            opp_id = int(parts[1])
                            chosen_qty = int(parts[2])

                            result = process_user_decision(opp_id, True, custom_quantity=chosen_qty)
                            if result:
                                real_cash, _, _ = get_current_capital(is_real=True)
                                msg = (
                                    f"✅ *COMPRA REGISTRADA EN TU CARTERA REAL*\n\n"
                                    f"📦 *Ítem:* `{result['item']}`\n"
                                    f"🔢 *Cantidad Comprada:* `{result['quantity']} unidad(es)`\n"
                                    f"💵 *Gasto Total:* `{CURRENCY_SYMBOL} {result['spent']:.2f}`\n"
                                    f"💼 *Saldo Restante en Steam:* `{CURRENCY_SYMBOL} {real_cash:.2f}`\n\n"
                                    f"🎯 *Monitoreo Activo:* El bot vigilará el mercado 24/7 y te avisará por aquí exactamente cuándo vender al mejor precio para asegurar tu ganancia neta."
                                )
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": msg, "parse_mode": "Markdown"
                                })

                        elif cb_data.startswith("prompt_custom:"):
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "✍️ *ESCRITURA LIBRE:* Escribe solo el número de unidades en este chat (ejemplo: `15` o `50`) y registraré tu compra con esa cantidad exacta.",
                                "parse_mode": "Markdown"
                            })

                        elif cb_data.startswith("decision:no:"):
                            opp_id = int(cb_data.split(":")[2])
                            result = process_user_decision(opp_id, False)
                            if result:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id,
                                    "text": f"ℹ️ Descartada compra real de *{result['item']}*. Se envió al Simulador Virtual para medir qué hubiera pasado.",
                                    "parse_mode": "Markdown"
                                })

                    # 2. Manejo de mensajes de texto (Comandos o texto libre 'si' / 'no')
                    elif "message" in update and "text" in update["message"]:
                        msg_obj = update["message"]
                        chat_id = msg_obj["chat"]["id"]
                        text = msg_obj["text"].strip().lower()

                        import re
                        is_plain_yes = text in ["si", "s", "sí"]
                        has_qty = False
                        custom_qty = None

                        nums = re.findall(r"\d+", text)
                        if (text.startswith("si ") or text.startswith("sí ") or text.startswith("compre ") or text.startswith("compré ")) and nums:
                            has_qty = True
                            custom_qty = int(nums[0])
                        elif text.isdigit():
                            has_qty = True
                            custom_qty = int(text)

                        if is_plain_yes:
                            # Si el usuario solo escribe 'si', le mostramos los botones del 1 al 10
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM portfolio WHERE status = 'PENDING_CONFIRMATION' ORDER BY id DESC LIMIT 1")
                            row = cursor.fetchone()
                            conn.close()

                            if row:
                                opp_id = row["id"]
                                opp_qty = row["quantity"]
                                buy_price = row["buy_price"]
                                item_name = row["item_name"]
                                kb = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "1", "callback_data": f"qty:{opp_id}:1"},
                                            {"text": "2", "callback_data": f"qty:{opp_id}:2"},
                                            {"text": "3", "callback_data": f"qty:{opp_id}:3"},
                                            {"text": "4", "callback_data": f"qty:{opp_id}:4"},
                                            {"text": "5", "callback_data": f"qty:{opp_id}:5"}
                                        ],
                                        [
                                            {"text": "6", "callback_data": f"qty:{opp_id}:6"},
                                            {"text": "7", "callback_data": f"qty:{opp_id}:7"},
                                            {"text": "8", "callback_data": f"qty:{opp_id}:8"},
                                            {"text": "9", "callback_data": f"qty:{opp_id}:9"},
                                            {"text": "10", "callback_data": f"qty:{opp_id}:10"}
                                        ]
                                    ]
                                }
                                if opp_qty > 10:
                                    kb["inline_keyboard"].append([
                                        {"text": f"📦 Comprar recomendadas ({opp_qty} u.)", "callback_data": f"qty:{opp_id}:{opp_qty}"}
                                    ])
                                kb["inline_keyboard"].append([
                                    {"text": "✍️ Escribir otra cantidad en el chat", "callback_data": f"prompt_custom:{opp_id}"}
                                ])

                                prompt_msg = (
                                    f"🔢 *¿CUÁNTAS UNIDADES COMPRASTE?*\n\n"
                                    f"📦 *Ítem:* `{item_name}`\n"
                                    f"💰 *Precio Unitario:* `{CURRENCY_SYMBOL} {buy_price:.2f}`\n\n"
                                    f"👉 *Toca un botón del 1 al 10* abajo, o escribe cualquier número directamente en este chat (ejemplo: `15`, `25`, `50`)."
                                )
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id,
                                    "text": prompt_msg,
                                    "parse_mode": "Markdown",
                                    "reply_markup": kb
                                })
                            else:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "No hay compras pendientes de confirmar en este momento."
                                })

                        elif has_qty:
                            # Si el usuario escribió un número directo (ej. '15')
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM portfolio WHERE status = 'PENDING_CONFIRMATION' ORDER BY id DESC LIMIT 1")
                            row = cursor.fetchone()
                            conn.close()

                            if row:
                                result = process_user_decision(row["id"], True, custom_quantity=custom_qty)
                                if result:
                                    real_cash, _, _ = get_current_capital(is_real=True)
                                    msg = (
                                        f"✅ *COMPRA REGISTRADA EN TU CARTERA REAL*\n\n"
                                        f"📦 *Ítem:* `{result['item']}`\n"
                                        f"🔢 *Cantidad Comprada:* `{result['quantity']} unidad(es)`\n"
                                        f"💵 *Gasto Total:* `{CURRENCY_SYMBOL} {result['spent']:.2f}`\n"
                                        f"💼 *Saldo Restante en Steam:* `{CURRENCY_SYMBOL} {real_cash:.2f}`\n\n"
                                        f"🎯 *Monitoreo Activo:* El bot vigilará el mercado 24/7 y te avisará por aquí exactamente cuándo vender al mejor precio para asegurar tu ganancia neta."
                                    )
                                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                        "chat_id": chat_id,
                                        "text": msg,
                                        "parse_mode": "Markdown"
                                    })
                            else:
                                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                    "chat_id": chat_id, "text": "No hay compras pendientes de confirmar en este momento."
                                })

                        elif text in ["no", "n", "rechazar", "cancelar"]:
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
                                        "text": f"ℹ️ Descartada compra real de *{result['item']}*. Se envió al Simulador Virtual para medir qué hubiera pasado.",
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

                        else:
                            # Si el usuario escribe cualquier otra cosa (ej. 'hola', 'como vas', etc.)
                            reply_msg = (
                                f"👋 ¡Hola! Soy tu **Steam Investor Bot**.\n\n"
                                f"Estoy activo y vigilando el mercado de Steam en tiempo real.\n\n"
                                f"📌 *Comandos que puedes enviarme:*\n"
                                f"• `/status` - Ver estado y hora en Perú\n"
                                f"• `/resumen` - Ver tu saldo en Soles y activos\n"
                                f"• `/grafico` - Ver evolución del portafolio\n"
                                f"• O responde `SI` / `NO` cuando te envíe una alerta."
                            )
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                                "chat_id": chat_id, "text": reply_msg, "parse_mode": "Markdown"
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
