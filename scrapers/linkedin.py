import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENTS, REQUEST_DELAY, SEARCH_KEYWORDS, LOCATIONS, EXPERIENCE_MODIFIERS


def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def _build_search_url(keyword, location, start=0):
    base = "https://www.linkedin.com/jobs/search/"
    params = {
        "keywords": keyword,
        "location": location,
        "f_E": "2",  # entry level
        "f_TPR": "r2592000",  # past month
        "position": 1,
        "pageNum": 0,
        "start": start,
    }
    query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
    return f"{base}?{query}"


def _parse_job_card(card):
    try:
        title_el = card.find("h3", class_="base-search-card__title")
        company_el = card.find("h4", class_="base-search-card__subtitle")
        location_el = card.find("span", class_="job-search-card__location")
        link_el = card.find("a", class_="base-card__full-link")
        time_el = card.find("time")

        if not title_el or not link_el:
            return None

        title = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else "Unknown"
        location = location_el.get_text(strip=True) if location_el else "Unknown"
        link = link_el.get("href", "").split("?")[0]
        posted = time_el.get("datetime", "") if time_el else ""

        return {
            "company": company,
            "role": title,
            "location": location,
            "source": "LinkedIn",
            "apply_link": link,
            "salary": "",
            "posted_date": posted,
            "description_snippet": "",
        }
    except Exception:
        return None


def scrape_linkedin():
    print("  [LinkedIn] Starting scrape...")
    jobs = []
    seen_links = set()

    search_combos = []
    for role_type, keywords in SEARCH_KEYWORDS.items():
        for keyword in keywords[:3]:
            for country, cities in LOCATIONS.items():
                country_name = cities[-1]
                for modifier in EXPERIENCE_MODIFIERS[:3]:
                    search_combos.append(f"{modifier} {keyword}")
                    search_combos.append(keyword)

    search_combos = list(set(search_combos))

    for country, cities in LOCATIONS.items():
        country_name = cities[-1]
        for keyword in search_combos[:15]:
            url = _build_search_url(keyword, country_name)
            try:
                time.sleep(random.uniform(*REQUEST_DELAY))
                resp = requests.get(url, headers=_get_headers(), timeout=15)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="base-card")

                for card in cards:
                    job = _parse_job_card(card)
                    if job and job["apply_link"] not in seen_links:
                        seen_links.add(job["apply_link"])
                        jobs.append(job)

                print(f"  [LinkedIn] {country_name} / '{keyword}' -> {len(cards)} listings")
            except requests.RequestException as e:
                print(f"  [LinkedIn] Error for '{keyword}' in {country_name}: {e}")
                continue

    print(f"  [LinkedIn] Total: {len(jobs)} unique jobs found")
    return jobs
