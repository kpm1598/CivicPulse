// Authority dashboard: stats, charts, hotspots, reports table, admin updates.
const keyInput = document.getElementById("adminKey");
keyInput.value = localStorage.getItem("civicpulse_admin_key") || "";
document.getElementById("saveKeyBtn").onclick = () => {
  localStorage.setItem("civicpulse_admin_key", keyInput.value.trim());
  alert("Admin key saved in this browser");
};
let selectedCode = null, charts = [];
function barChart(id, dataObj, colour) {
  const el = document.getElementById(id);
  if (!el || typeof Chart === "undefined") return;
  charts.push(new Chart(el, { type: "bar",
    data: { labels: Object.keys(dataObj),
            datasets: [{ data: Object.values(dataObj), backgroundColor: colour }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } } }));
}

async function loadDashboard() {
  try {
    const s = await api("/api/stats");
    document.getElementById("statTotal").textContent = s.total;
    document.getElementById("statOpen").textContent = s.open;
    document.getElementById("statResolved").textContent = s.resolved;
    document.getElementById("statCritical").textContent = s.by_priority_tier.Critical || 0;
    charts.forEach(c => c.destroy()); charts = [];
    barChart("chartCategory", s.by_category, "#0b6e4f");
    barChart("chartStatus", s.by_status, "#f77f00");
    barChart("chartPriority", s.by_priority_tier, "#d62828");

    const hs = await api("/api/hotspots");
    document.getElementById("hotspotList").innerHTML = hs.by_locality.map(h =>
      `<p>🔥 <b>${esc(h.name)}</b> - ${h.count} reports, mostly <b>${esc(h.top_category)}</b>, avg priority ${h.avg_priority}</p>`).join("")
      || "<p class='small'>No hotspots yet.</p>";
    hs.by_grid.filter(g => g.count >= 2).forEach(g =>
      L.circle([g.lat, g.lng], { radius: 350, color: "#d62828" }).addTo(hotspotMap)
        .bindPopup(`${esc(g.name)}: ${g.count} reports`));
    loadReports();
  } catch (err) {
    const m = document.getElementById("dashMsg"); m.className = "msg error"; m.textContent = "Error: " + err.message;
  }
}
const hotspotMap = makeMap("hotspotMap");

async function loadReports() {
  const cat = document.getElementById("filterCategory").value;
  const st = document.getElementById("filterStatus").value;
  const reports = await api(`/api/reports?category=${encodeURIComponent(cat)}&status=${encodeURIComponent(st)}`);
  document.getElementById("reportsBody").innerHTML = reports.map(r =>
    `<tr class="clickable" data-code="${esc(r.code)}"><td>${esc(r.code)}</td><td>${esc(r.title)}</td>` +
    `<td>${esc(r.category)}</td><td>${esc(r.locality || "-")}</td>` +
    `<td>${badge(r.priority_tier)} ${r.priority_score}</td><td>${esc(r.status)}</td><td>${esc(r.assigned_to || "-")}</td></tr>`).join("");
  document.querySelectorAll("tr.clickable").forEach(tr =>
    tr.onclick = () => openEdit(tr.dataset.code, reports.find(r => r.code === tr.dataset.code)));
}
document.getElementById("filterCategory").onchange = loadReports;
document.getElementById("filterStatus").onchange = loadReports;

function openEdit(code, r) {
  selectedCode = code;
  document.getElementById("editPanel").style.display = "block";
  document.getElementById("editCode").textContent = code;
  document.getElementById("editStatus").value = r.status;
  document.getElementById("editAssigned").value = r.assigned_to || "";
  document.getElementById("editDept").value = r.department;
  document.getElementById("editPanel").scrollIntoView({ behavior: "smooth" });
}
document.getElementById("editSaveBtn").onclick = async () => {
  const msg = document.getElementById("editMsg"); msg.className = "msg";
  try {
    await api("/api/admin/reports/" + encodeURIComponent(selectedCode), {
      method: "PATCH",
      headers: { "Content-Type": "application/json",
                 "X-Admin-Key": localStorage.getItem("civicpulse_admin_key") || keyInput.value.trim() },
      body: JSON.stringify({ status: document.getElementById("editStatus").value,
                             assigned_to: document.getElementById("editAssigned").value,
                             department: document.getElementById("editDept").value,
                             note: document.getElementById("editNote").value }) });
    msg.className = "msg success"; msg.textContent = "Saved! Refreshing dashboard...";
    loadDashboard();
  } catch (err) { msg.className = "msg error"; msg.textContent = "Error: " + err.message + " (check your admin key)"; }
};
loadDashboard();
