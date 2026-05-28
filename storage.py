import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
SEEN_JOBS_FILE = Path("seen_jobs.json")


def load_seen_ids() -> set[str]:
    if not SEEN_JOBS_FILE.exists():
        return set()
    with SEEN_JOBS_FILE.open() as f:
        data = json.load(f)
    return set(data.get("seen_ids", []))


def save_seen_ids(seen_ids: set[str]) -> None:
    with SEEN_JOBS_FILE.open("w") as f:
        json.dump({"seen_ids": sorted(seen_ids)}, f, indent=2)
    logger.info(f"Saved {len(seen_ids)} seen job IDs")


def filter_new_jobs(jobs: list[dict], seen_ids: set[str]) -> list[dict]:
    return [j for j in jobs if j["id"] not in seen_ids]


def add_to_seen(jobs: list[dict], seen_ids: set[str]) -> set[str]:
    return seen_ids | {j["id"] for j in jobs}
