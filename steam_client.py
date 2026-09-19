import requests
import time
import re
import random
from config import STEAM_CURRENCY_ID, NET_MULTIPLIER
from database import get_connection, update_real_wallet_balance
from steam_auth import steam_auth_mgr

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Lista ampliada y diversificada de 36 activos según las 4 estrategias
WATCHLIST = [
    # ESTRATEGIA 1: Sniping de Skins Populares (1 a 7 días / Errores de precio)
    {"app_id": 730, "name": "AK-47 | Slate (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "AK-47 | Phantom Disruptor (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "AK-47 | Elite Build (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "AWP | Atheris (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "AWP | Mortis (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "AWP | Duality (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "USP-S | Cortex (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "USP-S | Cyrex (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "M4A4 | Evil Daimyo (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "M4A1-S | Night Terror (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "M4A1-S | Decimator (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "Desert Eagle | Mecha Industries (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "Desert Eagle | Trigger Discipline (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "Glock-18 | Water Elemental (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},
    {"app_id": 730, "name": "Glock-18 | Vogue (Field-Tested)", "strategy": "Sniping de Skin", "horizon": "1 a 7 días"},

    # ESTRATEGIA 2: Buy Orders en Ítems Líquidos (Diario / Rotación continua)
    {"app_id": 730, "name": "Revolution Case", "strategy": "Buy Orders Líquidas", "horizon": "1 a 3 días"},
    {"app_id": 730, "name": "Dreams & Nightmares Case", "strategy": "Buy Orders Líquidas", "horizon": "1 a 3 días"},
    {"app_id": 730, "name": "Recoil Case", "strategy": "Buy Orders Líquidas", "horizon": "1 a 3 días"},
    {"app_id": 730, "name": "Snakebite Case", "strategy": "Buy Orders Líquidas", "horizon": "1 a 3 días"},
    {"app_id": 440, "name": "Mann Co. Supply Crate Key", "strategy": "Divisa Líquida TF2", "horizon": "Diario / Inmediato"},
    {"app_id": 440, "name": "Tour of Duty Ticket", "strategy": "Divisa Líquida TF2", "horizon": "Diario / Inmediato"},

    # ESTRATEGIA 3: Cajas Clásicas y Rebajas (2 a 4 semanas)
    {"app_id": 730, "name": "Fracture Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Kilowatt Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Clutch Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Prisma 2 Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Danger Zone Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Horizon Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Chroma 3 Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "Gamma 2 Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},
    {"app_id": 730, "name": "CS20 Case", "strategy": "Swing Rebajas/Escasez", "horizon": "2 a 4 semanas"},

    # ESTRATEGIA 4: Cápsulas de Torneos Majors (Mediano / Largo Plazo)
    {"app_id": 730, "name": "Paris 2023 Contenders Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Paris 2023 Legends Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Paris 2023 Champions Autograph Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Copenhagen 2024 Challengers Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Copenhagen 2024 Contenders Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Antwerp 2022 Challengers Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},
    {"app_id": 730, "name": "Stockholm 2021 Contenders Sticker Capsule", "strategy": "Cápsula de Major", "horizon": "1 a 6 meses"},

    # ESTRATEGIA 5: Micro-Arbitraje de Centavos Continuos (Alta Rotación Diaria)
    # A. Graffitis Sellados de CS2 (Drops continuos masivos)
    {"app_id": 730, "name": "Sealed Graffiti | Salt (Tracer Yellow)", "strategy": "Micro-Centavos (Graffiti)", "horizon": "Horas / 1 día"},
    {"app_id": 730, "name": "Sealed Graffiti | GGWP (Tiger Orange)", "strategy": "Micro-Centavos (Graffiti)", "horizon": "Horas / 1 día"},
    {"app_id": 730, "name": "Sealed Graffiti | EZ (War Pig Pink)", "strategy": "Micro-Centavos (Graffiti)", "horizon": "Horas / 1 día"},

    # B. Skins de Centavos para Contratos CS2 (Trade-Up Fillers)
    {"app_id": 730, "name": "P250 | Sand Dune (Field-Tested)", "strategy": "Micro-Centavos (Trade-Up Filler)", "horizon": "Horas / 1 día"},
    {"app_id": 730, "name": "Nova | Predator (Field-Tested)", "strategy": "Micro-Centavos (Trade-Up Filler)", "horizon": "Horas / 1 día"},
    {"app_id": 730, "name": "P90 | Sand Spray (Field-Tested)", "strategy": "Micro-Centavos (Trade-Up Filler)", "horizon": "Horas / 1 día"},
    {"app_id": 730, "name": "SG 553 | Army Sheen (Field-Tested)", "strategy": "Micro-Centavos (Trade-Up Filler)", "horizon": "Horas / 1 día"},

    # C. Cosméticos Líquidos Comunes de Dota 2
    {"app_id": 570, "name": "Inscribed The Fiend Cleaver", "strategy": "Micro-Centavos (Dota 2)", "horizon": "Horas / 1 día"},
    {"app_id": 570, "name": "Bracers of the Eastern Range", "strategy": "Micro-Centavos (Dota 2)", "horizon": "Horas / 1 día"},

    # D. Cromos Ultra-Populares de Steam (Subida de nivel continua)
    {"app_id": 753, "name": "730-Anarchist", "strategy": "Micro-Centavos (Cromo CS2)", "horizon": "Horas / 1 día"},
    {"app_id": 753, "name": "730-Balkan", "strategy": "Micro-Centavos (Cromo CS2)", "horizon": "Horas / 1 día"},
    {"app_id": 753, "name": "440-Heavy", "strategy": "Micro-Centavos (Cromo TF2)", "horizon": "Horas / 1 día"},

    # E. Materias Primas y Gemas de Steam (Alta liquidez comercial)
    {"app_id": 753, "name": "Sack of Gems", "strategy": "Arbitraje de Gemas/Booster", "horizon": "Diario / Reutilizable"}
]

def clean_price_string(price_str):
    """Convierte texto como 'S/. 3.45', 'S/ 3,45' o 'S/. 1,250.00' a float"""
    if not price_str:
        return None
    clean = re.sub(r"[^\d,\.]", "", price_str).strip()
    if not clean:
        return None
    
    if "," in clean and "." in clean:
        last_comma = clean.rfind(",")
        last_dot = clean.rfind(".")
        if last_comma > last_dot:
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(",", "")
    elif "," in clean:
        clean = clean.replace(",", ".")
    
    try:
        return float(clean)
    except ValueError:
        return None

def fetch_item_price(app_id, market_hash_name):
    """
    Consulta la API pública de Steam para un ítem dado en Soles (currency=27)
    Endpoint: https://steamcommunity.com/market/priceoverview/
    """
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "country": "PE",
        "currency": STEAM_CURRENCY_ID,
        "appid": app_id,
        "market_hash_name": market_hash_name
    }
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-PE,es;q=0.9,en;q=0.8"
    }

    try:
        # Si la cuenta está autenticada, usamos la sesión persistente para evitar bloqueos
        client = steam_auth_mgr.http_session if steam_auth_mgr.is_authenticated() else requests
        response = client.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 429:
            print("[ALERTA] Rate limit alcanzado en Steam (HTTP 429). Esperando 30 segundos...")
            time.sleep(30)
            return None
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                lowest_price = clean_price_string(data.get("lowest_price"))
                median_price = clean_price_string(data.get("median_price"))
                volume_str = data.get("volume", "0").replace(",", "").replace(".", "")
                volume = int(volume_str) if volume_str.isdigit() else 0
                
                # Guardar en histórico de precios para gráficos
                if lowest_price:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO price_history (item_name, price, volume_24h, timestamp)
                    VALUES (?, ?, ?, datetime('now'))
                    """, (market_hash_name, lowest_price, volume))
                    conn.commit()
                    conn.close()

                return {
                    "item_name": market_hash_name,
                    "app_id": app_id,
                    "lowest_price": lowest_price,
                    "median_price": median_price,
                    "volume_24h": volume,
                    "raw": data
                }
    except Exception as e:
        print(f"[ERROR] Error al consultar {market_hash_name}: {e}")
    return None

def build_steam_market_url(app_id, market_hash_name):
    """Construye el enlace directo a la ficha del ítem en el mercado de Steam"""
    encoded_name = requests.utils.quote(market_hash_name)
    return f"https://steamcommunity.com/market/listings/{app_id}/{encoded_name}"

def build_steam_store_url(app_id):
    """Construye el enlace directo a la página del juego en la tienda oficial de Steam"""
    return f"https://store.steampowered.com/app/{app_id}/"

def fetch_steam_game_glitches():
    """
    Consulta las ofertas y destacados de la Tienda de Steam en Soles peruanos (PEN).
    Detecta juegos con descuentos anómalos (errores de precio / glitch > 80% o precios a céntimos).
    """
    url = "https://store.steampowered.com/api/featuredcategories"
    params = {"cc": "pe", "l": "spanish"}
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-PE,es;q=0.9,en;q=0.8"
    }

    glitches = []
    try:
        r = requests.get(url, params=params, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            specials = data.get("specials", {}).get("items", [])
            top_sellers = data.get("top_sellers", {}).get("items", [])
            all_items = specials + [item for item in top_sellers if item.get("discounted")]

            seen_ids = set()
            for g in all_items:
                game_id = g.get("id")
                if not game_id or game_id in seen_ids:
                    continue
                seen_ids.add(game_id)

                discount_pct = g.get("discount_percent", 0)
                orig_cents = g.get("original_price", 0)
                final_cents = g.get("final_price", 0)

                orig_soles = orig_cents / 100.0
                final_soles = final_cents / 100.0

                # Criterios de Glitch / Error Humano:
                # 1. Descuento extremo >= 85% en juegos de más de S/ 40
                # 2. Descuento >= 90% en cualquier juego
                # 3. Juegos caros (> S/ 80) puestos a menos de S/ 15
                is_glitch = False
                if discount_pct >= 88:
                    is_glitch = True
                elif orig_soles >= 50.0 and discount_pct >= 80 and final_soles <= 12.0:
                    is_glitch = True
                elif orig_soles >= 90.0 and final_soles <= 10.0:
                    is_glitch = True

                if is_glitch:
                    glitches.append({
                        "id": game_id,
                        "name": g.get("name"),
                        "original_price": orig_soles,
                        "final_price": final_soles,
                        "discount_percent": discount_pct,
                        "header_image": g.get("header_image", ""),
                        "store_url": build_steam_store_url(game_id)
                    })
    except Exception as e:
        print(f"[ERROR] Error al consultar tienda de juegos de Steam: {e}")

    return glitches

def sync_live_steam_wallet():
    """
    Si hay una sesión activa de Steam (mediante QR / refresh_token),
    consulta el saldo real de la cuenta y lo sincroniza en la base de datos.
    """
    if steam_auth_mgr.is_authenticated():
        bal = steam_auth_mgr.fetch_wallet_balance()
        if bal is not None:
            update_real_wallet_balance(bal)
            return bal
    return None
