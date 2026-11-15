"""
Seed demo data: 18 realistic Bengaluru reports so charts, maps, hotspots
and priorities look real in a demo.

Run:  py seed_demo.py
WARNING: this CLEARS all existing reports and re-creates the demo set.
Photos: seed rows have photo_path = None on purpose - we never invent files.
"""
from datetime import datetime, timedelta, timezone

from app.database import get_db, init_db
from app.services.priority import calculate_priority

NOW = datetime.now(timezone.utc)

# (days_ago, title, description, category, department, severity, status,
#  locality, lat, lng, assigned_to)
SEEDS = [
    (9, "Huge pothole near bus stop", "Huge pothole on the main road, dangerous for bikes, accident almost happened yesterday", "pothole", "Roads & Infrastructure", 5, "In Progress", "Jayanagar", 12.9299, 77.5833, "Ramesh K."),
    (8, "Same pothole reported again", "Big pothole near Jayanagar bus stop, water filled, very dangerous", "pothole", "Roads & Infrastructure", 5, "Reported", "Jayanagar", 12.92995, 77.58335, None),  # duplicate of #1 (~7 m away)
    (7, "Road damaged after rain", "Road is damaged badly near the signal, tar has washed away", "pothole", "Roads & Infrastructure", 4, "Assigned", "Banashankari", 12.9081, 77.5755, "Suresh M."),
    (2, "Crater in middle of road", "Deep crater in middle of the road near metro pillar", "pothole", "Roads & Infrastructure", 4, "Reported", "Whitefield", 12.9698, 77.7500, None),
    (6, "Garbage overflowing for many days", "Garbage dump overflowing since long, foul smell, stray dogs everywhere", "garbage", "Sanitation", 4, "In Progress", "Koramangala", 12.9352, 77.6245, "Anita S."),
    (5, "Waste dumped on footpath", "People dumping waste and trash on the footpath, no bin available", "garbage", "Sanitation", 3, "Reported", "Koramangala", 12.9356, 77.6249, None),
    (4, "Overflowing bin near park", "Overflowing bin and garbage scattered near the park entrance", "garbage", "Sanitation", 3, "Assigned", "Koramangala", 12.9348, 77.6241, "Anita S."),
    (1, "Garbage not collected", "Garbage and litter near apartment gate, not collected for 3 days", "garbage", "Sanitation", 3, "Reported", "Koramangala", 12.9360, 77.6253, None),
    (3, "Rubbish near market", "Rubbish dump growing near vegetable market, flies everywhere", "garbage", "Sanitation", 3, "Resolved", "Indiranagar", 12.9784, 77.6408, "Anita S."),
    (8, "Street light not working", "Street light not working, dark street at night, unsafe for women walking home", "streetlight", "Electricity", 4, "Assigned", "Indiranagar", 12.9789, 77.6412, "Vikram R."),
    (2, "Lamp post broken", "Lamp post light not working near the school gate", "streetlight", "Electricity", 3, "Reported", "Jayanagar", 12.9305, 77.5840, None),
    (5, "Dark street, no lights", "Whole street light system off, dark street for a week", "streetlight", "Electricity", 4, "In Progress", "Banashankari", 12.9086, 77.5760, "Vikram R."),
    (9, "Pipe burst, water wasting", "Pipe burst on main road, water leakage wasting thousands of litres, flooding the road", "water_leakage", "Water Supply", 5, "In Progress", "Koramangala", 12.9345, 77.6238, "Deepak N."),
    (6, "Leaking pipe near house", "Water leaking pipe near our house, continuous water wasting since 4 days", "water_leakage", "Water Supply", 4, "Assigned", "Whitefield", 12.9703, 77.7505, "Deepak N."),
    (1, "Tap leak in park", "Small tap leak in the park, minor water leakage", "water_leakage", "Water Supply", 2, "Reported", "Jayanagar", 12.9295, 77.5828, None),
    (7, "Blocked drain, sewage overflow", "Blocked drain and sewage overflowing, stagnant water, foul smell, emergency near homes", "drainage", "Drainage & Sewage", 5, "In Progress", "Koramangala", 12.9359, 77.6250, "Manjunath H."),
    (4, "Drainage blocked after rain", "Drainage blocked, manhole open, stagnant water on the road", "drainage", "Drainage & Sewage", 4, "Reported", "Indiranagar", 12.9779, 77.6403, None),
    (3, "Open manhole danger", "Manhole cover missing near footpath, drainage visible, dangerous", "drainage", "Drainage & Sewage", 5, "Resolved", "Banashankari", 12.9076, 77.5750, "Manjunath H."),
]


def main():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM status_history")
        conn.execute("DELETE FROM reports")
        # Restart complaint codes at CP-0001 for a clean demo database
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('reports', 'status_history')")
        # Pass 1: insert all rows (duplicate link fixed in pass 2, needs row 1's code)
        codes = []
        for days_ago, title, desc, cat, dept, sev, status, loc, lat, lng, assigned in SEEDS:
            created = (NOW - timedelta(days=days_ago)).isoformat()
            row = conn.execute("SELECT COALESCE(MAX(id),0) AS m FROM reports").fetchone()
            code = f"CP-{row['m'] + 1:04d}"
            codes.append(code)
            score, tier = calculate_priority(cat, sev, 0, created)
            conn.execute(
                """INSERT INTO reports (code, title, description, category, department,
                   severity, priority_score, priority_tier, status, citizen_name,
                   citizen_phone, locality, lat, lng, photo_path, duplicate_of,
                   duplicate_count, assigned_to, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?, ?, ?, 'Demo Citizen', NULL, ?,?,?, NULL, NULL, 0, ?, ?, ?)""",
                (code, title, desc, cat, dept, sev, score, tier, status, loc, lat, lng,
                 assigned, created, created))
            conn.execute(
                "INSERT INTO status_history (report_code, status, note, changed_by, created_at) VALUES (?,?,?,?,?)",
                (code, "Reported", "Report submitted (demo seed)", "citizen", created))
            if status != "Reported":
                conn.execute(
                    "INSERT INTO status_history (report_code, status, note, changed_by, created_at) VALUES (?,?,?,?,?)",
                    (code, status, f"Status updated to {status} (demo seed)", "authority", created))
        # Pass 2: report #2 is a duplicate of #1 (index 1 -> index 0)
        conn.execute("UPDATE reports SET duplicate_of=? WHERE code=?", (codes[0], codes[1]))
        orig = conn.execute("SELECT * FROM reports WHERE code=?", (codes[0],)).fetchone()
        score, tier = calculate_priority(orig["category"], orig["severity"], 1, orig["created_at"])
        conn.execute(
            "UPDATE reports SET duplicate_count=1, priority_score=?, priority_tier=? WHERE code=?",
            (score, tier, codes[0]))
        total = conn.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"]
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS c FROM reports GROUP BY status").fetchall()
    print(f"Seeded {total} demo reports.")
    for r in by_status:
        print(f"  {r['status']}: {r['c']}")


if __name__ == "__main__":
    main()
