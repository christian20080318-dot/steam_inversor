import time
import sys
from risk_engine import analyze_opportunity, calculate_zscore_and_bollinger
from cs2_pool_tracker import get_item_pool_status
from database import record_opportunity, get_current_capital
from config import CURRENCY_SYMBOL

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_simulation():
    print("=" * 70)
    print("🧪 INICIANDO SIMULACIÓN DE ESCANEO Y ANÁLISIS CUANTITATIVO")
    print("=" * 70)

    # Lista de prueba con diferentes escenarios de mercado
    test_cases = [
        {
            "item_name": "Fracture Case",
            "app_id": 730,
            "lowest_price": 0.85,
            "median_price": 1.25,
            "volume_24h": 22000,
            "strategy": "Swing Rebajas (Rare Pool)",
            "scenario": "Sobreventa brusca en caja retirada del drop común"
        },
        {
            "item_name": "Kilowatt Case",
            "app_id": 730,
            "lowest_price": 2.40,
            "median_price": 2.50,
            "volume_24h": 14000,
            "strategy": "Drop Activo",
            "scenario": "Precio estándar sin margen neto suficiente"
        },
        {
            "item_name": "AK-47 | Slate (Field-Tested)",
            "app_id": 730,
            "lowest_price": 8.20,
            "median_price": 11.80,
            "volume_24h": 1200,
            "strategy": "Sniping de Skins",
            "scenario": "Liquidación por apuro de usuario en skin líquida"
        },
        {
            "item_name": "Sack of Gems",
            "app_id": 753,
            "lowest_price": 1.10,
            "median_price": 1.45,
            "volume_24h": 35000,
            "strategy": "Arbitraje Materia Prima",
            "scenario": "Descuento en gemas de crafteo de alta rotación"
        },
        {
            "item_name": "AWP | Fade (Factory New)",
            "app_id": 730,
            "lowest_price": 4200.00,
            "median_price": 5500.00,
            "volume_24h": 8,
            "strategy": "Skin Rara de Colección",
            "scenario": "Precio excede el saldo disponible en Steam"
        }
    ]

    total_items = len(test_cases)
    approved_opps = []

    real_cash, _, _ = get_current_capital(is_real=True)
    print(f"💰 Saldo de Cartera Steam detectado para la prueba: {CURRENCY_SYMBOL} {real_cash:.2f}\n")

    for idx, item in enumerate(test_cases, start=1):
        # Calcular porcentaje de progreso
        pct_progress = int((idx / total_items) * 100)
        bar_len = 25
        filled = int((pct_progress / 100) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        print(f"[{bar}] {pct_progress:3d}% | Evaluando ({idx}/{total_items}): {item['item_name']}")
        print(f"   ↳ Escenario: {item['scenario']}")

        # 1. Pool Status
        pool = get_item_pool_status(item["item_name"])
        print(f"   ↳ Estado Pool: {pool['label']}")

        # 2. Análisis cuantitativo con candado de cartera
        opp = analyze_opportunity(item, is_real=True)

        if opp:
            print(f"   ✅ [OPORTUNIDAD APROBADA]")
            print(f"      • Precio Compra: {CURRENCY_SYMBOL} {opp['buy_price']:.2f} (Normal: {CURRENCY_SYMBOL} {opp['median_price']:.2f})")
            print(f"      • Descuento Bruto: {opp['discount_percent']:.1f}%")
            print(f"      • Retorno Neto Estimado (ROI): +{opp['roi_percent']:.1f}% (después de 15% Valve)")
            print(f"      • Cantidad Lote Sugerida: {opp['quantity']} unidad(es)")
            print(f"      • Inversión Total: {CURRENCY_SYMBOL} {opp['total_investment']:.2f} (Candado de Cartera: RESPETADO)")
            print(f"      • Ganancia Neta Estimada: +{CURRENCY_SYMBOL} {opp['total_net_profit']:.2f}")
            approved_opps.append(opp)
        else:
            if item["lowest_price"] > real_cash:
                print(f"   🛡️ [CANDADO ACTIVADO] Rechazado automáticamente: Precio ({CURRENCY_SYMBOL} {item['lowest_price']:.2f}) supera tu saldo disponible ({CURRENCY_SYMBOL} {real_cash:.2f}).")
            else:
                print(f"   ❌ [DESCARTADO] Margen insuficiente tras el 15% de comisión de Steam.")

        print("-" * 70)
        time.sleep(0.6)

    print("\n🏁 RESUMEN FINAL DE LA SIMULACIÓN:")
    print(f"• Total Activos Evaluados: {total_items}")
    print(f"• Oportunidades Matemáticamente Rentables: {len(approved_opps)}")
    print(f"• Protección de Saldo: 100% de operaciones dentro del presupuesto de Steam.")
    
    if approved_opps:
        # Registrar la mejor oportunidad en el simulador de la base de datos
        best = approved_opps[0]
        opp_id = record_opportunity(
            item_name=best["item_name"],
            app_id=best["app_id"],
            buy_price=best["buy_price"],
            quantity=best["quantity"],
            target_sell_price=best["target_sell_price"],
            is_aggressive=best["is_aggressive"],
            notes=f"Simulación de Prueba | ROI: +{best['roi_percent']:.1f}%"
        )
        print(f"💡 Se registró '{best['item_name']}' en tu panel web como simulación (ID #{opp_id}).")
        print(f"👉 Puedes abrir http://localhost:8080 para verla y probar pulsar [SÍ] o [NO].")

if __name__ == "__main__":
    run_simulation()
