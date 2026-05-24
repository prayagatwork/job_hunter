import time
import random
import requests
from bs4 import BeautifulSoup
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENTS, REQUEST_DELAY, SEARCH_KEYWORDS, EXPERIENCE_MODIFIERS

BASE_URL = "https://relocate.me"

SEARCH_URLS = [
    "/search?query=software+engineer&experience=junior",
    "/search?query=software+engineer&experience=mid",
    "/search?query=data+scientist&experience=junior",
    "/search?query=AI+engineer",
    "/search?query=machine+learning",
    "/search?query=backend+engineer",
    "/search?query=full+stack+developer",
    "/search?query=data+analyst",
    "/search?query=python+developer",
    "/search?query=java+developer",
    "/search?query=junior+developer",
]

NL_DE_KEYWORDS = [
    "amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague",
    "netherlands", "holland",
    "berlin", "munich", "hamburg", "frankfurt", "cologne", "düsseldorf",
    "germany", "deutschland",
]


def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _is_nl_de(location):
    loc_lower = location.lower()
    return any(kw in loc_lower for kw in NL_DE_KEYWORDS)


def _get_country(location):
    loc_lower = location.lower()
    nl_kw = ["amsterdam", "rotterdam", "eindhoven", "utrecht", "the hague", "netherlands", "holland"]
    if any(kw in loc_lower for kw in nl_kw):
        return "Netherlands"
    return "Germany"


def scrape_relocateme():
    print("  [Relocate.me] Starting scrape...")
    all_jobs = []
    seen = set()

    for path in SEARCH_URLS:
        url = f"{BASE_URL}{path}"
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))
            resp = requests.get(url, headers=_get_headers(), timeout=15)
            if resp.status_code != 200:
                print(f"  [Relocate.me] {path} returned {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            job_links = soup.find_all("a", href=True)
            cards = []
            for link in job_links:
                href = link.get("href", "")
                if href.startswith("/") and href.count("/") >= 4 and "search" not in href and "page" not in href:
                    parent = link.find_parent(["div", "article", "li"])
                    if parent:
                        cards.append((link, parent, href))

            for link_el, card, href in cards:
                title = link_el.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                full_text = card.get_text(" ", strip=True)

                company = ""
                location = ""

                parts = full_text.split(title)
                if len(parts) > 1:
                    after = parts[1].strip()
                    text_parts = [p.strip() for p in after.split("|")]
                    if not text_parts:
                        text_parts = [p.strip() for p in after.split("·")]
                    if not text_parts:
                        text_parts = [p.strip() for p in after.split("—")]

                    for part in text_parts:
                        if any(kw in part.lower() for kw in NL_DE_KEYWORDS + ["london", "tokyo", "remote"]):
                            location = part
                        elif not company and part and len(part) > 1:
                            company = part

                spans = card.find_all("span")
                for span in spans:
                    span_text = span.get_text(strip=True)
                    if any(kw in span_text.lower() for kw in NL_DE_KEYWORDS):
                        location = span_text
                    elif not company and span_text and span_text != title and len(span_text) > 2:
                        company = span_text

                if not _is_nl_de(location) and not _is_nl_de(full_text):
                    continue

                if not location:
                    for kw in NL_DE_KEYWORDS:
                        if kw in full_text.lower():
                            location = kw.title()
                            break

                job_url = f"{BASE_URL}{href}" if href.startswith("/") else href
                key = f"{title}|{company}"
                if key in seen:
                    continue
                seen.add(key)

                all_jobs.append({
                    "company": company if company else "See listing",
                    "role": title,
                    "location": f"{location}, {_get_country(location)}" if location else "Netherlands/Germany",
                    "source": "Relocate.me",
                    "apply_link": job_url,
                    "salary": "",
                    "posted_date": "",
                    "description_snippet": "",
                    "visa_sponsorship_flag": True,
                })

            print(f"  [Relocate.me] '{path.split('=')[1].split('&')[0]}' -> found listings")

        except requests.RequestException as e:
            print(f"  [Relocate.me] Error: {e}")
            continue

    print(f"  [Relocate.me] Total: {len(all_jobs)} NL/DE jobs found (all include relocation support)")
    return all_jobs
