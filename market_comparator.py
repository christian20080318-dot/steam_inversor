import requests
import json
import time

USD_TO_PEN = 3.75 # Tipo de cambio referencial de Soles
STEAM_WALLET_DISCOUNT_FACTOR = 0.75 # 1 USD de saldo Steam equivale a ~0.75 USD de dinero en efectivo real

def get_csfloat_reference_price(market_hash_name):
    """
    Consulta la API pública de solo lectura de CSFloat para obtener el precio
    internacional de referencia en efectivo (USD) y compararlo con Steam (PEN).
    No requiere clave API, tarjetas bancarias ni registro.
    """
    url = "https://csfloat.com/api/v1/listings"
    params = {
        "market_hash_name": market_hash_name,
        "limit": 3,
        "sort_by": "lowest_price"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            # En CSFloat el precio viene en centavos de dólar estadounidense (cents)
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                price_cents = first_item.get("price", 0)
                if price_cents > 0:
                    price_usd = price_cents / 100.0
                    price_pen_cash = price_usd * USD_TO_PEN
                    # El valor equivalente que debería tener en la cartera de Steam
                    fair_steam_price_pen = price_pen_cash / STEAM_WALLET_DISCOUNT_FACTOR

                    return {
                        "available": True,
                        "cash_price_usd": price_usd,
                        "cash_price_pen": price_pen_cash,
                        "fair_steam_price_pen": fair_steam_price_pen,
                        "source": "CSFloat Public API"
                    }
    except Exception:
        # Fallback silencioso y seguro sin interrumpir la ejecución
        pass

    return {
        "available": False,
        "cash_price_usd": None,
        "cash_price_pen": None,
        "fair_steam_price_pen": None,
        "source": "None"
    }

def evaluate_cross_market_arbitrage(market_hash_name, steam_price_pen):
    """
    Compara el precio actual en Soles de la Cartera de Steam contra el valor
    internacional para detectar si está subvaluado.
    """
    ref = get_csfloat_reference_price(market_hash_name)
    if not ref["available"] or not ref["fair_steam_price_pen"]:
        return {
            "has_arbitrage": False,
            "discount_vs_fair_pct": 0.0,
            "details": "Sin datos externos disponibles (Evaluación puramente interna de Steam)"
        }

    fair_val = ref["fair_steam_price_pen"]
    diff = fair_val - steam_price_pen
    discount_pct = (diff / fair_val) * 100.0 if fair_val > 0 else 0.0

    has_arb = discount_pct >= 12.0 # Descuento significativo frente a paridad internacional

    return {
        "has_arbitrage": has_arb,
        "discount_vs_fair_pct": round(discount_pct, 2),
        "fair_steam_price_pen": round(fair_val, 2),
        "cash_price_usd": ref["cash_price_usd"],
        "details": f"Precio Steam: S/ {steam_price_pen:.2f} vs Valor Justo Internacional: S/ {fair_val:.2f} ({discount_pct:+.1f}%)"
    }
