import sys
import datetime
from database import get_connection, get_current_capital, DB_PATH
from chart_generator import generate_portfolio_chart
from config import CURRENCY_SYMBOL

def print_menu():
    print("\n" + "="*55)
    print("🛠️  CONSOLA DE INYECCIÓN MANUAL Y GESTIÓN DE CAPITAL")
    print("="*55)
    real_cash, real_inv, real_eq = get_current_capital(is_real=True)
    sim_cash, sim_inv, sim_eq = get_current_capital(is_real=False)
    print(f"💰 CARTERA REAL:      Efectivo: {CURRENCY_SYMBOL} {real_cash:.2f} | Inv: {CURRENCY_SYMBOL} {real_inv:.2f} | Total: {CURRENCY_SYMBOL} {real_eq:.2f}")
    print(f"🎮 CARTERA SIMULADA:  Efectivo: {CURRENCY_SYMBOL} {sim_cash:.2f} | Inv: {CURRENCY_SYMBOL} {sim_inv:.2f} | Total: {CURRENCY_SYMBOL} {sim_eq:.2f}")
    print("="*55)
    print("1. Inyectar compra manual en Cartera Real (Registrar ítem que compraste)")
    print("2. Modificar / Recargar saldo de efectivo en Soles")
    print("3. Forzar Cierre de Día (10:00 PM) y generar gráficos (3d / 7d / 30d)")
    print("4. Ver posiciones activas")
    print("5. Salir")
    print("="*55)

def inject_manual_purchase():
    print("\n--- REGISTRAR COMPRA MANUAL REAL ---")
    item_name = input("Nombre del ítem (ej. Snakebite Case): ").strip()
    if not item_name:
        return
    try:
        buy_price = float(input(f"Precio unitario pagado en {CURRENCY_SYMBOL}: ").strip())
        quantity = int(input("Cantidad comprada: ").strip())
        target_sell_price = float(input(f"Precio objetivo de venta en {CURRENCY_SYMBOL}: ").strip())
    except ValueError:
        print("Valores numéricos inválidos.")
        return

    total_spent = buy_price * quantity
    real_cash, real_inv, real_eq = get_current_capital(is_real=True)
    
    if total_spent > real_cash:
        print(f"⚠️ Advertencia: El gasto ({CURRENCY_SYMBOL} {total_spent:.2f}) supera el efectivo actual ({CURRENCY_SYMBOL} {real_cash:.2f}).")
        confirm = input("¿Deseas registrarlo de todas formas ajustando el saldo? (s/n): ").strip().lower()
        if confirm != 's':
            return

    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO portfolio (
        item_name, app_id, buy_price, quantity, total_spent, 
        target_sell_price, buy_date, status, is_real, is_aggressive, notes
    ) VALUES (?, 730, ?, ?, ?, ?, ?, 'REAL_ACTIVE', 1, 0, 'Inyectado manualmente')
    """, (item_name, buy_price, quantity, total_spent, target_sell_price, now_str))

    new_cash = max(0.0, real_cash - total_spent)
    new_inv = real_inv + total_spent
    new_eq = new_cash + new_inv

    cursor.execute("""
    INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
    VALUES (?, 'REAL', ?, ?, ?, ?)
    """, (now_str, new_cash, new_inv, new_eq, f"Inyección manual: {item_name} x{quantity}"))
    
    conn.commit()
    conn.close()
    print(f"✅ Compra de '{item_name}' registrada exitosamente en tu Cartera Real.")

def adjust_cash_balance():
    print("\n--- MODIFICAR SALDO DE EFECTIVO ---")
    print("1. Cartera Real")
    print("2. Cartera Simulada")
    choice = input("Selecciona (1 o 2): ").strip()
    is_real = (choice == "1")
    mode = "REAL" if is_real else "SIMULATED"
    
    cash, inv, eq = get_current_capital(is_real=is_real)
    print(f"Efectivo actual ({mode}): {CURRENCY_SYMBOL} {cash:.2f}")
    try:
        new_cash = float(input(f"Ingresa el nuevo monto de efectivo en {CURRENCY_SYMBOL}: ").strip())
    except ValueError:
        print("Monto inválido.")
        return

    new_eq = new_cash + inv
    now_str = datetime.datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
    VALUES (?, ?, ?, ?, ?, 'Ajuste manual de efectivo')
    """, (now_str, mode, new_cash, inv, new_eq))
    conn.commit()
    conn.close()
    print(f"✅ Saldo de efectivo actualizado a {CURRENCY_SYMBOL} {new_cash:.2f} en modo {mode}.")

def force_day_end_and_charts():
    print("\n--- GENERANDO CIERRE DE DÍA Y GRÁFICOS (10:00 PM) ---")
    c3 = generate_portfolio_chart(days=3, mode="REAL")
    c7 = generate_portfolio_chart(days=7, mode="REAL")
    c30 = generate_portfolio_chart(days=30, mode="REAL")
    print(f"📈 Gráfico 3 Días:  {c3}")
    print(f"📈 Gráfico 7 Días:  {c7}")
    print(f"📈 Gráfico 30 Días: {c30}")
    print("✅ Gráficos generados correctamente en la carpeta /charts/")

def view_positions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_name, quantity, buy_price, total_spent, target_sell_price, is_real, status FROM portfolio WHERE status IN ('REAL_ACTIVE', 'SIMULATED')")
    rows = cursor.fetchall()
    conn.close()
    print("\n--- POSICIONES ACTIVAS ---")
    if not rows:
        print("No hay posiciones abiertas actualmente.")
        return
    for r in rows:
        tipo = "REAL" if r["is_real"] else "SIMULADO"
        print(f"[{tipo}] ID: {r['id']} | {r['item_name']} x{r['quantity']} | Comprado a: {CURRENCY_SYMBOL} {r['buy_price']:.2f} (Total: {CURRENCY_SYMBOL} {r['total_spent']:.2f}) | Meta: {CURRENCY_SYMBOL} {r['target_sell_price']:.2f}")

def main():
    while True:
        print_menu()
        opt = input("Elige una opción (1-5): ").strip()
        if opt == "1":
            inject_manual_purchase()
        elif opt == "2":
            adjust_cash_balance()
        elif opt == "3":
            force_day_end_and_charts()
        elif opt == "4":
            view_positions()
        elif opt == "5":
            print("Saliendo de la consola.")
            break
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    main()
