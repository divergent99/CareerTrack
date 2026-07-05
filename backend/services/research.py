import os
import re
import json
import anthropic
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def _search(query, max_results=4):
    results = tavily.search(query=query, search_depth="basic", max_results=max_results, include_answer=False)
    return results.get("results", [])

def research_company(company_name):
    """Returns structured company info: rating, website, summary, recent_news."""

    overview_results = _search(f"{company_name} glassdoor rating reviews official website")
    news_results = _search(f"{company_name} news 2026")

    overview_text = "\n\n".join(f"{r['title']}: {r['content'][:400]}" for r in overview_results)
    news_text = "\n\n".join(f"{r['title']}: {r['content'][:300]}" for r in news_results)

    # extract a website URL directly from search result URLs, don't rely on the LLM to guess one
    website = None
    for r in overview_results:
        url = r.get("url", "")
        if company_name.lower().replace(" ", "") in url.lower().replace("-", "").replace(".", ""):
            website = url.split("/")[0] + "//" + url.split("/")[2] if "//" in url else url
            break

    prompt = f"""Extract structured info about {company_name} from this research. 
Return ONLY valid JSON, no markdown fences, no preamble.

Overview research:
{overview_text}

Recent news research:
{news_text}

Return this exact JSON shape:
{{
  "rating": "X.X/5 (Y reviews)" or null if not found,
  "summary": "2-3 sentence plain-language summary of what the company does and employee sentiment",
  "recent_move": "1-2 sentence note on a recent, specific development if one was found, else null"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    start, end = raw.find("{"), raw.rfind("}")
    parsed = json.loads(raw[start:end+1]) if start != -1 else {}

    return {
        "rating": parsed.get("rating"),
        "summary": parsed.get("summary", "No summary available."),
        "recent_move": parsed.get("recent_move"),
        "website": website,
    }