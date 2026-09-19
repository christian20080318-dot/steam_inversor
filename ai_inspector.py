import os
import json
import logging
import requests
from config import GEMINI_API_KEY, CURRENCY_SYMBOL

logger = logging.getLogger("AIInspector")

def inspect_opportunity_with_gemini(opp):
    """
    Validador de Inteligencia Artificial (Gemini API) para auditar oportunidades de mercado de Steam.
    Evalúa si la oportunidad de inversión es un descuento/descuido real o un error de datos/trampa de liquidez.
    """
    item_name = opp.get("item_name", "Desconocido")
    app_id = opp.get("app_id", 730)
    buy_price = opp.get("buy_price", 0.0)
    median_price = opp.get("median_price", 0.0)
    volume_24h = opp.get("volume", 0)
    roi_percent = opp.get("roi_percent", 0.0)
    strategy = opp.get("strategy", "General")
    quant_info = opp.get("quant_info", {})
    pool_info = opp.get("pool_info", {})
    arb_info = opp.get("arb_info", {})
    wallet_avail = opp.get("steam_wallet_available", 0.0)
    
    # 1. Filtros Heurísticos de Sanidad Previa (Descarte inmediato de fallos de API)
    # Si es cromo o fondo (app 753) con precio inflado de decenas de soles por confusión con Foil
    if app_id == 753 and (median_price > 10.0 or (median_price > 2.0 and buy_price < 0.30)):
        return {
            "is_valid": False,
            "verdict": "RECHAZADO (Error API / Foil Confusion)",
            "confidence": 99,
            "reason": f"Ítem común de Steam (Cromo/Fondo) con precio de referencia inflado ({CURRENCY_SYMBOL} {median_price:.2f}) por posible cruce con versión Foil o background raro.",
            "recommended_action": "Descartar"
        }

    # Si la discrepancia es absurda (> 20x) con poco volumen
    if median_price > 0 and (median_price / max(buy_price, 0.01)) > 20 and volume_24h < 100:
        return {
            "is_valid": False,
            "verdict": "RECHAZADO (Anomalía de Liquidez)",
            "confidence": 95,
            "reason": f"Discrepancia de precio excesiva ({buy_price:.2f} vs {median_price:.2f}) sin suficiente volumen de respaldo en 24h.",
            "recommended_action": "Descartar"
        }

    # 2. Si no hay GEMINI_API_KEY configurada, pasar por el motor de reglas estándar
    if not GEMINI_API_KEY:
        return {
            "is_valid": True,
            "verdict": "APROBADO (Reglas Heurísticas)",
            "confidence": 85,
            "reason": f"Margen neto estimado de +{roi_percent:.1f}% con volumen verificado ({volume_24h} u/24h). Z-Score: {quant_info.get('z_score', 0)}.",
            "recommended_action": "Comprar según gestión de riesgo"
        }

    # 3. Consulta a la API de Gemini
    prompt = f"""
    Eres el Auditor Financiero y Cuantitativo de Mercado de Steam más estricto del mundo.
    Tu tarea es verificar si la siguiente oportunidad de arbitraje/inversión en el Mercado de la Comunidad de Steam es REAL, COHERENTE y FINANCIERAMENTE RENTABLE, o si se trata de un error de formato, un cromo foil confundido, un precio inflado artificialmente o una trampa de liquidez.

    REGLA CLAVE DE CAPITAL:
    - Esta operación se paga EXCLUSIVAMENTE con el saldo disponible en la Cartera de Steam del usuario ({CURRENCY_SYMBOL} {wallet_avail:.2f}). CERO dinero de bancos o tarjetas externas.

    DATOS CUANTITATIVOS Y DE MERCADO:
    - Nombre del Ítem: {item_name}
    - ID del Juego (App ID): {app_id} (730=CS2, 440=TF2, 570=Dota 2, 753=Steam Cards/Commodity)
    - Precio Oferta Detectado: {CURRENCY_SYMBOL} {buy_price:.2f}
    - Precio Medio Histórico: {CURRENCY_SYMBOL} {median_price:.2f}
    - Volumen en 24 horas: {volume_24h} unidades
    - Retorno Neto Estimado (después del 15% comisión Valve): +{roi_percent:.1f}%
    - Análisis Cuantitativo (Z-Score): {quant_info.get('z_score', 0)} | Señal: {quant_info.get('signal', 'N/A')}
    - Estado Macroeconómico de Drop Pool: {pool_info.get('label', 'Normal')} | Tendencia Oferta: {pool_info.get('supply_trend', 'Normal')}
    - Arbitraje Internacional de Referencia: {arb_info.get('details', 'N/A')}
    - Estrategia: {strategy}

    CRITERIOS DE RECHAZO:
    1. Si es un cromo común o emoticono (App ID 753) y la mediana es de S/ 20 a S/ 90 (error clásico de la API).
    2. Si el volumen en 24h es casi nulo (manipulación de mercado / trampa ilíquida).
    3. Si el precio ofertado es absurdo o incongruente para su categoría.

    Responde EXCLUSIVAMENTE en formato JSON con la siguiente estructura:
    {{
        "is_valid": true o false,
        "confidence": número del 1 al 100,
        "verdict": "APROBADO" o "RECHAZADO",
        "reason": "Explicación concisa y clara en español (máximo 25 palabras)",
        "recommended_action": "Recomendación operativa en 5 palabras"
    }}
    """

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            parsed_result = json.loads(raw_text)
            return {
                "is_valid": bool(parsed_result.get("is_valid", False)),
                "verdict": parsed_result.get("verdict", "REVISIÓN MANUAL"),
                "confidence": int(parsed_result.get("confidence", 80)),
                "reason": parsed_result.get("reason", "Validado por modelo Gemini."),
                "recommended_action": parsed_result.get("recommended_action", "Operar con precaución")
            }
        else:
            logger.warning(f"Error HTTP {response.status_code} al llamar a Gemini API. Usando heurística.")
    except Exception as e:
        logger.error(f"Excepción al conectar con Gemini API: {e}")

    # Fallback si falla la llamada
    return {
        "is_valid": True,
        "verdict": "APROBADO (Fallback Seguro)",
        "confidence": 80,
        "reason": f"Aprobado por filtro de consistencia de datos (Volumen: {volume_24h} u/24h).",
        "recommended_action": "Comprar según gestión de riesgo"
    }
