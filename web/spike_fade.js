(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_spikefade_v1";
  let pollTimer = null;
  let elapsedTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let lastResult = null;
  let sortKey = "time";
  let sortDir = 1;
  let startedAt = null;
  let finishedAt = null;

  const FORM_IDS = [
    "sf-symbol",
    "sf-from",
    "sf-to",
    "sf-window",
    "sf-min",
    "sf-tp-pct",
    "sf-sl-pct",
    "sf-tp",
    "sf-sl",
    "sf-trail",
    "sf-arm",
    "sf-confirm",
    "sf-age",
    "sf-hold",
    "sf-cd",
    "sf-wknd",
    "sf-lag",
    "sf-workers",
    "sf-force",
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
      console.warn("spike fade save failed", e);
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
      console.warn("spike fade load failed", e);
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

  const REASON_TIP = {
    tp: "Hit take-profit (target pts from entry).",
    sl: "Hit the hard stop (initial SL, usually −2000 pts).",
    trail: "Hit the trailing stop (1000 pts behind the best price after +1000).",
    timeout:
      "Max hold reached (default 2 min). Price never hit TP, hard SL, or trail — closed at market, whatever P/L was.",
  };

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

  function holdMinutes(t) {
    var sec = holdSec(t);
    if (sec < 0) return "—";
    return (sec / 60).toFixed(2);
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
    const el = $("sf-elapsed");
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
    const label = running ? "elapsed " : "ran ";
    el.textContent = label + formatElapsed(endMs - startMs);
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
    document.querySelectorAll("#sf-table th.sf-sort").forEach(function (th) {
      const k = th.getAttribute("data-sort");
      th.classList.toggle("is-on", k === sortKey);
      const dir = th.querySelector(".dir");
      if (dir) dir.textContent = k === sortKey ? (sortDir > 0 ? "▲" : "▼") : "";
    });
  }

  function bindSortHeaders() {
    const table = $("sf-table");
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

  function render(result) {
    lastResult = result;
    const meta = $("sf-meta");
    const hero = $("sf-hero");
    const tb = $("sf-table") && $("sf-table").querySelector("tbody");
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
        " pts";
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("TP %", result.tp_pct != null ? result.tp_pct + "%" : "—") +
        heroItem("SL %", result.sl_pct != null ? result.sl_pct + "%" : "—") +
        heroItem("Trail %", result.trail_pct != null ? result.trail_pct + "%" : "—") +
        heroItem(
          "Timeout %",
          result.timeout_pct != null ? result.timeout_pct + "%" : "—",
          "Share of trades closed because max hold (2 min) expired — no TP, SL, or trail."
        ) +
        heroItem(
          "Avg pts",
          result.avg_pts,
          "Average P/L per trade in points (wins and losses together). 100 pts = $1 on XAU at 0.01 lot. Above 0 means the set made money in the backtest."
        ) +
        heroItem(
          "PF",
          result.profit_factor != null ? result.profit_factor : "—",
          "Profit factor = (sum of winning pts) ÷ (sum of losing pts). 1.0 = break-even, 2.0 = won twice what you lost. Empty if there were no losing trades."
        ) +
        heroItem(
          "Sum pts",
          result.sum_pts,
          "Total P/L of every trade added up, in points. The headline score for the whole date range."
        );
    }
    if (!tb) return;
    tb.innerHTML = "";
    updateSortHeaders();
    const rows = sortedRows(result.rows || []);
    if (!rows.length) {
      tb.innerHTML =
        '<tr><td colspan="11" class="muted">No trades in this window</td></tr>';
      return;
    }
    rows.forEach(function (t) {
      const tr = document.createElement("tr");
      const cls = t.pts > 0 ? "yes" : t.pts < 0 ? "no" : "";
      const why = t.exit_reason || "";
      tr.innerHTML =
        "<td>" +
        (t.entry_ts || "").replace("T", " ").slice(0, 19) +
        "</td><td>" +
        t.side +
        "</td><td>" +
        t.spike_dir +
        "</td><td>" +
        t.spike_pts +
        "</td><td>" +
        (t.tp_pts != null ? t.tp_pts : "—") +
        "</td><td>" +
        (t.sl_pts != null ? t.sl_pts : "—") +
        "</td><td>" +
        t.entry +
        "</td><td>" +
        (t.exit != null ? t.exit : "—") +
        "</td><td>" +
        holdMinutes(t) +
        "</td><td title=\"" +
        (REASON_TIP[why] || "") +
        '">' +
        reasonLabel(why) +
        '</td><td class="' +
        cls +
        '">' +
        t.pts +
        "</td>";
      tb.appendChild(tr);
    });
  }

  const LANE_HUES = [204, 158, 286, 22, 142, 338];

  function monthLabel(ln) {
    if (!ln || !ln.month) return "—";
    const a = String(ln.month).slice(0, 7);
    return a;
  }

  function renderLanes(st) {
    const el = $("sf-lanes");
    if (!el) return;
    const p = st.progress || {};
    let lanes = p.lanes || [];
    if (st.running && !lanes.length) {
      const n = Number(st.params && st.params.workers) || 4;
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
        const trades =
          ln.trades && phase !== "idle" ? ln.trades + " trades" : "";
        const pill =
          phase === "load" ? "load" : phase === "scan" ? "scan" : "idle";
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
    const r = await fetch("/api/spike-fade" + q);
    return r.json();
  }

  async function poll() {
    try {
      const st = await fetchState(false);
      const p = st.progress || {};
      const running = !!st.running;
      const pct = Number(p.pct) || 0;
      if ($("sf-progress-bar")) {
        $("sf-progress-bar").style.width = pct + "%";
      }
      if ($("sf-overall-pct")) {
        const md = p.months_done;
        const mt = p.months_total;
        $("sf-overall-pct").textContent =
          mt != null && mt > 0
            ? pct.toFixed(0) + "% · " + (md || 0) + "/" + mt
            : pct.toFixed(0) + "%";
      }
      if ($("sf-progress-msg")) {
        let msg = p.message || (running ? "Running…" : "Idle");
        if (p.phase === "error") msg = "Error: " + (p.message || "failed");
        $("sf-progress-msg").textContent = msg;
      }
      renderLanes(st);
      if ($("sf-run")) $("sf-run").disabled = running;
      if ($("sf-stop")) {
        $("sf-stop").disabled = !running;
        $("sf-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      if (p.started_at) startedAt = p.started_at;
      if (p.finished_at) finishedAt = p.finished_at;
      if (running) startElapsedTicker();
      else stopElapsedTicker();
      updateElapsedDisplay(running);
      const badge = $("status-badge");
      const finished =
        p.phase === "done" || p.phase === "cancelled";
      if (badge && running) {
        badge.textContent = st.cancel_requested ? "stopping" : "fade";
        badge.className = "badge run";
      }
      if (wasRunning && !running && finished) {
        if (badge) {
          badge.textContent = p.phase === "cancelled" ? "stopped" : "done";
          badge.className = "badge done";
        }
        const full = await fetchState(true);
        if (full.result) render(full.result);
      } else if (!running && st.result && finished) {
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

  loadForm();
  bindFormPersist();
  bindSortHeaders();

  if ($("sf-run")) {
    $("sf-run").addEventListener("click", async () => {
      const body = {
        symbol: $("sf-symbol").value,
        date_from: $("sf-from").value,
        date_to: $("sf-to").value,
        window_sec: Number($("sf-window").value),
        min_spike_pts: Number($("sf-min").value),
        tp_pct: Number($("sf-tp-pct") && $("sf-tp-pct").value),
        sl_pct: Number($("sf-sl-pct") && $("sf-sl-pct").value),
        tp_pts: Number($("sf-tp").value),
        sl_pts: Number($("sf-sl").value),
        trail_pts: Number($("sf-trail").value),
        trail_arm_pts: Number($("sf-arm") && $("sf-arm").value) || 0,
        confirm_pts: Number($("sf-confirm") && $("sf-confirm").value) || 0,
        max_extreme_age_sec: Number($("sf-age") && $("sf-age").value) || 0,
        max_hold_sec: Number($("sf-hold").value),
        cooldown_sec: Number($("sf-cd").value),
        weekend_blackout_min: Number($("sf-wknd").value),
        lag_sec: Number($("sf-lag") && $("sf-lag").value),
        workers: Number($("sf-workers") && $("sf-workers").value) || 3,
        force_download: $("sf-force") && $("sf-force").checked,
      };
      saveForm();
      $("sf-run").disabled = true;
      if ($("sf-stop")) $("sf-stop").disabled = false;
      startedAt = new Date().toISOString();
      finishedAt = null;
      startElapsedTicker();
      updateElapsedDisplay(true);
      $("sf-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/spike-fade/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("sf-run").disabled = false;
          if ($("sf-stop")) $("sf-stop").disabled = true;
          stopElapsedTicker();
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("sf-run").disabled = false;
        if ($("sf-stop")) $("sf-stop").disabled = true;
        stopElapsedTicker();
      }
    });
  }

  if ($("sf-stop")) {
    $("sf-stop").addEventListener("click", async () => {
      $("sf-stop").disabled = true;
      $("sf-stop").textContent = "Stopping…";
      try {
        const r = await fetch("/api/spike-fade/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("sf-stop").disabled = false;
          $("sf-stop").textContent = "Stop";
          return;
        }
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("sf-stop").disabled = false;
        $("sf-stop").textContent = "Stop";
      }
    });
  }

  poll();
})();
