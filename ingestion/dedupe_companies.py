# ingestion/dedupe_companies.py
import re
from db import get_conn

def normalize(name):
    if not name:
        return None
    n = name.lower().strip()
    n = re.sub(r'\s+', '', n)  # strip all whitespace FIRST
    n = re.sub(r'(ltd|limited|inc|services|solutions|pvt|private|technologies|tech)$', '', n)  # then strip suffix from the end
    return n

def find_and_merge_duplicates():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, company, date_applied FROM applications WHERE company IS NOT NULL")
    rows = cur.fetchall()

    groups = {}
    for app_id, company, date_applied in rows:
        key = normalize(company)
        groups.setdefault(key, []).append((app_id, company, date_applied))

    for key, entries in groups.items():
        if len(entries) <= 1:
            continue

        # keep the oldest entry (earliest date_applied), it's likely the "real" first contact
        entries.sort(key=lambda x: (x[2] is None, x[2]))
        keep_id, keep_company, _ = entries[0]
        losers = entries[1:]

        print(f"Merging into '{keep_company}' ({keep_id}):")
        for loser_id, loser_company, _ in losers:
            print(f"  - absorbing '{loser_company}' ({loser_id})")
            cur.execute("UPDATE gmail_events SET application_id = %s WHERE application_id = %s", (keep_id, loser_id))
            cur.execute("UPDATE interview_rounds SET application_id = %s WHERE application_id = %s", (keep_id, loser_id))
            cur.execute("DELETE FROM applications WHERE id = %s", (loser_id,))

        conn.commit()

    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    find_and_merge_duplicates()