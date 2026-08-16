"""SQLite 会话管理 — Layer 2 短期记忆"""
import sqlite3
import os
from datetime import datetime


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "sessions")
DB_PATH = os.path.join(DB_DIR, "memory.db")


def _ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """首次初始化表结构"""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time  TEXT NOT NULL,
                end_time    TEXT,
                title       TEXT,
                flushed     INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                timestamp   TEXT NOT NULL
            );
        """)


class SessionDB:
    def __init__(self):
        init_db()

    def new_session(self) -> int:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (start_time) VALUES (?)",
                (datetime.now().isoformat(),),
            )
            return cur.lastrowid

    def add_message(self, session_id: int, role: str, content: str):
        with _connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, datetime.now().isoformat()),
            )

    def get_session_messages(self, session_id: int) -> list[dict]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE session_id=? ORDER BY id",
                (session_id,),
            ).fetchall()
        return [{"role": r, "content": c} for r, c in rows]

    def get_message_count(self, session_id: int) -> int:
        with _connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?",
                (session_id,),
            ).fetchone()
        return row[0] if row else 0

    def mark_flushed(self, session_id: int):
        with _connect() as conn:
            conn.execute(
                "UPDATE sessions SET flushed=1 WHERE id=?",
                (session_id,),
            )

    def close_session(self, session_id: int):
        title = "Session"
        with _connect() as conn:
            row = conn.execute(
                "SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",
                (session_id,),
            ).fetchone()
            if row:
                title = row[0][:30]
            conn.execute(
                "UPDATE sessions SET end_time=?, title=? WHERE id=?",
                (datetime.now().isoformat(), title, session_id),
            )
