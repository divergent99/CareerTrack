from fastapi import APIRouter
from pydantic import BaseModel
import logging
import re
import time
import anthropic
from services.mcp_client import ask_claude
from services.db import (
    get_conn, create_session, save_message,
    get_session_messages, list_sessions, delete_session
)

router = APIRouter()
logger = logging.getLogger(__name__)


def try_fast_answer(cur, message):
    """Answer common analytics without invoking the MCP agent."""
    text = re.sub(r"[^a-z0-9 ]", " ", message.lower())

    if re.search(r"\b(how many|number of|count)\b.*\bapplications?\b", text):
        cur.execute("""
            SELECT count(*), count(*) FILTER (WHERE status IN
                ('rejection_after_application', 'rejection_after_interview'))
            FROM applications
        """)
        total, rejections = cur.fetchone()
        return f"You're tracking **{total} applications**, including **{rejections} rejections**."

    if re.search(r"\b(funnel|pipeline|where.*reject|rejection.*stage)\b", text):
        cur.execute("""
            SELECT CASE
                WHEN status IN ('applied_confirmation', 'other') THEN 'applied'
                WHEN status = 'screening_scheduled' THEN 'screening'
                WHEN status = 'interview_scheduled' THEN 'interview'
                WHEN status = 'offer' THEN 'offer'
                WHEN status = 'rejection_after_application' THEN 'rejected pre-interview'
                WHEN status = 'rejection_after_interview' THEN 'rejected post-interview'
                ELSE 'other' END AS stage, count(*)
            FROM applications GROUP BY stage ORDER BY count(*) DESC
        """)
        rows = "\n".join(f"| {stage} | {count} |" for stage, count in cur.fetchall())
        return f"Here's your pipeline breakdown:\n\n| Stage | Count |\n|---|---:|\n{rows}"

    if re.search(r"\b(summary|summarize|overview)\b.*\b(job search|applications?|progress)\b", text):
        cur.execute("""
            SELECT status, count(*) FROM applications
            GROUP BY status ORDER BY count(*) DESC
        """)
        counts = cur.fetchall()
        total = sum(count for _, count in counts)
        lines = "\n".join(
            f"- **{(status or 'unknown').replace('_', ' ')}**: {count}"
            for status, count in counts
        )
        return f"You have **{total} applications** tracked.\n\n{lines}"

    return None

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class SaveExchangeRequest(BaseModel):
    session_id: str | None = None
    user_message: str
    assistant_message: str

@router.post("/chat")
def chat(req: ChatRequest):
    started = time.perf_counter()
    conn = get_conn()
    cur = conn.cursor()

    session_id = req.session_id
    if not session_id:
        title = req.message[:40]
        session_id = str(create_session(cur, title))
        conn.commit()

    history = get_session_messages(cur, session_id, limit=12)
    save_message(cur, session_id, "user", req.message)
    conn.commit()

    reply = try_fast_answer(cur, req.message)
    path = "sql"

    # A remote agent call must not hold an idle CockroachDB connection.
    if reply is None:
        path = "mcp"
        cur.close()
        conn.close()
        try:
            reply = ask_claude(req.message, conversation_history=history)
        except (anthropic.APITimeoutError, anthropic.APIConnectionError):
            logger.warning("Chat MCP request timed out", exc_info=True)
            reply = (
                "That analysis exceeded the 50-second limit. Try narrowing the question "
                "to a company, date range, pipeline stage, or interview topic."
            )
        except anthropic.APIError:
            logger.exception("Chat MCP request failed")
            reply = "The analysis service failed to respond. Please try again."
        conn = get_conn()
        cur = conn.cursor()

    save_message(cur, session_id, "assistant", reply)
    conn.commit()

    cur.close()
    conn.close()

    logger.info("chat_completed path=%s duration_ms=%d", path,
                round((time.perf_counter() - started) * 1000))

    return {"session_id": session_id, "reply": reply}

@router.post("/chat/save")
def save_exchange(req: SaveExchangeRequest):
    """Persist a fast-path (non-LLM) Q&A exchange, e.g. from /stats endpoints."""
    conn = get_conn()
    cur = conn.cursor()

    session_id = req.session_id
    if not session_id:
        title = req.user_message[:40]
        session_id = str(create_session(cur, title))
        conn.commit()

    save_message(cur, session_id, "user", req.user_message)
    save_message(cur, session_id, "assistant", req.assistant_message)
    conn.commit()

    cur.close()
    conn.close()
    return {"session_id": session_id}

@router.get("/sessions")
def get_sessions():
    conn = get_conn()
    cur = conn.cursor()
    sessions = list_sessions(cur)
    cur.close()
    conn.close()
    return sessions

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    conn = get_conn()
    cur = conn.cursor()
    messages = get_session_messages(cur, session_id)
    cur.close()
    conn.close()
    return messages

@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    conn = get_conn()
    cur = conn.cursor()
    delete_session(cur, session_id)
    conn.commit()
    cur.close()
    conn.close()
    return {"deleted": session_id}
