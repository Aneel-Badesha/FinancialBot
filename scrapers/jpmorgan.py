import logging
import time

import requests

logger = logging.getLogger(__name__)

REST_URL = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
JOB_LINK_TEMPLATE = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{job_id}"
SITE_NUMBER = "CX_1001"
PAGE_SIZE = 25

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_jpmorgan() -> list[dict]:
    jobs = []
    offset = 0

    while True:
        finder = (
            f"findReqs;siteNumber={SITE_NUMBER},"
            f"sortBy=POSTING_DATES_DESC,"
            f"limit={PAGE_SIZE},"
            f"offset={offset}"
        )
        params = {"onlyData": "true", "expand": "requisitionList", "finder": finder}
        resp = requests.get(REST_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        has_more = data.get("hasMore", False)

        for item in data.get("items", []):
            for posting in item.get("requisitionList", []):
                if posting.get("PrimaryLocationCountry", "") != "CA":
                    continue

                title = posting.get("Title", "")
                if not _is_entry_level(title):
                    continue

                job_id_raw = str(posting.get("Id", ""))
                jobs.append({
                    "id": f"jpmorgan-{job_id_raw}",
                    "company": "JPMorgan",
                    "title": title,
                    "location": posting.get("PrimaryLocation", ""),
                    "link": JOB_LINK_TEMPLATE.format(job_id=job_id_raw),
                    "posted": posting.get("PostedDate", ""),
                })

        offset += PAGE_SIZE
        if not has_more:
            break
        time.sleep(0.5)

    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
