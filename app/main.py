"""
CivicPulse - FastAPI backend.
Serves BOTH the API (/api/...) and the frontend pages (same origin, so the
browser never hits CORS problems).

Run it with:  uvicorn app.main:app --reload --port 8000
Then open:    http://127.0.0.1:8000/            (citizen page)
              http://127.0.0.1:8000/authority   (authority dashboard)
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- Load .env BEFORE reading any config (Groq key / admin key live there) ---
def _load_dotenv():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import config  # noqa: E402
from app.config import ADMIN_KEY, ALLOWED_PHOTO_EXTENSIONS, DEPARTMENT_MAP, MAX_PHOTO_BYTES, STATUSES  # noqa: E402
from app.database import get_db, init_db, next_code, row_to_dict  # noqa: E402
from app.services.classifier import classify  # noqa: E402
from app.services.duplicates import find_original, haversine_metres  # noqa: E402
from app.services.priority import calculate_priority  # noqa: E402

app = FastAPI(title="CivicPulse")

# --- CORS: the web pages are same-origin (no CORS needed), but the Capacitor
# mobile apps run on https://localhost inside the WebView and call this API
# cross-origin. Demo scope: allow all origins; tighten before production use.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


init_db()  # create tables on start-up (also safe to call again later)


# --------------------------------------------------------------------------- #
#  Create a report (citizen)
# --------------------------------------------------------------------------- #
@app.post("/api/reports")
async def create_report(
    description: str = Form(...),
    title: str = Form(""),
    locality: str = Form(""),
    lat: float = Form(None),
    lng: float = Form(None),
    name: str = Form(""),
    phone: str = Form(""),
    photo: UploadFile = File(None),
):
    description = description.strip()
    if not description:
        raise HTTPException(400, "Description is required")

    # 1) Save the photo first (if one was sent). Never invent a photo path.
    photo_path = None
    if photo is not None and photo.filename:
        ext = Path(photo.filename).suffix.lower()
        if ext not in ALLOWED_PHOTO_EXTENSIONS:
            raise HTTPException(400, f"Photo must be one of: {sorted(ALLOWED_PHOTO_EXTENSIONS)}")
        data = await photo.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(400, "Photo is larger than 5 MB")
        config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{ext}"
        (config.UPLOAD_DIR / filename).write_bytes(data)
        photo_path = f"/uploads/{filename}"

    # 2) Classify -> department -> priority (Groq, else keyword fallback)
    category, severity, source = classify(description)
    department = DEPARTMENT_MAP[category]
    created = now_iso()
    score, tier = calculate_priority(category, severity, 0, created)

    # 3) Save, checking for a duplicate of an existing open report
    with get_db() as conn:
        init_db()
        original = find_original(conn, category, lat, lng)
        code = next_code(conn)
        conn.execute(
            """INSERT INTO reports (code, title, description, category, department,
               severity, priority_score, priority_tier, status, citizen_name,
               citizen_phone, locality, lat, lng, photo_path, duplicate_of,
               duplicate_count, assigned_to, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?, 'Reported', ?,?,?,?,?,?, ?, 0, NULL, ?, ?)""",
            (code, title.strip() or description[:60], description, category, department,
             severity, score, tier, name or None, phone or None, locality or None,
             lat, lng, photo_path, original["code"] if original else None, created, created),
        )
        conn.execute(
            "INSERT INTO status_history (report_code, status, note, changed_by, created_at) VALUES (?,?,?,?,?)",
            (code, "Reported", "Report submitted by citizen", "citizen", created),
        )
        # 4) If duplicate: bump the original's count and recompute its priority
        if original:
            new_count = original["duplicate_count"] + 1
            o_score, o_tier = calculate_priority(
                original["category"], original["severity"], new_count, original["created_at"])
            conn.execute(
                "UPDATE reports SET duplicate_count=?, priority_score=?, priority_tier=?, updated_at=? WHERE code=?",
                (new_count, o_score, o_tier, created, original["code"]),
            )
        row = conn.execute("SELECT * FROM reports WHERE code=?", (code,)).fetchone()

    result = row_to_dict(row)
    result["classification_source"] = source
    result["duplicate"] = {
        "is_duplicate": original is not None,
        "duplicate_of": original["code"] if original else None,
    }
    return result


# --------------------------------------------------------------------------- #
#  Read reports
# --------------------------------------------------------------------------- #
@app.get("/api/reports")
def list_reports(category: str = "", status: str = "", locality: str = "", min_priority: int = 0):
    init_db()
    sql, params = "SELECT * FROM reports WHERE priority_score >= ?", [min_priority]
    if category:
        sql, params = sql + " AND category=?", params + [category]
    if status:
        sql, params = sql + " AND status=?", params + [status]
    if locality:
        sql, params = sql + " AND locality LIKE ?", params + [f"%{locality}%"]
    sql += " ORDER BY priority_score DESC, created_at DESC"
    with get_db() as conn:
        return [row_to_dict(r) for r in conn.execute(sql, params).fetchall()]


def _get_report_or_404(conn, code: str):
    row = conn.execute("SELECT * FROM reports WHERE code=?", (code,)).fetchone()
    if row is None:
        raise HTTPException(404, f"No report found with code {code}")
    result = row_to_dict(row)
    history = conn.execute(
        "SELECT * FROM status_history WHERE report_code=? ORDER BY created_at, id", (code,)).fetchall()
    result["history"] = [row_to_dict(h) for h in history]
    return result


@app.get("/api/reports/{code}")
def get_report(code: str):
    init_db()
    with get_db() as conn:
        return _get_report_or_404(conn, code)


@app.get("/api/track/{code}")
def track_report(code: str):
    """Same as get_report - a friendly name for the citizen tracking page."""
    return get_report(code)


@app.get("/api/nearby")
def nearby(lat: float, lng: float, radius_km: float = 2.0):
    init_db()
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reports WHERE lat IS NOT NULL AND lng IS NOT NULL").fetchall()
    results = []
    for r in rows:
        d_km = haversine_metres(lat, lng, r["lat"], r["lng"]) / 1000.0
        if d_km <= radius_km:
            item = row_to_dict(r)
            item["distance_km"] = round(d_km, 2)
            results.append(item)
    return sorted(results, key=lambda x: x["distance_km"])


@app.get("/api/hotspots")
def hotspots():
    """Areas with the most reports, grouped two ways:
    1) by the locality text citizens typed, 2) by a rounded lat/lng grid."""
    init_db()
    with get_db() as conn:
        # --- grouping 1: by locality name ---
        by_locality = []
        for r in conn.execute(
                "SELECT locality AS name, COUNT(*) AS count, AVG(priority_score) AS avg_p "
                "FROM reports WHERE locality IS NOT NULL AND locality != '' "
                "GROUP BY locality ORDER BY count DESC").fetchall():
            top = conn.execute(
                "SELECT category FROM reports WHERE locality=? GROUP BY category "
                "ORDER BY COUNT(*) DESC LIMIT 1", (r["name"],)).fetchone()
            by_locality.append({"name": r["name"], "count": r["count"],
                                "top_category": top["category"] if top else None,
                                "avg_priority": round(r["avg_p"] or 0, 1)})
        # --- grouping 2: by map grid (lat/lng rounded to 2 decimals ~ 1 km) ---
        by_grid = []
        for r in conn.execute(
                "SELECT ROUND(lat,2) AS glat, ROUND(lng,2) AS glng, COUNT(*) AS count, "
                "AVG(priority_score) AS avg_p FROM reports WHERE lat IS NOT NULL "
                "GROUP BY glat, glng ORDER BY count DESC").fetchall():
            top = conn.execute(
                "SELECT category FROM reports WHERE ROUND(lat,2)=? AND ROUND(lng,2)=? "
                "GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1",
                (r["glat"], r["glng"])).fetchone()
            by_grid.append({"name": f"Area near {r['glat']}, {r['glng']}",
                            "lat": r["glat"], "lng": r["glng"], "count": r["count"],
                            "top_category": top["category"] if top else None,
                            "avg_priority": round(r["avg_p"] or 0, 1)})
    return {"by_locality": by_locality, "by_grid": by_grid}


def _counts(conn, column: str) -> dict:
    """Helper for /api/stats: {'pothole': 4, 'garbage': 3, ...}"""
    return {str(r[column]): r["c"] for r in conn.execute(
        f"SELECT {column}, COUNT(*) AS c FROM reports WHERE {column} IS NOT NULL "
        f"GROUP BY {column}").fetchall()}


@app.get("/api/stats")
def stats():
    """Everything the authority dashboard charts need, in one call."""
    init_db()
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
        resolved = conn.execute(
            "SELECT COUNT(*) AS c FROM reports WHERE status='Resolved'").fetchone()["c"]
        by_tier = _counts(conn, "priority_tier")
        for tier in ("Critical", "High", "Medium", "Low"):
            by_tier.setdefault(tier, 0)
        return {"total": total, "resolved": resolved, "open": total - resolved,
                "by_category": _counts(conn, "category"),
                "by_status": _counts(conn, "status"),
                "by_priority_tier": by_tier,
                "by_locality": _counts(conn, "locality")}


# --------------------------------------------------------------------------- #
#  Authority updates
# --------------------------------------------------------------------------- #
class AdminUpdate(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    department: str | None = None
    note: str | None = None


@app.patch("/api/admin/reports/{code}")
def admin_update(code: str, body: AdminUpdate, x_admin_key: str = Header("")):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(401, "Wrong or missing admin key (send header X-Admin-Key)")
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(400, f"Status must be one of: {STATUSES}")
    init_db()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reports WHERE code=?", (code,)).fetchone()
        if row is None:
            raise HTTPException(404, f"No report found with code {code}")
        new_status = body.status or row["status"]
        conn.execute(
            "UPDATE reports SET status=?, assigned_to=?, department=?, updated_at=? WHERE code=?",
            (new_status, body.assigned_to if body.assigned_to is not None else row["assigned_to"],
             body.department or row["department"], now_iso(), code))
        conn.execute(
            "INSERT INTO status_history (report_code, status, note, changed_by, created_at) VALUES (?,?,?,?,?)",
            (code, new_status, body.note or f"Updated by authority (status: {new_status})",
             "authority", now_iso()))
        return _get_report_or_404(conn, code)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "CivicPulse"}


# --------------------------------------------------------------------------- #
#  Frontend pages + uploaded photos (same origin)
# --------------------------------------------------------------------------- #
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")


@app.get("/")
def citizen_page():
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/authority")
def authority_page():
    return FileResponse(config.FRONTEND_DIR / "authority.html")


@app.get("/authority.html")
def authority_page_html():
    return FileResponse(config.FRONTEND_DIR / "authority.html")
