import sqlite3
import datetime
import pytz
import os
from config import INITIAL_CAPITAL, TIMEZONE

DB_PATH = os.path.join(os.path.dirname(__file__), "investor.db")
tz = pytz.timezone(TIMEZONE)

def get_today_str():
    """Devuelve la fecha actual en la zona horaria de Perú (YYYY-MM-DD)"""
    return datetime.datetime.now(tz).date().isoformat()

def get_now_str():
    """Devuelve la fecha y hora actual en formato ISO para Perú"""
    return datetime.datetime.now(tz).isoformat()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Posiciones y Oportunidades
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        app_id INTEGER DEFAULT 730,
        buy_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        total_spent REAL NOT NULL,
        target_sell_price REAL NOT NULL,
        buy_date TEXT NOT NULL,
        status TEXT NOT NULL, -- 'PENDING_CONFIRMATION', 'REAL_ACTIVE', 'SIMULATED', 'REJECTED', 'SOLD'
        is_real INTEGER DEFAULT 0, -- 1 = dinero real, 0 = simulado
        is_aggressive INTEGER DEFAULT 0,
        sold_price REAL,
        sold_date TEXT,
        net_profit REAL,
        roi_percent REAL,
        notes TEXT
    )
    """)

    # 2. Historial de Capital y Balances (Para los gráficos a 3 días, 7 días, 30 días)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS capital_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        mode TEXT NOT NULL, -- 'REAL' o 'SIMULATED'
        cash_balance REAL NOT NULL,
        inventory_value REAL NOT NULL,
        total_equity REAL NOT NULL,
        notes TEXT
    )
    """)

    # 3. Contador diario y estado de cierre
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_stats (
        date TEXT PRIMARY KEY,
        aggressive_count INTEGER DEFAULT 0,
        closed_at TEXT
    )
    """)

    # 4. Histórico de precios para gráficos individuales de items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        price REAL NOT NULL,
        volume_24h INTEGER,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()

    # Inicializar balance en el ledger si está vacío
    cursor.execute("SELECT COUNT(*) as count FROM capital_ledger")
    if cursor.fetchone()["count"] == 0:
        now_str = get_now_str()
        cursor.execute("""
        INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
        VALUES (?, 'SIMULATED', ?, 0.0, ?, 'Capital Inicial de Simulación')
        """, (now_str, INITIAL_CAPITAL, INITIAL_CAPITAL))
        
        cursor.execute("""
        INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
        VALUES (?, 'REAL', ?, 0.0, ?, 'Capital Inicial Real')
        """, (now_str, INITIAL_CAPITAL, INITIAL_CAPITAL))
        conn.commit()

    conn.close()

def get_current_capital(is_real=False):
    """Devuelve (cash_balance, inventory_value, total_equity)"""
    conn = get_connection()
    cursor = conn.cursor()
    mode = 'REAL' if is_real else 'SIMULATED'
    cursor.execute("""
    SELECT cash_balance, inventory_value, total_equity 
    FROM capital_ledger 
    WHERE mode = ? 
    ORDER BY id DESC LIMIT 1
    """, (mode,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return float(row["cash_balance"]), float(row["inventory_value"]), float(row["total_equity"])
    return INITIAL_CAPITAL, 0.0, INITIAL_CAPITAL

def get_today_aggressive_count():
    today = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT aggressive_count FROM daily_stats WHERE date = ?", (today,))
    row = cursor.fetchone()
    conn.close()
    return int(row["aggressive_count"]) if row else 0

def increment_aggressive_count():
    today = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_stats (date, aggressive_count)
    VALUES (?, 1)
    ON CONFLICT(date) DO UPDATE SET aggressive_count = aggressive_count + 1
    """, (today,))
    conn.commit()
    conn.close()

def is_day_closed(date_str=None):
    if not date_str:
        date_str = get_today_str()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT closed_at FROM daily_stats WHERE date = ?", (date_str,))
        row = cursor.fetchone()
        return bool(row and row["closed_at"])
    except Exception:
        return False
    finally:
        conn.close()

def mark_day_closed(date_str=None):
    if not date_str:
        date_str = get_today_str()
    now_str = get_now_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_stats (date, aggressive_count, closed_at)
    VALUES (?, 0, ?)
    ON CONFLICT(date) DO UPDATE SET closed_at = ?
    """, (date_str, now_str, now_str))
    conn.commit()
    conn.close()

def record_opportunity(item_name, app_id, buy_price, quantity, target_sell_price, is_aggressive=0, notes=""):
    """Registra una oportunidad pendiente de confirmación SÍ/NO del usuario"""
    total_spent = buy_price * quantity
    buy_date = get_now_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO portfolio (
        item_name, app_id, buy_price, quantity, total_spent, 
        target_sell_price, buy_date, status, is_real, is_aggressive, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_CONFIRMATION', 0, ?, ?)
    """, (item_name, app_id, buy_price, quantity, total_spent, target_sell_price, buy_date, is_aggressive, notes))
    opp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return opp_id

def process_user_decision(opp_id, user_said_yes):
    """
    Si el usuario responde SÍ:
      - Se marca como REAL_ACTIVE (compra real hecha por el usuario con su dinero).
      - Se descuenta el efectivo en el ledger real.
    Si el usuario responde NO:
      - Se marca como REJECTED para lo real, pero puede registrarse en el simulador para medir qué hubiera pasado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio WHERE id = ?", (opp_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return None

    now_str = get_now_str()

    if user_said_yes:
        # Registrar como compra real
        cursor.execute("""
        UPDATE portfolio SET status = 'REAL_ACTIVE', is_real = 1 WHERE id = ?
        """, (opp_id,))
        
        # Actualizar Ledger Real
        real_cash, real_inv, real_eq = get_current_capital(is_real=True)
        new_real_cash = max(0.0, real_cash - item["total_spent"])
        new_real_inv = real_inv + item["total_spent"]
        new_real_eq = new_real_cash + new_real_inv
        
        cursor.execute("""
        INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
        VALUES (?, 'REAL', ?, ?, ?, ?)
        """, (now_str, new_real_cash, new_real_inv, new_real_eq, f"Compra Real: {item['item_name']} x{item['quantity']}"))
        
        if item["is_aggressive"]:
            increment_aggressive_count()
            
        result = {"status": "REAL_ACTIVE", "spent": item["total_spent"], "item": item["item_name"]}
    else:
        # El usuario no lo compró con dinero real; pasa a SIMULATED para seguimiento del bot
        cursor.execute("""
        UPDATE portfolio SET status = 'SIMULATED', is_real = 0 WHERE id = ?
        """, (opp_id,))
        
        # En el simulador sí se ejecuta para contrastar métricas
        sim_cash, sim_inv, sim_eq = get_current_capital(is_real=False)
        new_sim_cash = max(0.0, sim_cash - item["total_spent"])
        new_sim_inv = sim_inv + item["total_spent"]
        new_sim_eq = new_sim_cash + new_sim_inv
        
        cursor.execute("""
        INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
        VALUES (?, 'SIMULATED', ?, ?, ?, ?)
        """, (now_str, new_sim_cash, new_sim_inv, new_sim_eq, f"Compra Simulada: {item['item_name']} x{item['quantity']}"))
        
        result = {"status": "SIMULATED", "spent": item["total_spent"], "item": item["item_name"]}

    conn.commit()
    conn.close()
    return result

def get_active_positions():
    """Obtiene posiciones abiertas (tanto reales como simuladas) para monitorizar ventas"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM portfolio 
    WHERE status IN ('REAL_ACTIVE', 'SIMULATED')
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_item_sold(item_id, sold_unit_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return None

    gross_total = sold_unit_price * item["quantity"]
    net_total = gross_total * 0.8695 # Descontando comisión de Steam (~15%)
    net_profit = net_total - item["total_spent"]
    roi_percent = (net_profit / item["total_spent"]) * 100.0 if item["total_spent"] > 0 else 0.0
    now_str = get_now_str()

    cursor.execute("""
    UPDATE portfolio 
    SET status = 'SOLD', sold_price = ?, sold_date = ?, net_profit = ?, roi_percent = ?
    WHERE id = ?
    """, (sold_unit_price, now_str, net_profit, roi_percent, item_id))

    # Actualizar ledger
    is_real = bool(item["is_real"])
    cash, inv, eq = get_current_capital(is_real=is_real)
    new_cash = cash + net_total
    new_inv = max(0.0, inv - item["total_spent"])
    new_eq = new_cash + new_inv
    mode = 'REAL' if is_real else 'SIMULATED'

    cursor.execute("""
    INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (now_str, mode, new_cash, new_inv, new_eq, f"Venta: {item['item_name']} x{item['quantity']}"))

    conn.commit()
    conn.close()
    return {
        "item_name": item["item_name"],
        "quantity": item["quantity"],
        "net_profit": net_profit,
        "roi_percent": roi_percent,
        "is_real": is_real
    }

def update_real_wallet_balance(real_cash_amount):
    """
    Sincroniza el efectivo real de la cartera con el saldo real extraído de Steam.
    """
    if real_cash_amount is None or real_cash_amount < 0:
        return
    now_str = get_now_str()
    cash, inv, eq = get_current_capital(is_real=True)
    # Si la diferencia es menor a 0.01 céntimo, no generar entrada redundante
    if abs(cash - real_cash_amount) < 0.01:
        return
    new_eq = real_cash_amount + inv
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO capital_ledger (timestamp, mode, cash_balance, inventory_value, total_equity, notes)
    VALUES (?, 'REAL', ?, ?, ?, 'Sincronización Automática con Cartera Steam')
    """, (now_str, real_cash_amount, inv, new_eq))
    conn.commit()
    conn.close()

init_db()
