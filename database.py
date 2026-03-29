import sqlite3
import os
import datetime

DB_PATH = "database.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id TEXT PRIMARY KEY,
        username TEXT,
        proxy TEXT,
        is_admin INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Stats Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value INTEGER DEFAULT 0
    )
    """)
    
    # Requirements Table (Channels/Groups)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requirements (
        chat_id TEXT PRIMARY KEY,
        url TEXT,
        name TEXT
    )
    """)
    
    # Initialize default stats
    cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_hits', 0)")
    cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('success_hits', 0)")
    cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_users', 0)")
    
    conn.commit()
    conn.close()

# --- USER FUNCTIONS ---

def get_user(chat_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE chat_id = ?", (str(chat_id),)).fetchone()
    conn.close()
    return user

def add_user(chat_id, username):
    conn = get_db()
    try:
        conn.execute("INSERT OR IGNORE INTO users (chat_id, username) VALUES (?, ?)", (str(chat_id), username))
        # Update user count stat
        conn.execute("UPDATE stats SET value = (SELECT COUNT(*) FROM users) WHERE key = 'total_users'")
        conn.commit()
    except Exception as e:
        print(f"DB Error (add_user): {e}")
    finally:
        conn.close()

def update_user_proxy(chat_id, proxy):
    conn = get_db()
    conn.execute("UPDATE users SET proxy = ? WHERE chat_id = ?", (proxy, str(chat_id)))
    conn.commit()
    conn.close()

# --- STATS FUNCTIONS ---

def increment_stat(key):
    conn = get_db()
    conn.execute("UPDATE stats SET value = value + 1 WHERE key = ?", (key,))
    conn.commit()
    conn.close()

def get_all_stats():
    conn = get_db()
    rows = conn.execute("SELECT * FROM stats").fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

# --- REQUIREMENTS FUNCTIONS ---

def add_requirement(chat_id, url, name):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO requirements (chat_id, url, name) VALUES (?, ?, ?)", (str(chat_id), url, name))
    conn.commit()
    conn.close()

def remove_requirement(chat_id):
    conn = get_db()
    conn.execute("DELETE FROM requirements WHERE chat_id = ?", (str(chat_id),))
    conn.commit()
    conn.close()

def get_requirements():
    conn = get_db()
    reqs = conn.execute("SELECT * FROM requirements").fetchall()
    conn.close()
    return [dict(row) for row in reqs]

# Initialize on import
if not os.path.exists(DB_PATH):
    init_db()
