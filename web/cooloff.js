(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_cooloff_v1";
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
    "co-symbol",
    "co-from",
    "co-to",
    "co-invert",
    "co-min-run",
    "co-tol",
    "co-range-min",
    "co-range-max",
    "co-rev-pct",
    "co-rev-min",
    "co-rev-max",
    "co-join-min",
    "co-join-max",
    "co-tp",
    "co-sl",
    "co-trail",
    "co-arm",
    "co-hold",
    "co-cd",
    "co-wknd",
    "co-workers",
    "co-force",
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
      console.warn("cooloff save failed", e);
    }
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveForm, 200);
  }

  function setInvert(on) {
    const v = on === true || on === 1 || on === "1" || on === "true";
    if ($("co-invert")) $("co-invert").value = v ? "1" : "0";
    const nat = $("co-side-nat");
    const opp = $("co-side-opp");
    if (nat) nat.classList.toggle("active", !v);
    if (opp) opp.classList.toggle("active", v);
    const hint = $("co-invert-hint");
    if (hint) {
      hint.textContent = v
        ? "Opposite = flip every fill (join becomes fade, reverse becomes continuation)."
        : "Natural = join with the run, reverse against a deep pullback.";
    }
  }

  function loadForm() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setInvert(false);
        return;
      }
      const cfg = JSON.parse(raw);
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el || cfg[id] == null) return;
        if (el.type === "checkbox") el.checked = !!cfg[id];
        else el.value = cfg[id];
      });
      const legacy = cfg["co-bias"];
      if (cfg["co-invert"] != null) setInvert(cfg["co-invert"]);
      else if (legacy === "DOWN") setInvert(true);
      else setInvert(false);
    } catch (e) {
      console.warn("cooloff load failed", e);
      setInvert(false);
    }
  }

  function bindFormPersist() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", scheduleSave);
      el.addEventListener("input", scheduleSave);
    });
    ["co-side-nat", "co-side-opp"].forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("click", function () {
        setInvert(el.getAttribute("data-invert") === "1");
        scheduleSave();
      });
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
    const el = $("co-elapsed");
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
      if (sortKey === "reason") {
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
    document.querySelectorAll("#co-table th.co-sort").forEach(function (th) {
      const k = th.getAttribute("data-sort");
      th.classList.toggle("is-on", k === sortKey);
      const dir = th.querySelector(".dir");
      if (dir) dir.textContent = k === sortKey ? (sortDir > 0 ? "▲" : "▼") : "";
    });
  }

  function bindSortHeaders() {
    const table = $("co-table");
    if (!table) return;
    table.querySelectorAll("th.co-sort").forEach(function (th) {
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

  function pctLabel(x) {
    if (x == null || !isFinite(x)) return "—";
    return (Number(x) * 100).toFixed(0) + "%";
  }

  function render(result) {
    lastResult = result;
    const meta = $("co-meta");
    const hero = $("co-hero");
    const tb = $("co-table") && $("co-table").querySelector("tbody");
    const totalEl = $("co-total-pts");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (tb) tb.innerHTML = "";
      if (totalEl) totalEl.textContent = "—";
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
        (result.params && result.params.invert ? "opposite fills" : "natural fills") +
        " · " +
        (result.trades || 0) +
        " trades · avg " +
        (result.avg_pts != null ? result.avg_pts : "—") +
        " pts" +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem(
          "Join",
          (result.join_n || 0) +
            (result.join_win_pct != null ? " · " + result.join_win_pct + "%" : "")
        ) +
        heroItem(
          "Reverse",
          (result.reverse_n || 0) +
            (result.reverse_win_pct != null
              ? " · " + result.reverse_win_pct + "%"
              : "")
        ) +
        heroItem("TP %", result.tp_pct != null ? result.tp_pct + "%" : "—") +
        heroItem("SL %", result.sl_pct != null ? result.sl_pct + "%" : "—") +
        heroItem("Avg pts", result.avg_pts) +
        heroItem(
          "PF",
          result.profit_factor != null ? result.profit_factor : "—"
        ) +
        heroItem("Sum pts", result.sum_pts);
    }
    if (!tb) return;
    tb.innerHTML = "";
    updateSortHeaders();
    const kindFilter = ($("co-kind-filter") && $("co-kind-filter").value) || "all";
    const rows = sortedRows(result.rows || []).filter(function (row) {
      return kindFilter === "all" || row.kind === kindFilter;
    });
    if (!rows.length) {
      tb.innerHTML =
        '<tr><td colspan="13" class="muted">No trades in this window</td></tr>';
      if (totalEl) {
        totalEl.textContent = "0 pts";
        totalEl.className = "";
      }
      return;
    }
    rows.forEach(function (t) {
      const tr = document.createElement("tr");
      const cls = t.pts > 0 ? "yes" : t.pts < 0 ? "no" : "";
      tr.innerHTML =
        "<td>" +
        (t.entry_ts || "").replace("T", " ").slice(0, 19) +
        "</td><td>" +
        (t.kind || "—") +
        (t.inverted ? " opp" : "") +
        "</td><td>" +
        (t.side || "—") +
        "</td><td>" +
        (t.run_dir || "—") +
        "</td><td>" +
        (t.run_length != null ? t.run_length : "—") +
        "</td><td>" +
        pctLabel(t.retrace) +
        "</td><td>" +
        (t.pause_bars != null ? t.pause_bars : "—") +
        "</td><td>" +
        (t.entry != null ? t.entry : "—") +
        "</td><td>" +
        (t.exit != null ? t.exit : "—") +
        '</td><td class="co-fav" title="Largest favorable move in points before exit or the max-hold timeout">' +
        (t.max_fav_pts != null ? t.max_fav_pts : "—") +
        '</td><td class="co-adv" title="Largest adverse move in points before exit or the max-hold timeout">' +
        (t.max_adv_pts != null ? t.max_adv_pts : "—") +
        "</td><td>" +
        (t.exit_reason || "—") +
        '</td><td class="' +
        cls +
        '">' +
        t.pts +
        "</td>";
      tb.appendChild(tr);
    });
    const totalPts = rows.reduce(function (sum, trade) {
      return sum + (Number(trade.pts) || 0);
    }, 0);
    if (totalEl) {
      totalEl.textContent = totalPts.toFixed(1) + " pts";
      totalEl.className = totalPts > 0 ? "yes" : totalPts < 0 ? "no" : "";
    }
  }

  const LANE_HUES = [204, 158, 286, 22, 142, 338];

  function monthLabel(ln) {
    if (!ln || !ln.month) return "—";
    return String(ln.month).slice(0, 7);
  }

  function renderLanes(st) {
    const el = $("co-lanes");
    if (!el) return;
    const p = st.progress || {};
    let lanes = p.lanes || [];
    if (st.running && !lanes.length) {
      const n = Number(st.params && st.params.workers) || 2;
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
    const r = await fetch("/api/cooloff" + q);
    return r.json();
  }

  async function poll() {
    try {
      const st = await fetchState(false);
      const p = st.progress || {};
      const running = !!st.running;
      const pct = Number(p.pct) || 0;
      if ($("co-progress-bar")) {
        $("co-progress-bar").style.width = pct + "%";
      }
      if ($("co-overall-pct")) {
        const md = p.months_done;
        const mt = p.months_total;
        $("co-overall-pct").textContent =
          mt != null && mt > 0
            ? pct.toFixed(0) + "% · " + (md || 0) + "/" + mt
            : pct.toFixed(0) + "%";
      }
      if ($("co-progress-msg")) {
        let msg = p.message || (running ? "Running…" : "Idle");
        if (p.phase === "error") msg = "Error: " + (p.message || "failed");
        $("co-progress-msg").textContent = msg;
      }
      renderLanes(st);
      if ($("co-run")) $("co-run").disabled = running;
      if ($("co-stop")) {
        $("co-stop").disabled = !running;
        $("co-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      if (p.started_at) startedAt = p.started_at;
      if (p.finished_at) finishedAt = p.finished_at;
      if (running) startElapsedTicker();
      else stopElapsedTicker();
      updateElapsedDisplay(running);
      const badge = $("status-badge");
      const finished = p.phase === "done" || p.phase === "cancelled";
      if (badge && running) {
        badge.textContent = st.cancel_requested ? "stopping" : "cool-off";
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

  loadForm();
  bindFormPersist();
  bindSortHeaders();
  if ($("co-kind-filter")) {
    $("co-kind-filter").addEventListener("change", function () {
      if (lastResult) render(lastResult);
    });
  }

  if ($("co-run")) {
    $("co-run").addEventListener("click", async () => {
      const body = {
        symbol: $("co-symbol").value,
        date_from: $("co-from").value,
        date_to: $("co-to").value,
        invert: ($("co-invert") && $("co-invert").value) === "1",
        min_run: Number($("co-min-run").value),
        max_tolerance: Number($("co-tol").value),
        min_run_range_pts: Number($("co-range-min").value) || 0,
        max_run_range_pts: Number($("co-range-max").value) || 0,
        reverse_frac: Number($("co-rev-pct").value) / 100,
        reverse_min_bars: Number($("co-rev-min").value),
        reverse_max_bars: Number($("co-rev-max").value),
        join_min_bars: Number($("co-join-min").value),
        join_max_bars: Number($("co-join-max").value),
        tp_pts: Number($("co-tp").value),
        sl_pts: Number($("co-sl").value),
        trail_pts: Number($("co-trail").value) || 0,
        trail_arm_pts: Number($("co-arm").value) || 0,
        max_hold_hours: Number($("co-hold").value),
        cooldown_min: Number($("co-cd").value) || 0,
        weekend_blackout_min: Number($("co-wknd").value) || 0,
        workers: Number($("co-workers").value) || 2,
        force_download: $("co-force") && $("co-force").checked,
      };
      saveForm();
      savedPicker.clearViewing();
      $("co-run").disabled = true;
      if ($("co-stop")) $("co-stop").disabled = false;
      startedAt = new Date().toISOString();
      finishedAt = null;
      startElapsedTicker();
      updateElapsedDisplay(true);
      $("co-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/cooloff/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("co-run").disabled = false;
          if ($("co-stop")) $("co-stop").disabled = true;
          stopElapsedTicker();
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("co-run").disabled = false;
        if ($("co-stop")) $("co-stop").disabled = true;
        stopElapsedTicker();
      }
    });
  }

  if ($("co-stop")) {
    $("co-stop").addEventListener("click", async () => {
      $("co-stop").disabled = true;
      $("co-stop").textContent = "Stopping…";
      try {
        const r = await fetch("/api/cooloff/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("co-stop").disabled = false;
          $("co-stop").textContent = "Stop";
          return;
        }
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 400);
        poll();
      } catch (e) {
        alert(String(e));
        $("co-stop").disabled = false;
        $("co-stop").textContent = "Stop";
      }
    });
  }

  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "cooloff",
      selectId: "co-saved",
      buttonId: "co-load",
      onLoaded: function (json) {
        render(json);
      },
    });
  }

  poll();
})();
