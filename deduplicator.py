import re
from config import VISA_KEYWORDS, NEGATIVE_VISA_KEYWORDS, PROFILE_KEYWORDS


def _normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower().strip())


def _make_key(job):
    company = _normalize(job.get("company", ""))
    role = _normalize(job.get("role", ""))
    location = _normalize(job.get("location", ""))
    return f"{company}|{role}|{location}"


def deduplicate(jobs):
    seen = {}
    unique = []
    for job in jobs:
        key = _make_key(job)
        if key not in seen:
            seen[key] = True
            unique.append(job)
    return unique


def detect_visa_sponsorship(job):
    if job.get("visa_sponsorship_flag"):
        return "Yes"

    text = f"{job.get('role', '')} {job.get('description_snippet', '')} {job.get('company', '')}".lower()

    for neg in NEGATIVE_VISA_KEYWORDS:
        if neg in text:
            return "No"

    for pos in VISA_KEYWORDS:
        if pos in text:
            return "Yes"

    return "Not Mentioned"


def compute_match_score(job):
    text = f"{job.get('role', '')} {job.get('description_snippet', '')}".lower()
    score = 0
    matched = []

    for keyword in PROFILE_KEYWORDS:
        if keyword in text:
            score += 1
            matched.append(keyword)

    title_lower = job.get("role", "").lower()
    high_value = ["ai engineer", "ml engineer", "machine learning", "software engineer",
                   "data scientist", "automation", "python", "java"]
    for hv in high_value:
        if hv in title_lower:
            score += 3

    entry_level = ["junior", "entry", "graduate", "associate", "early career"]
    for el in entry_level:
        if el in title_lower:
            score += 2

    return min(score, 100)


def enrich_jobs(jobs):
    for job in jobs:
        job["visa_sponsorship"] = detect_visa_sponsorship(job)
        job["match_score"] = compute_match_score(job)
    return jobs
