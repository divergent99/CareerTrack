import os
import re
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def extract_json(text):
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def classify_email(subject, sender, snippet, recipient="", sender_domain="", sender_is_aggregator=False):
    aggregator_note = (
        "The sender domain is a KNOWN JOB AGGREGATOR/PORTAL — do not use it as the company name."
        if sender_is_aggregator else
        f"The sender domain '{sender_domain}' is NOT a known aggregator. If this looks like a "
        f"company's own domain (e.g. jobs@companyname.com, hr@companyname.com), treat the domain "
        f"itself as strong evidence of the company name, even if the body doesn't restate it."
    )

    prompt = f"""You're parsing an email related to job hunting. Classify it into exactly one category.

{aggregator_note}

Subject lines and snippets are unreliable across ALL recruiter platforms and ATS tools, 
not just one specific vendor — generic subjects like "Notification: Role at Company" or 
"Your update from X" can mean an interview invite, a rejection, or nothing at all. Never 
infer the stage from the subject pattern alone. Base the stage strictly on body content: 
"we will not be able to take this forward" / "not the best fit" / "gaps between our needs 
and your expertise" / "unfortunately" / "other candidates" = rejection_after_application 
or rejection_after_interview (rejection_after_interview if the body references a call, 
panel discussion, or interview having already happened).

If this email was SENT BY the user (check if "From" looks like the user's own address, or 
the tone reads as a first-person reply/negotiation), the recipient ("To" field) is your 
best signal for which company this thread is about, NOT any company name mentioned in the 
body as a past employer. Phrases like "my previous organization X" or "my last company Y" 
refer to PAST employment context, not the company being discussed in this thread — do not 
extract those as the company.

Also watch for financial/loan/insurance spam that abuses job-portal branding or subject 
lines like "Application Received" — read the actual content, not just the subject pattern.

Note: Naukri/LinkedIn "job alert," "weekly roundup," "recommended jobs," or "you're invited 
to apply" emails are JOB LEADS, not application events. Educational content, prep guides, or 
job-search newsletters are NOT relevant on their own, but if the same email also confirms an 
actual application status change, classify based on that.

Extract:
- category: one of [application_event, job_lead, not_relevant]
- company: the company this THREAD is actually about, else null
- role: job title if mentioned, else null
- stage: one of [applied_confirmation, screening_scheduled, interview_scheduled, 
  walkin_invitation, interview_followup, rejection_after_application, 
  rejection_after_interview, offer, ghosted, feedback_request, post_offer_onboarding, other] 
  (only fill if category is application_event, else null)
  "walkin_invitation" is for walk-in interview drive invitations (open recruitment events, 
  no fixed appointment time), distinct from "interview_scheduled" which is a specific 
  scheduled 1:1 slot.
- lead_type: one of [recommended, invited_to_apply] 
  (only fill if category is job_lead, else null)
- confidence: high/medium/low

Return ONLY the JSON object, no preamble, no explanation, no markdown fences.

Subject: {subject}
From: {sender}
To: {recipient}
Snippet: {snippet}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.content[0].text.strip()
    json_text = extract_json(raw_text)

    if not json_text:
        print("EMPTY RESPONSE — raw response object:", response)
        raise ValueError("Claude returned empty text")

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        print("BAD JSON, raw text was:", repr(raw_text))
        raise