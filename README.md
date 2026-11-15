# CivicPulse – AI-Powered Smart City Issue Management Platform

Citizens report civic problems (potholes, garbage, broken streetlights, water
leakage, drainage blockages) with a photo, description and map location.
CivicPulse classifies each report, routes it to the right department, scores
its priority, flags duplicates, and shows authorities a live dashboard with
hotspots and analytics.

**Stack:** HTML/CSS/JS frontend (served by the backend itself) · Python
FastAPI backend · SQLite database · Groq AI (optional) · Leaflet +
OpenStreetMap maps · Chart.js analytics. **No Docker, no build step, ₹0 to run.**

---

## Run it on Windows (exact commands)

Open PowerShell **inside the extracted CivicPulse folder** (the folder that
contains this README), then:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
py seed_demo.py
py -m uvicorn app.main:app --port 8000
```

Then open in your browser:

| Page | URL |
|---|---|
| Citizen page (report + map + track) | http://127.0.0.1:8000/ |
| Authority dashboard | http://127.0.0.1:8000/authority |
| API docs (Swagger) | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/api/health |

- **Demo admin key:** `admin123` (type it into the Authority Dashboard to
  make changes). It is a demo default only — change `ADMIN_KEY` in `.env`
  before any public demo.
- `py seed_demo.py` loads 18 demo reports around Bengaluru. Warning: re-running
  it clears existing reports first. Skip it if you want an empty database.
- Or just double-click `run_civicpulse.bat` after the one-time setup above.
- Stop the server with `Ctrl+C`.

## How classification works (honest version)

1. If `GROQ_API_KEY` is set in `.env`, the backend sends the description to
   Groq and asks for a category + severity as JSON.
2. On **any** failure — no key, no internet, Groq error — it automatically
   falls back to a keyword classifier in `app/services/classifier.py`.
3. Every report response says which one actually ran:
   `classification_source` is `"groq"` or `"keyword_fallback"`. The demo
   **never dies** because Groq is down, and never pretends Groq ran when it didn't.

To use Groq: create a free key at https://console.groq.com, put it in `.env`
as `GROQ_API_KEY=...`, restart the server. The key is read **only** by the
backend and is never sent to the browser.

## How priority works (the formula judges will ask about)

Defined in ONE place — `app/services/priority.py`:

```
score = severity × 10            (severity 1–5  → 10–50 points)
      + category weight          (8–20 points, in app/config.py)
      + duplicate bonus          (duplicates × 5, max 15)
      + age bonus                (days open × 1.5, max 15)
      clamped to 0–100
Tiers: ≥75 Critical · ≥55 High · ≥35 Medium · <35 Low
```

**Departments:** pothole → Roads & Infrastructure · garbage → Sanitation ·
streetlight → Electricity · water_leakage → Water Supply ·
drainage → Drainage & Sewage · other → General Admin.

**Duplicates:** a new report with the same category, within 100 m, within
30 days, of an open report is stored but linked to the original
(`duplicate_of`). The original's duplicate count rises and its priority is
recomputed — many citizens reporting one problem makes it more urgent,
not a longer queue.

## Project structure (small on purpose)

```
app/config.py              ← THE one place for categories, keywords,
                             departments, weights, thresholds
app/main.py                ← all API routes + serving the frontend
app/database.py            ← SQLite tables (reports, status_history)
app/services/classifier.py ← Groq + keyword fallback classification
app/services/priority.py   ← the priority formula (documented at the top)
app/services/duplicates.py ← haversine distance + duplicate rule
frontend/index.html        ← citizen page      frontend/authority.html ← dashboard
frontend/css/style.css     ← shared styles     frontend/js/*.js ← page logic
seed_demo.py               ← demo data generator
tests/test_civicpulse.py   ← pytest suite (temp DB, Groq never called)
uploads/                   ← citizen photos are saved here (max 5 MB, images only)
```

See **EDIT_GUIDE.md** for exactly what to change to customise the project.

## Run the tests (optional, skippable on demo day)

```powershell
py -m pytest tests/ -q
```
Tests use a temporary database and never call the real Groq API.

## API quick reference

| Endpoint | What it does |
|---|---|
| `POST /api/reports` | Create a report (multipart: description, photo, lat, lng, locality, name, phone) |
| `GET /api/reports?category=&status=&locality=&min_priority=` | List/filter reports |
| `GET /api/reports/{code}` / `GET /api/track/{code}` | One report + status timeline |
| `GET /api/nearby?lat=&lng=&radius_km=` | Reports near a point |
| `GET /api/hotspots` | Hotspots by locality and by map grid |
| `GET /api/stats` | Totals + by category / status / tier / locality (for charts) |
| `PATCH /api/admin/reports/{code}` | Authority update — needs header `X-Admin-Key` |
