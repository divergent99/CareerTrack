from fastapi import APIRouter
from pydantic import BaseModel
import anthropic
import os
from services.db import get_conn
from services.research import research_company
from services.embeddings import get_embedding

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class RoadmapRequest(BaseModel):
    company: str
    role: str = ""
    jd_text: str = ""


def get_similar_past_questions(query_text, limit=5):
    """Vector search: pull the most relevant past interview questions for this JD/role,
    not just everything logged. Uses the questions_embedding vector index."""
    query_embedding = get_embedding(query_text)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.company, a.role, ir.round_type, ir.questions_asked, ir.outcome, ir.self_rating,
               ir.questions_embedding <-> %s::VECTOR AS distance
        FROM interview_rounds ir
        JOIN applications a ON ir.application_id = a.id
        WHERE ir.questions_embedding IS NOT NULL
        ORDER BY distance ASC
        LIMIT %s
    """, (query_embedding, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


@router.get("/roadmap/lookup/{company_name}")
def lookup_application(company_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, role, jd_text, status FROM applications 
        WHERE lower(company) LIKE lower(%s) LIMIT 1
    """, (f"%{company_name}%",))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return {"found": False}

    app_id, role, jd_text, status = row
    return {
        "found": True,
        "application_id": str(app_id),
        "role": role,
        "jd_text": jd_text,
        "status": status,
    }


@router.post("/roadmap/generate")
def generate_roadmap(req: RoadmapRequest):
    # embed the JD if given, else fall back to role+company so search has something to match against
    search_text = req.jd_text.strip() if req.jd_text.strip() else f"{req.role} at {req.company}"
    similar_questions = get_similar_past_questions(search_text)

    if similar_questions:
        history_text = "\n".join(
            f"- {company} ({role}, {rtype or 'unspecified round'}): {q} "
            f"[outcome: {outcome}, self-rated {rating}/5, similarity distance: {dist:.3f}]"
            for company, role, rtype, q, outcome, rating, dist in similar_questions
        )
    else:
        history_text = "No interview questions logged yet."

    company_research = research_company(req.company)
    research_summary = company_research.get("summary", "No research available.")
    recent_move = company_research.get("recent_move")

    jd_section = req.jd_text.strip() if req.jd_text.strip() else "No job description provided, base this on the role title and company research alone."

    prompt = f"""You're helping prepare for an upcoming interview. Build a focused prep roadmap.

Target role: {req.role or "unspecified role"} at {req.company}

Job description:
{jd_section}

Company research:
{research_summary}
{f"Recent development: {recent_move}" if recent_move else ""}

Most similar past interview questions from this person's history, retrieved via vector 
similarity search against the target JD/role (lower distance = more relevant, these have 
been specifically matched to this role, not just pulled from everything logged):
{history_text}

Write a roadmap with these sections:
1. **Likely focus areas** — based on the JD and the similar past questions retrieved above
2. **Company-specific prep** — what to know about {req.company} specifically
3. **Watch out for** — if the retrieved history shows a recurring weak spot (low self-ratings, failed outcomes), call it out directly
4. **Quick prep checklist** — 4-6 concrete action items

If no JD was given, be upfront that this is based on general role expectations and 
your own history, not the specific posting. Be direct and specific, no filler phrases."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"roadmap": response.content[0].text}