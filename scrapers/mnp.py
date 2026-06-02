import logging
import re
import time

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# MNP uses UKG Pro (UltiPro) recruiting portal
API_URL = "https://recruiting.ultipro.ca/MNP5000MNPL/JobBoard/d1e870eb-9c8c-4ce5-88ee-9f042cf2a12f/JobListings"
BASE_URL = "https://recruiting.ultipro.ca"
PAGE_SIZE = 20

HEADERS = {
    "Accept": "application/json, text/html",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_mnp() -> list[dict]:
    jobs = _try_json_api()
    if not jobs:
        jobs = _try_html_scrape()
    return jobs


def _try_json_api() -> list[dict]:
    jobs = []
    try:
        params = {"startIndex": "0", "pageSize": str(PAGE_SIZE)}
        offset = 0
        while True:
            params["startIndex"] = str(offset)
            resp = requests.get(
                API_URL, params=params,
                headers={**HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            postings = data.get("jobListings", data.get("jobs", []))
            if not postings:
                break
            for p in postings:
                title = p.get("title", p.get("jobTitle", ""))
                if not is_target_role(title):
                    continue
                job_id = str(p.get("opportunityId", p.get("id", "")))
                link = p.get("applyUrl", f"{BASE_URL}/MNP5000MNPL/JobBoard/e3b53a54-57f4-4cd4-acf5-ca2c7cfb4a57/{job_id}")
                location = p.get("location", p.get("city", "Canada"))
                jobs.append({
                    "id": f"mnp-{job_id}",
                    "company": "MNP",
                    "title": title,
                    "location": location,
                    "link": link,
                    "posted": p.get("postedDate", ""),
                })
            offset += PAGE_SIZE
            total = data.get("totalCount", data.get("total", len(postings)))
            if offset >= total:
                break
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"MNP JSON API failed: {e}")
        return []
    return jobs


def _try_html_scrape() -> list[dict]:
    jobs = []
    try:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for link_tag in soup.find_all("a", href=re.compile(r"JobDetails|/job/")):
            title = link_tag.get_text(strip=True)
            if not title or not is_target_role(title):
                continue
            href = link_tag["href"]
            full_link = BASE_URL + href if href.startswith("/") else href
            req_id = re.sub(r"[^a-zA-Z0-9]", "-", href.split("?")[0])[-40:]
            jobs.append({
                "id": f"mnp-{req_id}",
                "company": "MNP",
                "title": title,
                "location": "Canada",
                "link": full_link,
                "posted": "",
            })
    except Exception as e:
        logger.warning(f"MNP HTML scrape failed: {e}")
    return jobs

