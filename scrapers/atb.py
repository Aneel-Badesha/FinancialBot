import logging
import time

import requests

logger = logging.getLogger(__name__)

# ATB Financial uses Workable
API_URL = "https://apply.workable.com/api/v3/accounts/atb-financial/jobs"
BASE_URL = "https://apply.workable.com"
PAGE_SIZE = 50

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_atb() -> list[dict]:
    jobs = []
    token = None

    while True:
        payload: dict = {"limit": PAGE_SIZE}
        if token:
            payload["token"] = token

        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for job in data.get("results", []):
            title = job.get("title", "")
            if not _is_entry_level(title):
                continue

            job_id = job.get("shortcode", job.get("id", ""))
            location_obj = job.get("location", {})
            location = f"{location_obj.get('city', '')}, {location_obj.get('country', '')}".strip(", ")

            jobs.append({
                "id": f"atb-{job_id}",
                "company": "ATB Financial",
                "title": title,
                "location": location or "Alberta, Canada",
                "link": f"https://apply.workable.com/atb-financial/j/{job_id}/",
                "posted": job.get("published_on", ""),
            })

        token = data.get("token")
        if not token or not data.get("results"):
            break
        time.sleep(0.5)

    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
