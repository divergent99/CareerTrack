import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.environ["COCKROACH_URL"])

def normalize(name):
    if not name:
        return None
    n = name.lower().strip()
    n = re.sub(r'\s+', '', n)  # strip all whitespace FIRST
    n = re.sub(r'(ltd|limited|inc|services|solutions|pvt|private|technologies|tech)$', '', n)  # then strip suffix from the end
    return n

def find_or_create_application(cur, company, role, thread_id, date_applied=None):
    cur.execute("SELECT id FROM applications WHERE last_thread_id = %s", (thread_id,))
    row = cur.fetchone()
    if row:
        return row[0]

    norm = normalize(company)
    if norm:
        cur.execute("""
            SELECT id FROM applications 
            WHERE normalize_company_stub = %s
            ORDER BY created_at DESC LIMIT 1
        """, (norm,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE applications SET last_thread_id = %s WHERE id = %s",
                (thread_id, row[0])
            )
            return row[0]

    cur.execute("""
        INSERT INTO applications (company, role, status, date_applied, last_thread_id, normalize_company_stub)
        VALUES (%s, %s, 'applied', %s, %s, %s)
        RETURNING id
    """, (company, role, date_applied, thread_id, norm))
    return cur.fetchone()[0]

def insert_gmail_event(cur, application_id, thread_id, subject, snippet, stage, email_date):
    cur.execute("""
        INSERT INTO gmail_events (application_id, thread_id, subject, snippet, detected_stage, email_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (application_id, thread_id, subject, snippet, stage, email_date))

def update_application_status(cur, application_id, stage):
    cur.execute("""
        UPDATE applications 
        SET status = %s, status_source = 'gmail_detected', last_activity_date = now()
        WHERE id = %s
    """, (stage, application_id))

def insert_job_lead(cur, company, role, source, lead_type, snippet, email_date):
    cur.execute("""
        INSERT INTO job_leads (company, role, source, lead_type, jd_snippet, date_received)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (company, role, source, lead_type, snippet, email_date))