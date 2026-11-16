// CivicPulse shared helpers - used by every page.
const TIER_COLOURS = { Critical: "#d62828", High: "#f77f00", Medium: "#e9c400", Low: "#2a9d8f" };
const BENGALURU = [12.9716, 77.5946]; // default map centre

// MOBILE BUILD: the app runs inside a Capacitor WebView (https://localhost),
// so API calls must go to the live Render backend, not a relative path.
const API_BASE = "https://civicpulse-nkwc.onrender.com";
function mediaUrl(p) { return p && p.startsWith("/") ? API_BASE + p : p; }
async function api(path, options = {}) {
  const res = await fetch(path.startsWith("http") ? path : API_BASE + path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) { /* keep status text */ }
    throw new Error(detail);
  }
  return res.json();
}
function badge(tier) { return `<span class="badge ${tier}">${tier}</span>`; }
function esc(s) { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; }
function makeMap(id) {
  const map = L.map(id).setView(BENGALURU, 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { attribution: "© OpenStreetMap contributors" }).addTo(map);
  return map;
}
function markerFor(map, r) {
  return L.circleMarker([r.lat, r.lng],
    { radius: 9, color: TIER_COLOURS[r.priority_tier] || "#333",
      fillColor: TIER_COLOURS[r.priority_tier] || "#333", fillOpacity: 0.85 })
    .addTo(map)
    .bindPopup(`<b>${esc(r.code)}</b> - ${esc(r.category)}<br>${esc(r.title)}<br>` +
               `Priority: ${r.priority_score} (${esc(r.priority_tier)})<br>Status: ${esc(r.status)}`);
}
