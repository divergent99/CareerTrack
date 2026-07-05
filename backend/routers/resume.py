from fastapi import APIRouter, UploadFile, File
import anthropic
import os
import json
from services.db import get_conn
from services.resume import extract_resume_text

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def get_application_history():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT company, role, status FROM applications 
        WHERE company IS NOT NULL ORDER BY date_applied DESC
    """)
    apps = cur.fetchall()

    cur.execute("""
        SELECT a.company, ir.round_type, ir.questions_asked, ir.outcome
        FROM interview_rounds ir JOIN applications a ON ir.application_id = a.id
        WHERE ir.questions_asked IS NOT NULL
    """)
    rounds = cur.fetchall()

    cur.close()
    conn.close()
    return apps, rounds


@router.post("/resume/analyze")
async def analyze_resume(file: UploadFile = File(...)):
    file_bytes = await file.read()
    resume_text = extract_resume_text(file_bytes)

    apps, rounds = get_application_history()

    apps_text = "\n".join(f"- {c} ({r}): {s}" for c, r, s in apps) or "No applications tracked."
    rounds_text = "\n".join(f"- {c} ({rt}): {q} [outcome: {o}]" for c, rt, q, o in rounds) or "No interview history logged."

    prompt = f"""Analyze this resume against the person's actual job application history. 
Return ONLY valid JSON, no markdown fences, no preamble.

RESUME:
{resume_text[:6000]}

APPLICATION HISTORY:
{apps_text}

INTERVIEW QUESTIONS ASKED ACROSS APPLICATIONS:
{rounds_text}

Return this exact JSON shape:
{{
  "overall_summary": "2-3 sentence honest assessment of the resume's current positioning",
  "strengths": ["3-5 short bullet points of what's genuinely strong"],
  "gaps": ["3-5 short bullet points of what's missing or weak, be direct not diplomatic"],
  "company_fit": [
    {{"company": "name", "role": "role", "fit": "strong/moderate/weak", "reason": "1 sentence why"}}
  ],
  "suggested_edits": ["3-5 concrete, specific resume edit suggestions, not generic advice"],
  "pattern_from_rejections": "1-2 sentences if there's a visible pattern in what's causing rejections based on interview data, else null"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    parsed = json.loads(raw[start:end+1])

    return parsed