import os
import json
import time
import base64
import random
import string
import re
import requests
import io
import qrcode
from config import STEAM_SESSION_FILE, STEAM_CURRENCY_ID, CURRENCY_SYMBOL

class SteamAuthManager:
    """
    Gestor de autenticación persistente 24/7 para Steam mediante el protocolo
    oficial de Código QR (Steam Mobile App) y Refresh Tokens OAuth.
    Permite operar en la nube o localmente sin almacenar contraseñas.
    """
    
    API_BEGIN_QR = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaQR/v1/"
    API_POLL_QR = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"
    API_FINALIZE = "https://login.steampowered.com/jwt/finalizelogin"
    
    def __init__(self, session_file=STEAM_SESSION_FILE):
        self.session_file = session_file
        self.session_data = self._load_session()
        self.http_session = requests.Session()
        self._apply_cookies_to_session()
        self.active_qr_session = None

    def _load_session(self):
        """Carga la sesión guardada desde el archivo JSON si existe"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                print(f"[SteamAuth] Error al leer archivo de sesión: {e}")
        return {
            "authenticated": False,
            "steam_id": None,
            "account_name": None,
            "refresh_token": None,
            "cookies": {},
            "wallet_balance": None,
            "last_login": None
        }

    def _save_session(self):
        """Guarda la sesión actual de forma persistente"""
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, indent=4)
        except Exception as e:
            print(f"[SteamAuth] Error al guardar archivo de sesión: {e}")

    def _apply_cookies_to_session(self):
        """Aplica las cookies guardadas a la instancia de requests.Session"""
        if self.session_data.get("cookies"):
            for domain, cookies in self.session_data["cookies"].items():
                for name, value in cookies.items():
                    self.http_session.cookies.set(name, value, domain=domain)

    def is_authenticated(self):
        """Verifica si existe un refresh token y la sesión está marcada como activa"""
        return bool(self.session_data.get("authenticated") and self.session_data.get("refresh_token"))

    def start_qr_session(self):
        """
        Inicia un desafío de autenticación QR con los servidores de Steam.
        Devuelve el challenge_url, client_id, request_id y la imagen QR en Base64.
        """
        payload = {
            "device_friendly_name": "Steam Investor Bot (24/7 Cloud)",
            "platform_type": 1,
            "website_id": "Community"
        }
        
        try:
            res = requests.post(
                self.API_BEGIN_QR,
                data={"input_json": json.dumps(payload)},
                headers={"User-Agent": "SteamInvestorBot/2.0"},
                timeout=15
            )
            
            if res.status_code == 200:
                data = res.json().get("response", {})
                client_id = data.get("client_id")
                challenge_url = data.get("challenge_url")
                request_id = data.get("request_id")
                interval = data.get("interval", 5)

                if not challenge_url:
                    return {"success": False, "error": "No se recibió challenge_url de Steam"}

                # Generar imagen QR en PNG base64
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=8,
                    border=2,
                )
                qr.add_data(challenge_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                self.active_qr_session = {
                    "client_id": client_id,
                    "request_id": request_id,
                    "challenge_url": challenge_url,
                    "interval": interval,
                    "created_at": time.time()
                }

                return {
                    "success": True,
                    "client_id": client_id,
                    "challenge_url": challenge_url,
                    "qr_image_base64": f"data:image/png;base64,{qr_base64}",
                    "interval": interval
                }
            else:
                return {"success": False, "error": f"Error HTTP {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def poll_qr_status(self, client_id=None, request_id=None):
        """
        Consulta si el usuario ya escaneó y autorizó el QR en su celular.
        Si fue exitoso, finaliza la sesión y guarda el refresh_token.
        """
        if not client_id or not request_id:
            if not self.active_qr_session:
                return {"status": "error", "message": "No hay sesión QR activa"}
            client_id = self.active_qr_session["client_id"]
            request_id = self.active_qr_session["request_id"]

        payload = {
            "client_id": str(client_id),
            "request_id": str(request_id)
        }

        try:
            res = requests.post(
                self.API_POLL_QR,
                data={"input_json": json.dumps(payload)},
                headers={"User-Agent": "SteamInvestorBot/2.0"},
                timeout=15
            )

            if res.status_code == 200:
                resp = res.json().get("response", {})
                refresh_token = resp.get("refresh_token")
                account_name = resp.get("account_name")

                if refresh_token:
                    # El usuario autorizó en su celular
                    finalize_result = self.finalize_web_session(refresh_token, account_name)
                    if finalize_result.get("success"):
                        self.active_qr_session = None
                        return {
                            "status": "approved",
                            "message": "¡Sesión autorizada exitosamente desde el celular!",
                            "account_name": self.session_data.get("account_name"),
                            "steam_id": self.session_data.get("steam_id"),
                            "wallet_balance": self.session_data.get("wallet_balance")
                        }
                    else:
                        return {"status": "error", "message": finalize_result.get("error")}
                else:
                    return {"status": "waiting", "message": "Esperando escaneo en app de Steam..."}
            else:
                return {"status": "error", "message": f"Error Steam HTTP {res.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def finalize_web_session(self, refresh_token, account_name=None):
        """
        Canjea el refresh_token con el endpoint finalizelogin de Steam
        y obtiene las cookies de autenticación permanentes.
        """
        session_id = "".join(random.choices(string.hexdigits.lower(), k=24))
        payload = {
            "nonce": refresh_token,
            "sessionid": session_id,
            "redir": "https://steamcommunity.com/my"
        }

        try:
            res = requests.post(self.API_FINALIZE, data=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                steam_id = data.get("steamID")
                transfer_info = data.get("transfer_info", [])

                if not steam_id:
                    return {"success": False, "error": f"Fallo al finalizar login: {data}"}

                # Configurar sessionid inicial
                self.http_session.cookies.set("sessionid", session_id, domain="steamcommunity.com")
                self.http_session.cookies.set("sessionid", session_id, domain="store.steampowered.com")

                # Reclamar tokens en steamcommunity y store
                for item in transfer_info:
                    url = item.get("url")
                    params = item.get("params", {})
                    if url and params:
                        try:
                            self.http_session.post(url, data=params, timeout=10)
                        except Exception as transfer_err:
                            print(f"[SteamAuth] Error en transfer url {url}: {transfer_err}")

                # Extraer cookies generadas
                cookies_dict = {
                    "steamcommunity.com": {},
                    "store.steampowered.com": {}
                }
                for cookie in self.http_session.cookies:
                    domain_key = "steamcommunity.com" if "steamcommunity" in cookie.domain else "store.steampowered.com"
                    cookies_dict[domain_key][cookie.name] = cookie.value

                self.session_data.update({
                    "authenticated": True,
                    "steam_id": steam_id,
                    "account_name": account_name or self.session_data.get("account_name"),
                    "refresh_token": refresh_token,
                    "cookies": cookies_dict,
                    "last_login": time.strftime("%Y-%m-%d %H:%M:%S")
                })

                # Consultar saldo real de la billetera
                self.fetch_wallet_balance()
                self._save_session()
                return {"success": True, "steam_id": steam_id}
            else:
                return {"success": False, "error": f"HTTP {res.status_code} al finalizar login"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def refresh_session_if_needed(self):
        """
        Renueva las cookies web usando el refresh_token persistente.
        Se puede llamar periódicamente en segundo plano (24/7).
        """
        if not self.is_authenticated():
            return False
        
        refresh_token = self.session_data.get("refresh_token")
        if not refresh_token:
            return False

        print("[SteamAuth] Renovando cookies de sesión en segundo plano...")
        res = self.finalize_web_session(refresh_token, self.session_data.get("account_name"))
        return res.get("success", False)

    def fetch_wallet_balance(self):
        """
        Obtiene el saldo real de la cartera de Steam en Soles (PEN)
        desde la página autenticada de la comunidad / mercado.
        """
        if not self.is_authenticated():
            return None

        try:
            res = self.http_session.get(
                "https://steamcommunity.com/market/",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"},
                timeout=12
            )
            
            if res.status_code == 200:
                # Buscar saldo en el header de la web de Steam
                # Patrón ej: id="marketWalletBalanceAmount">S/. 123.45</span>
                match = re.search(r'id=["\']marketWalletBalanceAmount["\']>([^<]+)<', res.text)
                if not match:
                    match = re.search(r'id=["\']header_wallet_balance["\']>([^<]+)<', res.text)
                
                if match:
                    raw_str = match.group(1).strip()
                    # Limpiar texto para obtener float
                    clean = re.sub(r"[^\d,\.]", "", raw_str)
                    if "," in clean and "." in clean:
                        clean = clean.replace(",", "")
                    elif "," in clean:
                        clean = clean.replace(",", ".")
                    
                    val = float(clean) if clean else None
                    if val is not None:
                        self.session_data["wallet_balance"] = val
                        self._save_session()
                        return val
        except Exception as e:
            print(f"[SteamAuth] Error al consultar saldo de cartera: {e}")
            
        return self.session_data.get("wallet_balance")

    def get_status(self):
        """Devuelve el estado de conexión para la interfaz web o Telegram"""
        return {
            "authenticated": self.is_authenticated(),
            "steam_id": self.session_data.get("steam_id"),
            "account_name": self.session_data.get("account_name") or "Usuario Steam",
            "wallet_balance": self.session_data.get("wallet_balance"),
            "currency": CURRENCY_SYMBOL,
            "last_login": self.session_data.get("last_login")
        }

    def logout(self):
        """Cierra la sesión y limpia las credenciales guardadas"""
        self.session_data = {
            "authenticated": False,
            "steam_id": None,
            "account_name": None,
            "refresh_token": None,
            "cookies": {},
            "wallet_balance": None,
            "last_login": None
        }
        self.active_qr_session = None
        self.http_session.cookies.clear()
        self._save_session()
        return True

# Instancia global accesible para todo el sistema
steam_auth_mgr = SteamAuthManager()
