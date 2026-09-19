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
    if ai_verdict:
        ai_verdict_badge = "✅ APROBADO" if ai_verdict.get("is_valid") else "⚠️ REVISIÓN"
        ai_section = (
            f"🧠 *Auditoría IA (Gemini):* `{ai_verdict_badge}` (Confianza: {ai_verdict.get('confidence', 90)}%)\n"
            f"💬 _{ai_verdict.get('reason', 'Validado por coherencia de mercado')}_\n\n"
        )

    mensaje = (
        f"🚨 *OPORTUNIDAD DE INVERSIÓN DETECTADA*\n\n"
        f"📦 *Producto:* `{opp['item_name']}`\n"
        f"🎯 *Estrategia:* {opp.get('strategy', 'Oportunidad')} (Retorno: *{opp.get('horizon', '1 a 7 días')}*)\n"
        f"⚠️ *Nivel de Riesgo:* {opp['risk_level']}\n"
        f"📊 *Análisis Cuantitativo (Z-Score):* `{opp.get('quant_info', {}).get('z_score', 0)}` ({opp.get('quant_info', {}).get('signal', 'Normal')})\n"
        f"📦 *Estado de Drop Pool:* {opp.get('pool_info', {}).get('label', 'Mercado Regular')}\n"
        f"💰 *Precio Unitario:* `{CURRENCY_SYMBOL} {opp['buy_price']:.2f}` (Precio normal: {CURRENCY_SYMBOL} {opp['median_price']:.2f})\n"
        f"🔢 *Cantidad Recomendada:* `{opp['quantity']} unidad(es)` (Ajustado a tu saldo)\n"
        f"💵 *Inversión Total en Cartera:* `{CURRENCY_SYMBOL} {opp['total_investment']:.2f}` / Saldo Steam: `{CURRENCY_SYMBOL} {opp.get('steam_wallet_available', 0.0):.2f}`\n"
        f"📈 *Ganancia Neta Estimada:* `+{CURRENCY_SYMBOL} {opp['total_net_profit']:.2f}` (*ROI: +{opp['roi_percent']:.1f}%* tras comisión)\n"
        f"📊 *Volumen 24h:* {opp['volume_24h']} ventas/día\n\n"
        f"{ai_section}"
        f"ℹ️ *¿Qué hace el enlace?*\n"
        f"Abre directamente el mercado de Steam para que compres manualmente la cantidad indicada al precio ofertado.\n\n"
        f"🔗 [ABRIR LISTADO EN STEAM]({steam_url})\n\n"
        f"👉 *¿Compraste el producto con tu dinero real?*\n"
        f"Pulsa *SÍ* para registrarlo en tu cartera real o *NO* para guardarlo solo como simulación."
    )

    # Inline Keyboard con botones de acción rápida
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ SÍ, compré el producto", "callback_data": f"decision:yes:{opp_id}"},
                {"text": "❌ NO, no lo compré", "callback_data": f"decision:no:{opp_id}"}
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
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"[ERROR] Error enviando texto a Telegram: {e}")
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
