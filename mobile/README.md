# CivicPulse Mobile Apps (Capacitor, Android)

Two Android apps built from the same CivicPulse web frontend with Capacitor.
Both talk to the ONE live backend — no second server:

**Backend:** https://civicpulse-nkwc.onrender.com (Render free tier)
The backend allows cross-origin calls (CORS) because the apps run inside a
WebView on https://localhost. Free tier sleeps when idle — the first request
after a quiet period can take ~50 seconds. Open the demo link once before
presenting.

| App | Folder | App ID | Starts on |
|---|---|---|---|
| CivicPulse Citizen | `citizen/` | com.kasim.civicpulse.citizen | Report an issue, map, track complaint |
| CivicPulse Authority | `authority/` | com.kasim.civicpulse.authority | Dashboard, priority queue, hotspots (demo admin key `admin123`) |

## Build an APK on Windows (Android Studio — no Node needed)

The delivered zips already contain the generated `android/` project with the
web app synced inside. Node is NOT needed for this path:

1. Extract the app's zip to its own folder, e.g. `C:\Users\patel\Downloads\CivicPulseCitizen`
2. Android Studio → **Open** → select the **`android`** folder inside it
3. Wait for Gradle Sync to finish (first time downloads Gradle + SDK bits)
4. Connect the phone with USB debugging ON, pick it as the run device, press **Run ▶**
   — or **Build → Build App Bundle(s) / APK(s) → Build APK(s)** and copy
   `android\app\build\outputs\apk\debug\app-debug.apk` to the phone and install it.

## If you change the web code (developers)

Edit `www/`, then from the app folder in PowerShell:

```powershell
npm install
npx cap sync android
```

That copies the new `www/` into the Android project; rebuild in Studio after.

## Honest limits (v1)

- Login & signup are NOT in this version — citizens track reports with the
  tracking code (e.g. CP-0001), authorities use the shared demo admin key.
  User accounts (users table + JWT) are the planned next backend step.
- Photo upload uses the file picker (gallery/camera choice comes from Android).
- "Use my location" uses the WebView geolocation with the location permissions
  declared in AndroidManifest — verify on the real phone on first run.
- The apps need internet (backend, maps and charts are online by design).
