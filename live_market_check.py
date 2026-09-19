import time
import sys
from steam_client import fetch_item_price
from risk_engine import analyze_opportunity, calculate_zscore_and_bollinger
from cs2_pool_tracker import get_item_pool_status
from config import CURRENCY_SYMBOL

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def live_market_scan():
    print("=" * 70)
    print("🌐 CONECTANDO A STEAM COMMUNITY MARKET EN VIVO (MONEDA: SOLES PEN)")
    print("=" * 70)

    # 5 Activos reales de alta rotación para la consulta en vivo
    live_targets = [
        {"app_id": 730, "name": "Fracture Case", "strategy": "Swing Rare Pool"},
        {"app_id": 730, "name": "Kilowatt Case", "strategy": "Drop Activo CS2"},
        {"app_id": 730, "name": "AK-47 | Slate (Field-Tested)", "strategy": "Skin Líquida CS2"},
        {"app_id": 440, "name": "Mann Co. Supply Crate Key", "strategy": "Divisa TF2"},
        {"app_id": 753, "name": "Sack of Gems", "strategy": "Materia Prima Steam"}
    ]

    total = len(live_targets)
    print(f"📡 Consultando precios oficiales de Steam en tiempo real...\n")

    for i, target in enumerate(live_targets, start=1):
        pct = int((i / total) * 100)
        bar = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
        print(f"[{bar}] {pct:3d}% | Consultando Steam para: {target['name']}...")

        data = fetch_item_price(target["app_id"], target["name"])
        time.sleep(2.5) # Pausa respetuosa para evitar rate-limit de Steam

        if not data or not data.get("lowest_price"):
            print("   ⚠️ No se pudo obtener cotización en vivo en este instante (Steam no devolvió datos).\n")
            continue

        lowest = data["lowest_price"]
        median = data.get("median_price", lowest)
        volume = data.get("volume_24h", 0)
        pool = get_item_pool_status(target["name"])
        z_info = calculate_zscore_and_bollinger(target["name"], lowest)

        print(f"   📊 DATOS REALES DE STEAM AHORA MISMO:")
        print(f"      • Precio de Venta más bajo: {CURRENCY_SYMBOL} {lowest:.2f}")
        print(f"      • Precio Mediano Reciente: {CURRENCY_SYMBOL} {median:.2f}")
        print(f"      • Volumen en las últimas 24h: {volume:,} unidades vendidas")
        print(f"      • Categoría de Oferta: {pool['label']}")
        print(f"      • Señal Cuantitativa: {z_info['signal']}")

        target["lowest_price"] = lowest
        target["median_price"] = median
        target["volume_24h"] = volume
        target["item_name"] = target["name"]

        opp = analyze_opportunity(target, is_real=True)
        if opp:
            print(f"      🔥 ¡OPORTUNIDAD REAL DETECTADA EN VIVO!")
            print(f"         ↳ Retorno Neto: +{opp['roi_percent']:.1f}% | Ganancia: +{CURRENCY_SYMBOL} {opp['total_net_profit']:.2f}")
        else:
            diff_pct = ((median - lowest) / median) * 100.0 if median > 0 else 0
            print(f"      ⚖️ Estado: Precio en equilibrio de mercado (Diferencial: {diff_pct:+.1f}% | No supera comisión neta)")

        print("-" * 70)

    print("✅ Consulta en vivo completada exitosamente contra los servidores de Steam.")

if __name__ == "__main__":
    live_market_scan()
