// Citizen page logic: report form, map pin, nearby issues, tracking.
let pin = null;
const map = makeMap("map");
map.on("click", e => setPin(e.latlng.lat, e.latlng.lng));
function setPin(lat, lng) {
  document.getElementById("lat").value = lat.toFixed(6);
  document.getElementById("lng").value = lng.toFixed(6);
  if (pin) pin.setLatLng([lat, lng]); else pin = L.marker([lat, lng]).addTo(map);
}
document.getElementById("locateBtn").onclick = () => {
  if (!navigator.geolocation) return alert("Geolocation is not supported in this browser");
  navigator.geolocation.getCurrentPosition(
    p => { setPin(p.coords.latitude, p.coords.longitude); map.setView([p.coords.latitude, p.coords.longitude], 15); },
    () => alert("Could not get your location - please click the map instead"));
};

// ---- submit a report ----
document.getElementById("reportForm").addEventListener("submit", async e => {
  e.preventDefault();
  const msg = document.getElementById("formMsg"), btn = document.getElementById("submitBtn");
  msg.className = "msg"; document.getElementById("successPanel").style.display = "none";
  btn.disabled = true; btn.textContent = "Submitting...";
  try {
    const fd = new FormData();
    fd.append("description", document.getElementById("description").value);
    fd.append("locality", document.getElementById("locality").value);
    fd.append("name", document.getElementById("name").value);
    fd.append("phone", document.getElementById("phone").value);
    const lat = document.getElementById("lat").value, lng = document.getElementById("lng").value;
    if (lat) fd.append("lat", lat); if (lng) fd.append("lng", lng);
    const photo = document.getElementById("photo").files[0];
    if (photo) fd.append("photo", photo);
    const r = await api("/api/reports", { method: "POST", body: fd });
    const panel = document.getElementById("successPanel");
    panel.style.display = "block";
    panel.innerHTML = `✅ <b>Report saved!</b> Your complaint code is <b>${esc(r.code)}</b> - save it to track your issue.<br>` +
      `Detected category: <b>${esc(r.category)}</b> (source: ${esc(r.classification_source)})<br>` +
      `Department: <b>${esc(r.department)}</b> &nbsp; Priority: ${badge(r.priority_tier)} ${r.priority_score}/100` +
      (r.duplicate.is_duplicate
        ? `<br>🔁 This looks like a duplicate of <b>${esc(r.duplicate.duplicate_of)}</b> - we linked it and raised that report's priority instead of creating a separate queue.`
        : "");
    e.target.reset(); loadIssues();
  } catch (err) { msg.className = "msg error"; msg.textContent = "Error: " + err.message; }
  btn.disabled = false; btn.textContent = "Submit report";
});

// ---- nearby / all issues map + list ----
const nearbyMap = makeMap("nearbyMap");
async function loadIssues() {
  try {
    const reports = await api("/api/reports");
    document.getElementById("issueList").innerHTML = reports.slice(0, 10).map(r =>
      `<p>${badge(r.priority_tier)} <b>${esc(r.code)}</b> ${esc(r.title)} <span class="small">(${esc(r.category)} - ${esc(r.locality || "")} - ${esc(r.status)})</span></p>`).join("")
      || "<p class='small'>No reports yet - be the first to report one!</p>";
    reports.filter(r => r.lat && r.lng).forEach(r => markerFor(nearbyMap, r));
  } catch (e) { /* map stays empty if API is down */ }
}
loadIssues();

// ---- tracking ----
document.getElementById("trackBtn").onclick = async () => {
  const code = document.getElementById("trackCode").value.trim().toUpperCase();
  const box = document.getElementById("trackResult"), msg = document.getElementById("trackMsg");
  msg.className = "msg"; box.innerHTML = "";
  if (!code) return;
  try {
    const r = await api("/api/track/" + encodeURIComponent(code));
    box.innerHTML = `<h3>${esc(r.code)} - ${esc(r.title)}</h3>
      <p>Category: <b>${esc(r.category)}</b> | Department: <b>${esc(r.department)}</b> | Status: <b>${esc(r.status)}</b><br>
      Priority: ${badge(r.priority_tier)} ${r.priority_score}/100 | Locality: ${esc(r.locality || "-")}` +
      (r.duplicate_of ? `<br>🔁 Duplicate of ${esc(r.duplicate_of)}` : "") +
      (r.photo_path ? `<br><img src="${esc(mediaUrl(r.photo_path))}" style="max-width:280px;border-radius:8px">` : "") +
      `</p><div class="timeline">` +
      r.history.map(h => `<div><b>${esc(h.status)}</b> <span class="small">${esc(h.created_at.slice(0, 16).replace("T", " "))} - ${esc(h.note || "")}</span></div>`).join("") +
      `</div>`;
  } catch (err) { msg.className = "msg error"; msg.textContent = "Error: " + err.message; }
};
