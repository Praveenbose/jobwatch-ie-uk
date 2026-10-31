"""Rules that decide whether a job is relevant: location, seniority, visa signals, keywords."""
import re
from typing import Dict, List, Tuple

from .models import Job

LOCATION_PATTERNS = [
    r"\bireland\b", r"\bdublin\b", r"\bcork\b", r"\bgalway\b", r"\blimerick\b", r"\bwaterford\b",
    r"\bunited kingdom\b", r"\buk\b", r"\bgreat britain\b", r"\bengland\b", r"\bscotland\b", r"\bwales\b",
    r"\blondon\b", r"\bmanchester\b", r"\bbirmingham\b", r"\bedinburgh\b", r"\bglasgow\b",
    r"\bbelfast\b", r"\bleeds\b", r"\bbristol\b",
]
ENTRY_TERMS = ["junior", "graduate", "entry level", "entry-level", "trainee", "intern", "apprentice", "associate", "early career"]
SENIOR_TERMS = ["senior", "lead", "principal", "manager", "head of", "director", "architect", "staff", "expert"]
VISA_POSITIVE = ["visa sponsorship", "sponsorship available", "we sponsor", "will sponsor", "can sponsor",
                 "critical skills", "skilled worker", "relocation support", "relocation assistance", "relocation package"]
VISA_NEGATIVE = ["no sponsorship", "unable to sponsor", "not able to sponsor", "cannot sponsor", "can't sponsor",
                 "will not sponsor", "without sponsorship", "must have the right to work", "must have existing right to work"]


def in_target_location(job: Job) -> bool:
    text = f"{job.location} {job.title}".lower()
    return any(re.search(p, text) for p in LOCATION_PATTERNS)


def classify_level(title: str) -> str:
    t = title.lower()
    if any(re.search(rf"\b{re.escape(w)}\b", t) for w in SENIOR_TERMS):
        return "senior"
    if any(re.search(rf"\b{re.escape(w)}\b", t) for w in ENTRY_TERMS):
        return "entry"
    return "mid"


def visa_signal(job: Job) -> str:
    text = f"{job.title} {job.description}".lower()
    if any(p in text for p in VISA_NEGATIVE):      # negatives win
        return "unlikely"
    if any(p in text for p in VISA_POSITIVE):
        return "likely"
    return "unknown"


def evaluate(job: Job, prefs: Dict) -> Tuple[bool, int, List[str]]:
    """Return (matches?, score, reasons). prefs keys: levels, keywords, exclude, require_visa."""
    reasons: List[str] = []
    if not in_target_location(job):
        return False, 0, ["outside Ireland/UK"]
    level = classify_level(job.title)
    if prefs.get("levels") and level not in prefs["levels"]:
        return False, 0, [f"level {level} not wanted"]
    title, body = job.title.lower(), job.description.lower()
    if any(x.lower() in title for x in prefs.get("exclude", [])):
        return False, 0, ["excluded keyword"]
    score = 1
    reasons.append(f"{level} level")
    keywords = [k.lower() for k in prefs.get("keywords", [])]
    hits_title = [k for k in keywords if k in title]
    hits_body = [k for k in keywords if k in body and k not in hits_title]
    if keywords and not (hits_title or hits_body):
        return False, 0, ["no keyword match"]
    score += 2 * len(hits_title) + len(hits_body)
    if hits_title or hits_body:
        reasons.append("keywords: " + ", ".join(hits_title + hits_body))
    visa = visa_signal(job)
    if prefs.get("require_visa") and visa != "likely":
        return False, 0, [f"visa signal {visa}"]
    if visa == "likely":
        score += 3
        reasons.append("visa sponsorship mentioned")
    elif visa == "unlikely":
        reasons.append("visa: NOT sponsored")
    return True, score, reasons
