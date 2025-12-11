import sqlite3
import os
from contextlib import closing

DB_PATH = os.environ.get("DATABASE_URL", "rds_app.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        # app_settings
        cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        # payments default = "false"
        cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", ("payments_enabled", "false"))

        # payments table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            order_id TEXT,
            payment_id TEXT,
            amount INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # downloads table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            platform TEXT,
            video_url TEXT,
            format TEXT,
            quality TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def get_app_config():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM app_settings")
    rows = {r["key"]: r["value"] for r in cur.fetchall()}
    return rows

def set_payments_enabled(enabled: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", ("payments_enabled", "true" if enabled else "false"))
    conn.commit()

def create_payment(user_id, order_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO payments (user_id, order_id, amount, status) VALUES (?, ?, ?, ?)", (user_id, order_id, amount, "created"))
    conn.commit()

def update_payment(order_id, payment_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE payments SET payment_id = ?, status = ? WHERE order_id = ?", (payment_id, status, order_id))
    conn.commit()

def log_download(user_id, platform, video_url, fmt, quality):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO downloads (user_id, platform, video_url, format, quality) VALUES (?, ?, ?, ?, ?)", (user_id, platform, video_url, fmt, quality))
    conn.commit()

def get_stats():
    conn = get_conn()
    cur = conn.cursor()
    # total downloads
    cur.execute("SELECT COUNT(*) as c FROM downloads")
    total_downloads = cur.fetchone()["c"]
    # active users (unique user_id)
    cur.execute("SELECT COUNT(DISTINCT user_id) as c FROM downloads")
    active_users = cur.fetchone()["c"]
    # platform distribution
    cur.execute("SELECT platform, COUNT(*) as cnt FROM downloads GROUP BY platform")
    rows = cur.fetchall()
    platform_stats = {r["platform"] if r["platform"] else "unknown": r["cnt"] for r in rows}
    return {
        "total_downloads": total_downloads,
        "active_users": active_users,
        "platform_stats": platform_stats
    }
