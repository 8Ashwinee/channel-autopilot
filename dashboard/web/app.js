/* Channel Studio: sign-in (Cognito, code + PKCE), then hash-routed pages over /api. */
(() => {
  const C = window.STUDIO, origin = location.origin + "/";
  const $ = s => document.querySelector(s), main = () => $("#main");
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = n => n == null ? "–" : Number(n).toLocaleString("en-US");
  const short = n => n == null ? "–" : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + "K" : String(n);
  const pct = (a, b) => !b ? "" : `<span class="${a >= b ? "up" : "down"}">${a >= b ? "▲" : "▼"} ${Math.abs(Math.round((a - b) / b * 100))}%</span>`;
  const when = iso => iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "–";
  const toast = (m, ms = 2600) => { const t = $("#toast"); t.textContent = m; t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", ms); };
  const b64u = b => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const charts = [];

  // ---------------------------------------------------------------- auth
  async function signIn() {
    const v = b64u(crypto.getRandomValues(new Uint8Array(32)));
    const ch = b64u(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(v)));
    sessionStorage.setItem("pkce", v); sessionStorage.setItem("back", location.hash || "#/overview");
    location.href = `https://${C.domain}/oauth2/authorize?response_type=code&client_id=${C.clientId}&redirect_uri=${encodeURIComponent(origin)}` +
      `&scope=openid+email+profile&code_challenge=${ch}&code_challenge_method=S256`;
  }
  async function tokenCall(form) {
    const r = await fetch(`https://${C.domain}/oauth2/token`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(form) });
    if (!r.ok) throw new Error("token " + r.status);
    const t = await r.json(); const s = JSON.parse(localStorage.getItem("st") || "{}");
    localStorage.setItem("st", JSON.stringify({ id: t.id_token, refresh: t.refresh_token || s.refresh, exp: Date.now() + (t.expires_in - 60) * 1000 }));
  }
  async function idToken() {
    const s = JSON.parse(localStorage.getItem("st") || "{}");
    if (s.id && s.exp > Date.now()) return s.id;
    if (s.refresh) { try { await tokenCall({ grant_type: "refresh_token", client_id: C.clientId, refresh_token: s.refresh }); return JSON.parse(localStorage.getItem("st")).id; } catch (e) {} }
    localStorage.removeItem("st"); await signIn(); throw new Error("redirecting");
  }
  async function api(path, body) {
    const h = { "x-st-token": await idToken() }; let opt = { headers: h };
    if (body !== undefined) {
      const txt = JSON.stringify(body);
      h["Content-Type"] = "application/json";
      h["x-amz-content-sha256"] = [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(txt)))].map(b => b.toString(16).padStart(2, "0")).join("");
      opt = { method: "POST", headers: h, body: txt };
    }
    const r = await fetch("/api/" + path, opt);
    if (r.status === 401) { localStorage.removeItem("st"); await signIn(); throw new Error("redirecting"); }
    const j = await r.json(); if (!r.ok) throw new Error(j.error || r.status); return j;
  }

  // ---------------------------------------------------------------- charts
  function clearCharts() { while (charts.length) charts.pop().destroy(); }
  const gridC = "rgba(255,255,255,.06)", tickC = "#8b97ad";
  function chart(el, cfg) { const c = new Chart(el, cfg); charts.push(c); return c; }
  function spark(el, data) {
    chart(el, { type: "line", data: { labels: data.map((_, i) => i), datasets: [{ data, borderColor: "#ffe14d", borderWidth: 1.6, pointRadius: 0, fill: true, backgroundColor: "rgba(255,225,77,.08)", tension: .3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false, beginAtZero: true } } } });
  }
  const axis = (extra = {}) => ({ grid: { color: gridC }, ticks: { color: tickC, maxTicksLimit: 8 }, ...extra });

  // ---------------------------------------------------------------- pages
  let OV = null;
  async function sidebar() {
    if (!OV) OV = await api("overview");
    $("#side").innerHTML = `<h4>Channels</h4>` + OV.channels.map(c =>
      `<a href="#/channel/${c.ch}" data-ch="${c.ch}">${c.thumb ? `<img src="${esc(c.thumb)}" alt="">` : `<img alt="">`}<span>${esc(c.name)}</span></a>`).join("");
  }

  async function overview() {
    OV = await api("overview");
    const t = OV.channels.reduce((a, c) => ({ subs: a.subs + (c.subscribers || 0), v: a.v + c.views28, h: a.h + c.hours28, s: a.s + c.subs28 }), { subs: 0, v: 0, h: 0, s: 0 });
    main().innerHTML = `<h1>Overview</h1><p class="sub">Your channels, last 28 days. Data collected ${when(OV.last_collect)} · <a href="#" id="refresh">refresh now</a></p>
      <div class="grid g4">${[["Subscribers", fmt(t.subs)], ["Views (28 days)", fmt(t.v)], ["Watch hours (28 days)", fmt(Math.round(t.h))], ["Net new subscribers (28 days)", fmt(t.s)]]
        .map(([l, v]) => `<div class="card kpi big"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>
      <h2>Channels</h2><div class="grid g3">${OV.channels.map(c => `
        <div class="card click" data-go="#/channel/${c.ch}">
          <div class="chhead">${c.thumb ? `<img src="${esc(c.thumb)}" alt="">` : ""}<div><div class="t">${esc(c.name)}</div><div class="h">${esc(c.handle || "")} ${c.monetized ? '<span class="pill y">monetised</span>' : ""}</div></div></div>
          <div class="kpis">
            <div class="kpi"><div class="v">${short(c.subscribers)}</div><div class="l">subscribers</div></div>
            <div class="kpi"><div class="v">${short(c.views28)} ${pct(c.views28, c.views28_prev)}</div><div class="l">views, 28 days</div></div>
            <div class="kpi"><div class="v">${fmt(c.hours28)}</div><div class="l">watch hours, 28 days</div></div>
            <div class="kpi"><div class="v">${c.subs28 >= 0 ? "+" : ""}${fmt(c.subs28)}</div><div class="l">net subscribers, 28 days</div></div>
          </div><div style="height:44px"><canvas class="spark" id="sp-${c.ch}"></canvas></div></div>`).join("")}</div>`;
    OV.channels.forEach(c => spark($("#sp-" + c.ch), c.spark || []));
    main().querySelectorAll("[data-go]").forEach(e => e.onclick = () => location.hash = e.dataset.go);
    $("#refresh").onclick = async e => { e.preventDefault(); await api("collect", {}); toast("Collecting fresh data: about a minute. Reload then."); };
  }

  async function channel(ch) {
    const d = await api("channel?ch=" + ch);
    const daily = d.daily || [], last = daily.slice(-28);
    const avgDur = last.length ? Math.round(last.reduce((a, r) => a + (r.averageViewDuration || 0), 0) / last.length) : 0;
    const now = Date.now();
    const sched = (d.uploads || []).filter(v => v.publishAt && new Date(v.publishAt) > now).sort((a, b) => a.publishAt.localeCompare(b.publishAt));
    const recent = (d.uploads || []).filter(v => !(v.publishAt && new Date(v.publishAt) > now)).sort((a, b) => (b.published || "").localeCompare(a.published || "")).slice(0, 12);
    const titles = Object.fromEntries((d.uploads || []).map(v => [v.id, v]));
    main().innerHTML = `
      <div class="chhead">${d.thumb ? `<img src="${esc(d.thumb)}" alt="">` : ""}<div><h1>${esc(d.name)}</h1>
        <div class="h"><a href="https://youtube.com/${esc(d.handle || "")}" target="_blank" rel="noopener">${esc(d.handle || "")}</a> ${d.monetized ? '<span class="pill y">monetised</span>' : '<span class="pill">not monetised</span>'}</div></div></div>
      <div class="grid g4">${[["Subscribers", fmt(d.subscribers)], ["Views, 28 days", fmt(d.views28) + " " + pct(d.views28, d.views28_prev)],
        ["Watch hours, 28 days", fmt(d.hours28)], ["Average view duration", `${Math.floor(avgDur / 60)}:${String(avgDur % 60).padStart(2, "0")}`]]
        .map(([l, v]) => `<div class="card kpi big"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>
      <h2>Views and watch time, 90 days</h2><div class="card"><div class="chart"><canvas id="c1"></canvas></div></div>
      <div class="grid g2" style="margin-top:14px">
        <div class="card"><h2 style="margin-top:0">Subscribers gained and lost</h2><div class="chart" style="height:200px"><canvas id="c2"></canvas></div></div>
        <div class="card"><h2 style="margin-top:0">Where views come from (28 days)</h2><div class="chart" style="height:200px"><canvas id="c3"></canvas></div></div>
      </div>
      <div class="grid g2" style="margin-top:14px">
        <div class="card"><h2 style="margin-top:0">YouTube searches that found the channel (28 days)</h2>${table(["Search", "Views"], (d.search || []).map(r => [esc(r.insightTrafficSourceDetail), fmt(r.views)]), [0, 1])}</div>
        <div class="card"><h2 style="margin-top:0">Scheduled releases</h2>${sched.length ? sched.map(v => vid(v, `goes public ${when(v.publishAt)}`)).join("") : '<div class="empty">Nothing scheduled.</div>'}</div>
      </div>
      <h2>Top videos (28 days)</h2><div class="card tw">${table(["Video", "Views", "Watch hours", "Avg view %", "Avg duration", "Subs"],
        (d.topvideos || []).map(r => [titles[r.video] ? `<a href="https://youtube.com/watch?v=${r.video}" target="_blank" rel="noopener">${esc(titles[r.video].title)}</a>` : `<a href="https://youtube.com/watch?v=${r.video}" target="_blank" rel="noopener">${r.video}</a>`,
          fmt(r.views), fmt(Math.round((r.estimatedMinutesWatched || 0) / 60)), Math.round(r.averageViewPercentage || 0) + "%",
          `${Math.floor((r.averageViewDuration || 0) / 60)}:${String(Math.round(r.averageViewDuration || 0) % 60).padStart(2, "0")}`, fmt(r.subscribersGained)]), [0, 1, 1, 1, 1, 1])}</div>
      <h2>Recent uploads</h2><div class="card">${recent.map(v => vid(v, `${when(v.published)} · ${fmt(v.views)} views · ${v.privacy}`)).join("") || '<div class="empty">No uploads.</div>'}</div>`;
    const labels = daily.map(r => r.day.slice(5));
    chart($("#c1"), { type: "line", data: { labels, datasets: [
      { label: "Views", data: daily.map(r => r.views), borderColor: "#ffe14d", backgroundColor: "rgba(255,225,77,.08)", fill: true, pointRadius: 0, tension: .25, yAxisID: "y" },
      { label: "Watch hours", data: daily.map(r => +((r.estimatedMinutesWatched || 0) / 60).toFixed(1)), borderColor: "#5b93f7", pointRadius: 0, tension: .25, yAxisID: "y1" }] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { labels: { color: tickC } } },
        scales: { x: axis(), y: axis({ beginAtZero: true }), y1: axis({ beginAtZero: true, position: "right", grid: { display: false } }) } } });
    chart($("#c2"), { type: "bar", data: { labels, datasets: [{ label: "Gained", data: daily.map(r => r.subscribersGained), backgroundColor: "#3cd278" },
      { label: "Lost", data: daily.map(r => -(r.subscribersLost || 0)), backgroundColor: "#ef4444" }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: tickC } } }, scales: { x: axis({ stacked: true }), y: axis({ stacked: true }) } } });
    const tr = d.traffic || [];
    chart($("#c3"), { type: "bar", data: { labels: tr.map(r => nice(r.insightTrafficSourceType)), datasets: [{ data: tr.map(r => r.views), backgroundColor: "#2f6fe4" }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: axis(), y: axis({ grid: { display: false } }) } } });
  }
  const SRC = { EXT_URL: "External websites", NO_LINK_OTHER: "Direct or unknown", RELATED_VIDEO: "Suggested videos", YT_SEARCH: "YouTube search",
    YT_CHANNEL: "Channel pages", SHORTS: "Shorts feed", END_SCREEN: "End screens", HASHTAGS: "Hashtag pages", SUBSCRIBER: "Subscriptions / home",
    PLAYLIST: "Playlists", NOTIFICATION: "Notifications", YT_OTHER_PAGE: "Other YouTube pages", ADVERTISING: "Ads", ANNOTATION: "Cards",
    NO_LINK_EMBEDDED: "Embedded players", YT_PLAYLIST_PAGE: "Playlist pages", CAMPAIGN_CARD: "Campaign cards", SOUND_PAGE: "Sound pages",
    LIVE_REDIRECT: "Live redirects", PRODUCT_PAGE: "Product pages", VIDEO_REMIXES: "Remixes" };
  const nice = s => SRC[s] || String(s || "").toLowerCase().replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
  const vid = (v, meta) => `<div class="vid" style="margin-bottom:10px">${v.thumb ? `<img src="${esc(v.thumb)}" alt="">` : ""}<div><a href="https://youtube.com/watch?v=${v.id}" target="_blank" rel="noopener">${esc(v.title)}</a><div class="muted" style="font-size:12px">${esc(meta)}</div></div></div>`;
  function table(head, rows, num = []) {
    if (!rows.length) return '<div class="empty">No data yet.</div>';
    return `<div class="tw"><table><tr>${head.map((h, i) => `<th class="${num[i] ? "n" : ""}">${h}</th>`).join("")}</tr>${rows.map(r => `<tr>${r.map((c, i) => `<td class="${num[i] ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("")}</table></div>`;
  }

  async function rotation() {
    const d = await api("rotation");
    const N = d.names || {};
    const today = new Date().toISOString().slice(0, 10);
    const pinsHtml = Object.keys(N).map(ch => {
      const p = d.pins[ch] || [], b = d.bans[ch] || [];
      if (!p.length && !b.length) return "";
      return `<tr><td>${esc(N[ch])}</td><td>${p.map(k => `<span class="pill y">${esc(k)}</span> `).join("") || "–"}</td><td>${b.map(k => `<span class="pill r">${esc(k)}</span> `).join("") || "–"}</td></tr>`;
    }).join("");
    main().innerHTML = `<h1>Daily rotation</h1><p class="sub">One channel a day: 2 long videos + 1 Short, researched, made, uploaded and scheduled automatically. </p>
      <div class="card" style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <label class="switch ${d.enabled ? "on" : ""}" id="sw"><i></i><b>${d.enabled ? "Running" : "Paused"}</b></label>
        <span class="muted">${d.enabled ? "The next daily run will make and upload videos." : "Paused: the next rotation run stops before making anything."}</span></div>
      <div class="grid g2" style="margin-top:14px">
        <div class="card"><h2 style="margin-top:0">Coming up</h2>${table(["Date", "Channel"], (d.schedule || []).map(s => [s.date === today ? `<b>${s.date} (today)</b>` : s.date, esc(N[s.channel] || s.channel)]))}</div>
        <div class="card"><h2 style="margin-top:0">Topic choices</h2>${pinsHtml ? `<div class="tw"><table><tr><th>Channel</th><th>Use next</th><th>Never</th></tr>${pinsHtml}</table></div>` : '<div class="empty">None yet. Pin or ban topics on the Keywords page.</div>'}</div>
      </div>
      <h2>Recent days</h2>${(d.days || []).map(day => dayCard(day, N)).join("") || '<div class="card empty">No runs yet. Runs appear here once `autopilot rotation run` reports to this dashboard.</div>'}`;
    $("#sw").onclick = async () => { const r = await api("rotation/control", { enabled: !d.enabled }); toast(r.enabled ? "Rotation running" : "Rotation paused"); rotation(); };
  }
  function dayCard(day, N) {
    const vids = (day.videos || []).map(v => {
      const st = v.id ? `<span class="pill y">uploaded</span> goes public ${when(v.publishAt || v.publish_at)}`
        : v.queued ? `<span class="pill y">queued</span> goes public ${when(v.publish_at || v.publishAt)}`
        : (v.held || v.failed) ? `<span class="pill r">${v.failed ? "failed" : "held"}</span> ${esc(v.held_reason || v.reason || "")}`
        : `<span class="pill a">${esc(v.status || "making")}</span>`;
      const kind = v.kind === "short" ? "Short" : "Long";
      return `<tr><td>${kind}</td><td>${v.id ? `<a href="https://youtube.com/watch?v=${v.id}" target="_blank" rel="noopener">${esc(v.title || v.keyword)}</a>` : esc(v.title || v.keyword || "")}</td><td>${st}</td></tr>`;
    }).join("");
    const topics = (day.topics || []).map(t => `<span class="pill b">${esc(t.keyword)} · ${short(t.searches)}/mo · $${t.bid_high_usd ?? t.bid_high ?? 0}</span>`).join(" ");
    return `<div class="card" style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap"><b>${esc(day.date)} · ${esc(N[day.channel] || day.channel)}</b>
      <span class="muted">${esc(day.status || "")} ${day.updated ? "· " + when(day.updated) : ""}</span></div><div style="margin:8px 0">${topics}</div>${vids ? `<div class="tw"><table>${vids}</table></div>` : ""}</div>`;
  }

  async function keywords() {
    if (!OV) OV = await api("overview");
    const chans = OV.channels;
    main().innerHTML = `<h1>Keyword research</h1><p class="sub">Google Ads Keyword Planner, United States, English. Pick a channel to use its topic seeds, or type your own topics (comma-separated). Pin a topic to have the rotation make it next; ban it to never use it.</p>
      <div class="card"><div class="form">
        <label class="f">Channel<select id="k-ch"><option value="">(none)</option>${chans.map(c => `<option value="${c.ch}">${esc(c.name)}</option>`).join("")}</select></label>
        <label class="f" style="flex:1;min-width:220px">Topics (optional)<input id="k-seed" placeholder="e.g. credit card debt, balance transfer"></label>
        <label class="f">Min searches/mo<input id="k-min" type="number" value="10000" style="width:120px"></label>
        <label class="f">Max<input id="k-max" type="number" placeholder="no limit" style="width:110px"></label>
        <label class="f">Competition<select id="k-comp"><option>LOW,MEDIUM</option><option>LOW</option><option>LOW,MEDIUM,HIGH</option></select></label>
        <label class="f">Min bid $<input id="k-bid" type="number" value="0" step="0.5" style="width:80px"></label>
        <label class="f">Min words<input id="k-words" type="number" value="3" style="width:70px"></label>
        <label class="f" style="flex-direction:row;align-items:center;gap:6px"><input id="k-nav" type="checkbox"> include navigational</label>
        <button id="k-go">Search</button></div></div>
      <div id="k-out" style="margin-top:14px"></div>`;
    $("#k-go").onclick = async () => {
      const q = new URLSearchParams({ ch: $("#k-ch").value, seed: $("#k-seed").value, min: $("#k-min").value || 0, comp: $("#k-comp").value,
        minbid: $("#k-bid").value || 0, words: $("#k-words").value || 1, nav: $("#k-nav").checked ? "1" : "0" });
      if ($("#k-max").value) q.set("max", $("#k-max").value);
      $("#k-out").innerHTML = '<div class="card loading">Asking Keyword Planner… (10–40 seconds)</div>';
      try {
        const d = await api("keywords?" + q);
        if (d.error) { $("#k-out").innerHTML = `<div class="card">${esc(d.error)}</div>`; return; }
        const ch = $("#k-ch").value;
        $("#k-out").innerHTML = `<p class="sub">${fmt(d.ideas)} ideas · ${fmt(d.merged)} after merging misspellings · <b>${fmt(d.passed)}</b> passed your filters (showing up to 300, best first: searches × bid).</p>
          <div class="card tw"><table><tr><th>Keyword</th><th class="n">Searches/mo</th><th>Competition</th><th class="n">Bid</th><th class="n">Score</th><th></th></tr>
          ${d.rows.map(r => `<tr><td>${esc(r.keyword)} ${r.state ? `<span class="pill ${r.state === "pinned" ? "y" : "r"}">${r.state}</span>` : ""}</td><td class="n">${fmt(r.searches)}</td><td>${r.competition.toLowerCase()}</td>
            <td class="n">$${r.bid_low}–$${r.bid_high}</td><td class="n">${short(r.score)}</td>
            <td style="white-space:nowrap">${ch ? `<button class="small blue" data-a="pin" data-k="${esc(r.keyword)}">Use next</button> <button class="small red" data-a="ban" data-k="${esc(r.keyword)}">Never</button>` : ""}</td></tr>`).join("")}</table></div>`;
        $("#k-out").querySelectorAll("button[data-a]").forEach(b => b.onclick = async () => {
          await api("topics", { ch, keyword: b.dataset.k, action: b.dataset.a });
          b.closest("tr").querySelector("td").insertAdjacentHTML("beforeend", ` <span class="pill ${b.dataset.a === "pin" ? "y" : "r"}">${b.dataset.a === "pin" ? "pinned" : "banned"}</span>`);
          toast(b.dataset.a === "pin" ? "The rotation will use it on this channel's next day" : "Never used on this channel");
        });
      } catch (e) { $("#k-out").innerHTML = `<div class="card">${esc(e.message)}</div>`; }
    };
  }

  // Search Console: cards (one per site) → click → that site's page; a dropdown on the site page switches site.
  const siteName = s => s.replace("sc-domain:", "").replace(/^https?:\/\//, "").replace(/\/$/, "");
  const gscTotals = s => (s.daily || []).reduce((a, r) => ({ c: a.c + r.clicks, im: a.im + r.impressions, p: a.p + r.position * r.impressions }), { c: 0, im: 0, p: 0 });
  async function search(key) {
    const d = await api("gsc");
    const sites = (d.sites || []).sort((a, b) => gscTotals(b).im - gscTotals(a).im);
    if (!sites.length) { main().innerHTML = '<h1>Search Console</h1><div class="card empty">No Search Console data yet.</div>'; return; }
    const site = key ? sites.find(s => s.site === decodeURIComponent(key)) : null;
    if (!site) {
      main().innerHTML = `<h1>Search Console</h1><p class="sub">Google Search, last 28 days (data lags 2–3 days). Click a site for its queries and pages.</p>
        <div class="grid g3">${sites.map((s, i) => { const t = gscTotals(s); return `
          <div class="card click" data-go="#/search/${encodeURIComponent(s.site)}">
            <div class="chhead"><div><div class="t">${esc(siteName(s.site))}</div><div class="h">${s.site.startsWith("sc-domain:") ? "domain property" : "URL property"}</div></div></div>
            <div class="kpis">
              <div class="kpi"><div class="v">${fmt(t.c)}</div><div class="l">clicks</div></div>
              <div class="kpi"><div class="v">${short(t.im)}</div><div class="l">impressions</div></div>
              <div class="kpi"><div class="v">${t.im ? (t.c / t.im * 100).toFixed(1) + "%" : "–"}</div><div class="l">CTR</div></div>
              <div class="kpi"><div class="v">${t.im ? (t.p / t.im).toFixed(1) : "–"}</div><div class="l">avg position</div></div>
            </div><div style="height:44px"><canvas class="spark" id="gs${i}"></canvas></div></div>`; }).join("")}</div>`;
      sites.forEach((s, i) => spark($("#gs" + i), (s.daily || []).map(r => r.impressions)));
      main().querySelectorAll("[data-go]").forEach(e => e.onclick = () => location.hash = e.dataset.go);
      return;
    }
    const t = gscTotals(site);
    main().innerHTML = `<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:4px">
        <a href="#/search" class="muted">← All sites</a>
        <select id="g-site">${sites.map(s => `<option value="${esc(s.site)}" ${s.site === site.site ? "selected" : ""}>${esc(siteName(s.site))}</option>`).join("")}</select></div>
      <h1>${esc(siteName(site.site))}</h1><p class="sub">Google Search, ${esc(site.start || "")} to ${esc(site.end || "")}.</p>
      <div class="grid g4">${[["Clicks", fmt(t.c)], ["Impressions", fmt(t.im)], ["CTR", t.im ? (t.c / t.im * 100).toFixed(1) + "%" : "–"], ["Avg position", t.im ? (t.p / t.im).toFixed(1) : "–"]]
        .map(([l, v]) => `<div class="card kpi big"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")}</div>
      <h2>Clicks and impressions by day</h2><div class="card"><div class="chart"><canvas id="g-chart"></canvas></div></div>
      <div class="grid g2" style="margin-top:14px">
        <div class="card"><h2 style="margin-top:0">Top queries</h2>${table(["Query", "Clicks", "Impr.", "CTR", "Pos."], (site.queries || []).map(r => [esc(r.keys[0]), fmt(r.clicks), fmt(r.impressions), (r.ctr * 100).toFixed(1) + "%", r.position.toFixed(1)]), [0, 1, 1, 1, 1])}</div>
        <div class="card"><h2 style="margin-top:0">Top pages</h2>${table(["Page", "Clicks", "Impr."], (site.pages || []).map(r => [`<a href="${esc(r.keys[0])}" target="_blank" rel="noopener">${esc(r.keys[0].replace(/^https?:\/\/[^/]+/, "") || "/")}</a>`, fmt(r.clicks), fmt(r.impressions)]), [0, 1, 1])}</div>
      </div>
      <h2>Countries</h2><div class="card">${table(["Country", "Clicks", "Impr.", "Pos."], (site.countries || []).map(r => [esc(String(r.keys[0]).toUpperCase()), fmt(r.clicks), fmt(r.impressions), r.position.toFixed(1)]), [0, 1, 1, 1])}</div>`;
    $("#g-site").onchange = e => location.hash = "#/search/" + encodeURIComponent(e.target.value);
    chart($("#g-chart"), { type: "line", data: { labels: (site.daily || []).map(r => r.keys[0].slice(5)), datasets: [
      { label: "Clicks", data: (site.daily || []).map(r => r.clicks), borderColor: "#3cd278", pointRadius: 0, tension: .25, yAxisID: "y" },
      { label: "Impressions", data: (site.daily || []).map(r => r.impressions), borderColor: "#5b93f7", pointRadius: 0, tension: .25, yAxisID: "y1" }] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { labels: { color: tickC } } },
        scales: { x: axis(), y: axis({ beginAtZero: true }), y1: axis({ beginAtZero: true, position: "right", grid: { display: false } }) } } });
  }

  // ---------------------------------------------------------------- router
  async function render() {
    clearCharts();
    const h = location.hash || "#/overview", parts = h.slice(2).split("/");
    document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", h.startsWith(a.getAttribute("href"))));
    document.querySelectorAll("#side a").forEach(a => a.classList.toggle("on", a.dataset.ch === parts[1]));
    main().innerHTML = '<div class="loading">Loading…</div>';
    try {
      if (parts[0] === "channel") await channel(parts[1]);
      else if (parts[0] === "rotation") await rotation();
      else if (parts[0] === "keywords") await keywords();
      else if (parts[0] === "search") await search(parts.slice(1).join("/"));
      else await overview();
      document.querySelectorAll("#side a").forEach(a => a.classList.toggle("on", a.dataset.ch === parts[1]));
    } catch (e) { if (e.message !== "redirecting") main().innerHTML = `<div class="card">Could not load: ${esc(e.message)}</div>`; }
  }

  async function start() {
    const p = new URLSearchParams(location.search);
    if (p.get("code")) {
      try { await tokenCall({ grant_type: "authorization_code", client_id: C.clientId, code: p.get("code"), redirect_uri: origin, code_verifier: sessionStorage.getItem("pkce") || "" }); }
      catch (e) { localStorage.removeItem("st"); }
      history.replaceState(null, "", "/" + (sessionStorage.getItem("back") || "#/overview"));
    }
    try { const me = await api("me"); $("#who").textContent = me.email; } catch (e) { return; }
    $("#logout").onclick = () => { localStorage.removeItem("st"); location.href = `https://${C.domain}/logout?client_id=${C.clientId}&logout_uri=${encodeURIComponent(origin)}`; };
    await sidebar().catch(() => {});
    window.addEventListener("hashchange", render); render();
  }
  start();
})();
