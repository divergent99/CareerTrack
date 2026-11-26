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

MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-4-6")
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

SYSTEM_TEMPLATE = """You are CareerTrack's assistant. You answer questions about the user's own job search using their database.

Today's date: {today}

Database schema (live, embedding columns omitted):
{schema}

Rules for accuracy:
- Every number, company, date, status or interview detail you state must come from a run_sql result in this conversation. If you did not query it, do not state it.
- If a query returns 0 rows, say you found nothing for that. Do not fill the gap with guesses or general advice dressed up as their data.
- Filter categorical columns only with the exact values listed above. Match company/role text with ILIKE '%term%', never exact equality.
- Resolve relative dates ("last month", "this week") against today's date.
- If a query errors, fix it and retry once. Do not explore the schema, you already have it.
- Prefer a single query with joins, aggregates or CTEs. Use at most 3 queries per answer.
- If the question can't be answered from these tables, say so plainly.

Style: answer directly like a colleague stating a fact. No greetings, no "let me check", no narrating queries, no exclamation marks, no unsolicited follow-up offers. Use markdown tables for multi-row results. For pure acknowledgments (thanks, ok, cool) reply in a few words without querying."""


def _system_blocks():
    text = SYSTEM_TEMPLATE.format(today=date.today().isoformat(), schema=get_schema_text())
    # Cache the big static prefix so repeat turns are faster/cheaper.
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


# ---------- agent loop ----------

def ask_claude(user_message, conversation_history=None):
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (conversation_history or [])
        if m.get("content")
    ]
    # API requires the first message to be from the user.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": user_message})

    system = _system_blocks()

    for turn in range(MAX_TOOL_TURNS + 1):
        force_answer = turn == MAX_TOOL_TURNS
        kwargs = dict(
            model=MODEL,
            max_tokens=2000,
            temperature=0,
            system=system,
            messages=messages,
            tools=TOOLS,
        )
        if force_answer:
            kwargs["tool_choice"] = {"type": "none"}
        response = client.messages.create(**kwargs)

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return text or "I couldn't produce an answer for that. Try rephrasing."

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            t0 = time.perf_counter()
            result = run_sql(block.input.get("query", ""))
            logger.info(
                "chat_sql duration_ms=%d rows=%s error=%s",
                round((time.perf_counter() - t0) * 1000),
                result.get("row_count"),
                result.get("error"),
            )
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
                "is_error": "error" in result,
            })
        messages.append({"role": "user", "content": results})

    return "I couldn't produce an answer for that. Try rephrasing."
