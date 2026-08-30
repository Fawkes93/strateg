(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_micro_v1";
  let pollTimer = null;
  let elapsedTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let lastResult = null;
  let lastResultKey = "";
  let sortKey = "time";
  let sortDir = 1;
  let startedAt = null;
  let finishedAt = null;

  const FORM_IDS = [
    "mm-symbol",
    "mm-from",
    "mm-to",
    "mm-session",
    "mm-window",
    "mm-min",
    "mm-max",
    "mm-persist",
    "mm-use-1m",
    "mm-1m-body",
    "mm-tp",
    "mm-sl",
    "mm-trail",
    "mm-arm",
    "mm-hold",
    "mm-cd",
    "mm-lag",
    "mm-spread",
    "mm-wknd",
    "mm-workers",
    "mm-force",
  ];

  function saveForm() {
    try {
      const cfg = {};
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el) return;
        cfg[id] = el.type === "checkbox" ? el.checked : el.value;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    } catch (e) {
      console.warn("micro burst save failed", e);
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
      console.warn("micro burst load failed", e);
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

  function reasonLabel(r) {
    if (r === "timeout") return "timeout (max hold)";
    return r || "—";
  }

  function holdSec(t) {
    var sec = t.hold_sec;
    if (sec == null && t.entry_ts && t.exit_ts) {
      var a = Date.parse(t.entry_ts);
      var b = Date.parse(t.exit_ts);
      if (isFinite(a) && isFinite(b)) sec = (b - a) / 1000;
    }
    if (sec == null || !isFinite(sec) || sec < 0) return -1;
    return sec;
  }

  function formatElapsed(ms) {
    if (ms == null || !isFinite(ms) || ms < 0) return "—";
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) {
      return (
        h +
        "h " +
        String(m).padStart(2, "0") +
        "m " +
        String(sec).padStart(2, "0") +
        "s"
      );
    }
    if (m > 0) return m + "m " + String(sec).padStart(2, "0") + "s";
    return sec + "s";
  }

  function updateElapsedDisplay(running) {
    const el = $("mm-elapsed");
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

  function sortedRows(rows) {
    const copy = (rows || []).slice();
    copy.sort(function (a, b) {
      let va;
      let vb;
      if (sortKey === "dur") {
        va = holdSec(a);
        vb = holdSec(b);
      } else if (sortKey === "reason") {
        va = (a.exit_reason || "").toLowerCase();
        vb = (b.exit_reason || "").toLowerCase();
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
    document.querySelectorAll("#mm-table th.mm-sort").forEach(function (th) {
      const k = th.getAttribute("data-sort");
      th.classList.toggle("is-on", k === sortKey);
      const dir = th.querySelector(".dir");
      if (dir) dir.textContent = k === sortKey ? (sortDir > 0 ? "▲" : "▼") : "";
    });
  }

  function bindSortHeaders() {
    const table = $("mm-table");
    if (!table) return;
    table.querySelectorAll("th.mm-sort").forEach(function (th) {
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

  function resultKey(result) {
    if (!result) return "";
    return [
      result.partial ? "1" : "0",
      result.finished_at || "",
      result.trades,
      result.sum_pts,
      result.row_count,
      (result.rows || []).length,
    ].join("|");
  }

  function render(result) {
    lastResult = result;
    lastResultKey = resultKey(result);
    const meta = $("mm-meta");
    const hero = $("mm-hero");
    const tb = $("mm-table") && $("mm-table").querySelector("tbody");
    const card = $("mm-results-card");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (tb) tb.innerHTML = "";
      return;
    }
    if (meta) {
      meta.textContent =
        (result.symbol || "") +
        " · " +
        (result.date_from || "") +
        " → " +
        (result.date_to || "") +
        " · " +
        (result.trades || 0) +
        " trades · avg " +
        (result.avg_pts != null ? result.avg_pts : "—") +
        " pts" +
        (result.partial ? " · live" : "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("TP %", result.tp_pct != null ? result.tp_pct + "%" : "—") +
        heroItem("SL %", result.sl_pct != null ? result.sl_pct + "%" : "—") +
        heroItem(
          "Trail %",
          result.trail_pct != null ? result.trail_pct + "%" : "—",
          "Share of trades closed by the trailing stop (0 trail = off)."
        ) +
        heroItem(
          "Timeout %",
          result.timeout_pct != null ? result.timeout_pct + "%" : "—"
        ) +
        heroItem("Avg pts", result.avg_pts) +
        heroItem(
          "PF",
          result.profit_factor != null ? result.profit_factor : "—"
        ) +
        heroItem("Sum pts", result.sum_pts);
    }
    if (card) {
      card.classList.toggle("is-fresh", !result.partial);
    }
    if (!tb) return;
    tb.innerHTML = "";
    updateSortHeaders();
    const rows = sortedRows(result.rows || []);
    if (!rows.length) {
      tb.innerHTML =
        '<tr><td colspan="11" class="muted">' +
        (result.partial ? "Scanning… trades appear as they close." : "No trades in this window") +
        "</td></tr>";
      return;
    }
    rows.forEach(function (t) {
      const tr = document.createElement("tr");
      const cls = t.pts > 0 ? "yes" : t.pts < 0 ? "no" : "";
      const dur = holdSec(t);
      tr.innerHTML =
        "<td>" +
        (t.entry_ts || "").replace("T", " ").slice(0, 19) +
        "</td><td>" +
        t.side +
        "</td><td>" +
        (t.burst_pts != null ? t.burst_pts : "—") +
        "</td><td>" +
        (t.spread_pts != null ? t.spread_pts : "—") +
        "</td><td>" +
        (t.tp_pts != null ? t.tp_pts : "—") +
        "</td><td>" +
        (t.sl_pts != null ? t.sl_pts : "—") +
        "</td><td>" +
        t.entry +
        "</td><td>" +
        (t.exit != null ? t.exit : "—") +
        "</td><td>" +
        (dur < 0 ? "—" : dur.toFixed(1)) +
        "</td><td>" +
        reasonLabel(t.exit_reason) +
        '</td><td class="' +
        cls +
        '">' +
        t.pts +
        "</td>";
      tb.appendChild(tr);
    });
  }

  const LANE_HUES = [204, 158, 286, 22, 142, 338];

  function renderLanes(st) {
    const el = $("mm-lanes");
    if (!el) return;
    const p = st.progress || {};
    let lanes = p.lanes || [];
    if (st.running && !lanes.length) {
      const n = Number(st.params && st.params.workers) || 2;
      lanes = [];
      for (let i = 0; i < n; i++) {
        lanes.push({ slot: i, phase: "idle", pct: 0, detail: "waiting" });
      }
    }
    if (!lanes.length) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    el.innerHTML = lanes
      .map(function (ln, i) {
        const slot = ln.slot != null ? ln.slot : i;
        const hue = LANE_HUES[slot % LANE_HUES.length];
        const pct = Math.max(0, Math.min(100, Number(ln.pct) || 0));
        const month = ln.month ? String(ln.month).slice(0, 7) : "—";
        const pill = ln.phase || "idle";
        const detail = ln.detail || "";
        const trades = ln.trades ? ln.trades + " tr" : "";
        return (
          '<div class="sf-lane" style="--lane-h:' +
          hue +
          '"><div class="sf-lane-top">' +
          '<div class="sf-lane-who"><span class="sf-lane-id">Worker ' +
          (slot + 1) +
          "</span><div class=\"sf-lane-month\">" +
          month +
          "</div></div>" +
          '<div class="sf-lane-meta"><span class="sf-lane-phase">' +
          pill +
          "</span><span>" +
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
    const r = await fetch("/api/micro-momentum" + q);
    return r.json();
  }

  async function poll() {
    try {
      const runningHint = wasRunning || ($("mm-run") && $("mm-run").disabled);
      const st = await fetchState(!!runningHint || true);
      const p = st.progress || {};
      const running = !!st.running;
      const pct = Number(p.pct) || 0;
      if ($("mm-progress-bar")) $("mm-progress-bar").style.width = pct + "%";
      if ($("mm-overall-pct")) {
        const md = p.months_done;
        const mt = p.months_total;
        $("mm-overall-pct").textContent =
          mt != null && mt > 0
            ? pct.toFixed(0) + "% · " + (md || 0) + "/" + mt
            : pct.toFixed(0) + "%";
      }
      if ($("mm-progress-msg")) {
        let msg = p.message || (running ? "Running…" : "Idle");
        if (p.phase === "error") msg = "Error: " + (p.message || "failed");
        $("mm-progress-msg").textContent = msg;
      }
      renderLanes(st);
      if ($("mm-run")) $("mm-run").disabled = running;
      if ($("mm-stop")) {
        $("mm-stop").disabled = !running;
        $("mm-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      if (p.started_at) startedAt = p.started_at;
      if (p.finished_at) finishedAt = p.finished_at;
      if (running) startElapsedTicker();
      else stopElapsedTicker();
      updateElapsedDisplay(running);
      const badge = $("status-badge");
      const finished = p.phase === "done" || p.phase === "cancelled";
      if (badge && running) {
        badge.textContent = st.cancel_requested ? "stopping" : "burst";
        badge.className = "badge run";
      }
      if (st.result) {
        const key = resultKey(st.result);
        if (key !== lastResultKey) render(st.result);
      }
      if (wasRunning && !running && finished && badge) {
        badge.textContent = p.phase === "cancelled" ? "stopped" : "done";
        badge.className = "badge done";
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

  loadForm();
  bindFormPersist();
  bindSortHeaders();

  if ($("mm-run")) {
    $("mm-run").addEventListener("click", async () => {
      const body = {
        symbol: $("mm-symbol").value,
        date_from: $("mm-from").value,
        date_to: $("mm-to").value,
        session: $("mm-session").value,
        window_sec: Number($("mm-window").value),
        min_burst_pts: Number($("mm-min").value),
        max_burst_pts: Number($("mm-max").value),
        persist_frac: Number($("mm-persist").value),
        use_1m: $("mm-use-1m").value === "true",
        min_1m_body: Number($("mm-1m-body").value),
        tp_pts: Number($("mm-tp").value),
        sl_pts: Number($("mm-sl").value),
        trail_pts: Number($("mm-trail") && $("mm-trail").value) || 0,
        trail_arm_pts: Number($("mm-arm") && $("mm-arm").value) || 0,
        max_hold_sec: Number($("mm-hold").value),
        cooldown_sec: Number($("mm-cd").value),
        lag_sec: Number($("mm-lag").value),
        max_spread_pts: Number($("mm-spread").value),
        weekend_blackout_min: Number($("mm-wknd").value),
        workers: Number($("mm-workers").value) || 2,
        force_download: $("mm-force") && $("mm-force").checked,
      };
      saveForm();
      $("mm-run").disabled = true;
      if ($("mm-stop")) $("mm-stop").disabled = false;
      startedAt = new Date().toISOString();
      finishedAt = null;
      lastResult = null;
      lastResultKey = "";
      render(null);
      if ($("mm-meta")) $("mm-meta").textContent = "Run in progress — results update as trades close.";
      startElapsedTicker();
      updateElapsedDisplay(true);
      $("mm-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/micro-momentum/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("mm-run").disabled = false;
          if ($("mm-stop")) $("mm-stop").disabled = true;
          stopElapsedTicker();
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("mm-run").disabled = false;
        if ($("mm-stop")) $("mm-stop").disabled = true;
        stopElapsedTicker();
      }
    });
  }

  if ($("mm-stop")) {
    $("mm-stop").addEventListener("click", async () => {
      $("mm-stop").disabled = true;
      $("mm-stop").textContent = "Stopping…";
      try {
        const r = await fetch("/api/micro-momentum/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("mm-stop").disabled = false;
          $("mm-stop").textContent = "Stop";
          return;
        }
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("mm-stop").disabled = false;
        $("mm-stop").textContent = "Stop";
      }
    });
  }

  poll();
})();
