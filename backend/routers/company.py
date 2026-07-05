from fastapi import APIRouter
import anthropic
import os
from services.db import get_conn
from services.research import research_company

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def get_application_status(company_name: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, role, status, date_applied, company_context 
        FROM applications 
        WHERE lower(company) LIKE lower(%s) LIMIT 1
    """, (f"%{company_name}%",))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return None

    app_id, role, status, date_applied, cached_context = row

    cur.execute("""
        SELECT subject, detected_stage, email_date FROM gmail_events 
        WHERE application_id = %s ORDER BY email_date ASC
    """, (app_id,))
    events = cur.fetchall()

    cur.close()
    conn.close()
    return {
        "role": role,
        "status": status,
        "date_applied": date_applied.isoformat() if date_applied else None,
        "cached_context": cached_context,
        "event_count": len(events),
    }


@router.get("/company/{company_name}/status-with-research")
def status_with_research(company_name: str):
    app_data = get_application_status(company_name)
    if not app_data:
        return {"found": False}

    context = app_data["cached_context"]
    if not context:
        context = research_company(company_name)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE applications SET company_context = %s WHERE lower(company) LIKE lower(%s)",
            (context, f"%{company_name}%")
        )
        conn.commit()
        cur.close()
        conn.close()

    prompt = f"""Given this application data and company research, write a brief 2-3 
sentence status update followed by 2-3 sentences of relevant company context.

Application: {company_name}, role: {app_data['role']}, status: {app_data['status']}, 
applied: {app_data['date_applied']}, {app_data['event_count']} tracked email events.

Company research:
{context}

Be direct and factual. No filler phrases, no exclamation marks."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "found": True,
        "reply": response.content[0].text
    }