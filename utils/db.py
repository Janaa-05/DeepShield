import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scans.db')

@contextmanager
def get_db():
    """Context manager for thread-safe SQLite database connections with WAL mode and foreign keys."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """
    Initializes SQLite schema, performs safe migration from legacy scan_logs to analyses,
    creates users table, adds user_id column if missing, and ensures indexes.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Create users table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);')

        # 2. Check existing tables in DB
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # Migration: Rename scan_logs to analyses if scan_logs exists and analyses does not
        if 'scan_logs' in tables and 'analyses' not in tables:
            cursor.execute('ALTER TABLE scan_logs RENAME TO analyses;')
            tables.append('analyses')

        # Create analyses table if neither existed
        if 'analyses' not in tables:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_hash TEXT,
                    filename TEXT,
                    result TEXT,
                    confidence TEXT,
                    authenticity_score REAL,
                    source_attribution TEXT,
                    inference_time_ms REAL,
                    is_ai INTEGER,
                    ela_std_dev REAL,
                    fft_high_freq REAL,
                    noise_var REAL,
                    sharpness_score REAL,
                    gradcam_path TEXT,
                    ela_path TEXT,
                    fft_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')

        # 3. Check columns of analyses table and add user_id if missing
        cursor.execute("PRAGMA table_info(analyses);")
        columns = [row[1] for row in cursor.fetchall()]

        if 'user_id' not in columns:
            cursor.execute('ALTER TABLE analyses ADD COLUMN user_id INTEGER REFERENCES users(id);')

        # Create backward-compatibility VIEW for scan_logs if any legacy code queries scan_logs directly
        cursor.execute("CREATE VIEW IF NOT EXISTS scan_logs AS SELECT * FROM analyses;")

        # Indexes for fast querying
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses (user_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_file_hash ON analyses (file_hash);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_timestamp ON analyses (timestamp DESC);')

# ==================== USER MANAGEMENT DATABASE FUNCTIONS ====================

def get_user_by_email(email):
    """Retrieves user by email address (case-insensitive)."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    """Retrieves user record by user ID."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_user(name, email, password_hash, created_at):
    """Creates a new user record in SQLite database."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, created_at, last_login)
            VALUES (?, ?, ?, ?, NULL)
        ''', (name.strip(), email.strip().lower(), password_hash, created_at))
        return cursor.lastrowid

def update_user_last_login(user_id, timestamp):
    """Updates last login timestamp for user."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (timestamp, user_id))
        return True

def update_user_name(user_id, new_name):
    """Updates user full name."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET name = ? WHERE id = ?', (new_name.strip(), user_id))
        return True

def update_user_password(user_id, password_hash):
    """Updates user password hash."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        return True

# ==================== ANALYSIS DATABASE FUNCTIONS ====================

def log_scan(filename, file_hash, result, confidence, auth_score, source_attr, inf_time, is_ai, ela_std, fft_freq, noise_var, sharpness, gradcam_path, ela_path, fft_path, user_id=None):
    """Logs forensic scan record persistently with optional user_id."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analyses 
            (filename, file_hash, result, confidence, authenticity_score, source_attribution, inference_time_ms, is_ai, ela_std_dev, fft_high_freq, noise_var, sharpness_score, gradcam_path, ela_path, fft_path, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_hash, result, confidence, auth_score, source_attr, inf_time, 1 if is_ai else 0, ela_std, fft_freq, noise_var, sharpness, gradcam_path, ela_path, fft_path, user_id))
        return cursor.lastrowid

def get_scan_by_id(scan_id, user_id=None):
    """
    Retrieves scan record by ID.
    If user_id is provided, enforces SQL filtering for IDOR security.
    """
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute('SELECT * FROM analyses WHERE id = ? AND user_id = ?', (scan_id, user_id))
        else:
            cursor.execute('SELECT * FROM analyses WHERE id = ?', (scan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_recent_scans(limit=100, user_id=None):
    """
    Retrieves recent scan records sorted by timestamp.
    If user_id is provided, uses strict SQL filtering WHERE user_id = ?.
    """
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute('SELECT * FROM analyses WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
        else:
            cursor.execute('SELECT * FROM analyses ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_user_stats(user_id):
    """Calculates user-specific statistics directly in SQL."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM analyses WHERE user_id = ?', (user_id,))
        total = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM analyses WHERE user_id = ? AND is_ai = 1', (user_id,))
        ai_count = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM analyses WHERE user_id = ? AND is_ai = 0', (user_id,))
        real_count = cursor.fetchone()[0] or 0

        return {
            'total_analyses': total,
            'ai_detected': ai_count,
            'real_detected': real_count,
            'reports_generated': total
        }

def clear_scans(user_id=None):
    """Clears scan logs safely. If user_id is supplied, only clears scans for that user."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute('DELETE FROM analyses WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('DELETE FROM analyses')
        return True
