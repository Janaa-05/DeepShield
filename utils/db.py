import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scans.db')

@contextmanager
def get_db():
    """Context manager for thread-safe SQLite database connections with WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
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
    """Initializes SQLite schema and research indexes."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON scan_logs (file_hash);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON scan_logs (timestamp DESC);')

def log_scan(filename, file_hash, result, confidence, auth_score, source_attr, inf_time, is_ai, ela_std, fft_freq, noise_var, sharpness, gradcam_path, ela_path, fft_path):
    """Logs forensic scan record with research metrics persistently."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scan_logs 
            (filename, file_hash, result, confidence, authenticity_score, source_attribution, inference_time_ms, is_ai, ela_std_dev, fft_high_freq, noise_var, sharpness_score, gradcam_path, ela_path, fft_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_hash, result, confidence, auth_score, source_attr, inf_time, 1 if is_ai else 0, ela_std, fft_freq, noise_var, sharpness, gradcam_path, ela_path, fft_path))
        return cursor.lastrowid

def get_scan_by_id(scan_id):
    """Retrieves scan record by ID."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scan_logs WHERE id = ?', (scan_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_recent_scans(limit=100):
    """Retrieves recent scan records sorted by timestamp."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scan_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def clear_scans():
    """Clears scan logs safely."""
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scan_logs')
        return True
