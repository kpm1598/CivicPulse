"""
CivicPulse - THE ONE CONFIG FILE
=================================
Beginners: almost everything you will want to CHANGE lives in this file.
- Adding a category?          -> edit CATEGORIES, DEPARTMENT_MAP, CATEGORY_KEYWORDS, CATEGORY_WEIGHTS
- Changing a department?       -> edit DEPARTMENT_MAP
- Making priorities stricter?  -> edit CATEGORY_WEIGHTS and the numbers in app/services/priority.py
- Changing the admin key?      -> do NOT edit here, set ADMIN_KEY in your .env file (see .env.example)

Secrets (Groq key, admin key) are NEVER written in code. They come from the .env file.
"""
import os
from pathlib import Path

# --- Paths -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    """Database file. Tests override this with the CIVICPULSE_DB_PATH env var
    so tests NEVER touch the real/demo database."""
    return Path(os.getenv("CIVICPULSE_DB_PATH", PROJECT_ROOT / "civicpulse.db"))


UPLOAD_DIR = PROJECT_ROOT / "uploads"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# --- Secrets / environment (set in .env, see .env.example) -------------------
# Loaded in app/main.py from the .env file using a tiny built-in loader.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin123")  # demo-only default, change in .env

# --- Categories ---------------------------------------------------------------
# The fixed list of issue types a citizen can report.
CATEGORIES = [
    "pothole",
    "garbage",
    "streetlight",
    "water_leakage",
    "drainage",
    "other",
]

# Which city department each category is routed to.
DEPARTMENT_MAP = {
    "pothole": "Roads & Infrastructure",
    "garbage": "Sanitation",
    "streetlight": "Electricity",
    "water_leakage": "Water Supply",
    "drainage": "Drainage & Sewage",
    "other": "General Admin",
}

# Keywords for the OFFLINE fallback classifier (used when Groq is not
# configured or fails). Add words in the language your citizens actually use.
CATEGORY_KEYWORDS = {
    "pothole": ["pothole", "road damage", "broken road", "crater", "tar road", "road is damaged"],
    "garbage": ["garbage", "trash", "waste", "dump", "dumping", "litter", "overflowing bin", "rubbish"],
    "streetlight": ["streetlight", "street light", "lamp post", "light not working", "dark street", "pole light"],
    "water_leakage": ["water leakage", "water leak", "pipe burst", "pipeline", "water wasting", "leaking pipe", "tap leak"],
    "drainage": ["drainage", "drain", "sewage", "sewer", "blocked drain", "manhole", "stagnant water", "foul smell"],
    "other": [],
}

# How dangerous/urgent each category is, out of 20 points in the priority formula.
# Bigger number = authorities should look at it sooner.
CATEGORY_WEIGHTS = {
    "water_leakage": 20,
    "drainage": 18,
    "pothole": 17,
    "streetlight": 15,
    "garbage": 12,
    "other": 8,
}

# --- Priority tiers ------------------------------------------------------------
# Score ranges (0-100). See app/services/priority.py for the full formula.
PRIORITY_TIERS = [
    (75, "Critical"),
    (55, "High"),
    (35, "Medium"),
    (0, "Low"),
]

# --- Duplicate detection --------------------------------------------------------
DUPLICATE_RADIUS_METRES = 100      # within 100 metres...
DUPLICATE_WINDOW_DAYS = 30         # ...and reported within 30 days = duplicate

# --- Photo uploads ---------------------------------------------------------------
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB

# --- Valid statuses a report moves through ---------------------------------------
STATUSES = ["Reported", "Assigned", "In Progress", "Resolved"]

# --- Map default (Bengaluru city centre) ------------------------------------------
DEFAULT_LAT = 12.9716
DEFAULT_LNG = 77.5946
