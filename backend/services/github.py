import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
HEADERS = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}

def get_user_repos(username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()

def get_repo_languages(username, repo_name):
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    res = requests.get(url, headers=HEADERS)
    return res.json() if res.ok else {}

def get_commit_activity(username, repo_name):
    url = f"https://api.github.com/repos/{username}/{repo_name}/stats/commit_activity"
    res = requests.get(url, headers=HEADERS)
    data = res.json()
    print(f"{repo_name}: status={res.status_code}, data_type={type(data)}, len={len(data) if isinstance(data, list) else 'n/a'}")
    if res.status_code == 202:
        return None
    if not res.ok:
        return None
    if not data:
        return None
    total_commits = sum(week["total"] for week in data)
    active_weeks = sum(1 for week in data if week["total"] > 0)
    return {"total_commits_last_year": total_commits, "active_weeks": active_weeks}

def build_repo_summary(username):
    repos = get_user_repos(username)
    summary = []
    for r in repos:
        if r["fork"]:
            continue
        langs = get_repo_languages(username, r["name"])
        activity = get_commit_activity(username, r["name"])
        print(f"{r['name']}: activity={activity}")
        summary.append({
            "name": r["name"],
            "description": r["description"],
            "stars": r["stargazers_count"],
            "languages": list(langs.keys()),
            "updated_at": r["updated_at"],
            "url": r["html_url"],
            "commits_last_year": activity["total_commits_last_year"] if activity else None,
            "active_weeks": activity["active_weeks"] if activity else None,
        })
    return summary

def get_authenticated_username():
    res = requests.get("https://api.github.com/user", headers=HEADERS)
    res.raise_for_status()
    return res.json()["login"]