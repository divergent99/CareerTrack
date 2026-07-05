# 🧭 CareerTrack

**An agentic memory system for your job hunt.** CareerTrack ingests your Gmail, classifies every application-related email with Claude, stores it all in CockroachDB, and gives you a chat agent, dashboard, resume analyzer, GitHub project ranker, and interview roadmap generator, all grounded in your *actual* history instead of generic advice.

Built for the **CockroachDB × AWS Hackathon — Build with Agentic Memory**.

<p align="center">
  <img src="https://img.shields.io/badge/CockroachDB-6933FF?style=for-the-badge&logo=cockroachlabs&logoColor=white" alt="CockroachDB"/>
  <img src="https://img.shields.io/badge/AWS%20Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS Bedrock"/>
  <img src="https://img.shields.io/badge/Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"/>
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite"/>
  <img src="https://img.shields.io/badge/TailwindCSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Gmail%20API-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Gmail API"/>
  <img src="https://img.shields.io/badge/Tavily-000000?style=for-the-badge&logo=data:image/svg+xml;base64,&logoColor=white" alt="Tavily"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"/>
</p>

---

## Table of Contents

- [What it does](#what-it-does)
- [Why it exists](#why-it-exists)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [How CockroachDB is used](#how-cockroachdb-is-used)
- [How AWS is used](#how-aws-is-used)
- [Project structure](#project-structure)
- [Features, in depth](#features-in-depth)
- [Setup](#setup)
- [Known limitations](#known-limitations)
- [License](#license)

---

## What it does

CareerTrack turns your inbox into a queryable, reasoning-capable memory of your job search:

1. **Ingests** every job-related email from Gmail, applications, interview invites, rejections, offers, recruiter check-ins, even LinkedIn's notoriously ambiguous "Your update from X" template.
2. **Classifies** each email with Claude, extracting company, role, and pipeline stage, while filtering out loan spam, newsletters, and job-board noise that just *looks* like job content.
3. **Stores** everything in CockroachDB, deduplicated by thread and normalized company name, so one company's five emails collapse into one application timeline instead of five duplicate rows.
4. **Reasons over it** through a chat agent (Claude + CockroachDB's MCP server), a dashboard, a roadmap generator that vector-searches your own past interview questions, a resume critic that cross-references your actual application outcomes, and a GitHub analyzer that ranks your public repos by resume relevance.

None of this is synthetic demo data. It's one person's real, messy, ongoing job hunt.

## Why it exists

Most job-tracking tools are spreadsheets with extra steps. They store *that* you applied somewhere, not *what happened*, what you were asked, how you did, what the company is actually like, or whether a pattern exists in why you keep getting rejected at the same stage. CareerTrack is built around the idea that an agent with real memory across applications is more useful than a static tracker, because it can notice things you can't: "you've been asked about RAG evaluation three times and rated yourself low each time," or "your last two rejections both came right after the take-home."

## Architecture

```
┌─────────────┐        ┌──────────────────┐      ┌─────────────────────┐
│  Gmail API   │─────> │  Ingestion       │─────>│                     │
│  (read-only) │       │  (Python)        │      │                     │
└─────────────┘        │  - fetch emails  │      │                     │
                       │  - classify via  │      │    CockroachDB      │
                       │    Claude        │      │    (Cloud, Basic)   │
                       │  - dedupe by     │─────>│                     │
                       │    thread/company│      │  applications       │
                       └──────────────────┘      │  gmail_events       │
                                                 │  interview_rounds   │
┌─────────────┐        ┌──────────────────┐      │  job_leads          │
│   React UI  │<────>  │  FastAPI backend │<────>│  chat_sessions      │
│  (Vite +    │        │  - chat (MCP)    │      │  chat_messages      │
│  Tailwind)  │        │  - fast-path SQL │      │  (vector-indexed:   │
└─────────────┘        │  - roadmap gen   │      │   jd_embedding,     │
                       │  - resume review │      │   questions_embed.) │
                       │  - github rank   │      └─────────────────────┘
                       └────────┬─────────┘
                                │
                  ┌─────────────┼─────────────┐
                  ▼             ▼             ▼
          ┌────────────────┐ ┌─────────┐ ┌───────────────┐
          │ Claude API     │ │ Tavily  │ │ AWS Bedrock   │
          │ (chat, MCP,    │ │ (company│ │ (Titan Text   │
          │ classification,│ │research)│ │  Embeddings   │
          │ resume/GitHub  │ └─────────┘ │  V2, 1024-dim)│
          │ analysis)      │             └───────────────┘
          └────────────────┘
```

**Two distinct reasoning paths, by design:**

- **Fast path** — predictable questions ("how many applications do I have," "what's my rejection rate") hit direct SQL endpoints. No LLM round trip, no agent loop, sub-second response.
- **Agent path** — genuinely open-ended questions ("why do I keep getting rejected," "what's the story with Company X") go through Claude with the CockroachDB MCP connector, which lets Claude query the cluster directly rather than Claude guessing from a static context dump.

## Tech stack

| Layer | Technology | Role |
|---|---|---|
| Database | **CockroachDB Cloud** | Primary store, distributed vector indexing on interview questions & JDs |
| Agent connectivity | **CockroachDB MCP Server** | Lets Claude query the live cluster directly for open-ended questions |
| LLM | **Claude Sonnet 4.6** (Anthropic API) | Email classification, chat agent, roadmap generation, resume critique, GitHub ranking |
| Embeddings | **AWS Bedrock — Titan Text Embeddings V2** | 1024-dim vectors for interview questions & job descriptions |
| External research | **Tavily API** | Company overview, Glassdoor-style sentiment, recent news, cached in CockroachDB |
| Email ingestion | **Gmail API** (OAuth, read-only) | Source of every application event |
| Backend | **FastAPI** + **psycopg2** | REST API, MCP orchestration, direct SQL fast-paths |
| Frontend | **React** + **Vite** + **Tailwind CSS v4** | Chat UI, dashboard, applications manager, roadmap & resume tools |
| Charts | **Recharts** | Funnel, status distribution, application timeline |
| Markdown | **react-markdown** + **remark-gfm** | Renders agent responses with tables, bold, headers |
| GitHub API | **REST v3** (PAT-authenticated) | Repo metadata, language breakdown, commit activity |

## How CockroachDB is used

This project uses **two** CockroachDB tools, satisfying the hackathon's core requirement with real, working features rather than checkbox integrations:

1. **Distributed Vector Indexing** — `interview_rounds.questions_embedding` and `applications.jd_embedding` are `VECTOR(1024)` columns with `CREATE VECTOR INDEX`. The Roadmap Generator embeds a target job description via Bedrock, then runs a live `ORDER BY questions_embedding <-> query_embedding LIMIT 5` similarity search against every interview question the user has ever logged, surfacing only the *relevant* ones instead of dumping the entire history into the prompt.
2. **MCP Server** (`https://cockroachlabs.cloud/mcp`) — the chat agent connects to this endpoint via Claude's `mcp_toolset` beta, giving Claude direct, live SQL access to the cluster for anything that doesn't fit a predictable query shape. No data is pre-fetched and stuffed into context; Claude decides what to query.

## How AWS is used

**AWS Bedrock** (Titan Text Embeddings V2) generates every vector stored in CockroachDB. Every interview question logged through the Applications page is embedded server-side at write time; the Roadmap Generator embeds incoming job descriptions at query time. This is the model actually doing the semantic-similarity heavy lifting that the vector index searches over, not a decorative API call.

## Project structure

```
careertrack/
├── ingestion/              # Gmail → Claude classification → CockroachDB
│   ├── fetch_gmail.py      # OAuth, search, HTML/plaintext body extraction
│   ├── classify.py         # Claude-based email classification
│   ├── db.py                # Dedup logic (thread-based + normalized company match)
│   └── dedupe_companies.py # One-shot cleanup for near-duplicate company names
│
├── backend/
│   ├── main.py              # FastAPI app, router registration
│   ├── routers/
│   │   ├── chat.py          # Sessions, messages, MCP agent endpoint
│   │   ├── stats.py         # Fast-path SQL: summary, funnel, timeline
│   │   ├── company.py       # Tavily-backed company research + status synthesis
│   │   ├── applications.py  # CRUD for applications & interview rounds
│   │   ├── roadmap.py       # Vector search + roadmap generation
│   │   ├── resume.py        # PDF parsing + resume-vs-history analysis
│   │   └── github.py        # Repo pull, commit activity, resume-relevance ranking
│   └── services/
│       ├── db.py             # Connection + chat history helpers
│       ├── mcp_client.py     # Claude + CockroachDB MCP wiring
│       ├── embeddings.py     # Bedrock Titan embedding calls
│       ├── research.py       # Tavily search + structured extraction
│       ├── resume.py         # PDF text extraction
│       └── github.py         # GitHub REST API wrapper
│
└── frontend/
    └── src/
        ├── components/       # Sidebar, ChatWindow, Message, TypingIndicator, RippleGrid
        ├── pages/            # Dashboard, Applications, Roadmap, ResumeReview, GithubAnalysis
        └── api.js            # Single source of truth for backend calls
```

## Features, in depth

**Chat agent** — session history persisted in CockroachDB, fast-path suggestion cards for common questions, full MCP agent fallback for anything open-ended, acknowledgment detection so "thanks!" doesn't trigger a data re-query.

**Dashboard** — pipeline funnel, status distribution, application velocity over time, and per-company Tavily snapshots (rating, live-linked website, recent developments), all cached in `applications.company_context` to avoid redundant external calls.

**Applications manager** — inline company/status correction (the manual "confirm" step for ambiguous emails Gmail's classifier couldn't fully resolve) and interview round logging, which is what feeds the vector index.

**Roadmap generator** — pick a tracked application or enter a new one, paste a JD (optional), get a prep plan built from real vector-searched interview history plus live company research. Explicitly flags when it's working with less context (no JD given) rather than pretending otherwise.

**Resume review** — upload a PDF, get a structured critique: strengths, gaps, per-company fit against your actual application history, and a rejection-pattern callout if your interview logs show a recurring weak spot.

**GitHub analysis** — pulls your public repos (auto-detected from the authenticated token, no manual username entry), cross-references commit activity and languages, and ranks which projects are worth resume real estate for your target roles versus which are stale academic work.

## Setup

**Prerequisites:** Python 3.11+, Node 18+, a CockroachDB Cloud cluster, an Anthropic API key, an AWS account with Bedrock (Titan Text Embeddings V2) enabled in `us-east-1`, a Tavily API key, a Google Cloud project with Gmail API enabled, and a GitHub PAT (`public_repo` scope).

```bash
# Ingestion
cd ingestion
pip install -r requirements.txt
python create_tables.py
python fetch_gmail.py            # first run opens a browser for OAuth

# Backend
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8011

# Frontend
cd ../frontend
npm install
npm run dev
```

Each of `ingestion/`, `backend/` needs its own `.env` (see `.env.example` in each folder) with `COCKROACH_URL`, `ANTHROPIC_API_KEY`, `COCKROACH_MCP_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `TAVILY_API_KEY`, and `GITHUB_TOKEN`.

## Known limitations

- Gmail classification is snippet/body-based heuristic classification via Claude, not perfect; ambiguous or highly templated emails occasionally need manual correction via the Applications page.
- The GitHub analyzer only sees public repos; private work (which may include a person's most substantial projects) isn't factored in.
- Vector search quality scales with how many interview rounds are logged; with only a handful logged, results are necessarily thin.

## License

MIT — see [LICENSE](./LICENSE).