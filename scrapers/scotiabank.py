import logging
import re

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.scotiabank.com"
LISTING_URL = f"{BASE_URL}/go/Student-&-New-Grad-Jobs/2298417/"
PAGE_SIZE = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_scotiabank() -> list[dict]:
    jobs = []
    start = 0
    total = None

    while True:
        params = {"start": start} if start > 0 else {}
        resp = requests.get(LISTING_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        if total is None:
            match = re.search(r"Results\s+\d+\s*[–\-]\s*\d+\s+of\s+(\d+)", soup.get_text())
            total = int(match.group(1)) if match else PAGE_SIZE

        found_any = False
        for row in soup.find_all("tr"):
            link_tag = row.find("a", href=re.compile(r"^/job/"))
            if not link_tag:
                continue
            found_any = True

            title = link_tag.get_text(strip=True)
            if not is_target_role(title):
                continue
            href = link_tag["href"]
            job_id = f"scotiabank-{href.rstrip('/').split('/')[-1]}"
            full_link = BASE_URL + href

            tds = row.find_all("td")
            date_posted = tds[1].get_text(strip=True) if len(tds) >= 2 else ""
            location = tds[2].get_text(strip=True) if len(tds) >= 3 else ""

            jobs.append({
                "id": job_id,
                "company": "Scotiabank",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": date_posted,
            })

        start += PAGE_SIZE
        if start >= total or not found_any:
            break

    return jobs
