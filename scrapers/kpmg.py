import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://careers.kpmg.ca/students"
BASE_URL = "https://careers.kpmg.ca"
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


def scrape_kpmg() -> list[dict]:
    """
    KPMG Canada's student/new-grad page. Attempt their JSON API first,
    then fall back to HTML scraping.
    """
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    jobs = []
    try:
        api_url = f"{BASE_URL}/api/jobs"
        params = {
            "keywords": "",
            "location": "Canada",
            "start": "0",
            "num": str(PAGE_SIZE),
        }
        offset = 0
        while True:
            params["start"] = str(offset)
            resp = requests.get(
                api_url, params=params,
                headers={**HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            postings = data.get("jobs", data.get("positions", []))
            if not postings:
                break
            for p in postings:
                title = p.get("title", p.get("name", ""))
                if not _is_entry_level(title):
                    continue
                job_id = str(p.get("id", ""))
                link = p.get("canonicalPositionUrl", p.get("url", f"{BASE_URL}/professionals/{job_id}"))
                if link.startswith("/"):
                    link = BASE_URL + link
                jobs.append({
                    "id": f"kpmg-{job_id}",
                    "company": "KPMG",
                    "title": title,
                    "location": p.get("city", p.get("location", "Canada")),
                    "link": link,
                    "posted": p.get("postedDate", ""),
                })
            offset += PAGE_SIZE
            if offset >= data.get("total", len(postings)):
                break
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"KPMG JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    jobs = []
    try:
        page = 0
        while True:
            params = {"start": str(page * PAGE_SIZE)}
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            found_any = False
            for link_tag in soup.find_all("a", href=re.compile(r"/students/|/professionals/|/job/")):
                title = link_tag.get_text(strip=True)
                if not title or not _is_entry_level(title):
                    continue
                found_any = True
                href = link_tag["href"]
                full_link = BASE_URL + href if href.startswith("/") else href
                req_id = re.sub(r"[^a-zA-Z0-9]", "-", href.split("?")[0])[-40:]
                jobs.append({
                    "id": f"kpmg-{req_id}",
                    "company": "KPMG",
                    "title": title,
                    "location": "Canada",
                    "link": full_link,
                    "posted": "",
                })

            if not found_any or not soup.find("a", string=re.compile(r"Next", re.I)):
                break
            page += 1
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"KPMG HTML scrape failed: {e}")
    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
