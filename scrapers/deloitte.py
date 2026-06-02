import logging
import time

import requests
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# SmartRecruiters public API — no auth required
API_URL = "https://api.smartrecruiters.com/v1/companies/DeloitteCA/postings"
JOB_LINK_TEMPLATE = "https://careers.deloitte.ca/jobs/{job_id}"
PAGE_SIZE = 100

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_deloitte() -> list[dict]:
    jobs = []
    offset = 0

    while True:
        params = {
            "country": "ca",
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        postings = data.get("content", [])
        total = data.get("totalFound", 0)

        for posting in postings:
            title = posting.get("name", "")
            if not is_target_role(title):
                continue

            job_id = posting.get("id", "")
            location_obj = posting.get("location", {})
            city = location_obj.get("city", "")
            region = location_obj.get("region", "")
            location = f"{city}, {region}".strip(", ")

            jobs.append({
                "id": f"deloitte-{job_id}",
                "company": "Deloitte",
                "title": title,
                "location": location,
                "link": JOB_LINK_TEMPLATE.format(job_id=job_id),
                "posted": posting.get("releasedDate", ""),
            })

        offset += PAGE_SIZE
        if offset >= total or not postings:
            break
        time.sleep(0.5)

    return jobs

