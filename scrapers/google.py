import logging
import time

import requests

logger = logging.getLogger(__name__)

# Google has a public jobs JSON API
API_URL = "https://careers.google.com/api/v3/search/"
PAGE_SIZE = 20

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_google() -> list[dict]:
    jobs = []
    page = 1

    while True:
        params = {
            "q": "",
            "location": "Canada",
            "page": page,
            "page_size": PAGE_SIZE,
            "sort_by": "date",
        }
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            break
        data = resp.json()

        postings = data.get("jobs", [])
        if not postings:
            break

        for p in postings:
            title = p.get("title", "")
            if not _is_entry_level(title):
                continue

            job_id = p.get("id", "")
            locations = p.get("locations", [{}])
            location = locations[0].get("display", "Canada") if locations else "Canada"

            jobs.append({
                "id": f"google-{job_id}",
                "company": "Google",
                "title": title,
                "location": location,
                "link": f"https://careers.google.com/jobs/results/{job_id}",
                "posted": p.get("date", ""),
            })

        total = data.get("count", 0)
        if page * PAGE_SIZE >= total or len(postings) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.5)

    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
