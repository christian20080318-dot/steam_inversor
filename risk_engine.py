import math
from config import (
    MODERATE_RISK_PERCENT, 
    MAX_AGGRESSIVE_TRADES_PER_DAY, 
    NET_MULTIPLIER,
    CURRENCY_SYMBOL
)
from database import get_current_capital, get_today_aggressive_count, get_connection
from cs2_pool_tracker import get_item_pool_status
from market_comparator import evaluate_cross_market_arbitrage

def calculate_zscore_and_bollinger(item_name, current_price):
    """
    Calcula el Z-Score cuantitativo y Bandas de Bollinger a partir del
    historial de precios guardado en la base de datos (últimos 30 registros).
    Fórmula: Z = (Precio - Media) / Desviación Estándar.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT price FROM price_history 
            WHERE item_name = ? 
            ORDER BY id DESC LIMIT 30
        """, (item_name,))
        rows = cursor.fetchall()
        conn.close()

        prices = [float(r["price"]) for r in rows if r["price"] and r["price"] > 0]
        if len(prices) < 3:
            return {
                "z_score": 0.0,
                "mean": current_price,
                "std_dev": 0.0,
                "is_oversold": False,
                "signal": "Sin historial suficiente (Evaluación inicial)"
            }

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)

        if std_dev <= 0.0001:
            return {
                "z_score": 0.0,
                "mean": round(mean, 2),
                "std_dev": 0.0,
                "is_oversold": False,
                "signal": "Precio Estable / Sin Volatilidad"
            }

        z_score = (current_price - mean) / std_dev
        is_oversold = z_score <= -1.8

        if is_oversold:
            signal = f"🔥 SOBREVENTA ESTADÍSTICA (Z: {z_score:.2f} < -1.8 - Rebote Probable)"
        elif z_score <= -1.0:
            signal = f"📉 Descuento Moderado (Z: {z_score:.2f})"
        elif z_score >= 1.8:
            signal = f"⚠️ Sobreprecio / Burbuja (Z: {z_score:.2f})"
        else:
            signal = f"⚖️ Rango Normal de Mercado (Z: {z_score:.2f})"

        return {
            "z_score": round(z_score, 2),
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "is_oversold": is_oversold,
            "signal": signal
        }
    except Exception as e:
        return {
            "z_score": 0.0,
            "mean": current_price,
            "std_dev": 0.0,
            "is_oversold": False,
            "signal": f"Error cuantitativo: {e}"
        }

def analyze_opportunity(item_data, is_real=False):
    """
    Evalúa si un ítem representa una compra recomendada con:
    1. Candado Estricto de Saldo de Cartera Steam (CERO dinero de banco).
    2. Motor Cuantitativo (Z-Score y Reversión a la Media).
    3. Categorización macroeconómica de Drop Pool (CS2).
    4. Arbitraje de paridad con mercado internacional.
    """
    lowest_price = item_data.get("lowest_price")
    median_price = item_data.get("median_price")
    volume_24h = item_data.get("volume_24h", 0)
    item_name = item_data.get("item_name")
    
    if not lowest_price or not median_price or lowest_price <= 0:
        return None

    # Normalizar median_price si Steam desfasó decimales
    if lowest_price > 0 and median_price > lowest_price * 50:
        if abs((median_price / 1000.0) - lowest_price) < lowest_price:
            median_price = median_price / 1000.0

    # CANDADO ESTRICTO DE CARTERA STEAM:
    # Solo se evalúa con el efectivo que realmente hay disponible en Steam
    cash_balance, _, _ = get_current_capital(is_real=is_real)
    if cash_balance <= 0 or lowest_price > cash_balance:
        # Imposible comprar: excede el saldo actual de la cartera de Steam
        return None

    # Análisis de Drop Pool de CS2
    pool_info = get_item_pool_status(item_name)

    # Análisis Cuantitativo (Z-Score)
    quant_info = calculate_zscore_and_bollinger(item_name, lowest_price)

    # Comparación de mercado externa (CSFloat)
    arb_info = evaluate_cross_market_arbitrage(item_name, lowest_price)

    # Margen neto tras la comisión oficial del 15% de Steam
    net_received_if_sold_at_median = median_price * NET_MULTIPLIER
    net_profit_per_unit = net_received_if_sold_at_median - lowest_price
    roi_percent = (net_profit_per_unit / lowest_price) * 100.0
    discount_vs_median = ((median_price - lowest_price) / median_price) * 100.0

    # Filtro mínimo de ROI según tipo de activo
    is_penny = lowest_price <= 1.00
    min_roi = 7.0 if (is_penny or quant_info["is_oversold"] or arb_info["has_arbitrage"]) else 11.5
    if roi_percent < min_roi:
        return None

    # Clasificación de riesgo
    is_aggressive = 1 if (discount_vs_median >= 35.0 or (volume_24h < 100 and roi_percent >= 25.0)) else 0
    if is_aggressive:
        today_aggressive = get_today_aggressive_count()
        if today_aggressive >= MAX_AGGRESSIVE_TRADES_PER_DAY:
            return None

    # Asignación prudente de capital (máximo porcentaje configurado del saldo Steam)
    allocation_budget = cash_balance * MODERATE_RISK_PERCENT
    if is_penny:
        allocation_budget = min(allocation_budget, 15.0) # Límite para activos de centavos

    # Cantidad sugerida según presupuesto y volumen de absorción (máximo 5% del volumen 24h)
    max_by_budget = int(allocation_budget / lowest_price)
    max_by_volume = max(1, int(volume_24h * 0.05)) if volume_24h > 0 else 1

    recommended_quantity = min(max_by_budget, max_by_volume)
    if is_penny and recommended_quantity >= 5:
        recommended_quantity = (recommended_quantity // 5) * 5
    elif recommended_quantity < 1:
        recommended_quantity = 1

    # Asegurar con candado de hierro que nunca supere el saldo en efectivo de Steam
    total_investment = recommended_quantity * lowest_price
    if total_investment > cash_balance:
        recommended_quantity = int(cash_balance / lowest_price)
        total_investment = recommended_quantity * lowest_price

    if recommended_quantity <= 0:
        return None

    total_net_profit = net_profit_per_unit * recommended_quantity

    risk_label = "MICRO-CENTAVOS" if is_penny else ("AGRESIVO (Raro)" if is_aggressive else "MODERADO")
    if quant_info["is_oversold"]:
        risk_label += " + SOBREVENTA CUANTITATIVA"

    return {
        "item_name": item_name,
        "app_id": item_data.get("app_id"),
        "buy_price": lowest_price,
        "median_price": median_price,
        "target_sell_price": median_price,
        "quantity": recommended_quantity,
        "total_investment": total_investment,
        "net_profit_per_unit": net_profit_per_unit,
        "total_net_profit": total_net_profit,
        "roi_percent": roi_percent,
        "discount_percent": discount_vs_median,
        "volume_24h": volume_24h,
        "strategy": item_data.get("strategy", "Oportunidad General"),
        "horizon": pool_info.get("recommended_horizon", item_data.get("horizon", "1 a 7 días")),
        "is_aggressive": is_aggressive,
        "risk_level": risk_label,
        "pool_info": pool_info,
        "quant_info": quant_info,
        "arb_info": arb_info,
        "steam_wallet_available": cash_balance
    }
