import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# McKinsey uses a custom portal with a JSON search API
API_URL = "https://www.mckinsey.com/careers/search-jobs/jcr:content/root/responsivegrid/container/responsivegrid/container/searchjobs.model.json"
BASE_URL = "https://www.mckinsey.com"
PAGE_SIZE = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "application/json, text/html",
    "Referer": "https://www.mckinsey.com/careers/search-jobs",
}


def scrape_mckinsey() -> list[dict]:
    """
    McKinsey's careers page is largely JavaScript-rendered. We attempt their
    internal JSON endpoint first; if that fails we fall back to parsing the
    static HTML which lists some postings server-side.
    """
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    jobs = []
    try:
        params = {
            "country": "Canada",
            "start": "0",
            "rows": str(PAGE_SIZE),
        }
        offset = 0
        while True:
            params["start"] = str(offset)
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()
            postings = data.get("jobs", data.get("results", []))
            if not postings:
                break
            for p in postings:
                title = p.get("title", p.get("jobTitle", ""))
                if not is_target_role(title):
                    continue
                job_id = str(p.get("id", p.get("jobId", "")))
                link = p.get("url", p.get("applyUrl", f"https://www.mckinsey.com/careers/search-jobs#{job_id}"))
                if link.startswith("/"):
                    link = BASE_URL + link
                jobs.append({
                    "id": f"mckinsey-{job_id}",
                    "company": "McKinsey",
                    "title": title,
                    "location": p.get("location", p.get("city", "Canada")),
                    "link": link,
                    "posted": p.get("postingDate", ""),
                })
            offset += PAGE_SIZE
            if offset >= data.get("total", len(postings)):
                break
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"McKinsey JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(
            "https://www.mckinsey.com/careers/search-jobs",
            params={"location": "Canada"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for link_tag in soup.find_all("a", href=re.compile(r"/careers/search-jobs/overview")):
            title = link_tag.get_text(strip=True)
            if not title or not is_target_role(title):
                continue
            href = link_tag["href"]
            full_link = BASE_URL + href if href.startswith("/") else href
            req_id = re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]
            jobs.append({
                "id": f"mckinsey-{req_id}",
                "company": "McKinsey",
                "title": title,
                "location": "Canada",
                "link": full_link,
                "posted": "",
            })
    except Exception as e:
        logger.warning(f"McKinsey HTML scrape failed: {e}")
    return jobs

