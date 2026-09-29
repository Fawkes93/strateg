(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_asia_liq_v1";
  let pollTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let savedPicker = {
    isViewingSaved: function () {
      return false;
    },
    clearViewing: function () {},
    refresh: function () {
      return Promise.resolve();
    },
  };

  const FORM_IDS = [
    "al-symbol",
    "al-from",
    "al-to",
    "al-clock",
    "al-wait",
    "al-mode-a",
    "al-mode-b",
    "al-htf",
    "al-box-min",
    "al-box-max",
    "al-compress",
    "al-body",
    "al-range-atr",
    "al-break-buf",
    "al-sweep-buf",
    "al-reclaim",
    "al-confirm",
    "al-tp2",
    "al-risk",
    "al-equity",
    "al-news-mode",
    "al-news-set",
    "al-spread",
    "al-spread-mult",
    "al-flatten",
    "al-workers",
    "al-force",
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
      console.warn("asia liq save failed", e);
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
      console.warn("asia liq load failed", e);
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

  function clockPreset() {
    const v = $("al-clock") && $("al-clock").value;
    if (v === "moldova") {
      return { timezone: "Europe/Chisinau", exec_timezone: "UTC" };
    }
    return { timezone: "UTC", exec_timezone: "UTC" };
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="asia-liq"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "asia-liq");
      btn.textContent = "Asia liquidity";
      nav.appendChild(btn);
    }
    if ($("tab-asia-liq")) return;

    const panel = document.createElement("div");
    panel.id = "tab-asia-liq";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Dual-Mode Asia Liquidity Engine</h2>
      <ol>
        <li>Lock the Asia box at <strong>07:00</strong> (UTC, or Moldova 07:00 which is 04:00 UTC in summer / 05:00 UTC in winter). The box does not update after lock.</li>
        <li>Skip days that fail width vs ATR, compression, or news.</li>
        <li>After London wait: <em>Mode A</em> continuation close-through with 4H, <strong>or</strong> <em>Mode B</em> sweep-and-reclaim. Never both.</li>
        <li>Partial TP (50% at TP1), flatten 16:00 UTC. Judge PF / avg R / max DD, not win rate.</li>
      </ol>
      <p class="hint">
        Different bot from Overnight break (that one is Bucharest + EMA pullback).
        Live news veto stays in Reaktor. If Mode B is ~0 EV, disable it per market.
      </p>
    </section>

    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="al-symbol">
            ${window.strategSymbols.optionsHtml()}
          </select>
        </label>
        <label>From
          <input type="date" id="al-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="al-to" value="2025-08-01" />
        </label>
        <label>Box lock
          <select id="al-clock" title="UTC = 00:00–07:00 UTC. Moldova = 00:00–07:00 Europe/Chisinau; execution stays London UTC.">
            <option value="utc" selected>UTC 07:00 lock</option>
            <option value="moldova">Moldova 07:00 lock (London UTC exec)</option>
          </select>
        </label>
        <label>London wait (min)
          <input type="number" id="al-wait" value="30" min="0" max="90" step="15" />
        </label>
        <label class="chk">Mode A continuation
          <input type="checkbox" id="al-mode-a" checked />
        </label>
        <label class="chk">Mode B sweep-reclaim
          <input type="checkbox" id="al-mode-b" checked />
        </label>
        <label class="chk">4H EMA50 filter (Mode A)
          <input type="checkbox" id="al-htf" checked />
        </label>
        <label>Box / ATR min
          <input type="number" id="al-box-min" value="0.25" min="0" step="0.05" />
        </label>
        <label>Box / ATR max
          <input type="number" id="al-box-max" value="0.85" min="0" step="0.05" />
        </label>
        <label>Compression lookback (days)
          <input type="number" id="al-compress" value="20" min="0" max="60"
            title="0 = off. Skip if today's box ≥ the 20-session average." />
        </label>
        <label>Body % of range
          <input type="number" id="al-body" value="50" min="0" max="100" step="5" />
        </label>
        <label>Break range × ATR
          <input type="number" id="al-range-atr" value="0.6" min="0" step="0.1" />
        </label>
        <label>Break buffer × ATR
          <input type="number" id="al-break-buf" value="0.1" min="0" step="0.05" />
        </label>
        <label>Sweep buffer × ATR
          <input type="number" id="al-sweep-buf" value="0.15" min="0" step="0.05" />
        </label>
        <label>Reclaim bars
          <input type="number" id="al-reclaim" value="4" min="1" max="8" />
        </label>
        <label class="chk">Mode B confirm bar
          <input type="checkbox" id="al-confirm" checked
            title="Enter on the next 15m if it does not re-break. Off = enter on reclaim close." />
        </label>
        <label>TP2
          <select id="al-tp2">
            <option value="nearer" selected>nearer of 1.8R and box</option>
            <option value="farther">farther of 1.8R and box</option>
          </select>
        </label>
        <label>Risk % equity
          <input type="number" id="al-risk" value="0.5" min="0.1" max="2" step="0.1" />
        </label>
        <label>Start equity
          <input type="number" id="al-equity" value="1000" min="100" step="100" />
        </label>
        <label>News days
          <select id="al-news-mode">
            <option value="off">off</option>
            <option value="tag">tag only</option>
            <option value="filter" selected>filter out</option>
          </select>
        </label>
        <label>News set
          <select id="al-news-set">
            <option value="scheduled" selected>scheduled (FOMC/CPI/NFP/JH)</option>
            <option value="all">all (incl. shocks)</option>
          </select>
        </label>
        <label class="chk">Spread filter
          <input type="checkbox" id="al-spread" checked />
        </label>
        <label>Spread × median
          <input type="number" id="al-spread-mult" value="1.5" min="1" step="0.1" />
        </label>
        <label>Flatten hour (exec clock)
          <input type="number" id="al-flatten" value="16" min="8" max="23" />
        </label>
        <label>Workers
          <input type="number" id="al-workers" value="3" min="1" max="6" />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="al-run">Run Asia liquidity</button>
        <button type="button" class="secondary" id="al-stop" disabled>Stop</button>
        <label class="chk force">
          <input type="checkbox" id="al-force" /> Force re-download
        </label>
      </div>
    </section>

    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap">
        <div class="progress-bar" id="al-progress-bar" style="width:0%"></div>
      </div>
      <p class="progress-msg" id="al-progress-msg">Idle</p>
      <div class="sf-lanes" id="al-lanes" hidden></div>
    </section>

    <section class="card" id="al-results-card">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="al-saved" title="Open a saved Asia liquidity run from results/"></select>
          <button type="button" class="secondary" id="al-load">Load</button>
        </div>
      </div>
      <p class="muted" id="al-meta">No run yet.</p>
      <div class="hero-grid" id="al-hero"></div>
      <h3>Mode A vs Mode B</h3>
      <div class="hero-grid" id="al-mode-hero"></div>
      <p class="table-note" id="al-skip-breakdown"></p>
      <h3>By month</h3>
      <div class="table-wrap">
        <table id="al-months">
          <thead>
            <tr>
              <th>Month</th><th>Trades</th><th>Skipped</th><th>Win %</th>
              <th>Sum R</th><th>Avg R</th><th>PF</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Hour of entry (UTC)</h3>
      <div class="table-wrap">
        <table id="al-hours">
          <thead>
            <tr><th>Hour</th><th>Trades</th><th>Win %</th><th>Avg R</th><th>Sum R</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Box height / ATR</h3>
      <div class="table-wrap">
        <table id="al-buckets">
          <thead>
            <tr><th>Bucket</th><th>Trades</th><th>Win %</th><th>Avg R</th><th>PF</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Walk-forward (18m / 6m, same rules)</h3>
      <p class="table-note">No parameter fit. Empty if the window is shorter than one fold.</p>
      <div class="table-wrap">
        <table id="al-wf">
          <thead>
            <tr>
              <th>Train</th><th>Test</th>
              <th>Train n</th><th>Train PF</th><th>Train R</th>
              <th>Test n</th><th>Test PF</th><th>Test R</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Trades</h3>
      <div class="table-wrap">
        <table id="al-table">
          <thead>
            <tr>
              <th>Date</th><th>Mode</th><th>Side</th><th>Box</th><th>ATR</th>
              <th>HTF</th><th>Entry</th><th>SL</th><th>TP1</th><th>TP2</th>
              <th>Exit</th><th>Reason</th><th>Pts</th><th>R</th><th>TP1?</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Skipped days</h3>
      <div class="table-wrap">
        <table id="al-skips">
          <thead>
            <tr>
              <th>Date</th><th>Reason</th><th>Box</th><th>ATR</th><th>HTF</th><th>Detail</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;

    const foot = document.querySelector("footer.foot");
    if (foot) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("Asia liquidity") < 0) {
      foot.textContent += " Asia liquidity = UTC/Moldova box, Mode A or Mode B.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-asia-liq");
        if (panel) panel.classList.toggle("hidden", tab !== "asia-liq");
        if (tab === "asia-liq") {
          [
            "tab-research",
            "tab-sweep",
            "tab-session",
            "tab-spikefade",
            "tab-micro",
            "tab-burst",
            "tab-cooloff",
            "tab-overnight",
            "tab-fvg",
            "tab-impulse-fork",
          ].forEach((id) => {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "asia-liq");
          } catch (e) {}
        }
      });
    });
    try {
      const tab = localStorage.getItem("strateg_tab");
      if (tab === "asia-liq") {
        const btn = document.querySelector('.main-tab[data-tab="asia-liq"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  const SKIP_REASONS = {
    no_candles: "No 15m candles",
    thin_asia: "Asia window too thin",
    box_too_tight: "Box too tight vs ATR",
    box_too_wide: "Box too wide vs ATR",
    not_compressed: "Not compressed vs 20-day Asia",
    compression_warmup: "Compression warmup",
    atr_warmup: "ATR warmup",
    news_day: "News day",
    news_window: "News window",
    no_setup: "No Mode A or B",
    wide_spread: "Spread too wide",
    weekly_halt: "Weekly halt",
    daily_halt: "Daily halt",
    one_per_day: "Already traded",
    no_entry_tick: "No fill tick",
    zero_stop: "Zero stop",
    box_not_locked: "Box not locked yet",
    open_bar: "Open bar",
  };

  function dash(v) {
    return v == null || v === "" ? "—" : v;
  }

  function heroItem(label, value) {
    return (
      '<div class="hero"><div class="k">' +
      label +
      '</div><div class="v">' +
      (value == null ? "—" : value) +
      "</div></div>"
    );
  }

  function skipLabel(code) {
    return SKIP_REASONS[code] || code || "—";
  }

  function num(v, d) {
    if (v == null || v === "") return "—";
    const n = Number(v);
    if (Number.isNaN(n)) return String(v);
    return d == null ? String(n) : n.toFixed(d);
  }

  function renderLanes(lanes) {
    const el = $("al-lanes");
    if (!el) return;
    if (!lanes || !lanes.length) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    el.innerHTML = lanes
      .map(function (ln) {
        const pct = ln.pct != null ? ln.pct : 0;
        return (
          '<div class="sf-lane"><div class="sf-lane-h">' +
          dash(ln.month) +
          " · " +
          dash(ln.detail) +
          '</div><div class="sf-lane-track"><div class="sf-lane-bar" style="width:' +
          pct +
          '%"></div></div></div>'
        );
      })
      .join("");
  }

  function modeStats(result, mode) {
    const m = result && result.by_mode && result.by_mode[mode];
    return m || {};
  }

  function fillKvTable(tbody, rows, cols) {
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!rows || !rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="' + cols + '" class="muted">None</td></tr>';
      return;
    }
    rows.forEach(function (html) {
      const tr = document.createElement("tr");
      tr.innerHTML = html;
      tbody.appendChild(tr);
    });
  }

  function render(result) {
    const meta = $("al-meta");
    const hero = $("al-hero");
    const modeHero = $("al-mode-hero");
    const breakdown = $("al-skip-breakdown");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (modeHero) modeHero.innerHTML = "";
      if (breakdown) breakdown.textContent = "";
      ["al-months", "al-hours", "al-buckets", "al-wf", "al-table", "al-skips"].forEach(
        function (id) {
          const tb = $(id) && $(id).querySelector("tbody");
          if (tb) tb.innerHTML = "";
        }
      );
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
        " trades · " +
        (result.skipped || 0) +
        " skipped · max DD " +
        (result.max_dd_pct != null ? result.max_dd_pct + "%" : "—") +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("PF", result.profit_factor != null ? result.profit_factor : "—") +
        heroItem("Avg R", result.avg_r) +
        heroItem("Sum R", result.sum_r) +
        heroItem("Max DD", result.max_dd_pct != null ? result.max_dd_pct + "%" : "—") +
        heroItem("Trades", result.trades) +
        heroItem("Skipped", result.skipped) +
        heroItem("Equity", result.equity);
    }
    if (modeHero) {
      const a = modeStats(result, "A");
      const b = modeStats(result, "B");
      modeHero.innerHTML =
        heroItem("A n", a.trades) +
        heroItem("A win%", a.win_pct != null ? a.win_pct + "%" : "—") +
        heroItem("A PF", a.profit_factor) +
        heroItem("A avg R", a.avg_r) +
        heroItem("B n", b.trades) +
        heroItem("B win%", b.win_pct != null ? b.win_pct + "%" : "—") +
        heroItem("B PF", b.profit_factor) +
        heroItem("B avg R", b.avg_r);
    }
    if (breakdown) {
      const reasons = result.skip_reasons || {};
      const parts = Object.keys(reasons)
        .sort()
        .map(function (k) {
          return skipLabel(k) + " " + reasons[k];
        });
      breakdown.textContent = parts.length ? "Skip reasons: " + parts.join(" · ") : "";
    }
    const mb = $("al-months") && $("al-months").querySelector("tbody");
    fillKvTable(
      mb,
      (result.by_month || []).map(function (m) {
        const sum = m.sum_r;
        const cls = sum > 0 ? "yes" : sum < 0 ? "no" : "";
        return (
          "<td>" +
          dash(m.month) +
          "</td><td>" +
          dash(m.trades) +
          "</td><td>" +
          dash(m.skipped) +
          "</td><td>" +
          (m.win_pct != null ? m.win_pct + "%" : "—") +
          '</td><td class="' +
          cls +
          '">' +
          dash(m.sum_r) +
          "</td><td>" +
          dash(m.avg_r) +
          "</td><td>" +
          dash(m.profit_factor) +
          "</td>"
        );
      }),
      7
    );
    const hb = $("al-hours") && $("al-hours").querySelector("tbody");
    const hours = result.by_hour || {};
    fillKvTable(
      hb,
      Object.keys(hours)
        .sort(function (a, b) {
          return Number(a) - Number(b);
        })
        .map(function (h) {
          const row = hours[h];
          return (
            "<td>" +
            h +
            "</td><td>" +
            dash(row.trades) +
            "</td><td>" +
            (row.win_pct != null ? row.win_pct + "%" : "—") +
            "</td><td>" +
            dash(row.avg_r) +
            "</td><td>" +
            dash(row.sum_r) +
            "</td>"
          );
        }),
      5
    );
    const bb = $("al-buckets") && $("al-buckets").querySelector("tbody");
    const buckets = result.box_buckets || {};
    fillKvTable(
      bb,
      Object.keys(buckets).map(function (k) {
        const row = buckets[k];
        return (
          "<td>" +
          k +
          "</td><td>" +
          dash(row.trades) +
          "</td><td>" +
          (row.win_pct != null ? row.win_pct + "%" : "—") +
          "</td><td>" +
          dash(row.avg_r) +
          "</td><td>" +
          dash(row.profit_factor) +
          "</td>"
        );
      }),
      5
    );
    const wf = $("al-wf") && $("al-wf").querySelector("tbody");
    fillKvTable(
      wf,
      (result.walk_forward || []).map(function (f) {
        const tr = f.train || {};
        const te = f.test || {};
        return (
          "<td>" +
          dash(f.train_from) +
          " → " +
          dash(f.train_to) +
          "</td><td>" +
          dash(f.test_from) +
          " → " +
          dash(f.test_to) +
          "</td><td>" +
          dash(tr.trades) +
          "</td><td>" +
          dash(tr.profit_factor) +
          "</td><td>" +
          dash(tr.avg_r) +
          "</td><td>" +
          dash(te.trades) +
          "</td><td>" +
          dash(te.profit_factor) +
          "</td><td>" +
          dash(te.avg_r) +
          "</td>"
        );
      }),
      8
    );
    const tb = $("al-table") && $("al-table").querySelector("tbody");
    fillKvTable(
      tb,
      (result.rows || []).map(function (r) {
        const cls = r.r > 0 ? "yes" : r.r < 0 ? "no" : "";
        return (
          "<td>" +
          dash(r.local_date) +
          "</td><td>" +
          dash(r.mode) +
          "</td><td>" +
          dash(r.side) +
          "</td><td>" +
          num(r.asia_low, 2) +
          "–" +
          num(r.asia_high, 2) +
          "</td><td>" +
          num(r.atr, 2) +
          "</td><td>" +
          dash(r.htf_side) +
          "</td><td>" +
          num(r.entry, 2) +
          "</td><td>" +
          num(r.sl, 2) +
          "</td><td>" +
          num(r.tp1, 2) +
          "</td><td>" +
          num(r.tp2, 2) +
          "</td><td>" +
          num(r.exit, 2) +
          "</td><td>" +
          dash(r.exit_reason) +
          '</td><td class="' +
          cls +
          '">' +
          dash(r.pts) +
          '</td><td class="' +
          cls +
          '">' +
          dash(r.r) +
          "</td><td>" +
          (r.tp1_hit ? "yes" : "") +
          "</td>"
        );
      }),
      15
    );
    const sb = $("al-skips") && $("al-skips").querySelector("tbody");
    fillKvTable(
      sb,
      (result.skips || []).map(function (s) {
        return (
          "<td>" +
          dash(s.local_date) +
          "</td><td>" +
          skipLabel(s.reason) +
          "</td><td>" +
          (s.asia_low != null ? num(s.asia_low, 2) + "–" + num(s.asia_high, 2) : "—") +
          "</td><td>" +
          num(s.atr, 2) +
          "</td><td>" +
          dash(s.htf_side) +
          "</td><td>" +
          dash(s.detail) +
          "</td>"
        );
      }),
      6
    );
  }

  function collectBody() {
    const clock = clockPreset();
    return {
      symbol: ($("al-symbol") && $("al-symbol").value) || "XAUUSD",
      date_from: ($("al-from") && $("al-from").value) || "2025-05-01",
      date_to: ($("al-to") && $("al-to").value) || "2025-08-01",
      timezone: clock.timezone,
      exec_timezone: clock.exec_timezone,
      london_wait_minutes: Number($("al-wait") && $("al-wait").value) || 0,
      mode_a_enabled: !!($("al-mode-a") && $("al-mode-a").checked),
      mode_b_enabled: !!($("al-mode-b") && $("al-mode-b").checked),
      htf_enabled: !!($("al-htf") && $("al-htf").checked),
      box_atr_min: Number($("al-box-min") && $("al-box-min").value),
      box_atr_max: Number($("al-box-max") && $("al-box-max").value),
      compression_lookback: Number($("al-compress") && $("al-compress").value) || 0,
      body_frac: (Number($("al-body") && $("al-body").value) || 0) / 100.0,
      min_range_atr: Number($("al-range-atr") && $("al-range-atr").value),
      break_buffer_atr: Number($("al-break-buf") && $("al-break-buf").value),
      sweep_buffer_atr: Number($("al-sweep-buf") && $("al-sweep-buf").value),
      reclaim_bars: Number($("al-reclaim") && $("al-reclaim").value) || 4,
      mode_b_confirm: !!($("al-confirm") && $("al-confirm").checked),
      tp2_select: ($("al-tp2") && $("al-tp2").value) || "nearer",
      risk_pct: Number($("al-risk") && $("al-risk").value) || 0.5,
      start_equity: Number($("al-equity") && $("al-equity").value) || 1000,
      news_mode: ($("al-news-mode") && $("al-news-mode").value) || "filter",
      news_set: ($("al-news-set") && $("al-news-set").value) || "scheduled",
      spread_filter: !!($("al-spread") && $("al-spread").checked),
      spread_mult: Number($("al-spread-mult") && $("al-spread-mult").value) || 1.5,
      flatten_hour: Number($("al-flatten") && $("al-flatten").value) || 16,
      workers: Number($("al-workers") && $("al-workers").value) || 3,
      force_download: !!($("al-force") && $("al-force").checked),
    };
  }

  function applyFormFromResult(result) {
    if (!result) return;
    const p = result.params || {};
    if (result.date_from && $("al-from")) $("al-from").value = String(result.date_from).slice(0, 10);
    if (result.date_to && $("al-to")) $("al-to").value = String(result.date_to).slice(0, 10);
    if ($("al-clock")) {
      $("al-clock").value =
        p.timezone && String(p.timezone).indexOf("Chisinau") >= 0 ? "moldova" : "utc";
    }
    const map = {
      london_wait_minutes: "al-wait",
      box_atr_min: "al-box-min",
      box_atr_max: "al-box-max",
      compression_lookback: "al-compress",
      min_range_atr: "al-range-atr",
      break_buffer_atr: "al-break-buf",
      sweep_buffer_atr: "al-sweep-buf",
      reclaim_bars: "al-reclaim",
      tp2_select: "al-tp2",
      risk_pct: "al-risk",
      start_equity: "al-equity",
      news_mode: "al-news-mode",
      news_set: "al-news-set",
      spread_mult: "al-spread-mult",
      flatten_hour: "al-flatten",
    };
    Object.keys(map).forEach(function (k) {
      if (p[k] == null || !$(map[k])) return;
      $(map[k]).value = String(p[k]);
    });
    if (p.body_frac != null && $("al-body")) $("al-body").value = String(Math.round(Number(p.body_frac) * 100));
    if ($("al-mode-a")) $("al-mode-a").checked = p.mode_a_enabled !== false;
    if ($("al-mode-b")) $("al-mode-b").checked = p.mode_b_enabled !== false;
    if ($("al-htf")) $("al-htf").checked = p.htf_enabled !== false;
    if ($("al-confirm")) $("al-confirm").checked = p.mode_b_confirm !== false;
    if ($("al-spread")) $("al-spread").checked = !!p.spread_filter;
    scheduleSave();
  }

  async function poll() {
    try {
      const r = await fetch("/api/asia-liquidity");
      const data = await r.json();
      const running = !!data.running;
      const prog = data.progress || {};
      if ($("al-progress-bar")) $("al-progress-bar").style.width = (prog.pct || 0) + "%";
      if ($("al-progress-msg")) $("al-progress-msg").textContent = prog.message || (running ? "Running…" : "Idle");
      if ($("al-run")) $("al-run").disabled = running;
      if ($("al-stop")) $("al-stop").disabled = !running;
      renderLanes(prog.lanes);
      if (data.result && (!running || wasRunning) && !savedPicker.isViewingSaved()) {
        render(data.result);
      }
      if (wasRunning && !running) {
        const badge = $("status-badge");
        if (badge && prog.phase === "done") {
          badge.textContent = "done";
          badge.className = "badge done";
        }
        if (prog.phase === "done" && window.StrategSaved && window.StrategSaved.playDone) {
          window.StrategSaved.playDone();
        }
        if (savedPicker.refresh) savedPicker.refresh();
      }
      wasRunning = running;
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "asia liq";
        badge.className = "badge run";
      }
    } catch (e) {
      console.error(e);
    }
  }

  function wireRun() {
    if ($("al-run")) {
      $("al-run").addEventListener("click", async function () {
        if (savedPicker.clearViewing) savedPicker.clearViewing();
        $("al-run").disabled = true;
        $("al-progress-msg").textContent = "Starting…";
        try {
          const r = await fetch("/api/asia-liquidity/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(collectBody()),
          });
          if (!r.ok) {
            const err = await r.json().catch(function () {
              return {};
            });
            alert(err.detail || "Could not start");
            $("al-run").disabled = false;
            return;
          }
          wasRunning = true;
          if (pollTimer) clearInterval(pollTimer);
          pollTimer = setInterval(poll, 800);
          poll();
        } catch (e) {
          alert(String(e));
          $("al-run").disabled = false;
        }
      });
    }
    if ($("al-stop")) {
      $("al-stop").addEventListener("click", async function () {
        try {
          await fetch("/api/asia-liquidity/stop", { method: "POST" });
          poll();
        } catch (e) {
          alert(String(e));
        }
      });
    }
  }

  ensureTab();
  loadForm();
  bindFormPersist();
  wireTabs();
  wireRun();
  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "asia_liquidity",
      selectId: "al-saved",
      buttonId: "al-load",
      onLoaded: function (json) {
        applyFormFromResult(json);
        render(json);
      },
    });
  }
  poll();
  if (!pollTimer) pollTimer = setInterval(poll, 2000);
})();
