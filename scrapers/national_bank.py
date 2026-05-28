import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# National Bank uses Oracle Taleo
SEARCH_URL = "https://banquenationaleducanada.taleo.net/careersection/external/jobsearch.ftl"
BASE_URL = "https://banquenationaleducanada.taleo.net"
PAGE_SIZE = 25

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_national_bank() -> list[dict]:
    jobs = []
    session = requests.Session()
    session.get(SEARCH_URL, headers=HEADERS, timeout=15)

    page = 1
    while True:
        params = {
            "lang": "en",
            "startrow": str((page - 1) * PAGE_SIZE),
        }
        resp = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rows = soup.select("tr.listSectionContent")
        if not rows:
            rows = [r for r in soup.find_all("tr") if r.find("a", href=re.compile(r"jobdetail\.ftl"))]

        found_any = False
        for row in rows:
            link_tag = row.find("a", href=re.compile(r"jobdetail\.ftl"))
            if not link_tag:
                continue
            found_any = True

            title = link_tag.get_text(strip=True)
            if not _is_entry_level(title):
                continue

            href = link_tag.get("href", "")
            full_link = BASE_URL + href if href.startswith("/") else href
            req_match = re.search(r"job=(\d+)", href)
            req_id = req_match.group(1) if req_match else re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]

            tds = row.find_all("td")
            location = tds[1].get_text(strip=True) if len(tds) >= 2 else "Canada"

            jobs.append({
                "id": f"nationalbank-{req_id}",
                "company": "National Bank",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": "",
            })

        if not found_any or not soup.find("a", string=re.compile(r"Next", re.I)):
            break
        page += 1
        time.sleep(0.5)

    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
