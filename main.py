import logging
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

# Load .env when running locally (no-op if file doesn't exist or python-dotenv not installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from scrapers import (
    scrape_all_workday,
    scrape_scotiabank,
    scrape_jpmorgan,
    scrape_hsbc,
    scrape_bnpparibas,
    scrape_deloitte,
    scrape_ey,
    scrape_mckinsey,
    scrape_bcg,
    scrape_pwc,
    scrape_kpmg,
    scrape_rogers,
    scrape_bell,
    scrape_bain,
    scrape_national_bank,
    scrape_atb,
    scrape_shopify,
    scrape_amazon,
    scrape_google,
    scrape_oliver_wyman,
    scrape_grant_thornton,
    scrape_mnp,
    scrape_canada_life,
    scrape_fairfax,
    scrape_sobeys,
    scrape_wealthsimple,
    scrape_bank_of_america,
)
from storage import load_seen_ids, save_seen_ids, filter_new_jobs, add_to_seen, save_jobs_for_site
from emailer import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SCRAPERS = [
    ("Workday (27 companies)", scrape_all_workday),
    ("Scotiabank", scrape_scotiabank),
    ("JPMorgan", scrape_jpmorgan),
    # ("HSBC", scrape_hsbc),  # slow RSS feed
    ("BNP Paribas", scrape_bnpparibas),
    # ("National Bank", scrape_national_bank),  # slow RSS feed
    ("Deloitte", scrape_deloitte),
    ("EY", scrape_ey),
    # ("McKinsey", scrape_mckinsey),  # blocks scrapers
    ("BCG", scrape_bcg),
    # ("Bain & Company", scrape_bain),  # blocks scrapers
    # ("Oliver Wyman", scrape_oliver_wyman),  # dead URL
    ("PwC", scrape_pwc),
    ("KPMG", scrape_kpmg),
    # ("Grant Thornton", scrape_grant_thornton),  # dead URL
    # ("MNP", scrape_mnp),  # dead URL
    # ("Rogers", scrape_rogers),
    ("Bell", scrape_bell),
    # ("Shopify", scrape_shopify),  # left Lever, new ATS unknown
    ("ATB Financial", scrape_atb),
    ("Canada Life", scrape_canada_life),
    ("Fairfax Financial", scrape_fairfax),
    # ("Sobeys / Empire", scrape_sobeys),  # dead URL
    ("Wealthsimple", scrape_wealthsimple),
    ("Bank of America", scrape_bank_of_america),
]


def run_scraper(name: str, fn) -> list[dict]:
    try:
        results = fn()
        logger.info(f"{name}: {len(results)} relevant jobs found")
        return results
    except Exception as e:
        logger.error(f"{name} failed: {e}", exc_info=True)
        return []


def main():
    seen_ids = load_seen_ids()
    logger.info(f"Loaded {len(seen_ids)} previously seen job IDs")

    all_jobs = []
    for name, fn in SCRAPERS:
        all_jobs += run_scraper(name, fn)

    logger.info(f"Total jobs scraped (before dedup): {len(all_jobs)}")

    new_jobs = filter_new_jobs(all_jobs, seen_ids)
    logger.info(f"New jobs (not previously seen): {len(new_jobs)}")

    if new_jobs:
        try:
            send_digest(new_jobs)
        except Exception as e:
            logger.error(f"Failed to send email digest: {e}")
    else:
        logger.info("No new jobs — skipping email")

    updated_seen = add_to_seen(all_jobs, seen_ids)
    save_seen_ids(updated_seen)
    save_jobs_for_site(all_jobs)
    _push_site()


def _push_site():
    repo = Path(__file__).parent
    try:
        subprocess.run(["git", "add", "docs/jobs.json"], cwd=repo, check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=repo
        )
        if result.returncode == 0:
            logger.info("docs/jobs.json unchanged — skipping push")
            return
        subprocess.run(
            ["git", "commit", "-m", f"Update jobs.json [{date.today().isoformat()}]"],
            cwd=repo, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo, check=True)
        logger.info("Pushed docs/jobs.json to GitHub")
    except Exception as e:
        logger.error(f"Failed to push site update: {e}")


if __name__ == "__main__":
    main()
