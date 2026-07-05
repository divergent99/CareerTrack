import os
import re
import base64
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from classify import classify_email
from db import get_conn, find_or_create_application, insert_gmail_event, update_application_status, insert_job_lead

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
NOISE_SENDERS = ["naukrialerts@naukri.com"]
AGGREGATOR_DOMAINS = [
    "naukri.com", "linkedin.com", "indeed.com", "internshala.com",
    "getujobs.com", "shine.com", "monster.com", "glassdoor.com"
]

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def extract_plain_body(payload):
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        result = extract_plain_body(part)
        if result:
            return result
    return None

def extract_html_body(payload):
    if payload.get("mimeType") == "text/html" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        result = extract_html_body(part)
        if result:
            return result
    return None

def strip_html_tags(html):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_full_body(payload):
    plain = extract_plain_body(payload)
    if plain and len(plain.strip()) > 150:
        return plain
    html = extract_html_body(payload)
    if html:
        stripped = strip_html_tags(html)
        if stripped:
            return stripped
    return plain if plain else None

def extract_domain(sender):
    match = re.search(r'@([\w.-]+)', sender)
    return match.group(1).lower() if match else None

def is_aggregator_domain(domain):
    if not domain:
        return False
    return any(agg in domain for agg in AGGREGATOR_DOMAINS)

def parse_email_date(date_str):
    try:
        return parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        return None

def fetch_interview_threads(service, max_results=100):
    query = (
        'subject:(interview OR application OR "thank you for applying" OR shortlisted '
        'OR assessment OR HR OR "hr discussion" OR recruiter OR "hiring team" OR '
        '"next steps" OR offer OR compensation OR CTC OR "easy apply" OR '
        '"your application was sent" OR "your application to" OR '
        '"not moving forward" OR "other candidates" OR "position has been filled" OR '
        '"regarding your application" OR notification OR update OR discussion OR panel)'
    )
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = full["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        to = next((h["value"] for h in headers if h["name"] == "To"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")
        snippet = full.get("snippet", "")
        emails.append({
            "thread_id": msg["id"],
            "subject": subject,
            "from": sender,
            "to": to,
            "date": date,
            "snippet": snippet,
            "payload": full["payload"]
        })
    return emails

if __name__ == "__main__":
    service = get_gmail_service()
    emails = fetch_interview_threads(service)
    conn = get_conn()
    cur = conn.cursor()

    for e in emails:
        if any(noise in e["from"].lower() for noise in NOISE_SENDERS):
            print("SKIP (noise sender):", e["date"], "|", e["subject"])
            continue

        domain = extract_domain(e["from"])
        sender_is_aggregator = is_aggregator_domain(domain)

        result = classify_email(e["subject"], e["from"], e["snippet"], e["to"], domain, sender_is_aggregator)

        # Always verify against full body for application events. Subject lines and
        # snippets are unreliable across every ATS/recruiter platform, not just one —
        # cheaper to always double-check than to keep patching per-domain exceptions.
        if result["category"] == "application_event":
            body = get_full_body(e["payload"])
            if body:
                retry = classify_email(e["subject"], e["from"], body[:6000], e["to"], domain, sender_is_aggregator)
                result = retry

        parsed_date = parse_email_date(e["date"])

        if result["category"] == "application_event":
            app_id = find_or_create_application(cur, result.get("company"), result.get("role"), e["thread_id"], parsed_date)
            insert_gmail_event(cur, app_id, e["thread_id"], e["subject"], e["snippet"], result.get("stage"), parsed_date)
            update_application_status(cur, app_id, result.get("stage"))
            conn.commit()
            print("SAVED APPLICATION:", e["date"], "|", e["subject"], "|", result)

        elif result["category"] == "job_lead":
            insert_job_lead(cur, result.get("company"), result.get("role"), domain, result.get("lead_type"), e["snippet"], parsed_date)
            conn.commit()
            print("SAVED LEAD:", e["date"], "|", e["subject"], "|", result)

        else:
            print("SKIP:", e["date"], "|", e["subject"])

    cur.close()
    conn.close()