"""CivicPulse tests. Uses a TEMP database - never the shipped civicpulse.db.
Groq is disabled in every test (no real API calls, ever)."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

# Point the app at a throwaway DB BEFORE importing it.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["CIVICPULSE_DB_PATH"] = _tmp.name
os.environ.pop("GROQ_API_KEY", None)

from app import main  # noqa: E402
from app.services import classifier  # noqa: E402
from app.services.duplicates import haversine_metres  # noqa: E402
from app.services.priority import calculate_priority, tier_for_score  # noqa: E402

classifier.GROQ_API_KEY = ""  # belt & braces: keyword fallback only

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clean_db():
    main.init_db()
    with main.get_db() as conn:
        conn.execute("DELETE FROM status_history")
        conn.execute("DELETE FROM reports")
    yield


# ---------------- classifier ----------------
def test_keyword_classification_categories():
    assert classifier.keyword_classify("Huge pothole on the road")[0] == "pothole"
    assert classifier.keyword_classify("Garbage and trash dumped here")[0] == "garbage"
    assert classifier.keyword_classify("Street light not working, dark street")[0] == "streetlight"
    assert classifier.keyword_classify("Water leakage from a leaking pipe")[0] == "water_leakage"
    assert classifier.keyword_classify("Blocked drain, sewage overflowing")[0] == "drainage"
    assert classifier.keyword_classify("Something completely different")[0] == "other"


def test_classifier_reports_fallback_source_honestly():
    cat, sev, source = classifier.classify("Big pothole near my house")
    assert cat == "pothole" and source == "keyword_fallback"


# ---------------- priority ----------------
def test_priority_formula_and_tiers():
    # severity 5 water leak, fresh: 50 + 20 = 70 -> High
    score, tier = calculate_priority("water_leakage", 5, 0, datetime.now(timezone.utc))
    assert score == 70 and tier == "High"
    # duplicates + age push it to Critical: 70 + 15 + 15 = 100 capped
    old = datetime.now(timezone.utc) - timedelta(days=20)
    score, tier = calculate_priority("water_leakage", 5, 3, old)
    assert score == 100 and tier == "Critical"
    # minor garbage: 20 + 12 = 32 -> Low
    score, tier = calculate_priority("garbage", 2, 0, datetime.now(timezone.utc))
    assert score == 32 and tier == "Low"
    assert tier_for_score(75) == "Critical" and tier_for_score(55) == "High"
    assert tier_for_score(35) == "Medium" and tier_for_score(34) == "Low"


# ---------------- haversine / duplicates ----------------
def test_haversine_known_distance():
    # Bengaluru centre to Koramangala is roughly 6 km
    d = haversine_metres(12.9716, 77.5946, 12.9352, 77.6245)
    assert 5000 < d < 7500
    assert haversine_metres(12.97, 77.59, 12.97, 77.59) == pytest.approx(0, abs=1)


def _create(desc, lat=12.9352, lng=77.6245, locality="Koramangala"):
    return client.post("/api/reports", data={
        "description": desc, "locality": locality, "lat": lat, "lng": lng,
        "name": "Test Citizen"})


def test_create_report_flow():
    r = _create("Huge pothole on the main road, dangerous")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "CP-0001" and body["category"] == "pothole"
    assert body["department"] == "Roads & Infrastructure"
    assert body["classification_source"] == "keyword_fallback"
    assert body["duplicate"]["is_duplicate"] is False
    assert body["status"] == "Reported"


def test_duplicate_detection_links_and_bumps_original():
    first = _create("Huge pothole on the main road, dangerous").json()
    # ~20 metres away, same category -> duplicate
    second = _create("Big pothole again at the same spot", lat=12.93535, lng=77.6246).json()
    assert second["duplicate"]["is_duplicate"] is True
    assert second["duplicate"]["duplicate_of"] == first["code"]
    original = client.get(f"/api/reports/{first['code']}").json()
    assert original["duplicate_count"] == 1
    assert original["priority_score"] > first["priority_score"]
    # far away, same category -> NOT a duplicate
    far = _create("Another pothole far away", lat=12.9698, lng=77.7500, locality="Whitefield").json()
    assert far["duplicate"]["is_duplicate"] is False


# ---------------- tracking / stats / hotspots ----------------
def test_track_and_stats_and_hotspots():
    _create("Garbage overflowing near the park")
    _create("More garbage dumped nearby", lat=12.9354, lng=77.6247)
    code = client.get("/api/reports").json()[0]["code"]
    tracked = client.get(f"/api/track/{code}")
    assert tracked.status_code == 200 and len(tracked.json()["history"]) >= 1
    assert client.get("/api/track/CP-9999").status_code == 404
    stats = client.get("/api/stats").json()
    assert stats["total"] == 2 and stats["by_category"]["garbage"] == 2
    hs = client.get("/api/hotspots").json()
    assert hs["by_locality"][0]["name"] == "Koramangala" and hs["by_locality"][0]["count"] == 2
    assert len(hs["by_grid"]) >= 1
    nearby = client.get("/api/nearby", params={"lat": 12.9352, "lng": 77.6245, "radius_km": 1}).json()
    assert len(nearby) == 2


# ---------------- admin PATCH ----------------
def test_admin_patch_requires_key_and_updates():
    code = _create("Street light not working in our area").json()["code"]
    # no key -> 401
    r = client.patch(f"/api/admin/reports/{code}", json={"status": "Assigned"})
    assert r.status_code == 401
    # wrong key -> 401
    r = client.patch(f"/api/admin/reports/{code}", json={"status": "Assigned"},
                     headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 401
    # right key (demo default admin123) -> works, history grows
    r = client.patch(f"/api/admin/reports/{code}",
                     json={"status": "In Progress", "assigned_to": "Vikram R.", "note": "Team sent"},
                     headers={"X-Admin-Key": "admin123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "In Progress" and body["assigned_to"] == "Vikram R."
    assert len(body["history"]) >= 2
    # bad status -> 400
    r = client.patch(f"/api/admin/reports/{code}", json={"status": "Nonsense"},
                     headers={"X-Admin-Key": "admin123"})
    assert r.status_code == 400
