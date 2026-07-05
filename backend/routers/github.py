from fastapi import APIRouter
from pydantic import BaseModel
import anthropic
import os
import json
from services.github import build_repo_summary, get_authenticated_username

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class GithubAnalyzeRequest(BaseModel):
    target_roles: str = "GenAI Engineer, LLM Engineer, Agentic AI, RAG systems"


@router.post("/github/analyze")
def analyze_github(req: GithubAnalyzeRequest):
    username = get_authenticated_username()
    repos = build_repo_summary(username)

    repos_text = "\n".join(
        f"- {r['name']}: {r['description'] or 'no description'} "
        f"| Languages: {', '.join(r['languages']) or 'none listed'} "
        f"| Stars: {r['stars']} | Last updated: {r['updated_at'][:10]} "
        f"| Commits last year: {r['commits_last_year'] if r['commits_last_year'] is not None else 'unknown'} "
        f"| Active weeks: {r['active_weeks'] if r['active_weeks'] is not None else 'unknown'}"
        for r in repos
    )

    prompt = f"""Analyze this person's GitHub repos and suggest which to feature on a 
resume for these target roles: {req.target_roles}.

Return ONLY valid JSON, no markdown fences, no preamble.

REPOS:
{repos_text}

Return this exact JSON shape:
{{
  "overall_summary": "2-3 sentences on what the GitHub profile shows overall",
  "top_projects": [
    {{"name": "repo name", "relevance": "high/medium/low", "reason": "1 sentence why it fits the target roles", "resume_bullet_suggestion": "a ready-to-use resume bullet point for this project"}}
  ],
  "tech_stack_summary": {{"language_or_tool": count_of_repos_using_it}},
  "gaps": ["1-3 things missing from the GitHub profile that these target roles typically expect"],
  "projects_to_deprioritize": ["names of repos that are stale/irrelevant and shouldn't be on a resume"]
}}

Use commit activity and last-updated date to judge whether a repo is actively maintained 
or stale, factor that into relevance and the deprioritize list. Only include repos that 
actually exist in the list above. Rank top_projects by relevance, most relevant first, max 5."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    parsed = json.loads(raw[start:end+1])
    parsed["raw_repos"] = repos
    return parsed