from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import logging
import time
import anthropic
import psycopg2
from services.mcp_client import stream_agent
from services.db import (
    get_conn, create_session, save_message,
    get_session_messages, list_sessions, get_session, rename_session, delete_session
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class SaveExchangeRequest(BaseModel):
    session_id: str | None = None
    user_message: str
    assistant_message: str

class RenameSessionRequest(BaseModel):
    title: str


def _start_turn(req):
    """Create the session if needed, load history, store the user message.
    Autocommit so no transaction stays open while the model runs."""
    conn = get_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        session_id = req.session_id
        if not session_id:
            session_id = str(create_session(cur, req.message[:40]))
        history = get_session_messages(cur, session_id, limit=12)
        save_message(cur, session_id, "user", req.message)
        cur.close()
        return session_id, history
    finally:
        conn.close()


def _finish_turn(session_id, reply):
    conn = get_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        save_message(cur, session_id, "assistant", reply)
        cur.close()
    finally:
        conn.close()


def _error_text(e):
    if isinstance(e, (anthropic.APITimeoutError, anthropic.APIConnectionError)):
        return "That took too long on my end. Try again, or narrow it to a company or date range."
    if isinstance(e, anthropic.APIError):
        return f"The model API errored ({type(e).__name__}). Try again in a bit."
    if isinstance(e, psycopg2.Error):
        return "Couldn't reach the database just now. Try again."
    return f"Something broke: {type(e).__name__}: {str(e)[:200]}"


def _run_turn(req):
    """Generator of SSE-style events for one chat turn, including persistence."""
    started = time.perf_counter()
    session_id, history = _start_turn(req)
    yield {"type": "session", "session_id": session_id}

    text = ""
    try:
        for ev in stream_agent(req.message, history):
            if ev["type"] == "delta":
                text += ev["text"]
            elif ev["type"] == "reset":
                text = ""
            yield ev
        text = text.strip() or "I didn't get an answer back for that. Try rephrasing."
    except Exception as e:
        logger.exception("Chat agent failed")
        text = _error_text(e)
        yield {"type": "reset"}
        yield {"type": "delta", "text": text}

    try:
        _finish_turn(session_id, text)
    except Exception:
        logger.exception("Failed to save assistant reply")
    logger.info("chat_completed duration_ms=%d",
                round((time.perf_counter() - started) * 1000))
    yield {"type": "done", "reply": text}


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    def sse():
        for ev in _run_turn(req):
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(
        sse(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
def chat(req: ChatRequest):
    """Non-streaming fallback: same behaviour, returns the full reply."""
    session_id, reply = None, ""
    for ev in _run_turn(req):
        if ev["type"] == "session":
            session_id = ev["session_id"]
        elif ev["type"] == "done":
            reply = ev["reply"]
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

@router.get("/sessions/{session_id}")
def get_session_details(session_id: str):
    conn = get_conn()
    cur = conn.cursor()
    session = get_session(cur, session_id)
    cur.close()
    conn.close()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Chat not found")
    return session

@router.patch("/sessions/{session_id}")
def update_session(session_id: str, body: RenameSessionRequest):
    title = body.title.strip()
    if not title:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    title = title[:80]
    conn = get_conn()
    cur = conn.cursor()
    updated = rename_session(cur, session_id, title)
    conn.commit()
    cur.close()
    conn.close()
    if not updated:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"id": session_id, "title": title}

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
