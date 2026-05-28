import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://hsbc.taleo.net/careersection/external/jobsearch.ftl"
BASE_URL = "https://hsbc.taleo.net"
PAGE_SIZE = 25

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


def scrape_hsbc() -> list[dict]:
    jobs = []
    params = {
        "lang": "en",
        "location": "Canada",
        "radiusType": "K",
        "radius": "100",
        "psrc": "LOCATION",
    }

    session = requests.Session()
    # Taleo requires a session cookie from the initial page load
    session.get(SEARCH_URL, headers=HEADERS, timeout=15)

    page = 1
    while True:
        params["startrow"] = str((page - 1) * PAGE_SIZE)
        resp = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rows = soup.select("tr.listSectionContent")
        if not rows:
            # Try alternate row selector used by some Taleo versions
            rows = soup.select("table.dataTable tr[class]")

        found_any = False
        for row in rows:
            link_tag = row.find("a", href=re.compile(r"jobdetail\.ftl"))
            if not link_tag:
                continue
            found_any = True

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            full_link = BASE_URL + href if href.startswith("/") else href

            # Extract requisition ID from URL for dedup
            req_match = re.search(r"job=(\d+)", href)
            req_id = req_match.group(1) if req_match else href

            tds = row.find_all("td")
            location = ""
            for td in tds:
                text = td.get_text(strip=True)
                if _is_canada(text):
                    location = text
                    break

            if not _is_canada(location) and not any(_is_canada(td.get_text()) for td in tds):
                continue
            if not _is_entry_level(title):
                continue

            jobs.append({
                "id": f"hsbc-{req_id}",
                "company": "HSBC",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": "",
            })

        # Check if there are more pages
        next_link = soup.find("a", string=re.compile(r"Next", re.I))
        if not next_link or not found_any:
            break
        page += 1

    return jobs


def _is_canada(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in CANADIAN_LOCATIONS)


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)
