from fastapi import APIRouter
from pydantic import BaseModel
from services.db import get_conn
from services.embeddings import get_embedding

router = APIRouter()

@router.post("/applications/{app_id}/interview-rounds")
def log_interview_round(app_id: str, body: InterviewRound):
    conn = get_conn()
    cur = conn.cursor()

    embedding = get_embedding(body.questions_asked) if body.questions_asked else None

    cur.execute("""
        INSERT INTO interview_rounds 
        (application_id, round_number, round_type, date, questions_asked, self_rating, outcome, notes, questions_embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (app_id, body.round_number, body.round_type, body.date,
          body.questions_asked, body.self_rating, body.outcome, body.notes, embedding))
    conn.commit()
    cur.close()
    conn.close()
    return {"logged": True}

@router.get("/applications")
def list_applications():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, company, role, status, date_applied 
        FROM applications ORDER BY date_applied DESC NULLS LAST
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": str(r[0]), "company": r[1], "role": r[2],
            "status": r[3], "date_applied": r[4].isoformat() if r[4] else None
        }
        for r in rows
    ]

class UpdateApplication(BaseModel):
    company: str | None = None
    role: str | None = None
    status: str | None = None

@router.patch("/applications/{app_id}")
def update_application(app_id: str, body: UpdateApplication):
    conn = get_conn()
    cur = conn.cursor()
    updates, values = [], []
    if body.company is not None:
        updates.append("company = %s"); values.append(body.company)
    if body.role is not None:
        updates.append("role = %s"); values.append(body.role)
    if body.status is not None:
        updates.append("status = %s"); values.append(body.status)
        updates.append("status_source = 'manual'")

    if updates:
        values.append(app_id)
        cur.execute(f"UPDATE applications SET {', '.join(updates)} WHERE id = %s", values)
        conn.commit()

    cur.close()
    conn.close()
    return {"updated": app_id}

class InterviewRound(BaseModel):
    round_number: int | None = None
    round_type: str | None = None
    date: str | None = None
    questions_asked: str | None = None
    self_rating: int | None = None
    outcome: str | None = None
    notes: str | None = None

@router.post("/applications/{app_id}/interview-rounds")
def log_interview_round(app_id: str, body: InterviewRound):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO interview_rounds 
        (application_id, round_number, round_type, date, questions_asked, self_rating, outcome, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (app_id, body.round_number, body.round_type, body.date,
          body.questions_asked, body.self_rating, body.outcome, body.notes))
    conn.commit()
    cur.close()
    conn.close()
    return {"logged": True}

@router.get("/applications/{app_id}/interview-rounds")
def get_interview_rounds(app_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT round_number, round_type, date, questions_asked, self_rating, outcome, notes
        FROM interview_rounds WHERE application_id = %s ORDER BY round_number ASC
    """, (app_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "round_number": r[0], "round_type": r[1],
            "date": r[2].isoformat() if r[2] else None,
            "questions_asked": r[3], "self_rating": r[4],
            "outcome": r[5], "notes": r[6]
        }
        for r in rows
    ]