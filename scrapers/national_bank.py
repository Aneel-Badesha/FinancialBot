import logging
import xml.etree.ElementTree as ET

import requests
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

FEED_URL = "https://emplois.bnc.ca/en_CA/careers/searchjobs/feed/"
PAGE_SIZE = 20

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)"}


def scrape_national_bank() -> list[dict]:
    jobs = []
    offset = 0

    while True:
        params = {"jobRecordsPerPage": PAGE_SIZE, "jobOffset": offset}
        resp = requests.get(FEED_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []

        if not items:
            break

        for item in items:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")

            if not is_target_role(title):
                continue

            job_id = link.rstrip("/").split("/")[-1]
            jobs.append({
                "id": f"nationalbank-{job_id}",
                "company": "National Bank",
                "title": title,
                "location": "Canada",
                "link": link,
                "posted": pub_date,
            })

        if len(items) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return jobs
