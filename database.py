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
        c.execute("ALTER TABLE api_keys ADD COLUMN conversation_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN response_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN choice_id TEXT")
        c.execute("ALTER TABLE api_keys ADD COLUMN last_used REAL DEFAULT 0")
        c.execute("ALTER TABLE api_keys ADD COLUMN timeout_hours REAL DEFAULT 24")
    except sqlite3.OperationalError:
        pass
        
    # Security role for Admin API Keys
    try:
        c.execute("ALTER TABLE api_keys ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass

    # Rate Limiting Fields
    try:
        c.execute("ALTER TABLE api_keys ADD COLUMN req_per_min INTEGER DEFAULT 60")
        c.execute("ALTER TABLE api_keys ADD COLUMN current_req_count INTEGER DEFAULT 0")
        c.execute("ALTER TABLE api_keys ADD COLUMN window_start REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Extended Conversation State for Regeneration
    try:
        c.execute("ALTER TABLE api_keys ADD COLUMN conversation_token TEXT DEFAULT ''")
        c.execute("ALTER TABLE api_keys ADD COLUMN prev_response_id TEXT DEFAULT ''")
        c.execute("ALTER TABLE api_keys ADD COLUMN prev_choice_id TEXT DEFAULT ''")
        c.execute("ALTER TABLE api_keys ADD COLUMN prev_conversation_token TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # System status table for Extension Polling and Flood Control
    c.execute('''CREATE TABLE IF NOT EXISTS system_status
                 (id INTEGER PRIMARY KEY, needs_update INTEGER, last_alert REAL, global_req_per_min INTEGER)''')
    c.execute("INSERT OR IGNORE INTO system_status (id, needs_update, last_alert, global_req_per_min) VALUES (1, 0, 0, 60)")
    
    try:
        c.execute("ALTER TABLE system_status ADD COLUMN global_req_per_min INTEGER DEFAULT 60")
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

def get_global_rate_limit():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT global_req_per_min FROM system_status WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 60

def set_global_rate_limit(limit: int):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE system_status SET global_req_per_min = ? WHERE id = 1", (limit,))
    conn.commit()
    conn.close()

def generate_api_key(name, allowed_models="all", role="user"):
    key = "sk-" + uuid.uuid4().hex
    global_limit = get_global_rate_limit()
    
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO api_keys (key, name, active, allowed_models, last_used, timeout_hours, role, req_per_min) VALUES (?, ?, 1, ?, ?, ?, ?, ?)", 
                  (key, name, allowed_models, time.time(), 24.0, role, global_limit))
    except sqlite3.OperationalError:
        init_db() 
        c.execute("INSERT INTO api_keys (key, name, active, allowed_models, last_used, timeout_hours, role, req_per_min) VALUES (?, ?, 1, ?, ?, ?, ?, ?)", 
                  (key, name, allowed_models, time.time(), 24.0, role, global_limit))
    conn.commit()
    conn.close()
    return key

def list_api_keys():
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT key, name, active, allowed_models, timeout_hours, role, req_per_min FROM api_keys")
    except sqlite3.OperationalError:
        init_db()
        c.execute("SELECT key, name, active, allowed_models, timeout_hours, role, req_per_min FROM api_keys")
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
        c.execute("SELECT active, allowed_models, role FROM api_keys WHERE key = ?", (key,))
    except sqlite3.OperationalError:
        init_db()
        c.execute("SELECT active, allowed_models, role FROM api_keys WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row

def set_key_rate_limit(name_or_key, limit: int):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE api_keys SET req_per_min = ? WHERE name = ?", (limit, name_or_key))
    if c.rowcount == 0:
        c.execute("UPDATE api_keys SET req_per_min = ? WHERE key = ?", (limit, name_or_key))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def check_rate_limit(key: str) -> bool:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT req_per_min, current_req_count, window_start, role FROM api_keys WHERE key = ?", (key,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False
        
    req_per_min, current_req_count, window_start, role = row
    
    if role == 'admin':
        conn.close()
        return True
        
    now = time.time()
    if now - window_start > 60.0:
        c.execute("UPDATE api_keys SET current_req_count = 1, window_start = ? WHERE key = ?", (now, key))
        conn.commit()
        conn.close()
        return True
        
    if current_req_count >= req_per_min:
        conn.close()
        return False
        
    c.execute("UPDATE api_keys SET current_req_count = current_req_count + 1 WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return True

def get_api_key_session(key):
    conn = _get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT conversation_id, response_id, choice_id, last_used, timeout_hours, conversation_token, prev_response_id, prev_choice_id, prev_conversation_token FROM api_keys WHERE key = ?", (key,))
        row = c.fetchone()
    except sqlite3.OperationalError:
        init_db()
        c.execute("SELECT conversation_id, response_id, choice_id, last_used, timeout_hours, conversation_token, prev_response_id, prev_choice_id, prev_conversation_token FROM api_keys WHERE key = ?", (key,))
        row = c.fetchone()
    conn.close()
    
    if not row:
        return None
        
    cid, rid, chid, last_used, timeout_hours, ctok, prev_rid, prev_chid, prev_ctok = row
    
    if time.time() - last_used > (timeout_hours * 3600):
        update_api_key_session(key, None, None, None, None, False)
        return None
        
    return {"cid": cid, "rid": rid, "chid": chid, "ctok": ctok, "prev_rid": prev_rid, "prev_chid": prev_chid, "prev_ctok": prev_ctok}

def update_api_key_session(key, cid, rid, chid, ctok=None, is_regenerate=False):
    conn = _get_conn()
    c = conn.cursor()
    try:
        if not is_regenerate:
            # Shift the current state into the 'prev' columns before overwriting the current state
            c.execute("UPDATE api_keys SET prev_response_id = response_id, prev_choice_id = choice_id, prev_conversation_token = conversation_token WHERE key = ?", (key,))
        c.execute("UPDATE api_keys SET conversation_id = ?, response_id = ?, choice_id = ?, conversation_token = ?, last_used = ? WHERE key = ?", 
                  (cid, rid, chid, ctok, time.time(), key))
    except sqlite3.OperationalError:
        init_db()
        if not is_regenerate:
            c.execute("UPDATE api_keys SET prev_response_id = response_id, prev_choice_id = choice_id, prev_conversation_token = conversation_token WHERE key = ?", (key,))
        c.execute("UPDATE api_keys SET conversation_id = ?, response_id = ?, choice_id = ?, conversation_token = ?, last_used = ? WHERE key = ?", 
                  (cid, rid, chid, ctok, time.time(), key))
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

# ========================================================
# FLOOD CONTROL & EXTENSION SIGNALING SYSTEM
# ========================================================
def set_needs_update(status: bool):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE system_status SET needs_update = ? WHERE id = 1", (1 if status else 0,))
    conn.commit()
    conn.close()

def get_needs_update() -> bool:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT needs_update FROM system_status WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False

def check_and_set_alert_flood(cooldown_seconds=300) -> bool:
    """Returns True if an alert should be sent (not flooded), False if in cooldown."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT last_alert FROM system_status WHERE id = 1")
    row = c.fetchone()
    
    now = time.time()
    last_alert = row[0] if row else 0
    
    # If 5 minutes have passed since the last alert, allow a new one
    if now - last_alert > cooldown_seconds:
        c.execute("UPDATE system_status SET last_alert = ? WHERE id = 1", (now,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False