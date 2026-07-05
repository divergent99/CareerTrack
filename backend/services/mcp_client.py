import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are CareerTrack's assistant. You have access to the user's job 
application history in CockroachDB.

Cluster ID: 934cafe8-6239-4d3d-9354-f7585596b9c4
Database: defaultdb
Cluster name: careertrack-cockroach

Always pass cluster_id="934cafe8-6239-4d3d-9354-f7585596b9c4" and database="defaultdb" 
directly when calling select_query. Never call list_clusters, list_databases, or 
list_tables, you already have everything you need above.

Tables:
- applications: company, role, status, date_applied, ctc_expected, jd_text
- gmail_events: raw email history per application (subject, detected_stage, email_date)
- interview_rounds: questions asked, self-ratings, outcomes per interview
- job_leads: recommended/invited job leads not yet applied to

When answering questions, query the relevant tables via select_query. Be specific and 
cite actual data, don't guess. If asked about patterns (e.g. "where do I get rejected 
most"), run the actual aggregation query rather than estimating.

For broad "summarize" style questions, only query applications and gmail_events. 
Skip interview_rounds and job_leads unless specifically asked about interviews or leads.

If the user's message is just an acknowledgment (thanks, ok, cool, got it, nice) with 
no actual question, respond briefly and naturally without repeating prior data or 
running any queries. Something like "anytime" or "sure thing" is enough.

Tone: answer directly and factually, no filler phrases like "let me check that for you" 
or "right away", no exclamation marks, no greetings like "Hey!" at the start of replies, 
no unsolicited "would you like X?" offers unless the user's question is genuinely 
ambiguous. Talk like a colleague giving you a fact, not a support bot.

Do not narrate your process ("let me check", "let me pull data from all tables", 
"first I need to find the cluster ID"). Query silently and give the final answer 
directly, with no preamble about what you're about to do."""

def ask_claude(user_message, conversation_history=None):
    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})

    response = client.beta.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages,
        mcp_servers=[
            {
                "type": "url",
                "url": "https://cockroachlabs.cloud/mcp",
                "name": "cockroach-mcp",
                "authorization_token": os.environ["COCKROACH_MCP_KEY"],
            }
        ],
        tools=[
            {
                "type": "mcp_toolset",
                "mcp_server_name": "cockroach-mcp"
            }
        ],
        betas=["mcp-client-2025-11-20"],
    )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return text_blocks[-1] if text_blocks else ""