from fastapi import APIRouter
from services.db import get_conn
import json
from services.research import research_company

router = APIRouter()
@router.get("/stats/company-insights")
def get_company_insights():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, company, role, status, company_context 
        FROM applications 
        WHERE company IS NOT NULL 
        ORDER BY date_applied DESC NULLS LAST
        LIMIT 6
    """)
    rows = cur.fetchall()

    insights = []
    for app_id, company, role, status, cached_context in rows:
        if cached_context:
            data = json.loads(cached_context)
        else:
            data = research_company(company)
            cur.execute("UPDATE applications SET company_context = %s WHERE id = %s", (json.dumps(data), app_id))
            conn.commit()

        insights.append({
            "company": company,
            "role": role,
            "status": status,
            "rating": data.get("rating"),
            "summary": data.get("summary"),
            "recent_move": data.get("recent_move"),
            "website": data.get("website"),
        })

    cur.close()
    conn.close()
    return {"companies": insights}

@router.get("/stats/summary")
def get_summary():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM applications")
    total = cur.fetchone()[0]

    cur.execute("SELECT status, count(*) FROM applications GROUP BY status ORDER BY count(*) DESC")
    by_status = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute("SELECT count(*) FROM job_leads")
    leads = cur.fetchone()[0]

    cur.execute("""
        SELECT count(*) FROM applications 
        WHERE status IN ('rejection_after_application', 'rejection_after_interview')
    """)
    rejections = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_applications": total,
        "by_status": by_status,
        "pending_leads": leads,
        "total_rejections": rejections,
    }


@router.get("/stats/funnel")
def get_funnel():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            CASE 
                WHEN status IN ('applied_confirmation', 'other') THEN 'applied'
                WHEN status = 'screening_scheduled' THEN 'screening'
                WHEN status = 'interview_scheduled' THEN 'interview'
                WHEN status = 'offer' THEN 'offer'
                WHEN status = 'rejection_after_application' THEN 'rejected_pre_interview'
                WHEN status = 'rejection_after_interview' THEN 'rejected_post_interview'
                ELSE 'other'
            END AS stage,
            count(*) 
        FROM applications 
        GROUP BY stage
    """)
    funnel = {row[0]: row[1] for row in cur.fetchall()}

    cur.close()
    conn.close()
    return {"funnel": funnel}


@router.get("/stats/company/{company_name}")
def get_company_history(company_name: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, role, status, date_applied FROM applications 
        WHERE lower(company) LIKE lower(%s)
    """, (f"%{company_name}%",))
    apps = cur.fetchall()

    if not apps:
        cur.close()
        conn.close()
        return {"found": False}

    app_id = apps[0][0]
    cur.execute("""
        SELECT subject, detected_stage, email_date FROM gmail_events 
        WHERE application_id = %s ORDER BY email_date ASC
    """, (app_id,))
    events = [{"subject": s, "stage": st, "date": d.isoformat() if d else None} 
              for s, st, d in cur.fetchall()]

    cur.close()
    conn.close()
    return {
        "found": True,
        "role": apps[0][1],
        "current_status": apps[0][2],
        "date_applied": apps[0][3].isoformat() if apps[0][3] else None,
        "timeline": events,
    }


@router.get("/stats/timeline")
def get_timeline():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT date_applied::date, count(*) FROM applications 
        WHERE date_applied IS NOT NULL 
        GROUP BY date_applied::date ORDER BY date_applied::date
    """)
    timeline = [{"date": d.isoformat(), "count": c} for d, c in cur.fetchall()]

    cur.close()
    conn.close()
    return {"timeline": timeline}