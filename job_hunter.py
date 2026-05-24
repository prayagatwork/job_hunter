#!/usr/bin/env python3
"""
Job Hunter — Europe Entry-Level Job Scraper & Tracker
Scrapes 6 sources for entry-level SDE, AI/ML, and Analyst roles
in Netherlands and Germany.

Sources: LinkedIn, Indeed, arbeitnow, Relocate.me, BerlinStartupJobs, RemoteOK

Usage:
    python job_hunter.py [--source linkedin|indeed|arbeitnow|relocateme|berlinstartup|remoteok|all]
"""

import argparse
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.linkedin import scrape_linkedin
from scrapers.indeed import scrape_indeed
from scrapers.arbeitnow import scrape_arbeitnow
from scrapers.relocateme import scrape_relocateme
from scrapers.berlinstartupjobs import scrape_berlinstartupjobs
from scrapers.remoteok import scrape_remoteok
from deduplicator import deduplicate, enrich_jobs
from export import export_to_excel


BANNER = """
╔══════════════════════════════════════════════════════╗
║           JOB HUNTER — Europe Edition                ║
║     Entry-Level SDE / AI / Analyst Scraper           ║
║     Target: Netherlands & Germany                    ║
║                                                      ║
║  Sources: LinkedIn | Indeed | arbeitnow              ║
║           Relocate.me | BerlinStartupJobs | RemoteOK ║
╚══════════════════════════════════════════════════════════╝
"""

SCRAPERS = [
    ("linkedin", "LinkedIn", scrape_linkedin),
    ("indeed", "Indeed (NL + DE)", scrape_indeed),
    ("arbeitnow", "arbeitnow API", scrape_arbeitnow),
    ("relocateme", "Relocate.me", scrape_relocateme),
    ("berlinstartup", "BerlinStartupJobs", scrape_berlinstartupjobs),
    ("remoteok", "RemoteOK API", scrape_remoteok),
]


def main():
    parser = argparse.ArgumentParser(description="Scrape entry-level jobs in Europe")
    source_choices = [s[0] for s in SCRAPERS] + ["all"]
    parser.add_argument(
        "--source",
        choices=source_choices,
        default="all",
        help="Which source to scrape (default: all)",
    )
    args = parser.parse_args()

    print(BANNER)
    start_time = time.time()
    all_jobs = []

    total = len(SCRAPERS)
    for idx, (key, label, scraper_fn) in enumerate(SCRAPERS, 1):
        if args.source not in (key, "all"):
            continue

        print(f"\n[{idx}/{total}] Scraping {label}...")
        try:
            jobs = scraper_fn()
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  {label} scraping failed: {e}")

    if not all_jobs:
        print("\nNo jobs found. This might be due to rate limiting.")
        print("Try running with a single source: python job_hunter.py --source arbeitnow")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"[+] Raw total: {len(all_jobs)} jobs collected from all sources")

    print("[+] Deduplicating...")
    unique_jobs = deduplicate(all_jobs)
    print(f"    {len(unique_jobs)} unique jobs after dedup")

    print("[+] Enriching (visa detection + match scoring)...")
    enriched_jobs = enrich_jobs(unique_jobs)

    visa_yes = sum(1 for j in enriched_jobs if j.get("visa_sponsorship") == "Yes")
    high_match = sum(1 for j in enriched_jobs if j.get("match_score", 0) >= 6)
    print(f"    {visa_yes} jobs with confirmed visa sponsorship")
    print(f"    {high_match} high-match jobs (score >= 6)")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    filepath = export_to_excel(enriched_jobs, output_dir)

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"  Done in {elapsed:.1f}s")
    print(f"  {len(enriched_jobs)} jobs exported to Excel")
    print(f"  File: {filepath}")
    print(f"{'='*50}")

    print(f"\n  Source breakdown:")
    source_counts = {}
    for j in enriched_jobs:
        src = j.get("source", "Unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"    {src}: {count} jobs")

    print(f"\nNext steps:")
    print(f"  1. Open the Excel file")
    print(f"  2. Sort by 'Match Score' (highest first)")
    print(f"  3. Focus on green rows (Visa Sponsorship: Yes)")
    print(f"  4. Click 'Apply Here' links to apply")
    print(f"  5. Update 'Status' column as you apply")
    print(f"\nRe-run tomorrow to find new listings!")


if __name__ == "__main__":
    main()
