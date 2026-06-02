import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# BCG uses a custom portal at careers.bcg.com
API_URL = "https://careers.bcg.com/api/apply/v2/jobs"
BASE_URL = "https://careers.bcg.com"
PAGE_SIZE = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "application/json, text/html",
    "Referer": "https://careers.bcg.com/global/en/search-results",
}


def scrape_bcg() -> list[dict]:
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    jobs = []
    try:
        offset = 0
        while True:
            params = {
                "domain": "bcg.com",
                "start": str(offset),
                "num": str(PAGE_SIZE),
                "location": "Canada",
            }
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            postings = data.get("positions", data.get("jobs", []))
            if not postings:
                break
            for p in postings:
                title = p.get("name", p.get("title", ""))
                if not is_target_role(title):
                    continue
                job_id = str(p.get("id", p.get("externalPath", "")))
                link = p.get("canonicalPositionUrl", p.get("url", ""))
                if link.startswith("/"):
                    link = BASE_URL + link
                elif not link:
                    link = f"https://careers.bcg.com/global/en/job/{job_id}"
                location = p.get("location", p.get("primaryLocation", "Canada"))
                jobs.append({
                    "id": f"bcg-{job_id}",
                    "company": "BCG",
                    "title": title,
                    "location": location,
                    "link": link,
                    "posted": p.get("postedDate", ""),
                })
            offset += PAGE_SIZE
            if offset >= data.get("totalPositions", data.get("total", len(postings))):
                break
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"BCG JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(
            "https://careers.bcg.com/global/en/search-results",
            params={"keywords": "", "location": "Canada"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for link_tag in soup.find_all("a", href=re.compile(r"/global/en/job/")):
            title = link_tag.get_text(strip=True)
            if not title or not is_target_role(title):
                continue
            href = link_tag["href"]
            full_link = BASE_URL + href if href.startswith("/") else href
            req_match = re.search(r"/job/([^/]+)", href)
            req_id = req_match.group(1) if req_match else re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]
            jobs.append({
                "id": f"bcg-{req_id}",
                "company": "BCG",
                "title": title,
                "location": "Canada",
                "link": full_link,
                "posted": "",
            })
    except Exception as e:
        logger.warning(f"BCG HTML scrape failed: {e}")
    return jobs

