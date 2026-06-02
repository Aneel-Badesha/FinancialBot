INCLUDE_KEYWORDS = [
    "analyst", "associate", "advisor", "rotational", "graduate",
    "new grad", "new graduate", "early career", "campus",
]

SENIORITY_EXCLUSIONS = [
    "senior", " sr ", "sr.", "lead ", "manager", "director",
    "principal", "vp ", "vice president", "head of", "partner",
    "managing", "experienced", " ii ", " iii ", " iv ",
]

ROLE_EXCLUSIONS = [
    "teller", "cashier", "clerk", "hourly",
    "personal banking", "insolvency", "mortgage advisor",
]

INTERN_EXCLUSIONS = [
    "intern", "co-op", "coop", "internship",
    " 4 month", " 8 month", " 12 month", " 16 month",
]

# Workday postedOn strings within 48 hours
_RECENT_WORKDAY = {"posted today", "posted yesterday", "posted 1 day ago", "posted 2 days ago"}


def is_target_role(title: str) -> bool:
    t = title.lower()
    if any(excl in t for excl in SENIORITY_EXCLUSIONS):
        return False
    if t.endswith(" sr") or t.endswith(", sr"):
        return False
    if any(excl in t for excl in ROLE_EXCLUSIONS):
        return False
    if any(excl in t for excl in INTERN_EXCLUSIONS):
        return False
    return any(kw in t for kw in INCLUDE_KEYWORDS)


def is_recent(posted_on: str) -> bool:
    return posted_on.lower().strip() in _RECENT_WORKDAY
