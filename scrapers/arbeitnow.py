import time
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEARCH_KEYWORDS, EXPERIENCE_MODIFIERS

API_URL = "https://www.arbeitnow.com/api/job-board-api"

TARGET_LOCATIONS = [
    "amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague",
    "berlin", "munich", "hamburg", "frankfurt", "cologne",
    "netherlands", "germany", "deutschland",
]


def _is_target_location(location_str):
    loc_lower = location_str.lower()
    return any(city in loc_lower for city in TARGET_LOCATIONS)


def _is_entry_level(title, description=""):
    text = f"{title} {description}".lower()
    entry_signals = [
        "junior", "entry", "graduate", "early career", "associate",
        "intern", "trainee", "jr.", "jr ", "level 1", "level i",
        "0-2 years", "1-2 years", "0-3 years", "1-3 years",
        "no experience required", "fresh graduate",
    ]
    senior_signals = [
        "senior", "lead", "principal", "staff", "director",
        "manager", "head of", "vp ", "vice president", "architect",
        "10+ years", "8+ years", "7+ years", "6+ years",
    ]
    has_entry = any(s in text for s in entry_signals)
    has_senior = any(s in text for s in senior_signals)
    if has_senior and not has_entry:
        return False
    return True


def _is_relevant_role(title, tags=None):
    title_lower = title.lower()
    all_keywords = []
    for keywords in SEARCH_KEYWORDS.values():
        all_keywords.extend(kw.lower() for kw in keywords)
    extra = [
        "developer", "engineer", "analyst", "scientist",
        "data", "ai", "ml", "machine learning", "python",
        "java", "full stack", "backend", "frontend",
        "automation", "devops", "sdet", "qa engineer",
    ]
    all_keywords.extend(extra)

    if any(kw in title_lower for kw in all_keywords):
        return True

    if tags:
        tags_lower = [t.lower() for t in tags]
        if any(kw in " ".join(tags_lower) for kw in all_keywords):
            return True

    return False


def scrape_arbeitnow():
    print("  [arbeitnow] Starting API scrape...")
    all_jobs = []
    seen_slugs = set()
    page = 1
    max_pages = 20

    while page <= max_pages:
        try:
            resp = requests.get(API_URL, params={"page": page}, timeout=15)
            if resp.status_code != 200:
                print(f"  [arbeitnow] Page {page} returned {resp.status_code}, stopping")
                break

            data = resp.json()
            jobs = data.get("data", [])
            if not jobs:
                break

            for job in jobs:
                slug = job.get("slug", "")
                if slug in seen_slugs:
                    continue

                location = job.get("location", "")
                if not _is_target_location(location):
                    continue

                title = job.get("title", "")
                description = job.get("description", "")
                tags = job.get("tags", [])

                if not _is_relevant_role(title, tags):
                    continue

                if not _is_entry_level(title, description):
                    continue

                seen_slugs.add(slug)

                visa = "Not Mentioned"
                if job.get("visa_sponsorship"):
                    visa = "Yes"

                country = "Germany"
                loc_lower = location.lower()
                if any(c in loc_lower for c in ["amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague", "netherlands"]):
                    country = "Netherlands"

                all_jobs.append({
                    "company": job.get("company_name", "Unknown"),
                    "role": title,
                    "location": f"{location}, {country}" if country not in location else location,
                    "source": "arbeitnow",
                    "apply_link": job.get("url", f"https://www.arbeitnow.com/view/{slug}"),
                    "salary": "",
                    "posted_date": job.get("created_at", ""),
                    "description_snippet": description[:300] if description else "",
                    "visa_sponsorship_flag": job.get("visa_sponsorship", False),
                })

            print(f"  [arbeitnow] Page {page}: processed {len(jobs)} listings, {len(all_jobs)} matching so far")

            if not data.get("links", {}).get("next"):
                break
            page += 1
            time.sleep(1)

        except requests.RequestException as e:
            print(f"  [arbeitnow] Error on page {page}: {e}")
            break

    print(f"  [arbeitnow] Total: {len(all_jobs)} matching jobs found")
    return all_jobs
