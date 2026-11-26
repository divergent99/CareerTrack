import os
import threading
import time
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# Opening a TLS connection to Cockroach Cloud costs hundreds of ms, and every
# route opened a fresh one per request. Reuse a small pool instead.
_pool = None
_pool_lock = threading.Lock()
_last_used = {}
IDLE_CHECK_SECONDS = 60


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(1, 8, os.environ["COCKROACH_URL"])
        return _pool


class PooledConn:
    """Drop-in for a psycopg2 connection whose close() returns it to the pool."""

    def __init__(self):
        object.__setattr__(self, "_conn", None)
        p = _get_pool()
        conn = p.getconn()
        # Cockroach Cloud drops idle connections; ping ones that sat a while.
        if conn.closed or time.time() - _last_used.get(id(conn), time.time()) > IDLE_CHECK_SECONDS:
            try:
                with conn.cursor() as c:
                    c.execute("SELECT 1")
                conn.rollback()
            except psycopg2.Error:
                p.putconn(conn, close=True)
                conn = p.getconn()
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name):
        conn = object.__getattribute__(self, "_conn")
        if conn is None:
            raise psycopg2.InterfaceError("connection already returned to pool")
        return getattr(conn, name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_conn"), name, value)

    def close(self):
        conn = object.__getattribute__(self, "_conn")
        object.__setattr__(self, "_conn", None)
        if conn is None:
            return
        broken = bool(conn.closed)
        if not broken:
            try:
                conn.rollback()
                if conn.autocommit:
                    conn.autocommit = False
            except psycopg2.Error:
                broken = True
        _last_used[id(conn)] = time.time()
        _get_pool().putconn(conn, close=broken)

    def __del__(self):
        # A request that died without close() must not leave its connection
        # checked out with an open transaction holding row locks.
        try:
            self.close()
        except Exception:
            pass


def get_conn():
    return PooledConn()

def create_session(cur, title="New chat"):
    cur.execute(
        "INSERT INTO chat_sessions (title) VALUES (%s) RETURNING id",
        (title,)
    )
    return cur.fetchone()[0]

def save_message(cur, session_id, role, content):
    cur.execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, role, content)
    )
    cur.execute(
        "UPDATE chat_sessions SET updated_at = now() WHERE id = %s",
        (session_id,)
    )

def get_session_messages(cur, session_id, limit=None):
    if limit:
        cur.execute(
            "SELECT role, content FROM (SELECT role, content, seq FROM chat_messages WHERE session_id = %s ORDER BY seq DESC LIMIT %s) recent ORDER BY seq ASC",
            (session_id, limit),
        )
        return [{"role": r, "content": c} for r, c in cur.fetchall()]

    cur.execute(
        "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY seq ASC",
        (session_id,)
    )
    return [{"role": r, "content": c} for r, c in cur.fetchall()]

def list_sessions(cur):
    cur.execute(
        "SELECT id, title, updated_at FROM chat_sessions ORDER BY updated_at DESC"
    )
    return [{"id": str(i), "title": t, "updated_at": u.isoformat()} for i, t, u in cur.fetchall()]

def get_session(cur, session_id):
    cur.execute(
        "SELECT id, title, updated_at FROM chat_sessions WHERE id = %s",
        (session_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "title": row[1], "updated_at": row[2].isoformat()}

def rename_session(cur, session_id, title):
    cur.execute(
        "UPDATE chat_sessions SET title = %s, updated_at = now() WHERE id = %s RETURNING id",
        (title, session_id)
    )
    return cur.fetchone() is not None

def delete_session(cur, session_id):
    cur.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
    cur.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
