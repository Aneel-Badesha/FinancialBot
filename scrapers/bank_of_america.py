import logging
import time

import requests
from bs4 import BeautifulSoup
from scrapers.filters import is_target_role

logger = logging.getLogger(__name__)

BASE_URL = "https://bankcampuscareers.tal.net"
SEARCH_URL = (
    f"{BASE_URL}/vx/lang-en-GB/mobile-0/brand-4/user-36"
    f"/xf-1c8d608fd721/wid-1/candidate/jobboard/vacancy/1/adv/"
)
PAGE_SIZE = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def scrape_bank_of_america() -> list[dict]:
    jobs = []
    seen_ids = set()
    offset = 0

    while True:
        params = {
            "q": "",
            "location": "Canada",
            "btnSubmit": "Search",
            "start": offset,
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rows = soup.select("tr.search_res.details_row")
        if not rows:
            break

        found_any = False
        for row in rows:
            opp_id = row.get("data-oppid", "")
            if not opp_id or opp_id in seen_ids:
                continue
            seen_ids.add(opp_id)
            found_any = True

            link_tag = row.find("a", class_="subject")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            if not is_target_role(title):
                continue

            href = link_tag.get("href", "")
            full_link = href if href.startswith("http") else BASE_URL + href

            tds = row.find_all("td")
            location = tds[2].get_text(strip=True) if len(tds) >= 3 else ""

            if not _is_canada(location) and not _is_canada(title):
                continue

            jobs.append({
                "id": f"bofa-{opp_id}",
                "company": "Bank of America",
                "title": title,
                "location": location,
                "link": full_link,
                "posted": "",
            })

        if not found_any or len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.5)

    return jobs


CANADIAN_LOCATIONS = [
    "canada", "toronto", "montreal", "vancouver", "calgary", "edmonton",
    "ottawa", "ontario", "quebec", "british columbia", "alberta",
]


def _is_canada(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in CANADIAN_LOCATIONS)
