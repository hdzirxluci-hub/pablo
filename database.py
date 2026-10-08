import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'bot.db')

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # جدول کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            railway_token TEXT,
            is_banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # جدول پنل‌های ساخته شده
    c.execute('''
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            project_id TEXT,
            project_name TEXT,
            domain TEXT,
            repo_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # جدول تنظیمات سراسری
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    # ریپازیتوری پیش‌فرض
    if not get_setting('default_repo'):
        set_setting('default_repo', 'hdzirxluci-hub/pablo-panel')

def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute(
        'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?',
        (key, value, value)
    )
    conn.commit()
    conn.close()

def save_user(user_id, username, first_name):
    conn = get_db()
    conn.execute('''
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username = ?, first_name = ?
    ''', (user_id, username, first_name, username, first_name))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def set_user_token(user_id, token):
    conn = get_db()
    conn.execute('UPDATE users SET railway_token = ? WHERE user_id = ?', (token, user_id))
    conn.commit()
    conn.close()

def add_panel(user_id, project_id, project_name, domain, repo_name):
    conn = get_db()
    conn.execute('''
        INSERT INTO panels (user_id, project_id, project_name, domain, repo_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, project_id, project_name, domain, repo_name))
    conn.commit()
    conn.close()

def get_user_panels(user_id):
    conn = get_db()
    rows = conn.execute('SELECT * FROM panels WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_panel_by_id(panel_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM panels WHERE id = ?', (panel_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_panel(panel_id):
    conn = get_db()
    conn.execute('DELETE FROM panels WHERE id = ?', (panel_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    rows = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_panels():
    conn = get_db()
    rows = conn.execute('SELECT * FROM panels ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]