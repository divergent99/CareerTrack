import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ["COCKROACH_URL"])
conn.autocommit = True
cur = conn.cursor()

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    jd_text TEXT,
    jd_embedding VECTOR(1536),
    source TEXT,
    date_applied DATE,
    ctc_expected TEXT,
    company_context TEXT,
    status TEXT DEFAULT 'applied',
    status_source TEXT DEFAULT 'manual',
    last_activity_date DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interview_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    round_number INT,
    round_type TEXT,
    date DATE,
    questions_asked TEXT,
    questions_embedding VECTOR(1536),
    self_rating INT,
    outcome TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gmail_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    thread_id TEXT,
    subject TEXT,
    snippet TEXT,
    detected_stage TEXT,
    email_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT,
    role TEXT,
    source TEXT,
    lead_type TEXT,
    jd_snippet TEXT,
    date_received DATE,
    acted_on BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE VECTOR INDEX IF NOT EXISTS applications_jd_idx ON applications (jd_embedding);
CREATE VECTOR INDEX IF NOT EXISTS interview_rounds_q_idx ON interview_rounds (questions_embedding);
CREATE INDEX IF NOT EXISTS applications_date_idx ON applications (date_applied DESC);
CREATE INDEX IF NOT EXISTS gmail_events_application_date_idx ON gmail_events (application_id, email_date);
CREATE INDEX IF NOT EXISTS interview_rounds_application_round_idx ON interview_rounds (application_id, round_number);
"""

for statement in SCHEMA.strip().split(";"):
    stmt = statement.strip()
    if stmt:
        cur.execute(stmt)
        print(f"OK: {stmt[:60]}...")

cur.execute("SHOW TABLES;")
print("\nTables:", cur.fetchall())

cur.close()
conn.close()
