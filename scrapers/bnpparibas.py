import logging
import re

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

# BNP Paribas uses the TAL (Taleo) platform at bnppus.tal.net for North America
SEARCH_URL = "https://bnppus.tal.net/candidate"
BASE_URL = "https://bnppus.tal.net"
PAGE_SIZE = 25

CANADIAN_LOCATIONS = [
    "canada", "toronto", "montreal", "vancouver", "calgary",
    "ottawa", "edmonton", "winnipeg", "halifax", "ontario", "quebec",
    "british columbia", "alberta",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_bnpparibas() -> list[dict]:
    jobs = []
    session = requests.Session()
    # Establish session
    session.get(SEARCH_URL, headers=HEADERS, timeout=15)

    params = {
        "country": "Canada",
        "startrow": "0",
    }

    page = 1
    while True:
        params["startrow"] = str((page - 1) * PAGE_SIZE)
        resp = session.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rows = soup.select("tr.listSectionContent")
        if not rows:
            rows = soup.select("table.dataTable tr[class]")

        found_any = False
        for row in rows:
            link_tag = row.find("a", href=re.compile(r"jobdetail\.ftl|/job/"))
            if not link_tag:
                continue
            found_any = True

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            full_link = BASE_URL + href if href.startswith("/") else href

            req_match = re.search(r"job=(\d+)", href)
            req_id = req_match.group(1) if req_match else re.sub(r"[^a-zA-Z0-9]", "-", href)[-40:]

            tds = row.find_all("td")
            location = ""
            for td in tds:
                text = td.get_text(strip=True)
                if _is_canada(text):
                    location = text
                    break

            if not _is_canada(location) and not any(_is_canada(td.get_text()) for td in tds):
                continue
            if not is_target_role(title):
                continue

            jobs.append({
                "id": f"bnpparibas-{req_id}",
                "company": "BNP Paribas",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": "",
            })

        next_link = soup.find("a", string=re.compile(r"Next", re.I))
        if not next_link or not found_any:
            break
        page += 1

    return jobs


def _is_canada(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in CANADIAN_LOCATIONS)

