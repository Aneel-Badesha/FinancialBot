import logging
import time

import requests
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

API_URL = "https://api.lever.co/v0/postings/wealthsimple"
PAGE_SIZE = 100

CANADIAN_LOCATIONS = [
    "canada", "toronto", "montreal", "vancouver", "calgary",
    "ottawa", "remote", "waterloo", "ontario", "quebec",
]

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_wealthsimple() -> list[dict]:
    jobs = []
    offset = 0

    while True:
        params = {"mode": "json", "limit": PAGE_SIZE, "offset": offset}
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        postings = resp.json()

        if not postings:
            break

        for p in postings:
            title = p.get("text", "")
            if not is_target_role(title):
                continue

            location_text = p.get("categories", {}).get("location", "")
            if not _is_canada(location_text):
                continue

            job_id = p.get("id", "")
            jobs.append({
                "id": f"wealthsimple-{job_id}",
                "company": "Wealthsimple",
                "title": title,
                "location": location_text,
                "link": p.get("hostedUrl", f"https://jobs.lever.co/wealthsimple/{job_id}"),
                "posted": "",
            })

        if len(postings) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.5)

    return jobs


def _is_canada(location_text: str) -> bool:
    t = location_text.lower()
    return any(term in t for term in CANADIAN_LOCATIONS)
