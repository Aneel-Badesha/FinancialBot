import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# Oliver Wyman is part of Marsh McLennan; careers hosted at oliverwyman.com
SEARCH_URL = "https://careers.oliverwyman.com/search/"
BASE_URL = "https://careers.oliverwyman.com"
PAGE_SIZE = 10

CANADIAN_LOCATIONS = [
    "canada", "toronto", "montreal", "vancouver", "calgary",
    "ottawa", "ontario", "quebec", "british columbia", "alberta",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def scrape_oliver_wyman() -> list[dict]:
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    jobs = []
    try:
        api_url = f"{BASE_URL}/api/jobs"
        params = {"location": "Canada", "start": "0", "num": str(PAGE_SIZE)}
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
                if not is_target_role(title):
                    continue
                job_id = str(p.get("id", ""))
                link = p.get("canonicalPositionUrl", p.get("url", f"{BASE_URL}/search/{job_id}"))
                if link.startswith("/"):
                    link = BASE_URL + link
                jobs.append({
                    "id": f"oliverwyman-{job_id}",
                    "company": "Oliver Wyman",
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
        logger.warning(f"Oliver Wyman JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    jobs = []
    try:
        page = 0
        while True:
            params = {
                "query": "",
                "location": "Canada",
                "startrow": str(page * PAGE_SIZE),
            }
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            found_any = False
            for link_tag in soup.find_all("a", href=re.compile(r"/search/\d+|/jobs/\d+")):
                title = link_tag.get_text(strip=True)
                if not title or not is_target_role(title):
                    continue

                parent = link_tag.find_parent("li") or link_tag.find_parent("tr") or link_tag.find_parent("div")
                location = "Canada"
                if parent:
                    loc_el = parent.find(class_=re.compile(r"location|city", re.I))
                    if loc_el:
                        candidate = loc_el.get_text(strip=True)
                        if _is_canada(candidate):
                            location = candidate
                        elif not _is_canada(location):
                            continue

                found_any = True
                href = link_tag["href"]
                full_link = BASE_URL + href if href.startswith("/") else href
                req_match = re.search(r"/(\d+)$", href.rstrip("/"))
                req_id = req_match.group(1) if req_match else re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]
                jobs.append({
                    "id": f"oliverwyman-{req_id}",
                    "company": "Oliver Wyman",
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
        logger.warning(f"Oliver Wyman HTML scrape failed: {e}")
    return jobs


def _is_canada(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in CANADIAN_LOCATIONS)

