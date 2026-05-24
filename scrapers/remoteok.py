import time
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENTS, SEARCH_KEYWORDS

API_URL = "https://remoteok.com/api"

NL_DE_KEYWORDS = [
    "amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague",
    "netherlands", "holland", "dutch",
    "berlin", "munich", "hamburg", "frankfurt", "cologne",
    "germany", "deutschland", "german",
    "europe", "eu", "emea",
]


def _is_relevant_role(title, tags=None):
    title_lower = title.lower()
    all_keywords = []
    for keywords in SEARCH_KEYWORDS.values():
        all_keywords.extend(kw.lower() for kw in keywords)
    extra = [
        "developer", "engineer", "analyst", "scientist",
        "data", "ai", "ml", "machine learning", "python",
        "java", "full stack", "backend", "frontend",
        "automation", "devops",
    ]
    all_keywords.extend(extra)

    if any(kw in title_lower for kw in all_keywords):
        return True
    if tags:
        tags_str = " ".join(t.lower() for t in tags)
        if any(kw in tags_str for kw in all_keywords):
            return True
    return False


def _is_entry_level(title, description=""):
    text = f"{title} {description}".lower()
    senior_only = ["senior", "lead", "principal", "staff", "director", "head of", "vp ", "architect"]
    entry_signals = ["junior", "entry", "graduate", "associate", "trainee", "jr"]
    has_senior = any(s in text for s in senior_only)
    has_entry = any(s in text for s in entry_signals)
    if has_entry:
        return True
    if has_senior:
        return False
    return True


def scrape_remoteok():
    print("  [RemoteOK] Starting API scrape...")
    all_jobs = []

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "application/json",
    }

    try:
        resp = requests.get(API_URL, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"  [RemoteOK] API returned {resp.status_code}")
            return []

        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and "legal" in str(data[0]).lower():
            data = data[1:]

        for job in data:
            if not isinstance(job, dict):
                continue

            title = job.get("position", "")
            company = job.get("company", "")
            tags = job.get("tags", [])
            description = job.get("description", "")
            location = job.get("location", "")
            salary_min = job.get("salary_min", "")
            salary_max = job.get("salary_max", "")
            url = job.get("url", "")
            date = job.get("date", "")

            if not title:
                continue

            location_text = f"{location} {description[:500]}".lower()
            is_nl_de = any(kw in location_text for kw in NL_DE_KEYWORDS)

            if not is_nl_de:
                continue

            if not _is_relevant_role(title, tags):
                continue

            if not _is_entry_level(title, description[:500]):
                continue

            salary = ""
            if salary_min and salary_max:
                salary = f"${salary_min:,} - ${salary_max:,}"
            elif salary_min:
                salary = f"${salary_min:,}+"

            country = "Europe (Remote)"
            loc_lower = location.lower()
            if any(kw in loc_lower for kw in ["netherlands", "amsterdam", "holland", "dutch"]):
                country = "Netherlands"
            elif any(kw in loc_lower for kw in ["germany", "berlin", "munich", "german"]):
                country = "Germany"

            all_jobs.append({
                "company": company,
                "role": title,
                "location": f"{location}, {country}" if location else country,
                "source": "RemoteOK",
                "apply_link": url if url.startswith("http") else f"https://remoteok.com{url}",
                "salary": salary,
                "posted_date": date[:10] if date else "",
                "description_snippet": description[:300] if description else "",
            })

        print(f"  [RemoteOK] Processed {len(data)} listings, {len(all_jobs)} matching NL/DE")

    except requests.RequestException as e:
        print(f"  [RemoteOK] Error: {e}")
    except ValueError as e:
        print(f"  [RemoteOK] JSON parse error: {e}")

    print(f"  [RemoteOK] Total: {len(all_jobs)} jobs found")
    return all_jobs
