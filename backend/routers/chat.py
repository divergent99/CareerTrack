from fastapi import APIRouter
from pydantic import BaseModel
from services.mcp_client import ask_claude
from services.db import (
    get_conn, create_session, save_message,
    get_session_messages, list_sessions, delete_session
)

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class SaveExchangeRequest(BaseModel):
    session_id: str | None = None
    user_message: str
    assistant_message: str

@router.post("/chat")
def chat(req: ChatRequest):
    conn = get_conn()
    cur = conn.cursor()

    session_id = req.session_id
    if not session_id:
        title = req.message[:40]
        session_id = str(create_session(cur, title))
        conn.commit()

    history = get_session_messages(cur, session_id)
    save_message(cur, session_id, "user", req.message)
    conn.commit()

    reply = ask_claude(req.message, conversation_history=history)

    save_message(cur, session_id, "assistant", reply)
    conn.commit()

    cur.close()
    conn.close()

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