import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"


def load_seen_ids() -> set[str]:
    if not SEEN_JOBS_FILE.exists():
        return set()
    try:
        with SEEN_JOBS_FILE.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read {SEEN_JOBS_FILE} ({e}); treating as empty")
        return set()
    return set(data.get("seen_ids", []))


def save_seen_ids(seen_ids: set[str]) -> None:
    tmp = SEEN_JOBS_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump({"seen_ids": sorted(seen_ids)}, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(SEEN_JOBS_FILE)
    logger.info(f"Saved {len(seen_ids)} seen job IDs")


def filter_new_jobs(jobs: list[dict], seen_ids: set[str]) -> list[dict]:
    return [j for j in jobs if j["id"] not in seen_ids]


def add_to_seen(jobs: list[dict], seen_ids: set[str]) -> set[str]:
    return seen_ids | {j["id"] for j in jobs}


JOBS_SITE_FILE = Path(__file__).parent / "docs" / "jobs.json"


def save_jobs_for_site(jobs: list[dict]) -> None:
    JOBS_SITE_FILE.parent.mkdir(exist_ok=True)
    with JOBS_SITE_FILE.open("w") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "jobs": jobs,
        }, f, indent=2)
    logger.info(f"Saved {len(jobs)} jobs to {JOBS_SITE_FILE}")
