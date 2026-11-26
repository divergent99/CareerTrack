"""Chat agent: Claude + a local read-only SQL tool.

Previously this went through Cockroach Cloud's hosted MCP server, which added a
remote hop per tool call (slow) and only gave the model a partial, hand-written
schema (so it guessed column names / status values and then made things up).
Now the model gets the live schema plus the real enum-like values, and its SQL
runs directly against our own DB connection.
"""
import json
import logging
import os
import re
import threading
import time
from datetime import date, datetime
from decimal import Decimal

import anthropic
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Haiku is several times faster per call than Sonnet and plenty for
# text-to-SQL with the full schema in the prompt. Override via CHAT_MODEL.
MODEL = os.environ.get("CHAT_MODEL", "claude-haiku-4-5")
MAX_TOOL_TURNS = 4
MAX_ROWS = 100
MAX_CELL_CHARS = 400
SCHEMA_TTL_SECONDS = 600

TABLES = ["applications", "gmail_events", "interview_rounds", "job_leads"]
# Low-cardinality columns whose actual values the model must see, otherwise it
# filters on status = 'rejected' (doesn't exist), gets 0 rows, and improvises.
CATEGORICAL = {
    "applications": ["status", "status_source", "source"],
    "gmail_events": ["detected_stage"],
    "interview_rounds": ["round_type", "outcome"],
    "job_leads": ["lead_type", "source"],
}

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"], timeout=50.0, max_retries=1
)

_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(1, 4, os.environ["COCKROACH_URL"])
        return _pool


class _ReadOnlyConn:
    """Pooled connection, always read-only with a statement timeout."""

    def _open(self, p):
        self.conn = p.getconn()
        self.conn.rollback()
        # psycopg2 issues BEGIN READ ONLY for every transaction on this conn.
        self.conn.set_session(readonly=True, autocommit=False)
        self.cur = self.conn.cursor()
        self.cur.execute("SET statement_timeout = '8s'")

    def __enter__(self):
        p = _get_pool()
        try:
            self._open(p)
        except psycopg2.Error:
            # Stale pooled connection (Cockroach Cloud drops idle ones): replace once.
            p.putconn(self.conn, close=True)
            self._open(p)
        return self.cur

    def __exit__(self, exc_type, exc, tb):
        broken = False
        try:
            self.conn.rollback()
        except psycopg2.Error:
            broken = True
        self.cur.close()
        _get_pool().putconn(self.conn, close=broken)
        return False


# ---------- schema context ----------

_schema_cache = {"text": None, "at": 0.0}


def _build_schema_text():
    lines = []
    with _ReadOnlyConn() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            ORDER BY table_name, ordinal_position
            """,
            (TABLES,),
        )
        cols = {}
        for table, col, dtype in cur.fetchall():
            if "vector" in dtype.lower() or col.endswith("_embedding"):
                continue  # useless to the model and huge in results
            cols.setdefault(table, []).append(f"{col} {dtype}")

        for table in TABLES:
            if table not in cols:
                continue
            lines.append(f"- {table}({', '.join(cols[table])})")
            for col in CATEGORICAL.get(table, []):
                if not any(c.startswith(col + " ") for c in cols[table]):
                    continue
                cur.execute(
                    f"SELECT {col}, count(*) FROM {table} "
                    f"WHERE {col} IS NOT NULL GROUP BY 1 ORDER BY 2 DESC LIMIT 25"
                )
                vals = ", ".join(f"'{v}' ({n})" for v, n in cur.fetchall())
                if vals:
                    lines.append(f"    {col} values: {vals}")

        cur.execute("SELECT count(*), min(date_applied), max(date_applied) FROM applications")
        n, lo, hi = cur.fetchone()
        lines.append(f"\napplications has {n} rows, date_applied from {lo} to {hi}.")

    lines.append(
        "Relationships: gmail_events.application_id and interview_rounds.application_id "
        "-> applications.id. job_leads is standalone (leads not yet applied to)."
    )
    return "\n".join(lines)


def get_schema_text():
    now = time.time()
    if _schema_cache["text"] is None or now - _schema_cache["at"] > SCHEMA_TTL_SECONDS:
        try:
            _schema_cache["text"] = _build_schema_text()
            _schema_cache["at"] = now
        except psycopg2.Error:
            logger.exception("Schema introspection failed")
            if _schema_cache["text"] is None:
                raise
    return _schema_cache["text"]


# ---------- SQL tool ----------

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|upsert|"
    r"import|export|backup|restore|set|reset|copy)\b",
    re.IGNORECASE,
)


def _jsonable(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str) and len(v) > MAX_CELL_CHARS:
        return v[:MAX_CELL_CHARS] + "...[truncated]"
    if isinstance(v, (int, float, bool)) or v is None or isinstance(v, str):
        return v
    return str(v)


def run_sql(query):
    q = query.strip().rstrip(";")
    if ";" in q:
        return {"error": "Only one statement allowed."}
    if not re.match(r"^\s*(select|with)\b", q, re.IGNORECASE) or _FORBIDDEN.search(q):
        return {"error": "Only read-only SELECT / WITH queries are allowed."}
    try:
        with _ReadOnlyConn() as cur:
            cur.execute(q)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS + 1)
    except psycopg2.Error as e:
        return {"error": str(e).strip().splitlines()[0]}

    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    return {
        "columns": cols,
        "rows": [[_jsonable(v) for v in r] for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }


TOOLS = [
    {
        "name": "run_sql",
        "description": (
            "Run one read-only SQL query (CockroachDB / Postgres dialect) against the "
            "user's job-search database and get the rows back. Returns at most "
            f"{MAX_ROWS} rows; long text is truncated. Errors are returned as {{error}}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A single SELECT or WITH query."}},
            "required": ["query"],
        },
    }
]


# ---------- prompt ----------

SYSTEM_TEMPLATE = """You are CareerTrack, Abhineet's job-search copilot. You talk like a sharp friend who happens to have his entire application history in front of them: casual, direct, a little dry humor is fine.

Today's date: {today}

You have a run_sql tool over his job-search database. Schema (live, embedding columns omitted):
{schema}

How to behave:
- Be conversational. Greetings, small talk, follow-ups like "are you sure?" or "why?", and general career or interview advice can be answered naturally. Don't query for those unless his data actually matters to the answer.
- Anything about HIS data (counts, companies, statuses, dates, interview questions, outcomes) must come from run_sql results in this conversation. Never state a number or company from memory or assumption. If asked "are you sure?" about data, re-run a query to verify rather than just repeating yourself.
- When you mix general advice with his data, make it clear which part is from his records.
- If a query returns nothing, say so plainly. Don't paper over it.
- Filter categorical columns only with the exact values listed above. Match company/role text with ILIKE '%term%'. Resolve relative dates against today's date.
- Prefer one query with joins/aggregates/CTEs. At most 3 queries per answer. If a query errors, fix it once.
- Don't write anything before a tool call. Don't narrate ("let me check"). Just query, then answer.
- Keep answers tight. Markdown tables for multi-row data. No exclamation marks, no "Great question", no ending every reply with an offer."""


def _system_blocks():
    text = SYSTEM_TEMPLATE.format(today=date.today().isoformat(), schema=get_schema_text())
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def _clean_history(history, user_message):
    """Alternating user/assistant turns ending with the new user message.
    Earlier failed requests can leave two user turns in a row; merge them."""
    msgs = []
    for m in (history or []) + [{"role": "user", "content": user_message}]:
        content = (m.get("content") or "").strip()
        if not content or m.get("role") not in ("user", "assistant"):
            continue
        if msgs and msgs[-1]["role"] == m["role"]:
            msgs[-1]["content"] += "\n\n" + content
        else:
            msgs.append({"role": m["role"], "content": content})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


# ---------- agent loop ----------

def stream_agent(user_message, conversation_history=None):
    """Yields events: {"type": "status"|"delta"|"reset", ...}. Final text is the
    concatenation of deltas after the last reset."""
    messages = _clean_history(conversation_history, user_message)
    t0 = time.perf_counter()
    system = _system_blocks()
    logger.info("chat_schema duration_ms=%d", round((time.perf_counter() - t0) * 1000))

    for turn in range(MAX_TOOL_TURNS + 1):
        kwargs = dict(
            model=MODEL, max_tokens=2000, temperature=0.3,
            system=system, messages=messages, tools=TOOLS,
        )
        if turn == MAX_TOOL_TURNS:
            kwargs["tool_choice"] = {"type": "none"}

        t0 = time.perf_counter()
        emitted = False
        with client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "text" and event.text:
                    emitted = True
                    yield {"type": "delta", "text": event.text}
            response = stream.get_final_message()
        u = response.usage
        logger.info(
            "chat_llm turn=%d duration_ms=%d stop=%s in=%s cached=%s out=%s",
            turn, round((time.perf_counter() - t0) * 1000), response.stop_reason,
            u.input_tokens, getattr(u, "cache_read_input_tokens", None), u.output_tokens,
        )

        if response.stop_reason != "tool_use":
            return

        if emitted:
            # Model talked before calling a tool; drop that preamble.
            yield {"type": "reset"}
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            yield {"type": "status", "text": "Checking your data"}
            t1 = time.perf_counter()
            result = run_sql(block.input.get("query", ""))
            logger.info(
                "chat_sql duration_ms=%d rows=%s error=%s",
                round((time.perf_counter() - t1) * 1000),
                result.get("row_count"), result.get("error"),
            )
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
                "is_error": "error" in result,
            })
        messages.append({"role": "user", "content": results})
        yield {"type": "status", "text": "Writing it up"}


def ask_claude(user_message, conversation_history=None):
    """Non-streaming wrapper (used by the plain /chat endpoint)."""
    text = ""
    for ev in stream_agent(user_message, conversation_history):
        if ev["type"] == "delta":
            text += ev["text"]
        elif ev["type"] == "reset":
            text = ""
    return text.strip() or "I couldn't produce an answer for that. Try rephrasing."
