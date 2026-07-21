import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.environ["COCKROACH_URL"])

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
