import logging
import time

import requests

logger = logging.getLogger(__name__)

ENTRY_LEVEL_KEYWORDS = [
    "analyst", "associate", "graduate", "new grad", "entry",
    "junior", "intern", "co-op", "coop", "rotational",
    "early career", "campus",
]

CANADIAN_LOCATIONS = [
    "canada", ", ca", "toronto", "montreal", "vancouver", "calgary",
    "ottawa", "edmonton", "winnipeg", "halifax", "ontario", "quebec",
    "british columbia", "alberta", "nova scotia", "new brunswick",
    "manitoba", "saskatchewan", "newfoundland",
]

BANKS = [
    {"company": "RBC", "tenant": "rbc", "wd_instance": "wd3", "site": "RBCEARLYTALENT1"},
    {"company": "TD", "tenant": "td", "wd_instance": "wd3", "site": "TD_Bank_Careers"},
    {"company": "CIBC", "tenant": "cibc", "wd_instance": "wd3", "site": "search"},
    {"company": "Citibank", "tenant": "citi", "wd_instance": "wd5", "site": "citi"},
    {"company": "Capital One", "tenant": "capitalone", "wd_instance": "wd12", "site": "Capital_One"},
    {"company": "BMO", "tenant": "bmo", "wd_instance": "wd3", "site": "External"},
    {"company": "Deutsche Bank", "tenant": "db", "wd_instance": "wd3", "site": "DBWebsite"},
    {"company": "Enbridge", "tenant": "enbridge", "wd_instance": "wd3", "site": "enbridge_careers"},
    {"company": "Brookfield Asset Management", "tenant": "brookfield", "wd_instance": "wd5", "site": "brookfield"},
    {"company": "Accenture", "tenant": "accenture", "wd_instance": "wd103", "site": "AccentureCareers"},
    {"company": "George Weston", "tenant": "myview", "wd_instance": "wd3", "site": "George_Weston"},
    {"company": "Loblaw", "tenant": "myview", "wd_instance": "wd3", "site": "Loblaw-Digital_Careers_Carrieres"},
    {"company": "Bank of America", "tenant": "bankofamerica", "wd_instance": "wd1", "site": "Global_Campus_Careers"},
    # Insurance & financial services
    {"company": "Manulife", "tenant": "manulife", "wd_instance": "wd3", "site": "MFCJH_Jobs"},
    {"company": "Sun Life", "tenant": "sunlife", "wd_instance": "wd3", "site": "Sunlife"},
    {"company": "Intact Financial", "tenant": "intactfc", "wd_instance": "wd3", "site": "intactfc"},
    # Pension funds
    {"company": "CPP Investments", "tenant": "cppib", "wd_instance": "wd10", "site": "cppinvestments"},
    {"company": "OTPP", "tenant": "otppb", "wd_instance": "wd3", "site": "OntarioTeachers_Careers"},
    {"company": "CDPQ", "tenant": "cdpq", "wd_instance": "wd10", "site": "CDPQ"},
    {"company": "PSP Investments", "tenant": "investpsp", "wd_instance": "wd3", "site": "psp_careers"},
    # Global investment banks
    {"company": "Goldman Sachs", "tenant": "uasys", "wd_instance": "wd5", "site": "GS"},
    {"company": "Morgan Stanley", "tenant": "ms", "wd_instance": "wd5", "site": "External"},
    {"company": "Barclays", "tenant": "barclays", "wd_instance": "wd3", "site": "External_Career_Site_Barclays"},
    {"company": "Wells Fargo", "tenant": "wf", "wd_instance": "wd1", "site": "WellsFargoJobs"},
    # Asset management
    {"company": "BlackRock", "tenant": "blackrock", "wd_instance": "wd1", "site": "BlackRock_Professional"},
    {"company": "Fidelity Canada", "tenant": "fil", "wd_instance": "wd3", "site": "fidelitycanada"},
    # Consulting / accounting
    {"company": "BDO Canada", "tenant": "bdo", "wd_instance": "wd3", "site": "bdo"},
    # Retail / other
    {"company": "Couche-Tard", "tenant": "circlek", "wd_instance": "wd3", "site": "CircleKStoreJobs"},
]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; job-scraper/1.0)",
}


def scrape_workday(company: str, tenant: str, wd_instance: str, site: str) -> list[dict]:
    base_url = f"https://{tenant}.{wd_instance}.myworkdayjobs.com"
    api_url = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"

    jobs = []
    limit = 20
    offset = 0

    while True:
        payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
        resp = requests.post(api_url, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        postings = data.get("jobPostings", [])
        total = data.get("total", 0)

        for posting in postings:
            title = posting.get("title", "")
            location = posting.get("locationsText", "")
            external_path = posting.get("externalPath", "")

            if not _is_canada(location):
                continue
            if not _is_entry_level(title):
                continue

            job_id = f"workday-{tenant}-{external_path.strip('/')}"
            link = f"{base_url}/{site}{external_path}"

            jobs.append({
                "id": job_id,
                "company": company,
                "title": title,
                "location": location,
                "link": link,
                "posted": posting.get("postedOn", ""),
            })

        offset += limit
        if offset >= total or not postings:
            break
        time.sleep(0.5)

    return jobs


def _is_canada(location_text: str) -> bool:
    loc = location_text.lower()
    return any(term in loc for term in CANADIAN_LOCATIONS)


def _is_entry_level(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in ENTRY_LEVEL_KEYWORDS)


def scrape_all_workday() -> list[dict]:
    all_jobs = []
    for bank in BANKS:
        try:
            jobs = scrape_workday(**bank)
            logger.info(f"{bank['company']}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"{bank['company']} Workday scraper failed: {e}")
    return all_jobs
