import logging
import time

import requests
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# Amazon has a public jobs JSON API
API_URL = "https://www.amazon.jobs/en/search.json"
PAGE_SIZE = 10

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_amazon() -> list[dict]:
    jobs = []
    offset = 0

    while True:
        params = {
            "base_query": "",
            "loc_query": "Canada",
            "job_count": PAGE_SIZE,
            "result_limit": PAGE_SIZE,
            "sort": "recent",
            "offset": offset,
            "latitude": "",
            "longitude": "",
            "loc_group_id": "",
        }
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        postings = data.get("jobs", [])
        if not postings:
            break

        for p in postings:
            title = p.get("title", "")
            if not is_target_role(title):
                continue

            job_id = p.get("id_icims", p.get("job_id", ""))
            location = p.get("normalized_location", p.get("location", "Canada"))
            link = f"https://www.amazon.jobs/en/jobs/{job_id}" if job_id else "https://www.amazon.jobs"

            jobs.append({
                "id": f"amazon-{job_id}",
                "company": "Amazon",
                "title": title,
                "location": location,
                "link": link,
                "posted": p.get("posted_date", ""),
            })

        hits = data.get("hits", 0)
        offset += PAGE_SIZE
        if offset >= hits or len(postings) < PAGE_SIZE:
            break
        time.sleep(0.5)

    return jobs

