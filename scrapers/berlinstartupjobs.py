import time
import random
import requests
from bs4 import BeautifulSoup
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENTS, REQUEST_DELAY

BASE_URL = "https://berlinstartupjobs.com"

CATEGORY_URLS = [
    "/engineering/",
    "/skill-areas/python/",
    "/skill-areas/java/",
    "/skill-areas/javascript/",
    "/skill-areas/machine-learning/",
    "/skill-areas/data-science/",
    "/skill-areas/ai/",
    "/skill-areas/node-js/",
    "/skill-areas/react/",
    "/skill-areas/sql/",
    "/skill-areas/docker/",
    "/skill-areas/aws/",
]


def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _is_entry_friendly(title):
    title_lower = title.lower()
    senior_only = [
        "senior", "lead", "principal", "staff", "director",
        "head of", "vp ", "vice president", "cto", "cio",
        "manager", "architect",
    ]
    entry_signals = [
        "junior", "entry", "graduate", "working student",
        "trainee", "intern", "associate", "jr",
    ]
    has_senior = any(s in title_lower for s in senior_only)
    has_entry = any(s in title_lower for s in entry_signals)
    if has_entry:
        return True
    if has_senior:
        return False
    return True


def scrape_berlinstartupjobs():
    print("  [BerlinStartupJobs] Starting scrape...")
    all_jobs = []
    seen = set()

    for path in CATEGORY_URLS:
        url = f"{BASE_URL}{path}"
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))
            resp = requests.get(url, headers=_get_headers(), timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            job_entries = soup.find_all(["li", "div", "article"], class_=lambda c: c and ("bsj-jb" in c or "job" in c.lower()))
            if not job_entries:
                job_entries = soup.find_all("div", class_=lambda c: c and "listing" in c.lower()) if soup else []

            links_found = set()
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href", "")
                if BASE_URL in href and "/jobs/" not in path and href != url and "/engineering/" not in href and "/skill-areas/" not in href:
                    if any(seg for seg in href.rstrip("/").split("/") if len(seg) > 5):
                        links_found.add(href)

            all_links = soup.find_all("a", href=True)
            for a_tag in all_links:
                href = a_tag.get("href", "")
                title = a_tag.get_text(strip=True)

                if not title or len(title) < 5 or len(title) > 120:
                    continue
                if href in seen:
                    continue
                if not href.startswith("http"):
                    continue
                if BASE_URL not in href:
                    continue
                skip_paths = ["/engineering/", "/skill-areas/", "/page/", "/category/",
                              "/tag/", "/about", "/contact", "/privacy", "/terms",
                              "/login", "/register", "/pricing"]
                if any(sp in href for sp in skip_paths):
                    continue
                if href.rstrip("/") == BASE_URL:
                    continue

                parent = a_tag.find_parent(["li", "div", "article"])
                if not parent:
                    continue

                parent_text = parent.get_text(" ", strip=True)

                company = ""
                spans = parent.find_all(["span", "h4", "h3", "h2", "strong", "em", "p"])
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if span_text and span_text != title and len(span_text) > 2 and len(span_text) < 50:
                        if span_text.lower() not in title.lower():
                            company = span_text
                            break

                if not _is_entry_friendly(title):
                    continue

                seen.add(href)
                all_jobs.append({
                    "company": company if company else "Berlin Startup",
                    "role": title,
                    "location": "Berlin, Germany",
                    "source": "BerlinStartupJobs",
                    "apply_link": href,
                    "salary": "",
                    "posted_date": "",
                    "description_snippet": parent_text[:200] if parent_text else "",
                })

            category = path.split("/")[-2] if path.endswith("/") else path.split("/")[-1]
            print(f"  [BerlinStartupJobs] /{category}/ -> {len(job_entries)} entries")

        except requests.RequestException as e:
            print(f"  [BerlinStartupJobs] Error: {e}")
            continue

    print(f"  [BerlinStartupJobs] Total: {len(all_jobs)} entry-friendly jobs found")
    return all_jobs
