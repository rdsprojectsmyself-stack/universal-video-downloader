import sqlite3
from datetime import datetime

DB_NAME = 'rds_downloader.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Users table
    # Users table - Updated schema
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT,
            name TEXT,
            picture TEXT,
            is_paid BOOLEAN DEFAULT 0,
            razorpay_customer_id TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Payments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            order_id TEXT,
            payment_id TEXT,
            amount INTEGER,
            status TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Check if is_paid column exists (migration for existing db)
    try:
        c.execute('SELECT is_paid FROM users LIMIT 1')
    except sqlite3.OperationalError:
        print("Migrating users table: adding is_paid column")
        c.execute('ALTER TABLE users ADD COLUMN is_paid BOOLEAN DEFAULT 0')
        c.execute('ALTER TABLE users ADD COLUMN razorpay_customer_id TEXT')
        
    conn.commit()
    conn.close()

def add_user(user_info):
    conn = get_db()
    c = conn.cursor()
    try:
        # Check if user exists to preserve is_paid status if re-logging in
        c.execute('SELECT is_paid FROM users WHERE id = ?', (user_info['sub'],))
        row = c.fetchone()
        
        if not row:
            c.execute('''
                INSERT INTO users (id, email, name, picture, is_paid, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (user_info['sub'], user_info['email'], user_info.get('name'), user_info.get('picture'), datetime.utcnow()))
        else:
            # Update user info but keep payment status
            c.execute('''
                UPDATE users SET email=?, name=?, picture=? WHERE id=?
            ''', (user_info['email'], user_info.get('name'), user_info.get('picture'), user_info['sub']))
            
        conn.commit()
    except Exception as e:
        print(f"Error adding/updating user: {e}")
    finally:
        conn.close()

def log_download(user_id, platform, video_url, fmt, quality):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO downloads (user_id, platform, video_url, format, quality, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, platform, video_url, fmt, quality, datetime.utcnow()))
        conn.commit()
    except Exception as e:
        print(f"Error logging download: {e}")
    finally:
        conn.close()

def create_payment(user_id, order_id, amount, status='created'):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO payments (user_id, order_id, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, order_id, amount, status, datetime.utcnow()))
        conn.commit()
    except Exception as e:
        print(f"Error creating payment: {e}")
    finally:
        conn.close()

def update_payment(order_id, payment_id, status):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE payments SET payment_id=?, status=? WHERE order_id=?
        ''', (payment_id, status, order_id))
        
        if status == 'captured':
            # Get user_id from payment to update user status
            c.execute('SELECT user_id FROM payments WHERE order_id=?', (order_id,))
            row = c.fetchone()
            if row:
                user_id = row['user_id']
                c.execute('UPDATE users SET is_paid=1 WHERE id=?', (user_id,))
                
        conn.commit()
    except Exception as e:
        print(f"Error updating payment: {e}")
    finally:
        conn.close()

def get_user_status(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT is_paid FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row['is_paid'] if row else False


def get_stats():
    conn = get_db()
    c = conn.cursor()
    
    # Total downloads
    c.execute('SELECT COUNT(*) FROM downloads')
    total_downloads = c.fetchone()[0]
    
    # Active users (unique users who downloaded)
    c.execute('SELECT COUNT(DISTINCT user_id) FROM downloads')
    active_users = c.fetchone()[0]
    
    # Platform stats
    c.execute('SELECT platform, COUNT(*) as count FROM downloads GROUP BY platform')
    platform_stats = {row['platform']: row['count'] for row in c.fetchall()}
    
    conn.close()
    return {
        'total_downloads': total_downloads,
        'active_users': active_users,
        'platform_stats': platform_stats
    }

# Initialize on module load or manually
if __name__ == '__main__':
    init_db()
    print("Database initialized.")
