import os
import datetime
import sqlite3
try:
    import matplotlib
    matplotlib.use("Agg") # Modo sin interfaz gráfica para servidores en la nube
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
from config import CURRENCY_SYMBOL
from database import DB_PATH

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

def generate_portfolio_chart(days=7, mode="REAL"):
    """
    Genera un gráfico PNG de la evolución del capital (3 días, 7 días, 30 días)
    """
    if not HAS_MATPLOTLIB:
        print("[AVISO] matplotlib no está instalado. Se omite generación de gráfico.")
        return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    cursor.execute("""
    SELECT timestamp, cash_balance, inventory_value, total_equity 
    FROM capital_ledger 
    WHERE mode = ? AND timestamp >= ?
    ORDER BY timestamp ASC
    """, (mode, since_date))
    rows = cursor.fetchall()
    conn.close()

    if not rows or len(rows) < 2:
        # Si hay pocos puntos históricos, tomamos todos los registros disponibles
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT timestamp, cash_balance, inventory_value, total_equity 
        FROM capital_ledger 
        WHERE mode = ?
        ORDER BY timestamp ASC
        """, (mode,))
        rows = cursor.fetchall()
        conn.close()

    if not rows:
        return None

    timestamps = [datetime.datetime.fromisoformat(r[0]) for r in rows]
    cash = [r[1] for r in rows]
    inventory = [r[2] for r in rows]
    equity = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")

    ax.plot(timestamps, equity, label=f"Valor Total del Portafolio ({CURRENCY_SYMBOL})", color="#00ff88", linewidth=2.5)
    ax.plot(timestamps, cash, label=f"Efectivo Líquido ({CURRENCY_SYMBOL})", color="#00bfff", linestyle="--", alpha=0.8)
    ax.plot(timestamps, inventory, label=f"Inventario en Activos ({CURRENCY_SYMBOL})", color="#ffaa00", linestyle=":", alpha=0.8)

    ax.set_title(f"Evolución del Portafolio ({mode}) - Últimos {days} días", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel(f"Monto en {CURRENCY_SYMBOL}", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    fig.autofmt_xdate()

    ax.legend(loc="upper left")
    plt.tight_layout()

    filename = f"portfolio_{mode.lower()}_{days}d_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)
    plt.savefig(filepath)
    plt.close()

    return filepath

def generate_item_trend_chart(item_name, buy_price=None, target_price=None):
    """
    Genera un gráfico de tendencia del ítem con líneas de precio de compra y objetivo de venta
    """
    if not HAS_MATPLOTLIB:
        return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT timestamp, price FROM price_history 
    WHERE item_name = ? 
    ORDER BY timestamp ASC
    """, (item_name,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    timestamps = [datetime.datetime.fromisoformat(r[0]) for r in rows]
    prices = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    ax.plot(timestamps, prices, label="Precio de Mercado", color="#3498db", linewidth=2)

    if buy_price:
        ax.axhline(buy_price, color="#e74c3c", linestyle="--", label=f"Precio de Compra ({CURRENCY_SYMBOL} {buy_price:.2f})")
    if target_price:
        ax.axhline(target_price, color="#2ecc71", linestyle="--", label=f"Precio Meta Venta ({CURRENCY_SYMBOL} {target_price:.2f})")

    ax.set_title(f"Tendencia de Precio: {item_name}", fontsize=12, fontweight="bold")
    ax.set_ylabel(f"Precio ({CURRENCY_SYMBOL})")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.autofmt_xdate()
    ax.legend()
    plt.tight_layout()

    safe_name = "".join(c for c in item_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
    filename = f"item_{safe_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(CHARTS_DIR, filename)
    plt.savefig(filepath)
    plt.close()

    return filepath
