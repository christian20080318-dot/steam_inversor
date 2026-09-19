import os
from dotenv import load_dotenv

load_dotenv()

# Moneda: 27 es el código oficial de Steam para Soles Peruanos (PEN)
STEAM_CURRENCY_ID = int(os.getenv("STEAM_CURRENCY_ID", 27))
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "S/")

# Presupuesto y Gestión de Capital
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", 500.00))
# Porcentaje moderado de asignación por compra (ej. 25% del capital disponible)
MODERATE_RISK_PERCENT = float(os.getenv("MODERATE_RISK_PERCENT", 0.25))

# Límite de operaciones agresivas diarias
MAX_AGGRESSIVE_TRADES_PER_DAY = int(os.getenv("MAX_AGGRESSIVE_TRADES_PER_DAY", 3))

# Horario operativo en hora de Perú (UTC-5)
TIMEZONE = os.getenv("TIMEZONE", "America/Lima")
START_HOUR = int(os.getenv("START_HOUR", 7))   # 7:00 AM
END_HOUR = int(os.getenv("END_HOUR", 22))      # 10:00 PM

# Intervalo de chequeo de mercado (en minutos)
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 30))

# Comisión oficial de Steam (15% total aproximado = 5% Valve + 10% juego, corte neto ~0.8695)
STEAM_COMMISSION_FEE = float(os.getenv("STEAM_COMMISSION_FEE", 0.15))
NET_MULTIPLIER = 1.0 - (STEAM_COMMISSION_FEE / (1.0 + STEAM_COMMISSION_FEE)) # ~0.8695

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Gmail SMTP
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "")

# Google Gemini AI API Key (Auditor de Mercado Inteligente)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Sesión Persistente de Steam (QR Login / Refresh Token)
STEAM_SESSION_FILE = os.getenv("STEAM_SESSION_FILE", "steam_session.json")
STEAM_AUTO_REFRESH = os.getenv("STEAM_AUTO_REFRESH", "true").lower() == "true"
