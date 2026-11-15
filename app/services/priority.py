"""
Priority scoring - ONE deterministic function. Judges can follow this.

FORMULA (total is clamped to 0-100):
    severity points   = severity (1-5) x 10                  -> 10 to 50 points
    category points   = CATEGORY_WEIGHTS[category]           -> 8 to 20 points
    duplicate points  = duplicate_count x 5, max 15 points   (more citizens
                        reporting the same problem = more urgent)
    age points        = days open x 1.5, max 15 points       (old problems
                        slowly rise so nothing is forgotten forever)

TIERS:  >=75 Critical | >=55 High | >=35 Medium | <35 Low
To change how priority behaves, edit the numbers here or CATEGORY_WEIGHTS
in app/config.py - nowhere else.
"""
from datetime import datetime, timezone

from app.config import CATEGORY_WEIGHTS, PRIORITY_TIERS


def tier_for_score(score: int) -> str:
    for minimum, name in PRIORITY_TIERS:
        if score >= minimum:
            return name
    return "Low"


def _age_in_days(created_at, now=None) -> float:
    if not created_at:
        return 0.0
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - created_at).total_seconds() / 86400.0)


def calculate_priority(category: str, severity: int, duplicate_count: int = 0,
                       created_at=None, now=None) -> tuple[int, str]:
    """Return (priority_score 0-100, priority_tier)."""
    severity = max(1, min(5, int(severity)))
    score = severity * 10
    score += CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])
    score += min(int(duplicate_count) * 5, 15)
    score += min(_age_in_days(created_at, now) * 1.5, 15)
    score = int(round(max(0, min(100, score))))
    return score, tier_for_score(score)
