import sqlite3
import uuid
import time
import json
import os
import stat

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "database.db")

def _get_conn():

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA secure_delete = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cookies
                 (id INTEGER PRIMARY KEY, psid TEXT, psidts TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys
                 (key TEXT PRIMARY KEY, name TEXT, active INTEGER)''')
    
    # Auto-migrate table for new models and session storage
    try:
        c.execute("ALTER TABLE api_keys ADD COLUMN allowed_models TEXT DEFAULT 'all'")
    except sqlite3.OperationalError:
        pass
    
    # Session Persistence Columns
    try:
        c.execute("ALTER TABLE api_keys ADD COLUMN conversation_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN response_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN choice_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN last_used REAL DEFAULT 0")
        c.execute("ALTER TABLE api_keys ADD COLUMN timeout_hours REAL DEFAULT 24") # Default 24 hours
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

    try:
        os.chmod(DB_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass 

def update_cookies(c1, c2):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM cookies")
    c.execute("INSERT INTO cookies (psid, psidts) VALUES (?, ?)", (c1, c2))
    conn.commit()
    conn.close()

def get_cookies():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT psid, psidts FROM cookies LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row if row else (None, None)

def generate_api_key(name, allowed_models="all"):
    key = "sk-" + uuid.uuid4().hex
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO api_keys (key, name, active, allowed_models, last_used, timeout_hours) VALUES (?, ?, 1, ?, ?, ?)", 
                  (key, name, allowed_models, time.time(), 24.0))
    except sqlite3.OperationalError:
        init_db() 
        c.execute("INSERT INTO api_keys (key, name, active, allowed_models, last_used, timeout_hours) VALUES (?, ?, 1, ?, ?, ?)", 
                  (key, name, allowed_models, time.time(), 24.0))
    conn.commit()
    conn.close()
    return key

def list_api_keys():
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT key, name, active, allowed_models, timeout_hours FROM api_keys")
    except sqlite3.OperationalError:
        init_db()
        c.execute("SELECT key, name, active, allowed_models, timeout_hours FROM api_keys")
    rows = c.fetchall()
    conn.close()
    return rows

def revoke_api_key(key):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE api_keys SET active = 0 WHERE key = ?", (key,))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_api_key_details(key):
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT active, allowed_models FROM api_keys WHERE key = ?", (key,))
    except sqlite3.OperationalError:
        init_db()
        c.execute("SELECT active, allowed_models FROM api_keys WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row

def get_api_key_session(key):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT conversation_id, response_id, choice_id, last_used, timeout_hours FROM api_keys WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
        
    cid, rid, chid, last_used, timeout_hours = row
    
    # Check Expiration (Timeout in hours converted to seconds)
    if time.time() - last_used > (timeout_hours * 3600):
        # Session expired, clear it
        update_api_key_session(key, None, None, None)
        return None
        
    return {"cid": cid, "rid": rid, "chid": chid}

def update_api_key_session(key, cid, rid, chid):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE api_keys SET conversation_id = ?, response_id = ?, choice_id = ?, last_used = ? WHERE key = ?", 
              (cid, rid, chid, time.time(), key))
    conn.commit()
    conn.close()

def set_key_timeout(name, timeout_hours):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE api_keys SET timeout_hours = ? WHERE name = ?", (timeout_hours, name))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success