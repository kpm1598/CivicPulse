"""Duplicate detection: same problem, reported again by another citizen.

A new report is a duplicate of an existing OPEN report when ALL are true:
  - same category
  - within DUPLICATE_RADIUS_METRES (haversine / straight-line distance)
  - the original was created within DUPLICATE_WINDOW_DAYS
  - the original is not already Resolved, and is not itself a duplicate
"""
import math
from datetime import datetime, timezone

from app.config import DUPLICATE_RADIUS_METRES, DUPLICATE_WINDOW_DAYS


def haversine_metres(lat1, lng1, lat2, lng2) -> float:
    """Straight-line distance in metres between two lat/lng points."""
    if None in (lat1, lng1, lat2, lng2):
        return float("inf")
    r = 6371000  # Earth radius in metres
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_original(conn, category: str, lat, lng, now=None):
    """Return the row of the likely original report, or None."""
    if lat is None or lng is None:
        return None
    now = now or datetime.now(timezone.utc)
    rows = conn.execute(
        """SELECT * FROM reports
           WHERE category = ? AND status != 'Resolved' AND duplicate_of IS NULL
           ORDER BY created_at ASC""",
        (category,),
    ).fetchall()
    for row in rows:
        created = datetime.fromisoformat(row["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if (now - created).days > DUPLICATE_WINDOW_DAYS:
            continue
        if haversine_metres(lat, lng, row["lat"], row["lng"]) <= DUPLICATE_RADIUS_METRES:
            return row
    return None
