# EDIT GUIDE – how a beginner changes CivicPulse

Almost every common change is in **one file: `app/config.py`**.
Edit, save, restart the server (`Ctrl+C`, then run the uvicorn command again).

## 1. Add a new category (e.g. "footpath")

In `app/config.py`, add the word in FOUR places, using the same spelling:
1. `CATEGORIES` — add `"footpath",`
2. `DEPARTMENT_MAP` — add `"footpath": "Roads & Infrastructure",`
3. `CATEGORY_KEYWORDS` — add `"footpath": ["footpath", "broken footpath", "pavement"],`
4. `CATEGORY_WEIGHTS` — add `"footpath": 10,`

Then also add it to the two dropdowns so people can filter by it:
- `frontend/authority.html` → the "Filter by category" `<select>`
- (Optional) the department `<select>` in the same file, if it's a new department.

## 2. Change which department gets a category

`app/config.py` → `DEPARTMENT_MAP`. Change the text on the right side only,
e.g. `"garbage": "Sanitation"` → `"garbage": "City Cleanliness Cell"`.
If it's a brand-new department name, also add it to the department dropdown
in `frontend/authority.html`.

## 3. Change priority behaviour

- Make one category more urgent: `app/config.py` → `CATEGORY_WEIGHTS`
  (bigger number = higher priority, max sensible ~20).
- Change the overall formula (severity, duplicate, or age points) or the
  tier cut-offs (75/55/35): `app/services/priority.py` — the formula is
  explained in plain English at the top of that file, and the tier list is
  `PRIORITY_TIERS` in `app/config.py`.
- After changing this, run `py -m pytest tests/ -q` — the priority test will
  tell you if your new numbers changed the expected examples.

## 4. Change the project name, logo, or colours

- Name/logo text: search for `CivicPulse` in `frontend/index.html` and
  `frontend/authority.html` (the `<header>` at the top) and replace it.
  Also change `<title>` in both files.
- Colours: `frontend/css/style.css`, right at the top — `--brand`,
  `--brand-dark`, `--accent`, and the four priority colours
  (`--critical`, `--high`, `--medium`, `--low`). Nothing else needs touching.

## 5. Change the admin key

In your `.env` file (not in any code): set `ADMIN_KEY=your-own-word`.
Restart the server. Type the same word into the Authority Dashboard.
The demo default is `admin123` — never use it for a public demo.

## 6. Add your Groq API key (optional AI)

1. Get a free key at https://console.groq.com
2. In `.env`: `GROQ_API_KEY=paste-your-key-here`
3. Restart the server. New reports will show classification source `groq`.
   Remove the key (leave it empty) to go back to the offline keyword
   classifier. **Never** put the key in frontend files or on GitHub.

## 7. Change the duplicate rule or map centre

- Duplicate distance/days: `app/config.py` → `DUPLICATE_RADIUS_METRES`
  and `DUPLICATE_WINDOW_DAYS`.
- Default map city: `app/config.py` → `DEFAULT_LAT` / `DEFAULT_LNG`, and
  `BENGALURU` at the top of `frontend/js/common.js`.

## 8. Add seed/demo areas

`seed_demo.py` → the `SEEDS` list. Copy any line, change the text,
locality and lat/lng. Re-run `py seed_demo.py` (it clears old reports first).
