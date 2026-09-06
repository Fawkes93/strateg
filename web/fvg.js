(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_ifvg_v1";
  let pollTimer = null;
  let elapsedTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let lastResult = null;
  let sortKey = "time";
  let sortDir = 1;
  let startedAt = null;
  let finishedAt = null;
  let savedPicker = {
    isViewingSaved: function () {
      return false;
    },
    clearViewing: function () {},
  };

  const FORM_IDS = [
    "fvg-symbol",
    "fvg-from",
    "fvg-to",
    "fvg-tf",
    "fvg-swing",
    "fvg-entry-mode",
    "fvg-sl-mode",
    "fvg-hours",
    "fvg-thresholds",
    "fvg-adverse",
    "fvg-side",
    "fvg-max-wait",
    "fvg-raid-bars",
    "fvg-workers",
    "fvg-force",
  ];

  function saveForm() {
    try {
      const cfg = {};
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el) return;
        cfg[id] = el.type === "checkbox" ? !!el.checked : el.value;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    } catch (e) {
      console.warn("ifvg save failed", e);
    }
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveForm, 200);
  }

  function loadForm() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const cfg = JSON.parse(raw);
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el || cfg[id] == null) return;
        if (el.type === "checkbox") el.checked = !!cfg[id];
        else el.value = cfg[id];
      });
    } catch (e) {
      console.warn("ifvg load failed", e);
    }
  }

  function bindFormPersist() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", scheduleSave);
      el.addEventListener("input", scheduleSave);
    });
  }

  function heroItem(label, value, tip) {
    const info = tip
      ? ' <span class="info-tag" title="' +
        tip.replace(/"/g, "&quot;") +
        '">i</span>'
      : "";
    return (
      '<div class="hero"' +
      (tip ? ' title="' + tip.replace(/"/g, "&quot;") + '"' : "") +
      '><div class="k">' +
      label +
      info +
      '</div><div class="v">' +
      (value == null ? "—" : value) +
      "</div></div>"
    );
  }

  function formatElapsed(ms) {
    if (ms == null || !isFinite(ms) || ms < 0) return "—";
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) {
      return h + "h " + String(m).padStart(2, "0") + "m " + String(sec).padStart(2, "0") + "s";
    }
    if (m > 0) return m + "m " + String(sec).padStart(2, "0") + "s";
    return sec + "s";
  }

  function updateElapsedDisplay(running) {
    const el = $("fvg-elapsed");
    if (!el) return;
    if (!startedAt) {
      el.textContent = "—";
      el.classList.remove("live");
      return;
    }
    const startMs = Date.parse(startedAt);
    if (!isFinite(startMs)) {
      el.textContent = "—";
      return;
    }
    let endMs;
    if (running) {
      endMs = Date.now();
      el.classList.add("live");
    } else if (finishedAt) {
      endMs = Date.parse(finishedAt);
      if (!isFinite(endMs)) endMs = Date.now();
      el.classList.remove("live");
    } else {
      endMs = Date.now();
      el.classList.remove("live");
    }
    el.textContent = (running ? "elapsed " : "ran ") + formatElapsed(endMs - startMs);
  }

  function startElapsedTicker() {
    if (elapsedTimer) return;
    elapsedTimer = setInterval(function () {
      updateElapsedDisplay(true);
    }, 1000);
  }

  function stopElapsedTicker() {
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }
  }

  function parseThresholds(raw) {
    return String(raw || "")
      .split(/[,;\s]+/)
      .map(function (x) {
        return Number(x);
      })
      .filter(function (x) {
        return isFinite(x) && x > 0;
      });
  }

  function headlineScore(result, t) {
    const by = (result && result.by_threshold) || {};
    const key = String(t);
    if (by[key]) return by[key];
    const hk = result && result.headline_threshold;
    if (hk && by[hk]) return by[hk];
    const keys = Object.keys(by);
    return keys.length ? by[keys[0]] : null;
  }

  function sortedRows(rows) {
    const copy = (rows || []).slice();
    copy.sort(function (a, b) {
      let va;
      let vb;
      if (sortKey === "side") {
        va = a.side || "";
        vb = b.side || "";
      } else if (sortKey === "entry") {
        va = Number(a.entry) || 0;
        vb = Number(b.entry) || 0;
      } else {
        va = Date.parse(a.entry_ts) || 0;
        vb = Date.parse(b.entry_ts) || 0;
      }
      if (va < vb) return -sortDir;
      if (va > vb) return sortDir;
      return 0;
    });
    return copy;
  }

  function updateSortHeaders() {
    document.querySelectorAll("#fvg-table th.sf-sort").forEach(function (th) {
      const k = th.getAttribute("data-sort");
      th.classList.toggle("is-on", k === sortKey);
      const dir = th.querySelector(".dir");
      if (dir) dir.textContent = k === sortKey ? (sortDir > 0 ? "▲" : "▼") : "";
    });
  }

  function bindSortHeaders() {
    const table = $("fvg-table");
    if (!table) return;
    table.querySelectorAll("th.sf-sort").forEach(function (th) {
      th.addEventListener("click", function () {
        const k = th.getAttribute("data-sort");
        if (sortKey === k) sortDir = -sortDir;
        else {
          sortKey = k;
          sortDir = 1;
        }
        updateSortHeaders();
        if (lastResult) render(lastResult);
      });
    });
  }

  function renderThresholdTable(result) {
    const tb = $("fvg-thr-table") && $("fvg-thr-table").querySelector("tbody");
    if (!tb) return;
    tb.innerHTML = "";
    const by = (result && result.by_threshold) || {};
    const keys = Object.keys(by).sort(function (a, b) {
      return Number(a) - Number(b);
    });
    if (!keys.length) {
      tb.innerHTML = '<tr><td colspan="6" class="muted">No scored thresholds</td></tr>';
      return;
    }
    keys.forEach(function (k) {
      const s = by[k] || {};
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        k +
        "</td><td>" +
        (s.hit_rate_pct != null ? s.hit_rate_pct + "%" : "—") +
        "</td><td>" +
        (s.clean_rate_pct != null ? s.clean_rate_pct + "%" : "—") +
        "</td><td>" +
        (s.clean_given_hit_pct != null ? s.clean_given_hit_pct + "%" : "—") +
        "</td><td>" +
        (s.avg_realized_pts != null ? s.avg_realized_pts : "—") +
        "</td><td>" +
        (s.sum_realized_pts != null ? s.sum_realized_pts : "—") +
        "</td>";
      tb.appendChild(tr);
    });
  }

  function render(result) {
    lastResult = result;
    const meta = $("fvg-meta");
    const hero = $("fvg-hero");
    const tb = $("fvg-table") && $("fvg-table").querySelector("tbody");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (tb) tb.innerHTML = "";
      renderThresholdTable(null);
      return;
    }
    const head = headlineScore(result, 500);
    if (meta) {
      meta.textContent =
        (result.symbol || "") +
        " · " +
        (result.date_from || "") +
        " → " +
        (result.date_to || "") +
        " · " +
        (result.trades || result.alerts || 0) +
        " entries · TF " +
        ((result.params && result.params.timeframe_min) || "—") +
        "m" +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Entries", result.trades || result.alerts || 0) +
        heroItem("Long / Short", (result.longs || 0) + " / " + (result.shorts || 0)) +
        heroItem(
          "Hit %",
          head && head.hit_rate_pct != null ? head.hit_rate_pct + "%" : result.hit_rate_pct != null ? result.hit_rate_pct + "%" : "—",
          "Share of entries that reached headline T within look-ahead."
        ) +
        heroItem(
          "Clean %",
          head && head.clean_rate_pct != null ? head.clean_rate_pct + "%" : result.clean_rate_pct != null ? result.clean_rate_pct + "%" : "—",
          "Hit and adverse stayed ≤ opposite% × T until first touch of T."
        ) +
        heroItem("Avg pts", head ? head.avg_realized_pts : result.avg_pts, "Hard-SL realized pts at opposite% × T (headline T).") +
        heroItem("Sum pts", head ? head.sum_realized_pts : result.sum_pts, "Sum of realized pts across entries (headline T).");
    }
    renderThresholdTable(result);
    if (!tb) return;
    tb.innerHTML = "";
    updateSortHeaders();
    const rows = sortedRows(result.rows || []);
    const hk = (result.headline_threshold || "500") + "";
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="10" class="muted">No IFVG entries in this window</td></tr>';
      return;
    }
    rows.forEach(function (t) {
      const sc = (t.scores && (t.scores[hk] || t.scores["500"])) || {};
      const pts = sc.realized_pts;
      const cls = pts > 0 ? "yes" : pts < 0 ? "no" : "";
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        (t.entry_ts || "").replace("T", " ").slice(0, 19) +
        "</td><td>" +
        (t.side || "") +
        "</td><td>" +
        (t.entry != null ? t.entry : "—") +
        "</td><td>" +
        (t.p != null ? t.p : "—") +
        "</td><td>" +
        (t.ce != null ? t.ce : "—") +
        "</td><td>" +
        (t.distal != null ? t.distal : "—") +
        "</td><td>" +
        (t.sl != null ? t.sl : "—") +
        "</td><td>" +
        (sc.hit ? "Y" : "N") +
        "</td><td>" +
        (sc.clean ? "Y" : "N") +
        '</td><td class="' +
        cls +
        '">' +
        (pts != null ? pts : "—") +
        "</td>";
      tb.appendChild(tr);
    });
  }

  const LANE_HUES = [204, 158, 286, 22, 142, 338];

  function monthLabel(ln) {
    if (!ln || !ln.month) return "—";
    return String(ln.month).slice(0, 7);
  }

  function renderLanes(st) {
    const el = $("fvg-lanes");
    if (!el) return;
    const p = st.progress || {};
    let lanes = p.lanes || [];
    if (st.running && !lanes.length) {
      const n = Number(st.params && st.params.workers) || 3;
      lanes = [];
      for (let i = 0; i < n; i++) {
        lanes.push({ slot: i, phase: "idle", pct: 0, detail: "starting…" });
      }
    }
    if (!lanes.length) {
      el.innerHTML = "";
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.innerHTML = lanes
      .map(function (ln, i) {
        const slot = ln.slot != null ? ln.slot : i;
        const hue = LANE_HUES[slot % LANE_HUES.length];
        const phase = ln.phase || "idle";
        const pct = Math.max(0, Math.min(100, Number(ln.pct) || 0));
        const month = monthLabel(ln);
        const detail = ln.detail || (phase === "idle" ? "waiting" : "");
        const trades = ln.trades && phase !== "idle" ? ln.trades + " entries" : "";
        const pill = phase === "load" ? "load" : phase === "scan" ? "scan" : "idle";
        return (
          '<div class="sf-lane is-' +
          phase +
          '" style="--lane-h:' +
          hue +
          '">' +
          '<div class="sf-lane-top">' +
          '<div class="sf-lane-who">' +
          '<span class="sf-lane-id">Worker ' +
          (slot + 1) +
          "</span>" +
          '<div class="sf-lane-month">' +
          month +
          "</div></div>" +
          '<div class="sf-lane-meta">' +
          '<span class="sf-lane-phase">' +
          pill +
          "</span>" +
          "<span>" +
          pct.toFixed(0) +
          "%</span>" +
          (detail ? "<span>" + detail + "</span>" : "") +
          (trades ? "<span>" + trades + "</span>" : "") +
          "</div></div>" +
          '<div class="sf-lane-track"><div class="sf-lane-bar" style="width:' +
          pct +
          '%"></div></div></div>'
        );
      })
      .join("");
  }

  async function fetchState(withRows) {
    const q = withRows ? "?rows=1&limit=400" : "";
    const r = await fetch("/api/fvg" + q);
    return r.json();
  }

  async function poll() {
    try {
      const st = await fetchState(false);
      const p = st.progress || {};
      const running = !!st.running;
      const pct = Number(p.pct) || 0;
      if ($("fvg-progress-bar")) $("fvg-progress-bar").style.width = pct + "%";
      if ($("fvg-overall-pct")) {
        const md = p.months_done;
        const mt = p.months_total;
        $("fvg-overall-pct").textContent =
          mt != null && mt > 0 ? pct.toFixed(0) + "% · " + (md || 0) + "/" + mt : pct.toFixed(0) + "%";
      }
      if ($("fvg-progress-msg")) {
        let msg = p.message || (running ? "Running…" : "Idle");
        if (p.phase === "error") msg = "Error: " + (p.message || "failed");
        $("fvg-progress-msg").textContent = msg;
      }
      renderLanes(st);
      if ($("fvg-run")) $("fvg-run").disabled = running;
      if ($("fvg-stop")) {
        $("fvg-stop").disabled = !running;
        $("fvg-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      if (p.started_at) startedAt = p.started_at;
      if (p.finished_at) finishedAt = p.finished_at;
      if (running) startElapsedTicker();
      else stopElapsedTicker();
      updateElapsedDisplay(running);
      const badge = $("status-badge");
      const finished = p.phase === "done" || p.phase === "cancelled";
      if (badge && running) {
        badge.textContent = st.cancel_requested ? "stopping" : "ifvg";
        badge.className = "badge run";
      }
      const holdSaved = savedPicker.isViewingSaved();
      if (wasRunning && !running && finished) {
        if (badge) {
          badge.textContent = p.phase === "cancelled" ? "stopped" : "done";
          badge.className = "badge done";
        }
        if (p.phase === "done" && window.StrategSaved && window.StrategSaved.playDone) {
          window.StrategSaved.playDone();
        }
        if (!holdSaved) {
          const full = await fetchState(true);
          if (full.result) render(full.result);
        }
      } else if (!running && st.result && finished && !holdSaved) {
        if (!st.result.rows || !st.result.rows.length) {
          const full = await fetchState(true);
          if (full.result) render(full.result);
        } else {
          render(st.result);
        }
      }
      if (p.phase === "error" && badge) {
        badge.textContent = "err";
        badge.className = "badge err";
      }
      wasRunning = running;
      if (!running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (e) {
      console.error(e);
    }
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="fvg"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "fvg");
      btn.textContent = "Inverse FVG";
      nav.appendChild(btn);
    }

    if ($("tab-fvg")) return;

    const panel = document.createElement("div");
    panel.id = "tab-fvg";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Inverse FVG after liquidity raid</h2>
      <ol>
        <li>Mark a swing low/high (lookback bars each side).</li>
        <li><strong>SSL / BSL</strong>: expansion raids through that swing.</li>
        <li>FVG forms in the expansion (bearish after SSL / bullish after BSL).</li>
        <li><strong>IFVG confirm</strong>: close back through proximal P.</li>
        <li>Entry on retrace into the half toward P (CE mid-gap). Score with look-ahead hit/clean like Research.</li>
      </ol>
      <p class="hint">
        Not plain FVG. Candles from ticks at 15m; 30/60/240 are aggregated from 15m.
        SL field is meta only — clean uses opposite% × T in the forward walk.
      </p>
    </section>

    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="fvg-symbol"><option value="XAUUSD" selected>XAUUSD (gold)</option></select>
        </label>
        <label>From
          <input type="date" id="fvg-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="fvg-to" value="2025-06-01" />
        </label>
        <label>Timeframe (min)
          <select id="fvg-tf">
            <option value="15" selected>15</option>
            <option value="30">30</option>
            <option value="60">60</option>
            <option value="240">240</option>
          </select>
        </label>
        <label>Swing lookback
          <input type="number" id="fvg-swing" value="3" min="1" max="20" step="1"
            title="Bars each side to confirm a swing high/low." />
        </label>
        <label>Entry mode
          <select id="fvg-entry-mode">
            <option value="first_touch" selected>first touch of zone</option>
            <option value="ce_touch">require CE touch</option>
          </select>
        </label>
        <label>SL meta
          <select id="fvg-sl-mode">
            <option value="far_edge" selected>far edge (distal)</option>
            <option value="below_ce">at CE</option>
          </select>
        </label>
        <label>Look-ahead
          <select id="fvg-hours">
            <option value="6" selected>6 hours</option>
            <option value="12">12 hours</option>
            <option value="24">24 hours</option>
          </select>
        </label>
        <label>Thresholds T (pts)
          <input type="text" id="fvg-thresholds" value="100,200,500,800,1000,1200,1500,2000" />
        </label>
        <label>Opposite % of T
          <input type="number" id="fvg-adverse" value="100" min="0" step="1"
            title="Adverse budget for clean = this% × T (100 = 1×T)." />
        </label>
        <label>Side
          <select id="fvg-side">
            <option value="both" selected>both</option>
            <option value="long">long only</option>
            <option value="short">short only</option>
          </select>
        </label>
        <label>Max wait bars
          <input type="number" id="fvg-max-wait" value="24" min="1" max="100" step="1" />
        </label>
        <label>FVG after raid (bars)
          <input type="number" id="fvg-raid-bars" value="8" min="1" max="40" step="1" />
        </label>
        <label>Workers
          <input type="number" id="fvg-workers" value="3" min="1" max="6" step="1" />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="fvg-run">Run Inverse FVG</button>
        <button type="button" class="secondary" id="fvg-stop" disabled>Stop</button>
        <label class="chk force">
          <input type="checkbox" id="fvg-force" /> Force re-download
        </label>
        <span class="muted" id="fvg-elapsed">—</span>
        <span class="muted" id="fvg-overall-pct"></span>
      </div>
    </section>

    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap">
        <div class="progress-bar" id="fvg-progress-bar" style="width:0%"></div>
      </div>
      <p class="progress-msg" id="fvg-progress-msg">Idle</p>
      <div class="sf-lanes" id="fvg-lanes" hidden></div>
    </section>

    <section class="card" id="fvg-results-card">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="fvg-saved" title="Open a saved IFVG run from results/"></select>
          <button type="button" class="secondary" id="fvg-load">Load</button>
        </div>
      </div>
      <p class="muted" id="fvg-meta">No run yet.</p>
      <div class="hero-grid" id="fvg-hero"></div>
      <h3>By threshold</h3>
      <div class="table-wrap">
        <table id="fvg-thr-table">
          <thead>
            <tr>
              <th>T</th>
              <th>Hit %</th>
              <th>Clean %</th>
              <th>Clean|Hit</th>
              <th>Avg pts</th>
              <th>Sum pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Entries</h3>
      <div class="table-wrap">
        <table id="fvg-table">
          <thead>
            <tr>
              <th class="sf-sort" data-sort="time">Time <span class="dir"></span></th>
              <th class="sf-sort" data-sort="side">Side <span class="dir"></span></th>
              <th class="sf-sort" data-sort="entry">Entry <span class="dir"></span></th>
              <th>P</th>
              <th>CE</th>
              <th>Distal</th>
              <th>SL meta</th>
              <th>Hit</th>
              <th>Clean</th>
              <th>Pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
    `;

    const foot = document.querySelector("footer.foot");
    if (foot) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);

    if (foot && foot.textContent.indexOf("Inverse FVG") < 0) {
      foot.textContent += " Inverse FVG = SSL/BSL raid → IFVG confirm → zone entry, scored hit/clean.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-fvg");
        if (panel) panel.classList.toggle("hidden", tab !== "fvg");
        if (tab === "fvg") {
          [
            "tab-research",
            "tab-sweep",
            "tab-session",
            "tab-spikefade",
            "tab-micro",
            "tab-burst",
            "tab-cooloff",
            "tab-overnight",
          ].forEach((id) => {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "fvg");
          } catch (e) {}
        }
      });
    });

    try {
      const tab = localStorage.getItem("strateg_tab");
      if (tab === "fvg") {
        const btn = document.querySelector('.main-tab[data-tab="fvg"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  function wireRun() {
    if (!$("fvg-run")) return;
    $("fvg-run").addEventListener("click", async () => {
      const thr = parseThresholds($("fvg-thresholds").value);
      const adversePct = Number($("fvg-adverse").value);
      const body = {
        symbol: $("fvg-symbol").value,
        date_from: $("fvg-from").value,
        date_to: $("fvg-to").value,
        timeframe_min: Number($("fvg-tf").value) || 15,
        swing_lookback: Number($("fvg-swing").value) || 3,
        entry_mode: $("fvg-entry-mode").value,
        sl_mode: $("fvg-sl-mode").value,
        hours: Number($("fvg-hours").value) || 6,
        thresholds: thr.length ? thr : [500],
        adverse_mult: isFinite(adversePct) ? adversePct / 100.0 : 1.0,
        side_filter: $("fvg-side").value,
        max_wait_bars: Number($("fvg-max-wait").value) || 24,
        fvg_after_raid_bars: Number($("fvg-raid-bars").value) || 8,
        workers: Number($("fvg-workers").value) || 3,
        force_download: $("fvg-force") && $("fvg-force").checked,
      };
      saveForm();
      savedPicker.clearViewing();
      $("fvg-run").disabled = true;
      if ($("fvg-stop")) $("fvg-stop").disabled = false;
      startedAt = new Date().toISOString();
      finishedAt = null;
      startElapsedTicker();
      updateElapsedDisplay(true);
      $("fvg-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/fvg/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("fvg-run").disabled = false;
          if ($("fvg-stop")) $("fvg-stop").disabled = true;
          stopElapsedTicker();
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("fvg-run").disabled = false;
        if ($("fvg-stop")) $("fvg-stop").disabled = true;
        stopElapsedTicker();
      }
    });
  }

  function wireStop() {
    if (!$("fvg-stop")) return;
    $("fvg-stop").addEventListener("click", async () => {
      $("fvg-stop").disabled = true;
      $("fvg-stop").textContent = "Stopping…";
      try {
        const r = await fetch("/api/fvg/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("fvg-stop").disabled = false;
          $("fvg-stop").textContent = "Stop";
          return;
        }
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("fvg-stop").disabled = false;
        $("fvg-stop").textContent = "Stop";
      }
    });
  }

  ensureTab();
  loadForm();
  bindFormPersist();
  bindSortHeaders();
  wireTabs();
  wireRun();
  wireStop();
  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "fvg",
      selectId: "fvg-saved",
      buttonId: "fvg-load",
      onLoaded: function (json) {
        render(json);
      },
    });
  }
  poll();
})();
