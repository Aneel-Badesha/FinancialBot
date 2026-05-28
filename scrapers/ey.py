import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# EY uses SAP SuccessFactors; the public job search is at careers.ey.com
SEARCH_URL = "https://careers.ey.com/ey/jobs"
BASE_URL = "https://careers.ey.com"
PAGE_SIZE = 10

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

CANADIAN_LOCATIONS = [
    "canada", "toronto", "montreal", "vancouver", "calgary",
    "ottawa", "edmonton", "winnipeg", "halifax", "ontario", "quebec",
    "british columbia", "alberta",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_ey() -> list[dict]:
    jobs = []
    params = {
        "location_input": "Canada",
        "location_name": "Canada",
        "location_type": "country",
        "job_country": "CA",
        "start": "0",
    }

    page = 0
    while True:
        params["start"] = str(page * PAGE_SIZE)
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        job_cards = soup.select("li.job-card, article.job-result, div.job-listing")
        if not job_cards:
            # Fallback: look for any link with /ey/jobs/ in href
            job_cards = soup.find_all("a", href=re.compile(r"/ey/jobs/\d+"))

        if not job_cards:
            break

        found_any = False
        for card in job_cards:
            if hasattr(card, "find"):
                link_tag = card.find("a", href=re.compile(r"/ey/jobs/\d+")) or (
                    card if card.name == "a" else None
                )
            else:
                link_tag = card

            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if not title or not href:
                continue

            found_any = True
            full_link = BASE_URL + href if href.startswith("/") else href
            req_match = re.search(r"/jobs/(\d+)", href)
            req_id = req_match.group(1) if req_match else re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]

            location_el = (
                card.find(class_=re.compile(r"location|city", re.I)) if hasattr(card, "find") else None
            )
            location = location_el.get_text(strip=True) if location_el else "Canada"

            if not _is_entry_level(title):
                continue

            jobs.append({
                "id": f"ey-{req_id}",
                "company": "EY",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": "",
            })

        if not found_any:
            break

        # Check for next page
        next_btn = soup.find("a", string=re.compile(r"Next", re.I))
        if not next_btn:
            break
        page += 1
        time.sleep(0.5)

    return jobs


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
