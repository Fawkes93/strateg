(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_sweep_v1";

  let schema = null;
  let pollTimer = null;
  let elapsedTimer = null;
  let wasRunning = false;
  let lastReport = null;
  let saveTimer = null;
  let batchStartedAt = null; // ISO string from server
  let batchFinishedAt = null;
  /** Sweep report filters (research row label + engine + T). */
  let reportFilterRow = "";
  let reportFilterEngine = "";
  let reportFilterT = ""; // string form of numeric T, e.g. "500"
  let reportFilterBound = false;

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
    if (m > 0) {
      return m + "m " + String(sec).padStart(2, "0") + "s";
    }
    return sec + "s";
  }

  function updateElapsedDisplay(running) {
    const el = $("sw-elapsed");
    if (!el) return;
    if (!batchStartedAt) {
      el.textContent = "—";
      el.classList.remove("live");
      return;
    }
    const startMs = Date.parse(batchStartedAt);
    if (!isFinite(startMs)) {
      el.textContent = "—";
      return;
    }
    let endMs;
    if (running) {
      endMs = Date.now();
      el.classList.add("live");
    } else if (batchFinishedAt) {
      endMs = Date.parse(batchFinishedAt);
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

  // ----- persist form -----
  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveForm, 200);
  }

  function saveForm() {
    try {
      const cfg = {
        symbol: $("sw-symbol") && $("sw-symbol").value,
        hours: $("sw-hours") && $("sw-hours").value,
        adverse: $("sw-adverse") && $("sw-adverse").value,
        sl_manage: $("sw-sl-manage") && $("sw-sl-manage").value,
        sl_lock: $("sw-sl-lock") && $("sw-sl-lock").value,
        topn: $("sw-topn") && $("sw-topn").value,
        thresholds: $("sw-thresholds") && $("sw-thresholds").value,
        pairing: $("sw-pairing") && $("sw-pairing").value,
        workers: $("sw-workers") && $("sw-workers").value,
        test_range: $("sw-test-range") && $("sw-test-range").checked,
        test_spike: $("sw-test-spike") && $("sw-test-spike").checked,
        test_spike_neo: $("sw-test-spike-neo") && $("sw-test-spike-neo").checked,
        test_impulse_retrace: $("sw-test-impulse") && $("sw-test-impulse").checked,
        test_range_wick: $("sw-test-wick") && $("sw-test-wick").checked,
        date_ranges: [],
        range_rows: readExpRows("sw-range-table"),
        spike_rows: readExpRows("sw-spike-table"),
        spike_neo_rows: readExpRows("sw-neo-table"),
        impulse_retrace_rows: readExpRows("sw-impulse-table"),
        range_wick_rows: readExpRows("sw-wick-table"),
      };
      $("sw-ranges").querySelectorAll(".sw-range-row").forEach((row) => {
        cfg.date_ranges.push({
          from: row.querySelector(".sw-from").value,
          to: row.querySelector(".sw-to").value,
        });
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    } catch (e) {
      console.warn("sweep save failed", e);
    }
  }

  function loadForm() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // ----- tabs -----
  document.querySelectorAll(".main-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.getAttribute("data-tab");
      $("tab-research").classList.toggle("hidden", tab !== "research");
      $("tab-sweep").classList.toggle("hidden", tab !== "sweep");
      try {
        localStorage.setItem("strateg_tab", tab);
      } catch (e) {}
    });
  });

  // ----- date ranges -----
  function addRange(from, to) {
    const wrap = $("sw-ranges");
    const row = document.createElement("div");
    row.className = "sw-range-row";
    row.innerHTML =
      '<input type="date" class="sw-from" value="' +
      (from || "2026-04-01") +
      '" />' +
      '<span class="muted">→</span>' +
      '<input type="date" class="sw-to" value="' +
      (to || "2026-05-01") +
      '" />' +
      '<button type="button" class="secondary sw-rm">✕</button>';
    row.querySelector(".sw-rm").addEventListener("click", () => {
      row.remove();
      updateRunCount();
      scheduleSave();
    });
    row.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", () => {
        updateRunCount();
        scheduleSave();
      });
    });
    wrap.appendChild(row);
    updateRunCount();
    scheduleSave();
  }

  $("sw-add-range").addEventListener("click", () => addRange());

  // ----- experiment tables -----
  function buildExpTable(tableId, fields) {
    const table = $(tableId);
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    thead.innerHTML =
      "<tr>" +
      fields.map((f) => "<th title=\"" + f.full + "\">" + f.short + "</th>").join("") +
      "<th></th></tr>";
    tbody.innerHTML = "";
    return { table, tbody, fields };
  }

  function addExpRow(tbody, fields, values) {
    const tr = document.createElement("tr");
    fields.forEach((f) => {
      const td = document.createElement("td");
      const inp = document.createElement("input");
      inp.type = "text";
      inp.className = "exp-cell";
      inp.dataset.short = f.short;
      inp.placeholder = String(f.default);
      const v = values && values[f.short] != null ? values[f.short] : "";
      inp.value = v === "" || v == null ? "" : String(v);
      inp.title = f.full + " (default " + f.default + "). Comma-sep to expand.";
      // Live count: input + change + paste (delegation also covers these)
      ["input", "change", "keyup", "paste"].forEach(function (ev) {
        inp.addEventListener(ev, function () {
          // paste fires before value updates
          setTimeout(function () {
            updateRunCount();
            scheduleSave();
          }, 0);
        });
      });
      td.appendChild(inp);
      tr.appendChild(td);
    });
    const tdRm = document.createElement("td");
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "secondary";
    rm.textContent = "✕";
    rm.addEventListener("click", () => {
      tr.remove();
      updateRunCount();
      scheduleSave();
    });
    tdRm.appendChild(rm);
    tr.appendChild(tdRm);
    tbody.appendChild(tr);
    updateRunCount();
    scheduleSave();
  }

  function bindExpTableLive(tableId) {
    const table = $(tableId);
    if (!table || table.dataset.liveBound) return;
    table.dataset.liveBound = "1";
    function onEdit(e) {
      if (!e.target || !e.target.classList || !e.target.classList.contains("exp-cell"))
        return;
      setTimeout(function () {
        updateRunCount();
        scheduleSave();
      }, 0);
    }
    table.addEventListener("input", onEdit, true);
    table.addEventListener("change", onEdit, true);
    table.addEventListener("keyup", onEdit, true);
    table.addEventListener("paste", onEdit, true);
  }

  function readExpRows(tableId) {
    const rows = [];
    const root = $(tableId);
    if (!root) return rows;
    root.querySelectorAll("tbody tr").forEach((tr) => {
      // Explicit "defaults only" row (user clicked + Defaults)
      if (tr.classList.contains("exp-defaults-row")) {
        rows.push({});
        return;
      }
      const obj = {};
      let any = false;
      tr.querySelectorAll("input.exp-cell").forEach((inp) => {
        const v = (inp.value || "").trim();
        if (v !== "") {
          obj[inp.dataset.short] = v;
          any = true;
        }
      });
      // Blank placeholder rows do not count. Empty table = 0 experiments.
      if (any) rows.push(obj);
    });
    return rows;
  }

  /** How many variants one cell expands to (comma-separated). */
  function cellVariantCount(v) {
    const s = String(v == null ? "" : v).trim();
    if (!s) return 0;
    if (s.indexOf(",") < 0) return 1;
    const parts = s.split(",").map(function (x) {
      return x.trim();
    }).filter(Boolean);
    return parts.length || 1;
  }

  function countExpanded(rows) {
    if (!rows.length) return 0;
    let n = 0;
    rows.forEach((row) => {
      // {} = one explicit defaults experiment
      if (!row || !Object.keys(row).length) {
        n += 1;
        return;
      }
      let c = 1;
      let hasKey = false;
      Object.keys(row).forEach((k) => {
        const vc = cellVariantCount(row[k]);
        if (vc > 0) {
          hasKey = true;
          c *= vc;
        }
      });
      n += hasKey ? c : 0;
    });
    return n;
  }

  function expCountForTable(tableId, enabled) {
    if (!enabled) return { n: 0, hasRows: false, allDefaults: false, raw: 0 };
    const rows = readExpRows(tableId);
    if (!rows.length) return { n: 0, hasRows: false, allDefaults: false, raw: 0 };
    const allDefaults = rows.every(function (r) {
      return !r || !Object.keys(r).length;
    });
    const n = countExpanded(rows);
    return { n: n, hasRows: true, allDefaults: allDefaults, raw: n };
  }

  function updateRunCount() {
    const el = $("sw-run-count");
    if (!el) return;
    const ranges = $("sw-ranges")
      ? $("sw-ranges").querySelectorAll(".sw-range-row").length
      : 0;
    const testR = $("sw-test-range") && $("sw-test-range").checked;
    const testS = $("sw-test-spike") && $("sw-test-spike").checked;
    const testN = $("sw-test-spike-neo") && $("sw-test-spike-neo").checked;
    const testI = $("sw-test-impulse") && $("sw-test-impulse").checked;
    const testW = $("sw-test-wick") && $("sw-test-wick").checked;
    const rInfo = expCountForTable("sw-range-table", testR);
    const sInfo = expCountForTable("sw-spike-table", testS);
    const nInfo = expCountForTable("sw-neo-table", testN);
    const iInfo = expCountForTable("sw-impulse-table", testI);
    const wInfo = expCountForTable("sw-wick-table", testW);
    const rawR = testR ? rInfo.raw : 0;
    const rawS = testS ? sInfo.raw : 0;
    const rawN = testN ? nInfo.raw : 0;
    const rawI = testI ? iInfo.raw : 0;
    const rawW = testW ? wInfo.raw : 0;
    let nR = rInfo.n;
    let nS = sInfo.n;
    let nNeo = nInfo.n;
    let nIr = iInfo.n;
    let nW = wInfo.n;
    let partnerNote = "";
    const anyFilled = nR + nS + nNeo + nIr + nW > 0;
    if (anyFilled) {
      if (testR && nR === 0) {
        nR = 1;
        partnerNote = "range=defaults partner";
      }
      if (testS && nS === 0) {
        nS = 1;
        partnerNote = (partnerNote ? partnerNote + "; " : "") + "spike=defaults partner";
      }
      if (testN && nNeo === 0) {
        nNeo = 1;
        partnerNote = (partnerNote ? partnerNote + "; " : "") + "neo=defaults partner";
      }
      if (testI && nIr === 0) {
        nIr = 1;
        partnerNote = (partnerNote ? partnerNote + "; " : "") + "impulse=defaults partner";
      }
      if (testW && nW === 0) {
        nW = 1;
        partnerNote = (partnerNote ? partnerNote + "; " : "") + "wick=defaults partner";
      }
    }
    let pairing = ($("sw-pairing") && $("sw-pairing").value) || "together";
    if (
      pairing === "zip" ||
      pairing === "independent" ||
      pairing === "by_alert"
    ) {
      pairing = "together";
    }
    let perDate = 0;
    if (!testR && !testS && !testN && !testI && !testW) {
      perDate = 0;
    } else if (nR === 0 && nS === 0 && nNeo === 0 && nIr === 0 && nW === 0) {
      perDate = 0;
    } else if (pairing === "grid") {
      const parts = [];
      if (testR) parts.push(nR || 1);
      if (testS) parts.push(nS || 1);
      if (testN) parts.push(nNeo || 1);
      if (testI) parts.push(nIr || 1);
      if (testW) parts.push(nW || 1);
      perDate = parts.reduce(function (a, b) {
        return a * b;
      }, 1);
    } else {
      const parts = [];
      if (testR) parts.push(nR);
      if (testS) parts.push(nS);
      if (testN) parts.push(nNeo);
      if (testI) parts.push(nIr);
      if (testW) parts.push(nW);
      perDate = Math.max.apply(null, parts.length ? parts : [0]);
    }
    const n = ranges * perDate;

    const live =
      "range " +
      (testR ? rawR : "off") +
      " · spike " +
      (testS ? rawS : "off") +
      " · neo " +
      (testN ? rawN : "off") +
      " · impulse " +
      (testI ? rawI : "off") +
      " · wick " +
      (testW ? rawW : "off");

    if (!ranges) {
      el.textContent = live + " · Add date ranges";
      return;
    }
    if (!testR && !testS && !testN && !testI && !testW) {
      el.textContent = live + " · Enable at least one engine";
      return;
    }
    if (perDate === 0) {
      el.textContent =
        live +
        " · 0 runs — fill a cell or “+ Defaults only”";
      return;
    }
    const bits = [];
    bits.push("~" + n + " runs");
    bits.push(ranges + " date" + (ranges === 1 ? "" : "s"));
    if (pairing === "grid") {
      bits.push("grid ×" + perDate);
    } else {
      bits.push("together ×" + perDate);
    }
    bits.push(live);
    if (partnerNote) bits.push(partnerNote);
    el.textContent = bits.join(" · ");
  }

  function addDefaultsOnlyRow(tbody) {
    const tr = document.createElement("tr");
    tr.className = "exp-defaults-row";
    const td = document.createElement("td");
    td.colSpan = 20;
    td.innerHTML =
      '<span class="exp-defaults-label">Reaktor defaults</span> ' +
      '<span class="muted">(no param overrides)</span>';
    const tdRm = document.createElement("td");
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "secondary";
    rm.textContent = "✕";
    rm.addEventListener("click", () => {
      tr.remove();
      updateRunCount();
      scheduleSave();
    });
    tdRm.appendChild(rm);
    tr.appendChild(td);
    tr.appendChild(tdRm);
    tbody.appendChild(tr);
    updateRunCount();
    scheduleSave();
  }

  function bindSaveOn(el) {
    if (!el) return;
    el.addEventListener("change", () => {
      updateRunCount();
      scheduleSave();
    });
    el.addEventListener("input", scheduleSave);
  }
  $("sw-test-range").addEventListener("change", () => {
    updateRunCount();
    scheduleSave();
  });
  $("sw-test-spike").addEventListener("change", () => {
    updateRunCount();
    scheduleSave();
  });
  if ($("sw-test-spike-neo")) {
    $("sw-test-spike-neo").addEventListener("change", () => {
      updateRunCount();
      scheduleSave();
    });
  }
  if ($("sw-test-impulse")) {
    $("sw-test-impulse").addEventListener("change", () => {
      updateRunCount();
      scheduleSave();
    });
  }
  if ($("sw-test-wick")) {
    $("sw-test-wick").addEventListener("change", () => {
      updateRunCount();
      scheduleSave();
    });
  }
  bindSaveOn($("sw-pairing"));
  bindSaveOn($("sw-workers"));
  bindSaveOn($("sw-symbol"));
  bindSaveOn($("sw-hours"));
  bindSaveOn($("sw-adverse"));
  bindSaveOn($("sw-sl-manage"));
  bindSaveOn($("sw-sl-lock"));
  bindSaveOn($("sw-topn"));
  bindSaveOn($("sw-thresholds"));

  // ----- run batch -----
  function buildConfig() {
    const date_ranges = [];
    $("sw-ranges").querySelectorAll(".sw-range-row").forEach((row) => {
      date_ranges.push({
        from: row.querySelector(".sw-from").value,
        to: row.querySelector(".sw-to").value,
      });
    });
    const thr = ($("sw-thresholds").value || "")
      .split(",")
      .map((x) => Number(x.trim()))
      .filter((x) => isFinite(x));
    const workers = Number(($("sw-workers") && $("sw-workers").value) || 4);
    return {
      symbol: $("sw-symbol").value,
      hours: Number($("sw-hours").value),
      adverse_mult: Number($("sw-adverse").value) / 100,
      sl_manage: ($("sw-sl-manage") && $("sw-sl-manage").value) || "off",
      sl_manage_at_frac: 0.5,
      sl_manage_lock_pts: Number(($("sw-sl-lock") && $("sw-sl-lock").value) || 100),
      top_n: Number($("sw-topn").value) || 3,
      workers: isFinite(workers) && workers > 0 ? workers : 4,
      thresholds: thr,
      test_range: $("sw-test-range").checked,
      test_spike: $("sw-test-spike").checked,
      test_spike_neo: $("sw-test-spike-neo") && $("sw-test-spike-neo").checked,
      test_impulse_retrace: $("sw-test-impulse") && $("sw-test-impulse").checked,
      test_range_wick: $("sw-test-wick") && $("sw-test-wick").checked,
      pairing: ($("sw-pairing") && $("sw-pairing").value) || "together",
      date_ranges,
      range_rows: readExpRows("sw-range-table"),
      spike_rows: readExpRows("sw-spike-table"),
      spike_neo_rows: readExpRows("sw-neo-table"),
      impulse_retrace_rows: readExpRows("sw-impulse-table"),
      range_wick_rows: readExpRows("sw-wick-table"),
      filters: {}, // defaults from server apply_overrides
    };
  }

  function playDone() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var now = ctx.currentTime;
      [523.25, 659.25, 783.99].forEach(function (freq, i) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.setValueAtTime(0.0001, now);
        g.gain.exponentialRampToValueAtTime(0.1, now + 0.02 + i * 0.1);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.4 + i * 0.1);
        o.connect(g);
        g.connect(ctx.destination);
        o.start(now + i * 0.1);
        o.stop(now + 0.5 + i * 0.1);
      });
    } catch (e) {}
  }

  async function pollBatch() {
    try {
      const r = await fetch("/api/batch");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if (p.started_at) batchStartedAt = p.started_at;
      if (p.finished_at) batchFinishedAt = p.finished_at;
      else if (running) batchFinishedAt = null;

      $("sw-progress-bar").style.width = (p.pct || 0) + "%";
      $("sw-progress-msg").textContent = p.message || (running ? "Running…" : "Idle");
      $("sw-progress-stats").textContent = running
        ? "run " +
          (p.run_index || 0) +
          "/" +
          (p.run_total || 0) +
          (p.sub_message ? " · " + p.sub_message : "")
        : "";
      $("sw-run").disabled = running;
      if ($("sw-stop")) $("sw-stop").disabled = !running;
      $("status-badge").textContent = running
        ? st.cancel_requested
          ? "stopping"
          : "sweep"
        : p.phase || "idle";
      $("status-badge").className =
        "badge" +
        (running
          ? " run"
          : p.phase === "done" || p.phase === "cancelled"
            ? " done"
            : p.phase === "error"
              ? " err"
              : "");

      if (running) {
        startElapsedTicker();
        updateElapsedDisplay(true);
      } else {
        stopElapsedTicker();
        updateElapsedDisplay(false);
      }

      if (
        wasRunning &&
        !running &&
        (p.phase === "done" || p.phase === "cancelled")
      ) {
        playDone();
      }
      wasRunning = running;

      if (st.report) {
        lastReport = st.report;
        renderReport(st.report);
        $("sw-pdf").disabled = false;
      }
      if (!running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (e) {
      console.error(e);
    }
  }

  function fmt(v) {
    if (v == null) return "—";
    return typeof v === "number" ? v : v;
  }

  function engineLabel(eng) {
    if (eng === "candle") return "Range live";
    if (eng === "spike_neo") return "Spike Neo";
    if (eng === "impulse_retrace") return "Impulse retrace (all)";
    if (eng && eng.indexOf("impulse_retrace_") === 0) {
      var pct = eng.split("_").pop();
      return "Impulse retrace " + pct + "%";
    }
    if (eng === "candle_wick" || eng === "range_wick") return "Range wick";
    if (eng === "spike") return "Spike";
    return eng || "engine";
  }

  function collectReportOptions(report) {
    const labels = new Set();
    const engines = new Set();
    const tSet = new Set();
    function addT(v) {
      if (v == null || v === "") return;
      const n = Number(v);
      if (isFinite(n)) tSet.add(n);
    }
    (report && report.thresholds ? report.thresholds : []).forEach(addT);
    const by = (report && report.by_date_range) || {};
    Object.keys(by).forEach(function (rangeKey) {
      (by[rangeKey] || []).forEach(function (row) {
        if (row && row.label) labels.add(String(row.label));
        if (row && row.engine) engines.add(String(row.engine));
        (row.top_ts || []).forEach(function (t) {
          if (t) addT(t.T);
        });
        (row.all_ts || []).forEach(function (t) {
          if (t) addT(t.T);
        });
      });
    });
    const ts = Array.from(tSet).sort(function (a, b) {
      return a - b;
    });
    return {
      labels: Array.from(labels).sort(),
      engines: Array.from(engines).sort(),
      thresholds: ts.map(String),
    };
  }

  function tMatchesFilter(tRow) {
    if (!reportFilterT) return true;
    if (!tRow || tRow.T == null) return false;
    return String(tRow.T) === String(reportFilterT);
  }

  /** Stats rows for one experiment, after clean/topN (or fixed T filter). */
  function pickThresholdRows(row, report) {
    const MIN_CLEAN = 50;
    const topN = report.top_n || 3;
    function passesClean(t) {
      return t && t.clean_rate_pct != null && Number(t.clean_rate_pct) >= MIN_CLEAN;
    }

    // Specific T: show that threshold even if below clean% floor / outside top N
    if (reportFilterT) {
      const pool = []
        .concat(row.all_ts || [])
        .concat(row.top_ts || []);
      const hit = pool.find(function (t) {
        return tMatchesFilter(t);
      });
      return hit ? [hit] : [];
    }

    let topTs = (row.top_ts || []).filter(passesClean);
    if (topTs.length < topN && (row.all_ts || []).length) {
      topTs = (row.all_ts || [])
        .filter(passesClean)
        .slice()
        .sort(function (a, b) {
          const ca = Number(a.clean_rate_pct) || 0;
          const cb = Number(b.clean_rate_pct) || 0;
          if (cb !== ca) return cb - ca;
          const ha = Number(a.hit_rate_pct) || 0;
          const hb = Number(b.hit_rate_pct) || 0;
          if (hb !== ha) return hb - ha;
          return (Number(b.n) || 0) - (Number(a.n) || 0);
        })
        .slice(0, topN);
    }
    return topTs;
  }

  function fillSelect(sel, options, allLabel, selected) {
    if (!sel) return;
    const prev = selected != null ? selected : sel.value;
    sel.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = allLabel;
    sel.appendChild(optAll);
    options.forEach(function (v) {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      sel.appendChild(o);
    });
    // Keep selection if still present
    const has = Array.from(sel.options).some(function (o) {
      return o.value === prev;
    });
    sel.value = has ? prev : "";
    return sel.value;
  }

  function updateReportFilters(report) {
    const wrap = $("sw-report-filters");
    const rowSel = $("sw-filter-row");
    const engSel = $("sw-filter-engine");
    const tSel = $("sw-filter-t");
    if (!wrap || !rowSel || !engSel || !tSel) return;
    const opts = collectReportOptions(report);
    if (!opts.labels.length && !opts.engines.length && !opts.thresholds.length) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    reportFilterRow = fillSelect(
      rowSel,
      opts.labels,
      "All research rows",
      reportFilterRow
    );
    // Engine select shows friendly labels as text, value = raw engine id
    const prevEng = reportFilterEngine;
    engSel.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "All engines";
    engSel.appendChild(optAll);
    opts.engines.forEach(function (eng) {
      const o = document.createElement("option");
      o.value = eng;
      o.textContent = engineLabel(eng) + " (" + eng + ")";
      engSel.appendChild(o);
    });
    const hasEng = Array.from(engSel.options).some(function (o) {
      return o.value === prevEng;
    });
    engSel.value = hasEng ? prevEng : "";
    reportFilterEngine = engSel.value;

    reportFilterT = fillSelect(
      tSel,
      opts.thresholds,
      "All T",
      reportFilterT
    );

    if (!reportFilterBound) {
      reportFilterBound = true;
      rowSel.addEventListener("change", function () {
        reportFilterRow = rowSel.value || "";
        if (lastReport) renderReport(lastReport);
      });
      engSel.addEventListener("change", function () {
        reportFilterEngine = engSel.value || "";
        if (lastReport) renderReport(lastReport);
      });
      tSel.addEventListener("change", function () {
        reportFilterT = tSel.value || "";
        if (lastReport) renderReport(lastReport);
      });
    }
  }

  function rowPassesFilters(row) {
    if (reportFilterRow && String(row.label || "") !== reportFilterRow) {
      return false;
    }
    if (reportFilterEngine && String(row.engine || "") !== reportFilterEngine) {
      return false;
    }
    // When filtering by T, only keep blocks that have stats for that T
    if (reportFilterT) {
      const pool = []
        .concat(row.all_ts || [])
        .concat(row.top_ts || []);
      const hasT = pool.some(function (t) {
        return tMatchesFilter(t);
      });
      if (!hasT) return false;
    }
    return true;
  }

  function renderReport(report) {
    const el = $("sw-report");
    $("sw-report-meta").textContent =
      (report.symbol || "") +
      " · " +
      (report.run_count || 0) +
      " runs · look-ahead " +
      report.hours +
      "h · top " +
      (report.top_n || 3) +
      " T by clean% (≥50%)" +
      (function () {
        const mode = report.sl_manage || "off";
        if (mode === "be") return " · SL ½T→BE";
        if (mode === "lock")
          return " · SL ½T→lock +" + (report.sl_manage_lock_pts || 100);
        return "";
      })();

    updateReportFilters(report);

    const by = report.by_date_range || {};
    let html = "";
    let shown = 0;
    let total = 0;
    Object.keys(by)
      .sort()
      .forEach((rangeKey) => {
        const rows = by[rangeKey] || [];
        const filtered = rows.filter(rowPassesFilters);
        total += rows.length;
        if (!filtered.length) return;
        html += "<h3 class=\"sw-range-title\">" + rangeKey + "</h3>";
        filtered.forEach((row) => {
          shown += 1;
          if (!row.ok) {
            html +=
              "<div class=\"sw-exp-fail\"><strong>" +
              (row.label || row.engine) +
              "</strong> · error: " +
              (row.error || "?") +
              "</div>";
            return;
          }
          html +=
            "<div class=\"sw-exp-block\"><div class=\"sw-exp-head\"><strong>" +
            engineLabel(row.engine) +
            "</strong> · " +
            (row.label || "") +
            " · n_alerts=" +
            fmt(row.alerts) +
            "</div>";
          html +=
            "<table class=\"sw-top\"><thead><tr>" +
            "<th>rank</th><th>T</th><th>n</th><th>Clean %</th><th>Hit %</th>" +
            "<th>avg clean dur (min)</th><th>avg fav</th><th>avg adv</th>" +
            "<th>armed %</th><th>BE/lock %</th><th>avg pts</th>" +
            "</tr></thead><tbody>";
          const topTs = pickThresholdRows(row, report);
          topTs.forEach((t, i) => {
            html +=
              "<tr>" +
              "<td>" +
              (i + 1) +
              "</td><td>" +
              t.T +
              "</td><td>" +
              fmt(t.n) +
              "</td><td>" +
              (t.clean_rate_pct != null ? t.clean_rate_pct + "%" : "—") +
              "</td><td>" +
              (t.hit_rate_pct != null ? t.hit_rate_pct + "%" : "—") +
              "</td><td>" +
              fmt(t.avg_clean_hit_min) +
              "</td><td>" +
              fmt(t.avg_max_fav) +
              "</td><td>" +
              fmt(t.avg_max_adv) +
              "</td><td>" +
              (t.manage_armed_pct != null ? t.manage_armed_pct + "%" : "—") +
              "</td><td>" +
              (t.stopped_manage_pct != null ? t.stopped_manage_pct + "%" : "—") +
              "</td><td>" +
              (t.avg_realized_pts != null ? t.avg_realized_pts : "—") +
              "</td></tr>";
          });
          if (!topTs.length) {
            html +=
              "<tr><td colspan=\"11\" class=\"muted\">" +
              (reportFilterT
                ? "no stats for T=" + reportFilterT
                : "no T with clean% ≥ 50") +
              "</td></tr>";
          }
          html += "</tbody></table></div>";
        });
      });
    const countEl = $("sw-filter-count");
    const anyFilter = !!(reportFilterRow || reportFilterEngine || reportFilterT);
    if (countEl) {
      if (anyFilter) {
        countEl.textContent =
          "showing " +
          shown +
          " / " +
          total +
          " blocks" +
          (reportFilterT ? " · T=" + reportFilterT : "");
      } else {
        countEl.textContent = total ? total + " blocks" : "";
      }
    }
    if (!html) {
      if (total && anyFilter) {
        el.innerHTML =
          "<p class=\"muted\">No blocks match the research row / engine / T filter.</p>";
      } else {
        el.innerHTML = "<p class=\"muted\">Empty report</p>";
      }
    } else {
      el.innerHTML = html;
    }
  }

  $("sw-run").addEventListener("click", async () => {
    const cfg = buildConfig();
    if (!cfg.date_ranges.length) {
      alert("Add at least one date range");
      return;
    }
    const nR = cfg.test_range ? (cfg.range_rows || []).length : 0;
    const nS = cfg.test_spike ? (cfg.spike_rows || []).length : 0;
    const nN = cfg.test_spike_neo ? (cfg.spike_neo_rows || []).length : 0;
    const nI = cfg.test_impulse_retrace
      ? (cfg.impulse_retrace_rows || []).length
      : 0;
    const nW = cfg.test_range_wick ? (cfg.range_wick_rows || []).length : 0;
    if (nR === 0 && nS === 0 && nN === 0 && nI === 0 && nW === 0) {
      alert(
        "No research rows. Fill a param cell, or click “+ Defaults only”."
      );
      return;
    }
    $("sw-run").disabled = true;
    if ($("sw-stop")) $("sw-stop").disabled = false;
    $("sw-progress-msg").textContent = "Starting batch…";
    batchStartedAt = new Date().toISOString();
    batchFinishedAt = null;
    startElapsedTicker();
    updateElapsedDisplay(true);
    try {
      const r = await fetch("/api/batch/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(err.detail || "Could not start batch");
        $("sw-run").disabled = false;
        if ($("sw-stop")) $("sw-stop").disabled = true;
        stopElapsedTicker();
        batchStartedAt = null;
        updateElapsedDisplay(false);
        return;
      }
      wasRunning = true;
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(pollBatch, 1000);
      pollBatch();
    } catch (e) {
      alert(String(e));
      $("sw-run").disabled = false;
      if ($("sw-stop")) $("sw-stop").disabled = true;
      stopElapsedTicker();
      batchStartedAt = null;
      updateElapsedDisplay(false);
    }
  });

  if ($("sw-stop")) {
    $("sw-stop").addEventListener("click", async () => {
      $("sw-stop").disabled = true;
      $("sw-progress-msg").textContent = "Stop requested…";
      try {
        const r = await fetch("/api/batch/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("sw-stop").disabled = false;
        }
      } catch (e) {
        alert(String(e));
        $("sw-stop").disabled = false;
      }
    });
  }

  $("sw-pdf").addEventListener("click", () => {
    if (!lastReport) return;
    document.body.classList.add("print-sweep");
    const prev = document.title;
    document.title = "Strateg_sweep_" + (lastReport.finished_at || "").slice(0, 10);
    window.print();
    document.title = prev;
    document.body.classList.remove("print-sweep");
  });

  // init
  async function init() {
    const saved = loadForm();
    try {
      const r = await fetch("/api/batch/schema");
      schema = await r.json();
      $("sw-range-hint").textContent =
        "Short names: " +
        (schema.range_fields || []).map((f) => f.short).join(" · ") +
        ". " +
        (schema.hint || "") +
        " Inputs are saved in this browser.";
      $("sw-spike-hint").textContent =
        "Short names: " +
        (schema.spike_fields || []).map((f) => f.short).join(" · ") +
        ". " +
        (schema.hint || "");
      if ($("sw-neo-hint")) {
        $("sw-neo-hint").textContent =
          "Short names: " +
          (schema.spike_neo_fields || []).map((f) => f.short).join(" · ") +
          ". " +
          (schema.hint || "");
      }
      if ($("sw-impulse-hint")) {
        $("sw-impulse-hint").textContent =
          "Short names: " +
          (schema.impulse_retrace_fields || []).map((f) => f.short).join(" · ") +
          ". " +
          (schema.hint || "");
      }
      if ($("sw-wick-hint")) {
        $("sw-wick-hint").textContent =
          "Short names: " +
          (schema.range_wick_fields || []).map((f) => f.short).join(" · ") +
          ". " +
          (schema.hint || "");
      }
      buildExpTable("sw-range-table", schema.range_fields || []);
      buildExpTable("sw-spike-table", schema.spike_fields || []);
      if ($("sw-neo-table")) {
        buildExpTable("sw-neo-table", schema.spike_neo_fields || []);
      }
      if ($("sw-impulse-table")) {
        buildExpTable("sw-impulse-table", schema.impulse_retrace_fields || []);
      }
      if ($("sw-wick-table")) {
        buildExpTable("sw-wick-table", schema.range_wick_fields || []);
      }
      bindExpTableLive("sw-range-table");
      bindExpTableLive("sw-spike-table");
      if ($("sw-neo-table")) bindExpTableLive("sw-neo-table");
      if ($("sw-impulse-table")) bindExpTableLive("sw-impulse-table");
      if ($("sw-wick-table")) bindExpTableLive("sw-wick-table");

      // Restore saved form or seed defaults
      if (saved) {
        if (saved.symbol && $("sw-symbol")) $("sw-symbol").value = saved.symbol;
        if (saved.hours && $("sw-hours")) $("sw-hours").value = saved.hours;
        if (saved.adverse != null && $("sw-adverse"))
          $("sw-adverse").value = saved.adverse;
        if (saved.sl_manage && $("sw-sl-manage"))
          $("sw-sl-manage").value = saved.sl_manage;
        if (saved.sl_lock != null && $("sw-sl-lock"))
          $("sw-sl-lock").value = saved.sl_lock;
        if (saved.topn != null && $("sw-topn")) $("sw-topn").value = saved.topn;
        if (saved.thresholds && $("sw-thresholds"))
          $("sw-thresholds").value = saved.thresholds;
        if (saved.pairing && $("sw-pairing")) {
          var p = saved.pairing;
          if (p === "zip" || p === "independent" || p === "by_alert") p = "together";
          $("sw-pairing").value = p;
        }
        if (saved.workers != null && $("sw-workers")) {
          $("sw-workers").value = String(saved.workers);
        }
        if (typeof saved.test_range === "boolean")
          $("sw-test-range").checked = saved.test_range;
        if (typeof saved.test_spike === "boolean")
          $("sw-test-spike").checked = saved.test_spike;
        if (typeof saved.test_spike_neo === "boolean" && $("sw-test-spike-neo"))
          $("sw-test-spike-neo").checked = saved.test_spike_neo;
        if (typeof saved.test_impulse_retrace === "boolean" && $("sw-test-impulse"))
          $("sw-test-impulse").checked = saved.test_impulse_retrace;
        if (typeof saved.test_range_wick === "boolean" && $("sw-test-wick"))
          $("sw-test-wick").checked = saved.test_range_wick;

        $("sw-ranges").innerHTML = "";
        const dr = saved.date_ranges || [];
        if (dr.length) {
          dr.forEach((d) => addRange(d.from, d.to));
        } else {
          addRange("2026-04-01", "2026-05-01");
        }

        const rFields = schema.range_fields || [];
        const sFields = schema.spike_fields || [];
        const nFields = schema.spike_neo_fields || [];
        const rBody = $("sw-range-table").querySelector("tbody");
        const sBody = $("sw-spike-table").querySelector("tbody");
        const nBody = $("sw-neo-table") && $("sw-neo-table").querySelector("tbody");
        const iBody =
          $("sw-impulse-table") && $("sw-impulse-table").querySelector("tbody");
        const wBody =
          $("sw-wick-table") && $("sw-wick-table").querySelector("tbody");
        const iFields = schema.impulse_retrace_fields || [];
        const wFields = schema.range_wick_fields || [];
        const rRows = Array.isArray(saved.range_rows) ? saved.range_rows : [];
        const sRows = Array.isArray(saved.spike_rows) ? saved.spike_rows : [];
        const nRows = Array.isArray(saved.spike_neo_rows) ? saved.spike_neo_rows : [];
        const iRows = Array.isArray(saved.impulse_retrace_rows)
          ? saved.impulse_retrace_rows
          : [];
        const wRows = Array.isArray(saved.range_wick_rows)
          ? saved.range_wick_rows
          : [];
        rRows.forEach((row) => {
          if (!row || !Object.keys(row).length) addDefaultsOnlyRow(rBody);
          else addExpRow(rBody, rFields, row);
        });
        sRows.forEach((row) => {
          if (!row || !Object.keys(row).length) addDefaultsOnlyRow(sBody);
          else addExpRow(sBody, sFields, row);
        });
        if (nBody) {
          nRows.forEach((row) => {
            if (!row || !Object.keys(row).length) addDefaultsOnlyRow(nBody);
            else addExpRow(nBody, nFields, row);
          });
        }
        if (iBody) {
          iRows.forEach((row) => {
            if (!row || !Object.keys(row).length) addDefaultsOnlyRow(iBody);
            else addExpRow(iBody, iFields, row);
          });
        }
        if (wBody) {
          wRows.forEach((row) => {
            if (!row || !Object.keys(row).length) addDefaultsOnlyRow(wBody);
            else addExpRow(wBody, wFields, row);
          });
        }
      } else {
        addRange("2026-04-01", "2026-05-01");
        addRange("2026-05-01", "2026-06-01");
        addRange("2026-07-01", "2026-08-01");
      }

      $("sw-add-range-row").addEventListener("click", () =>
        addExpRow(
          $("sw-range-table").querySelector("tbody"),
          schema.range_fields || [],
          {}
        )
      );
      $("sw-add-spike-row").addEventListener("click", () =>
        addExpRow(
          $("sw-spike-table").querySelector("tbody"),
          schema.spike_fields || [],
          {}
        )
      );
      if ($("sw-add-neo-row")) {
        $("sw-add-neo-row").addEventListener("click", () =>
          addExpRow(
            $("sw-neo-table").querySelector("tbody"),
            schema.spike_neo_fields || [],
            {}
          )
        );
      }
      if ($("sw-add-impulse-row")) {
        $("sw-add-impulse-row").addEventListener("click", () =>
          addExpRow(
            $("sw-impulse-table").querySelector("tbody"),
            schema.impulse_retrace_fields || [],
            {}
          )
        );
      }
      if ($("sw-add-wick-row")) {
        $("sw-add-wick-row").addEventListener("click", () =>
          addExpRow(
            $("sw-wick-table").querySelector("tbody"),
            schema.range_wick_fields || [],
            {}
          )
        );
      }
      $("sw-add-range-defaults").addEventListener("click", () =>
        addDefaultsOnlyRow($("sw-range-table").querySelector("tbody"))
      );
      $("sw-add-spike-defaults").addEventListener("click", () =>
        addDefaultsOnlyRow($("sw-spike-table").querySelector("tbody"))
      );
      if ($("sw-add-neo-defaults")) {
        $("sw-add-neo-defaults").addEventListener("click", () =>
          addDefaultsOnlyRow($("sw-neo-table").querySelector("tbody"))
        );
      }
      if ($("sw-add-impulse-defaults")) {
        $("sw-add-impulse-defaults").addEventListener("click", () =>
          addDefaultsOnlyRow($("sw-impulse-table").querySelector("tbody"))
        );
      }
      if ($("sw-add-wick-defaults")) {
        $("sw-add-wick-defaults").addEventListener("click", () =>
          addDefaultsOnlyRow($("sw-wick-table").querySelector("tbody"))
        );
      }
    } catch (e) {
      console.error(e);
    }

    // restore last tab
    try {
      const tab = localStorage.getItem("strateg_tab");
      if (tab === "sweep") {
        document.querySelector('.main-tab[data-tab="sweep"]').click();
      }
    } catch (e) {}

    updateRunCount();
    scheduleSave();
    pollBatch();
  }

  init();
})();
