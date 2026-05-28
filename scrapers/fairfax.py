import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.fairfax.ca/employment/"
BASE_URL = "https://www.fairfax.ca"
PAGE_SIZE = 10

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_fairfax() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for link_tag in soup.find_all("a", href=re.compile(r"/employment/|/job/|/careers/")):
            title = link_tag.get_text(strip=True)
            if not title or len(title) < 5 or not _is_entry_level(title):
                continue
            href = link_tag["href"]
            full_link = BASE_URL + href if href.startswith("/") else href
            req_id = re.sub(r"[^a-zA-Z0-9]", "-", href.split("?")[0])[-40:]
            jobs.append({
                "id": f"fairfax-{req_id}",
                "company": "Fairfax Financial",
                "title": title,
                "location": "Toronto, Canada",
                "link": full_link,
                "posted": "",
            })
    except Exception as e:
        logger.warning(f"Fairfax scrape failed: {e}")
    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
