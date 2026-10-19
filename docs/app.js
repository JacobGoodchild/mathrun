/* mathrun dashboard - plain JavaScript, no external libraries.
 * Reads status/index.json and status/<slug>.json. */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function getJSON(path) {
  const r = await fetch(path + "?t=" + Date.now(), { cache: "no-store" });
  if (!r.ok) throw new Error(path + ": " + r.status);
  return r.json();
}

function fmtNum(x) {
  if (x == null || x === "") return "–";
  const n = Number(x);
  if (!isFinite(n)) return String(x);
  const a = Math.abs(n);
  if (a >= 1e15) return n.toExponential(2).replace("e+", "×10^");
  if (a >= 1e12) return (n / 1e12).toFixed(2) + " T";
  if (a >= 1e9) return (n / 1e9).toFixed(2) + " B";
  if (a >= 1e6) return (n / 1e6).toFixed(2) + " M";
  if (a >= 1e4) return (n / 1e3).toFixed(1) + " k";
  if (Number.isInteger(n)) return String(n);
  return n.toPrecision(3);
}
function fmtHours(h) {
  if (!h) return "0 h";
  if (h < 1) return Math.round(h * 60) + " min";
  return h < 100 ? h.toFixed(1) + " h" : Math.round(h) + " h";
}
function ago(t) {
  if (!t) return "never";
  const s = Math.max(0, Date.now() / 1000 - t);
  if (s < 90) return Math.round(s) + "s ago";
  if (s < 5400) return Math.round(s / 60) + " min ago";
  if (s < 172800) return (s / 3600).toFixed(1) + " h ago";
  return Math.round(s / 86400) + " days ago";
}
function when(t) { return t ? new Date(t * 1000).toLocaleString() : "–"; }

const CAT = { "Number theory": "--cat-number", "Geometry and combinatorics": "--cat-geometry",
  "Combinatorics": "--cat-geometry", "Geometry": "--cat-geometry",
  "Graph theory and design theory": "--cat-graph", "Design theory": "--cat-graph",
  "Computer science": "--cat-cs" };

function statePill(state) {
  const s = state || "idle";
  let cls = "idle";
  if (s === "running") cls = "good";
  else if (s.startsWith("paused: possible") || s.startsWith("stopped")) cls = "bad";
  else if (s.startsWith("paused")) cls = "warn";
  return `<span class="pill ${cls}">${esc(s)}</span>`;
}

/* ---------- charts ---------- */
function series(hist, key) {
  return (hist || []).filter((p) => p[key] != null && isFinite(Number(p[key])))
    .map((p) => [p.t, Number(p[key])]);
}

function sparkline(pts) {
  if (pts.length < 2) return `<svg class="spark" viewBox="0 0 300 44" role="img" aria-label="no history yet">
    <line x1="0" y1="40" x2="300" y2="40" stroke="var(--grid)" stroke-width="2"/></svg>`;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const X = (x) => 2 + ((x - x0) / (x1 - x0 || 1)) * 296;
  const Y = (y) => 40 - ((y - y0) / (y1 - y0 || 1)) * 34;
  const d = pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1)).join(" ");
  return `<svg class="spark" viewBox="0 0 300 44" preserveAspectRatio="none" role="img" aria-label="progress over time">
    <path d="${d} L${X(x1).toFixed(1)} 42 L${X(x0).toFixed(1)} 42 Z" fill="var(--series-1-fill)"/>
    <path d="${d}" fill="none" stroke="var(--series-1)" stroke-width="2" vector-effect="non-scaling-stroke"
      stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}

function lineChart(box, pts, label) {
  box.innerHTML = "";
  if (pts.length < 2) {
    box.innerHTML = `<div class="empty"><h3>No history yet</h3>Points are added every few minutes while the searcher runs.</div>`;
    return;
  }
  const W = 720, H = 260, L = 64, R = 12, T = 12, B = 28;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  let y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const X = (x) => L + ((x - x0) / (x1 - x0 || 1)) * (W - L - R);
  const Y = (y) => T + (1 - (y - y0) / (y1 - y0)) * (H - T - B);
  let grid = "";
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (i / 4) * (y1 - y0), y = Y(v);
    grid += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="var(--grid)"/>
      <text x="${L - 6}" y="${y + 4}" text-anchor="end">${esc(fmtNum(v))}</text>`;
  }
  for (let i = 0; i <= 3; i++) {
    const t = x0 + (i / 3) * (x1 - x0);
    grid += `<text x="${X(t)}" y="${H - 8}" text-anchor="${i === 0 ? "start" : i === 3 ? "end" : "middle"}">${esc(new Date(t * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " + new Date(t * 1000).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }))}</text>`;
  }
  const d = pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1)).join(" ");
  box.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)} over time">
    ${grid}
    <path d="${d} L${X(x1)} ${H - B} L${X(x0)} ${H - B} Z" fill="var(--series-1-fill)"/>
    <path d="${d}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <line class="cross" y1="${T}" y2="${H - B}" stroke="var(--text-muted)" stroke-dasharray="3 3" visibility="hidden"/>
    <circle class="dot" r="5" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2" visibility="hidden"/>
    <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" class="hit"/>
  </svg><div class="tip"></div>`;
  const svg = $("svg", box), tip = $(".tip", box), cross = $(".cross", box), dot = $(".dot", box);
  $(".hit", box).addEventListener("mousemove", (e) => {
    const r = svg.getBoundingClientRect();
    const mx = ((e.clientX - r.left) / r.width) * W;
    let best = pts[0];
    for (const p of pts) if (Math.abs(X(p[0]) - mx) < Math.abs(X(best[0]) - mx)) best = p;
    const px = X(best[0]), py = Y(best[1]);
    cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("visibility", "visible");
    dot.setAttribute("cx", px); dot.setAttribute("cy", py); dot.setAttribute("visibility", "visible");
    tip.style.display = "block";
    tip.innerHTML = `<b>${esc(fmtNum(best[1]))}</b> ${esc(label)}<br><span class="muted">${esc(when(best[0]))}</span>`;
    const left = (px / W) * r.width;
    tip.style.left = Math.min(Math.max(0, left - 60), r.width - 160) + "px";
    tip.style.top = Math.max(0, (py / H) * r.height - 58) + "px";
  });
  $(".hit", box).addEventListener("mouseleave", () => {
    tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden");
  });
}

/* ---------- tiny markdown renderer (headings, lists, tables, code, links, emphasis) ---------- */
function inline(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+|[^)\s:]+)\)/g, '<a href="$2" rel="noopener">$1</a>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" rel="noopener">$2</a>');
  return s;
}
function markdown(md) {
  const lines = (md || "").replace(/\r/g, "").split("\n");
  let out = "", i = 0;
  while (i < lines.length) {
    const ln = lines[i];
    if (/^```/.test(ln)) {
      let code = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
      i++; out += `<pre><code>${esc(code.join("\n"))}</code></pre>`; continue;
    }
    const h = ln.match(/^(#{1,4})\s+(.*)/);
    if (h) { out += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; i++; continue; }
    if (/^\|/.test(ln)) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
      const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      let t = "<table>";
      rows.forEach((r, k) => {
        if (k === 1 && /^[\s|:-]+$/.test(r)) return;
        const tag = k === 0 ? "th" : "td";
        t += "<tr>" + cells(r).map((c) => `<${tag}>${inline(c)}</${tag}>`).join("") + "</tr>";
      });
      out += t + "</table>"; continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(ln)) {
      const ordered = /^\s*\d+\./.test(ln);
      let items = [];
      while (i < lines.length && (/^\s*([-*]|\d+\.)\s+/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ""));
        else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      const tag = ordered ? "ol" : "ul";
      out += `<${tag}>` + items.map((x) => `<li>${inline(x)}</li>`).join("") + `</${tag}>`; continue;
    }
    if (/^>\s?/.test(ln)) {
      let q = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, ""));
      out += `<blockquote>${inline(q.join(" "))}</blockquote>`; continue;
    }
    if (!ln.trim()) { i++; continue; }
    let para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\||\s*([-*]|\d+\.)\s+|>)/.test(lines[i])) para.push(lines[i++]);
    out += `<p>${inline(para.join(" "))}</p>`;
  }
  return out;
}

/* ---------- index page ---------- */
function machinePanel(idx) {
  const m = idx.machine || {};
  const stale = Date.now() / 1000 - (idx.generated || 0) > (idx.stale_after_s || 120);
  let state = m.state || "stopped", reason = m.reason || "";
  if (stale && state !== "stopped") { state = "stopped"; reason = "no update since " + ago(idx.generated) + " (computer off?)"; }
  const cls = state === "running" ? "good" : state === "paused" ? "warn" : "idle";
  return `<div class="panel machine">
    <div class="stat"><div class="label">Searchers</div><div class="value"><span class="pill ${cls}">${esc(state)}</span></div><div class="sub">${esc(reason)}</div></div>
    <div class="stat"><div class="label">CPU temperature</div><div class="value">${m.temp_c != null ? Math.round(m.temp_c) + " °C" : "–"}</div><div class="sub">${m.temp_c != null ? "pauses at the configured limit" : "unreadable: safe on/off cycle"}</div></div>
    <div class="stat"><div class="label">Cores busy</div><div class="value">${stale ? 0 : (m.workers_busy || 0)} / ${m.workers_max || "–"}</div><div class="sub">lowest priority (nice 19)</div></div>
    <div class="stat"><div class="label">Data stored</div><div class="value">${fmtNum(m.disk_mb || 0)} MB</div><div class="sub">cap ${esc(m.disk_cap_gb)} GB</div></div>
    <div class="stat"><div class="label">Last update</div><div class="value">${esc(ago(idx.generated))}</div><div class="sub">${esc(when(idx.generated))}</div></div>
  </div>`;
}

function alertBanner(alerts) {
  if (!alerts || !alerts.length) return "";
  return `<div class="banner"><strong>VERIFIED CANDIDATE — needs human review.</strong>
    An independent checker confirmed it by computer. That is not a proof: please look at it carefully and ask an expert.
    <ul>${alerts.map((a) => `<li><a href="problem.html?p=${encodeURIComponent(a.slug)}">${esc(a.name)}</a>: ${esc(a.summary)} <span class="muted">(${esc(when(a.found_at))})</span></li>`).join("")}</ul></div>`;
}

function card(p, hist) {
  const f = p.frontier || {};
  const accent = CAT[p.category] || "--cat-other";
  return `<a class="panel card" style="--accent: var(${accent})" href="problem.html?p=${encodeURIComponent(p.slug)}">
    <div class="head"><div><div class="cat">${esc(p.category)}</div><h3>${esc(p.name)}</h3></div>${statePill(p.state)}</div>
    <div class="frontier"><b>Reached:</b> ${esc(f.text || "not started")}</div>
    <div class="record"><b>World record / known limit:</b> ${esc(p.record || "–")}</div>
    ${sparkline(series(hist, "f"))}
    ${p.last_error ? `<div class="err">Last problem: ${esc(p.last_error)}</div>` : ""}
    <div class="kv">
      <div>Speed<b>${p.speed_per_cpu_s ? fmtNum(p.speed_per_cpu_s) + "/s" : "–"}</b>${esc(p.speed_unit)} per core</div>
      <div>Compute<b>${fmtHours(p.cpu_hours)}</b>${fmtNum(p.units_done)} units</div>
      <div>Checkpoint<b>${esc(ago(p.last_checkpoint))}</b>${p.candidates_total ? p.candidates_total + " candidates" : "no candidates"}</div>
    </div></a>`;
}

function ledgerTable(idx, details) {
  const rows = idx.problems.map((p) => {
    const h = series((details[p.slug] || {}).history, "f");
    const cpu = series((details[p.slug] || {}).history, "cpu");
    let rate = "–";
    if (h.length >= 2 && cpu.length >= 2) {
      const dcpu = (cpu[cpu.length - 1][1] - cpu[0][1]) / 3600;
      if (dcpu > 0) rate = fmtNum((h[h.length - 1][1] - h[0][1]) / dcpu);
    }
    return `<tr><td><a href="problem.html?p=${encodeURIComponent(p.slug)}">${esc(p.name)}</a></td>
      <td class="n">${fmtHours(p.cpu_hours)}</td><td class="n">${fmtNum(p.units_done)}</td>
      <td class="n">${fmtNum(p.cases)}</td><td class="n">${rate}</td></tr>`;
  }).join("");
  const total = idx.problems.reduce((a, p) => a + (p.cpu_hours || 0), 0);
  return `<div class="panel" style="overflow-x:auto"><table class="data">
    <tr><th>Problem</th><th class="n">CPU time</th><th class="n">Units</th><th class="n">Cases checked</th><th class="n">Frontier moved per CPU-hour</th></tr>
    ${rows}<tr><th>Total</th><th class="n">${fmtHours(total)}</th><th></th><th></th><th></th></tr></table></div>`;
}

async function renderIndex() {
  const root = $("#app");
  let idx;
  try { idx = await getJSON("status/index.json"); }
  catch (e) {
    root.innerHTML = `<div class="panel empty lift"><h3>No status yet</h3>
      Start the searchers with <code>./mathrun start</code>. This page fills in within a minute.
      <p class="muted">On GitHub Pages it appears after the first <code>./mathrun publish</code>.</p></div>`;
    return;
  }
  $("#updated").textContent = "Updated " + ago(idx.generated);
  const details = {};
  await Promise.all(idx.problems.map(async (p) => {
    try { details[p.slug] = await getJSON("status/" + p.slug + ".json"); } catch (e) { details[p.slug] = {}; }
  }));
  const cats = [...new Set(idx.problems.map((p) => p.category))];
  let cardsHtml = "";
  for (const c of cats) {
    cardsHtml += `<h2 class="section">${esc(c)}</h2><div class="grid">` +
      idx.problems.filter((p) => p.category === c).map((p) => card(p, (details[p.slug] || {}).history)).join("") + "</div>";
  }
  if (!idx.problems.length) cardsHtml = `<div class="panel empty" style="margin-top:24px"><h3>No problems are running</h3>Check <code>[problems]</code> in config.local.toml, and run <code>./mathrun install</code>.</div>`;
  root.innerHTML = `<div class="lift">${machinePanel(idx)}</div>${alertBanner(idx.alerts)}${cardsHtml}
    <h2 class="section">Compute ledger</h2>${ledgerTable(idx, details)}`;
}

/* ---------- detail page ---------- */
async function renderProblem() {
  const slug = new URLSearchParams(location.search).get("p") || "";
  const root = $("#app");
  let d;
  try { d = await getJSON("status/" + encodeURIComponent(slug) + ".json"); }
  catch (e) { root.innerHTML = `<div class="panel empty lift"><h3>Unknown problem</h3><a href="./">Back to all problems</a></div>`; return; }
  document.title = d.name + " · mathrun";
  $("#title").textContent = d.name;
  $("#subtitle").textContent = d.summary || "";
  const f = d.frontier || {};
  const verified = (d.candidates || []).filter((c) => (c.status || "").startsWith("VERIFIED"));
  const cands = (d.candidates || []).slice().reverse().map((c) => `<div class="cand ${(c.status || "").startsWith("VERIFIED") ? "verified" : ""}">
      <b>${esc(c.status)}</b><div>${esc(c.summary)}</div>
      <div class="meta">found ${esc(when(c.found_at))} · id ${esc(c.id)}</div>
      <details><summary>data and verifier output</summary><pre>${esc(JSON.stringify(c.data, null, 1))}</pre><pre>${esc(c.verifier_output || "")}</pre></details></div>`).join("");
  const bests = (d.bests || []).slice().reverse().map((b) => `<tr><td>${esc(b.summary || JSON.stringify(b))}</td><td class="muted">${esc(ago(b.t))}</td></tr>`).join("");
  root.innerHTML = `<div class="lift">
    ${verified.length ? alertBanner(verified.map((c) => ({ slug: d.slug, name: d.name, summary: c.summary, found_at: c.found_at }))) : ""}
    <div class="detail" style="margin-top:16px">
      <div>
        <div class="panel">
          <div class="tabs" id="tabs"></div>
          <div class="chart-box" id="chart"></div>
        </div>
        <div class="panel readme" style="margin-top:16px">${markdown(d.readme)}</div>
      </div>
      <div>
        <div class="panel">
          <div class="stat"><div class="label">Status</div><div class="value">${statePill(d.state)}</div></div>
          <p><b>Reached:</b> ${esc(f.text || "not started")}</p>
          <p><b>World record / known limit:</b> ${esc(d.record || "–")}</p>
          <table class="data">
            <tr><td>Speed</td><td class="n">${d.speed_per_cpu_s ? fmtNum(d.speed_per_cpu_s) + " " + esc(d.speed_unit) + "/s per core" : "–"}</td></tr>
            <tr><td>Compute spent</td><td class="n">${fmtHours(d.cpu_hours)}</td></tr>
            <tr><td>Units finished</td><td class="n">${fmtNum(d.units_done)}</td></tr>
            <tr><td>${esc(d.speed_unit)} checked</td><td class="n">${fmtNum(d.cases)}</td></tr>
            <tr><td>Last checkpoint</td><td class="n">${esc(ago(d.last_checkpoint))}</td></tr>
          </table>
          ${d.bug ? `<p class="err" style="color:var(--critical)"><b>Paused:</b> a candidate failed independent verification, which means the searcher may have a bug. Look at the candidate below, then run <code>./mathrun clear-bug ${esc(d.slug)}</code>.</p>` : ""}
          ${d.last_error ? `<p style="color:var(--critical)">Last problem: ${esc(d.last_error)}</p>` : ""}
        </div>
        <div class="panel" style="margin-top:16px"><h3 style="margin-top:0">Candidates</h3>
          ${cands || `<p class="muted">None yet. Anything the searcher flags is saved at once and re-checked by separate code before it is shown as verified.</p>`}</div>
        ${bests ? `<div class="panel" style="margin-top:16px"><h3 style="margin-top:0">Recent bests</h3><table class="data">${bests}</table></div>` : ""}
      </div>
    </div></div>`;
  const metrics = [["f", "frontier"], ["cases", d.speed_unit || "cases"], ["cpu", "CPU seconds"]];
  const tabs = $("#tabs");
  const show = (k) => {
    [...tabs.children].forEach((b) => b.classList.toggle("on", b.dataset.k === k));
    const m = metrics.find((x) => x[0] === k);
    lineChart($("#chart"), series(d.history, k), m[1]);
  };
  tabs.innerHTML = metrics.map(([k, l]) => `<button data-k="${k}">${esc(l)}</button>`).join("");
  tabs.addEventListener("click", (e) => { if (e.target.dataset.k) show(e.target.dataset.k); });
  show("f");
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  const go = page === "problem" ? renderProblem : renderIndex;
  go();
  if (page !== "problem") setInterval(go, 30000);
});
