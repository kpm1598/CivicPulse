"""
Issue classification.

Honest rule: we try Groq ONLY if a key is configured. On ANY problem
(no key, network error, bad reply) we fall back to a simple keyword
classifier. The caller always reports which one actually ran via
`classification_source` = "groq" or "keyword_fallback" - we never pretend
Groq ran when it did not.
"""
import json

import requests

from app.config import CATEGORIES, CATEGORY_KEYWORDS, GROQ_API_KEY, GROQ_MODEL


def keyword_classify(description: str) -> tuple[str, int]:
    """Offline fallback: count keyword hits per category, guess severity
    from urgency words. Returns (category, severity 1-5)."""
    text = (description or "").lower()
    best_category, best_hits = "other", 0
    for category, words in CATEGORY_KEYWORDS.items():
        hits = sum(1 for w in words if w in text)
        if hits > best_hits:
            best_category, best_hits = category, hits
    severity = 3
    if any(w in text for w in ["danger", "dangerous", "accident", "emergency", "huge", "severe", "flooding", "overflow"]):
        severity = 5
    elif any(w in text for w in ["big", "large", "many days", "since long", "badly"]):
        severity = 4
    elif any(w in text for w in ["small", "minor", "little"]):
        severity = 2
    return best_category, severity


def groq_classify(description: str) -> tuple[str, int]:
    """Call Groq chat completions and return (category, severity).
    Raises on any failure so the caller can fall back honestly."""
    prompt = (
        "Classify this civic issue report into exactly one category from "
        f"{CATEGORIES} and rate severity 1 (minor) to 5 (dangerous/urgent). "
        'Reply with ONLY JSON like {"category": "pothole", "severity": 4}. '
        f"Report: {description}"
    )
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=15,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    category = str(data["category"]).strip().lower()
    if category not in CATEGORIES:
        raise ValueError(f"Groq returned unknown category: {category}")
    severity = max(1, min(5, int(data["severity"])))
    return category, severity


def classify(description: str) -> tuple[str, int, str]:
    """Main entry point. Returns (category, severity, source)."""
    if GROQ_API_KEY:
        try:
            category, severity = groq_classify(description)
            return category, severity, "groq"
        except Exception:
            pass  # fall through to the honest fallback below
    category, severity = keyword_classify(description)
    return category, severity, "keyword_fallback"
