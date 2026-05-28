import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Bain uses a custom careers portal at joinbain.com
SEARCH_URL = "https://www.joinbain.com/apply-to-bain/open-positions/default.asp"
BASE_URL = "https://www.joinbain.com"
PAGE_SIZE = 10

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def scrape_bain() -> list[dict]:
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    """Attempt Bain's internal JSON API endpoint."""
    jobs = []
    try:
        api_url = "https://www.bain.com/api/careers/jobs"
        params = {
            "country": "Canada",
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
            postings = data.get("jobs", data.get("positions", data.get("results", [])))
            if not postings:
                break
            for p in postings:
                title = p.get("title", p.get("name", ""))
                if not _is_entry_level(title):
                    continue
                job_id = str(p.get("id", p.get("jobId", "")))
                link = p.get("url", p.get("canonicalPositionUrl", f"https://www.joinbain.com/job/{job_id}"))
                if link.startswith("/"):
                    link = "https://www.joinbain.com" + link
                location_obj = p.get("location", {})
                location = (
                    location_obj.get("city", "") + ", " + location_obj.get("country", "")
                    if isinstance(location_obj, dict)
                    else str(location_obj)
                ).strip(", ")
                jobs.append({
                    "id": f"bain-{job_id}",
                    "company": "Bain & Company",
                    "title": title,
                    "location": location or "Canada",
                    "link": link,
                    "posted": p.get("postedDate", ""),
                })
            offset += PAGE_SIZE
            if offset >= data.get("total", len(postings)):
                break
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Bain JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    """Scrape Bain's joinbain.com open positions page filtered to Canada."""
    jobs = []
    try:
        params = {"office_country": "Canada"}
        page = 0
        while True:
            if page > 0:
                params["start"] = str(page * PAGE_SIZE)
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            found_any = False
            for link_tag in soup.find_all("a", href=re.compile(r"/apply-to-bain/open-positions/|/job/")):
                title = link_tag.get_text(strip=True)
                if not title or not _is_entry_level(title):
                    continue
                found_any = True
                href = link_tag["href"]
                full_link = BASE_URL + href if href.startswith("/") else href
                req_id = re.sub(r"[^a-zA-Z0-9]", "-", href.split("?")[0])[-40:]
                # Try to find location near this link
                parent = link_tag.find_parent("tr") or link_tag.find_parent("li") or link_tag.find_parent("div")
                location = "Canada"
                if parent:
                    loc_el = parent.find(class_=re.compile(r"location|city|office", re.I))
                    if loc_el:
                        location = loc_el.get_text(strip=True)
                jobs.append({
                    "id": f"bain-{req_id}",
                    "company": "Bain & Company",
                    "title": title,
                    "location": location,
                    "link": full_link,
                    "posted": "",
                })

            if not found_any or not soup.find("a", string=re.compile(r"Next", re.I)):
                break
            page += 1
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Bain HTML scrape failed: {e}")
    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
