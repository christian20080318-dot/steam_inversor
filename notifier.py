import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import requests
from config import (
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_ID, 
    GMAIL_USER, 
    GMAIL_APP_PASSWORD, 
    GMAIL_RECIPIENT,
    CURRENCY_SYMBOL
)
from steam_client import build_steam_market_url

def send_telegram_alert(opp, opp_id, chart_path=None, ai_verdict=None):
    """
    Envía una alerta a Telegram con botones interactivos [SÍ] y [NO] y la auditoría de IA de Gemini.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[AVISO] Telegram no configurado en .env (Se omite envío por Telegram)")
        return False

    steam_url = build_steam_market_url(opp["app_id"], opp["item_name"])
    
    ai_section = ""
    break_even = round(opp['buy_price'] / 0.8695, 2)
    if ai_verdict:
        ai_verdict_badge = "✅ APROBADO" if ai_verdict.get("is_valid") else "⚠️ REVISIÓN"
        pros = ai_verdict.get('pros', f"Descuento real de +{opp['roi_percent']:.1f}% neto con {opp['volume_24h']} ventas/día.")
        cons = ai_verdict.get('cons_and_risks', f"Debes vender a más de {CURRENCY_SYMBOL} {break_even:.2f} para cubrir la comisión oficial de Valve (15%).")
        break_even = ai_verdict.get('break_even_price', break_even)
        
        ai_section = (
            f"🧠 *AUDITORÍA IA (GEMINI):* `{ai_verdict_badge}` (Confianza: {ai_verdict.get('confidence', 90)}%)\n"
            f"• *Veredicto:* _{ai_verdict.get('reason', 'Validado')}_\n\n"
            f"👍 *¿POR QUÉ ES RENTABLE? (Puntos a Favor):*\n"
            f"_{pros}_\n\n"
            f"⚠️ *POSIBLES FALLOS Y RIESGOS (¿Cuándo NO habría ganancia?):*\n"
            f"• *Precio Mínimo de Rescate (Break-even):* `{CURRENCY_SYMBOL} {break_even:.2f}` (Si vendes por debajo de esto, incurres en pérdida).\n"
            f"• *Factores de Riesgo:* _{cons}_\n\n"
        )

    mensaje = (
        f"🚨 *OPORTUNIDAD DE INVERSIÓN DETECTADA*\n\n"
        f"📦 *Producto:* `{opp['item_name']}`\n"
        f"🎯 *Estrategia:* {opp.get('strategy', 'Oportunidad')} (Retorno estimado: *{opp.get('horizon', '1 a 7 días')}*)\n"
        f"⚠️ *Nivel de Riesgo:* {opp['risk_level']}\n"
        f"📊 *Análisis Cuantitativo (Z-Score):* `{opp.get('quant_info', {}).get('z_score', 0)}` ({opp.get('quant_info', {}).get('signal', 'Normal')})\n"
        f"📦 *Estado de Drop Pool:* {opp.get('pool_info', {}).get('label', 'Mercado Regular')}\n\n"
        f"💰 *Precio Oferta Actual:* `{CURRENCY_SYMBOL} {opp['buy_price']:.2f}`\n"
        f"🏷️ *Precio Medio Habitual:* `{CURRENCY_SYMBOL} {opp['median_price']:.2f}`\n"
        f"🔢 *Cantidad Recomendada:* `{opp['quantity']} unidad(es)` (Ajustado a tu saldo disponible)\n"
        f"💵 *Inversión Sugerida:* `{CURRENCY_SYMBOL} {opp['total_investment']:.2f}` (Tu saldo: `{CURRENCY_SYMBOL} {opp.get('steam_wallet_available', 0.0):.2f}`)\n"
        f"📈 *Ganancia Neta Esperada:* `+{CURRENCY_SYMBOL} {opp['total_net_profit']:.2f}` (*ROI: +{opp['roi_percent']:.1f}%* tras comisión 15%)\n"
        f"📊 *Rotación de Mercado:* {opp['volume_24h']} ventas/día (~{opp['volume_24h'] * 30} ventas/mes)\n"
    )
    
    if opp['volume_24h'] < 10:
        mensaje += f"👻 *¡CUIDADO - ÍTEM FANTASMA!* (Liquidez extremadamente baja, muy difícil de revender rápido)\n"
    
    mensaje += (
        f"\n{ai_section}"
        f"🔗 [ABRIR LISTADO OFICIAL EN STEAM]({steam_url})\n\n"
        f"👉 *¿Compraste el producto con tu saldo de Steam?*\n"
        f"• Si compraste todas ({opp['quantity']} u.), pulsa el botón **SÍ** abajo.\n"
        f"• **¿Compraste otra cantidad?** Responde este chat con: `SI <cantidad>` (ejemplo: `SI 10` o `SI 5`) y se registrará tu gasto exacto."
    )

    # Inline Keyboard con botones de acción rápida
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"✅ SÍ, compré las {opp['quantity']} u.", "callback_data": f"decision:yes:{opp_id}"},
                {"text": "❌ NO comprar", "callback_data": f"decision:no:{opp_id}"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        
        # Enviar gráfico si está disponible
        if chart_path and os.path.exists(chart_path):
            send_telegram_photo(chart_path, caption=f"Tendencia de mercado: {opp['item_name']}")
            
        return r.status_code == 200
    except Exception as e:
        print(f"[ERROR] No se pudo enviar mensaje por Telegram: {e}")
        return False

def send_telegram_photo(image_path, caption=""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
            requests.post(url, files=files, data=data, timeout=15)
            return True
    except Exception as e:
        print(f"[ERROR] Error enviando imagen a Telegram: {e}")
        return False

def send_telegram_simple_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

def send_telegram_emergency_auth_alert():
    """Envía alerta crítica por desconexión HTTP 401 de Steam."""
    text = (
        "🚨 *EMERGENCIA: SESIÓN DE STEAM CERRADA (HTTP 401)* 🚨\n\n"
        "El bot ha perdido conexión con tu cuenta de Steam.\n"
        "El token actual (`steam_session.json`) expiró o Valve forzó una desconexión.\n\n"
        "⚠️ El sistema ya no puede leer tu saldo real en Soles.\n"
        "🔧 *Acción requerida:* Reinicia el bot o ejecuta la autenticación QR de nuevo para reconectar."
    )
    send_telegram_simple_message(text)
    print("\n[ALERTA ROJA] Sesión cerrada. Se ha enviado aviso por Telegram.\n")
    return False

def send_gmail_alert(subject, html_content, attachment_image_path=None):
    """
    Envía un reporte por Gmail mediante SMTP seguro
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not GMAIL_RECIPIENT:
        print("[AVISO] Gmail no configurado en .env (Se omite envío por correo)")
        return False

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_RECIPIENT

    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    msg_text = MIMEText(html_content, "html")
    msg_alternative.attach(msg_text)

    # Adjuntar gráfico si existe
    if attachment_image_path and os.path.exists(attachment_image_path):
        try:
            with open(attachment_image_path, "rb") as img_file:
                img = MIMEImage(img_file.read())
                img.add_header("Content-ID", "<chart_img>")
                img.add_header("Content-Disposition", "attachment", filename=os.path.basename(attachment_image_path))
                msg.attach(img)
        except Exception as e:
            print(f"[ERROR] Error adjuntando gráfico a Gmail: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_RECIPIENT, msg.as_string())
        print("[INFO] Correo enviado exitosamente a Gmail.")
        return True
    except Exception as e:
        print(f"[ERROR] Error enviando correo por Gmail: {e}")
        return False

def send_game_glitch_alert(game):
    """
    Envía una alerta de error de precio en juego de la tienda oficial de Steam a Telegram
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    mensaje = (
        f"🎮 *¡ERROR DE PRECIO EN JUEGO DETECTADO! (TIENDA STEAM)*\n\n"
        f"🕹️ *Juego:* `{game['name']}`\n"
        f"💰 *Precio con Error:* `{CURRENCY_SYMBOL} {game['final_price']:.2f}` *(Normal: {CURRENCY_SYMBOL} {game['original_price']:.2f})*\n"
        f"🔥 *Descuento Anómalo:* `-{game['discount_percent']}%` *(Posible error de empresa/decimal)*\n\n"
        f"ℹ️ *¿Qué hacer?*\n"
        f"Las empresas corrigen estos errores en 10 a 45 minutos. Si lo compras antes de que lo corrijan, la licencia queda permanentemente en tu biblioteca de Steam.\n\n"
        f"🛒 [COMPRAR JUEGO DIRECTO EN STEAM]({game['store_url']})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERROR] Error al enviar alerta de juego: {e}")
        return False
