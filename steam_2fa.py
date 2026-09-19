import hmac
import hashlib
import struct
import base64
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

STEAM_SHARED_SECRET = os.getenv("STEAM_SHARED_SECRET", "")
STEAM_IDENTITY_SECRET = os.getenv("STEAM_IDENTITY_SECRET", "")
STEAM_AUTO_CONFIRM_MARKET = os.getenv("STEAM_AUTO_CONFIRM_MARKET", "false").lower() == "true"

STEAM_ALPHABET = "23456789BCDFGHJKMNPQRTVWXY"

def generate_steam_guard_code(shared_secret=None, timestamp=None):
    """
    Genera el código de 5 caracteres de Steam Guard (2FA) idéntico a la app móvil de Steam
    o SteamDesktopAuthenticator (SDA) usando HMAC-SHA1 y el alfabeto seguro de Valve.
    """
    secret = shared_secret or STEAM_SHARED_SECRET
    if not secret:
        return None

    try:
        if timestamp is None:
            timestamp = int(time.time())

        # Intervalo de 30 segundos
        interval = int(timestamp // 30)
        # Empaquetar entero de 64 bits en formato big-endian
        msg = struct.pack(">Q", interval)
        key = base64.b64decode(secret)

        mac = hmac.new(key, msg, hashlib.sha1).digest()
        offset = mac[19] & 0x0F
        code_bytes = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF

        code = []
        for _ in range(5):
            code.append(STEAM_ALPHABET[code_bytes % len(STEAM_ALPHABET)])
            code_bytes //= len(STEAM_ALPHABET)

        return "".join(code)
    except Exception as e:
        print(f"[Steam2FA Error] Error al generar código Steam Guard: {e}")
        return None

def generate_confirmation_hash(tag, identity_secret=None, timestamp=None):
    """
    Genera el hash de autenticación para consultar o aprobar confirmaciones móviles en Steam.
    """
    secret = identity_secret or STEAM_IDENTITY_SECRET
    if not secret:
        return None

    try:
        if timestamp is None:
            timestamp = int(time.time())

        tag_bytes = tag.encode("ascii") if isinstance(tag, str) else tag
        msg = struct.pack(">Q", timestamp) + tag_bytes
        key = base64.b64decode(secret)

        digest = hmac.new(key, msg, hashlib.sha1).digest()
        return base64.b64encode(digest).decode("ascii")
    except Exception as e:
        print(f"[Steam2FA Error] Error al generar hash de confirmación: {e}")
        return None

def is_2fa_configured():
    """Verifica si el usuario ha configurado los secretos 2FA en su .env"""
    return bool(STEAM_SHARED_SECRET and STEAM_IDENTITY_SECRET)

def get_2fa_status():
    """Devuelve el estado del módulo 2FA para el panel o reportes"""
    configured = is_2fa_configured()
    code = generate_steam_guard_code() if configured else None
    return {
        "configured": configured,
        "auto_confirm_market": STEAM_AUTO_CONFIRM_MARKET,
        "current_code": code,
        "security_policy": "ESTRICTA: Solo permite ventas en el Mercado de la Comunidad. Bloquea intercambios externos."
    }
