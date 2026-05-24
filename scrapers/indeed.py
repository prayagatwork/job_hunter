import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USER_AGENTS, REQUEST_DELAY, SEARCH_KEYWORDS, EXPERIENCE_MODIFIERS

INDEED_DOMAINS = {
    "Netherlands": "https://nl.indeed.com",
    "Germany": "https://de.indeed.com",
}

INDEED_CITIES = {
    "Netherlands": ["Amsterdam", "Rotterdam", "Eindhoven", "Utrecht"],
    "Germany": ["Berlin", "Munich", "Hamburg", "Frankfurt"],
}


def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


def _build_indeed_url(domain, keyword, city):
    return f"{domain}/jobs?q={quote_plus(keyword)}&l={quote_plus(city)}&sort=date"


def _parse_indeed_page(soup, domain, country):
    jobs = []
    cards = soup.find_all("div", class_="job_seen_beacon")
    if not cards:
        cards = soup.find_all("div", attrs={"class": lambda c: c and "jobsearch-ResultsList" in c})
        if cards:
            cards = cards[0].find_all("div", recursive=False)

    for card in cards:
        try:
            title_el = card.find("h2")
            if not title_el:
                title_el = card.find("a", attrs={"data-jk": True})
            if not title_el:
                continue

            title_link = title_el.find("a") if title_el.name != "a" else title_el
            title = title_el.get_text(strip=True)

            link = ""
            if title_link and title_link.get("href"):
                href = title_link["href"]
                if href.startswith("/"):
                    link = f"{domain}{href}"
                else:
                    link = href
            elif title_link and title_link.get("data-jk"):
                link = f"{domain}/viewjob?jk={title_link['data-jk']}"

            company_el = card.find("span", attrs={"data-testid": "company-name"})
            if not company_el:
                company_el = card.find("span", class_="companyName")
            if not company_el:
                company_el = card.find("span", class_="company")
            company = company_el.get_text(strip=True) if company_el else "Unknown"

            location_el = card.find("div", attrs={"data-testid": "text-location"})
            if not location_el:
                location_el = card.find("div", class_="companyLocation")
            location = location_el.get_text(strip=True) if location_el else country

            salary_el = card.find("div", class_="salary-snippet-container")
            if not salary_el:
                salary_el = card.find("div", attrs={"class": lambda c: c and "salary" in c.lower()}) if card else None
            salary = salary_el.get_text(strip=True) if salary_el else ""

            snippet_el = card.find("div", class_="job-snippet")
            if not snippet_el:
                snippet_el = card.find("table", class_="jobCardShelfContainer")
            snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""

            date_el = card.find("span", class_="date")
            posted = date_el.get_text(strip=True) if date_el else ""

            if title and link:
                jobs.append({
                    "company": company,
                    "role": title,
                    "location": f"{location}, {country}",
                    "source": f"Indeed ({country})",
                    "apply_link": link,
                    "salary": salary,
                    "posted_date": posted,
                    "description_snippet": snippet,
                })
        except Exception:
            continue

    return jobs


def scrape_indeed():
    print("  [Indeed] Starting scrape...")
    all_jobs = []
    seen_links = set()

    search_terms = []
    for role_type, keywords in SEARCH_KEYWORDS.items():
        for keyword in keywords[:2]:
            for modifier in EXPERIENCE_MODIFIERS[:2]:
                search_terms.append(f"{modifier} {keyword}")
            search_terms.append(keyword)
    search_terms.append("software engineer visa sponsorship")
    search_terms.append("AI engineer visa sponsorship")
    search_terms.append("junior developer visa sponsorship")
    search_terms = list(set(search_terms))

    for country, domain in INDEED_DOMAINS.items():
        cities = INDEED_CITIES[country]
        for city in cities[:3]:
            for keyword in search_terms[:10]:
                url = _build_indeed_url(domain, keyword, city)
                try:
                    time.sleep(random.uniform(*REQUEST_DELAY))
                    resp = requests.get(url, headers=_get_headers(), timeout=15, allow_redirects=True)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    jobs = _parse_indeed_page(soup, domain, country)

                    for job in jobs:
                        if job["apply_link"] not in seen_links:
                            seen_links.add(job["apply_link"])
                            all_jobs.append(job)

                    print(f"  [Indeed] {country}/{city} / '{keyword}' -> {len(jobs)} listings")
                except requests.RequestException as e:
                    print(f"  [Indeed] Error: {e}")
                    continue

    print(f"  [Indeed] Total: {len(all_jobs)} unique jobs found")
    return all_jobs
