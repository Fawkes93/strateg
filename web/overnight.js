(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_overnight_v1";
  let pollTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let savedPicker = {
    isViewingSaved: function () {
      return false;
    },
    clearViewing: function () {},
  };

  const FORM_IDS = [
    "ob-symbol",
    "ob-from",
    "ob-to",
    "ob-asia-start",
    "ob-asia-end",
    "ob-min-asia",
    "ob-break-up",
    "ob-break-dn",
    "ob-break-wick",
    "ob-max-break-candles",
    "ob-pullback-mode",
    "ob-ema",
    "ob-max-wait",
    "ob-wait-from-break",
    "ob-timeout",
    "ob-higher-close",
    "ob-resume-closes",
    "ob-late-short-wait",
    "ob-late-short-asia",
    "ob-side",
    "ob-seasonal-mode",
    "ob-seasonal-join",
    "ob-week2",
    "ob-trend-flat",
    "ob-news-mode",
    "ob-news-set",
    "ob-sl-mode",
    "ob-sl-fixed",
    "ob-sl-range-mult",
    "ob-tp-mode",
    "ob-tp-fixed",
    "ob-tp-range-mult",
    "ob-tp-r-mult",
    "ob-trail-arm-mode",
    "ob-trail-arm",
    "ob-trail-arm-cap",
    "ob-trail",
    "ob-max-hold",
    "ob-flatten",
    "ob-one-per-day",
    "ob-workers",
    "ob-force",
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
      console.warn("overnight save failed", e);
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
      // Removed pullback mode "ema" (= required + resume off).
      if (cfg["ob-pullback-mode"] === "ema") {
        if ($("ob-pullback-mode")) $("ob-pullback-mode").value = "required";
        if ($("ob-higher-close")) $("ob-higher-close").checked = false;
      }
    } catch (e) {
      console.warn("overnight load failed", e);
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

  function syncPullbackControls() {
    const mode = $("ob-pullback-mode") && $("ob-pullback-mode").value;
    const resume = $("ob-higher-close");
    const resumeCloses = $("ob-resume-closes");
    const timeout = $("ob-timeout");
    if (resume) resume.disabled = mode === "off";
    if (resumeCloses) {
      resumeCloses.disabled = mode === "off" || (resume && !resume.checked);
    }
    if (timeout) timeout.disabled = mode !== "preferred";
  }

  function syncTrailArmControls() {
    const mode = $("ob-trail-arm-mode") && $("ob-trail-arm-mode").value;
    const fixed = $("ob-trail-arm");
    const cap = $("ob-trail-arm-cap");
    if (fixed) {
      fixed.disabled = false;
      fixed.title =
        mode === "asia"
          ? "Ignored when Trail arm mode is Asia range (arm = Asia range, capped)."
          : "Profit (pts) before the trail turns on. 0 = off.";
    }
    if (cap) {
      cap.disabled = false;
      cap.title =
        mode === "asia"
          ? "Max trail-arm when using Asia range. 0 = no cap."
          : "Cap is used when Trail arm mode is Asia range. 0 = no cap. Always editable so you can set it before switching mode.";
    }
  }

  // ----- inject tab button + panel if missing (keeps index.html unchanged) -----
  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="overnight"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "overnight");
      btn.textContent = "Overnight break";
      nav.appendChild(btn);
    }

    if ($("tab-overnight")) return;

    const panel = document.createElement("div");
    panel.id = "tab-overnight";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Asia range breakout (Bucharest)</h2>
      <ol>
        <li>Lock the Asia high/low in <strong>Europe/Bucharest</strong> (default 00:00–07:00).</li>
        <li>First completed 15m bar that clears Asia by min break pts = break signal (close only, or wick if the toggle is on).</li>
        <li>Entry = first of: <em>EMA touch</em> or <em>higher/lower close resume</em> during the wait window (resume closes = consecutive directional closes; uncheck resume for EMA-only; break close if pullback = off). <em>Wait from break</em> counts max wait from the break bar instead of leftover Asia-break bars.</li>
        <li>No partial TP. Trail arms after a profit threshold (fixed pts, or Asia range with a cap), then trails. Flatten at local hour.</li>
      </ol>
      <p class="hint">
        Mid fill. One trade per day by default. Skips days with no valid break / no pullback (required mode).
        Seasonal month (optional): Jan/Aug long, May/Jun short. Filter skips the against-side break.
        Join inside box takes the combined bias side when price never left the Asia range.
        2-week trend: if it disagrees with the month, both are called out and the day trades with no side filter.
      </p>
    </section>

    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ob-symbol"><option value="XAUUSD" selected>XAUUSD (gold)</option></select>
        </label>
        <label>From (local date)
          <input type="date" id="ob-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="ob-to" value="2025-08-01" />
        </label>
        <label>Asia start hour
          <input type="number" id="ob-asia-start" value="0" min="0" max="23" />
        </label>
        <label>Asia end hour
          <input type="number" id="ob-asia-end" value="7" min="1" max="23" />
        </label>
        <label>Min Asia range (pts)
          <input type="number" id="ob-min-asia" value="300" min="0" step="50" />
        </label>
        <label>Min break above (pts)
          <input type="number" id="ob-break-up" value="200" min="0" step="50" />
        </label>
        <label>Min break below (pts)
          <input type="number" id="ob-break-dn" value="200" min="0" step="50" />
        </label>
        <label class="chk">Count wicks (not only close)
          <input type="checkbox" id="ob-break-wick"
            title="Off = 15m close must clear Asia by min break pts. On = a wick (high/low) of that size is enough even if the bar closes back inside." />
        </label>
        <label>Max break candles after Asia
          <input type="number" id="ob-max-break-candles" value="8" min="1" max="20" />
        </label>
        <label>Pullback mode
          <select id="ob-pullback-mode">
            <option value="required" selected>required (EMA or higher-close)</option>
            <option value="preferred">preferred (timeout action)</option>
            <option value="off">off (enter on break close)</option>
          </select>
        </label>
        <label>EMA period (15m)
          <input type="number" id="ob-ema" value="21" min="5" max="100" />
        </label>
        <label>Max wait candles
          <input type="number" id="ob-max-wait" value="8" min="1" max="20" />
        </label>
        <label class="chk">Wait from break
          <input type="checkbox" id="ob-wait-from-break"
            title="Off = wait only inside leftover max-break-after-Asia bars. On = count max wait candles from the actual break bar (not clipped by a late break)." />
        </label>
        <label>Timeout action (preferred)
          <select id="ob-timeout">
            <option value="skip" selected>skip</option>
            <option value="market">market</option>
            <option value="worst">worst</option>
          </select>
        </label>
        <label class="chk">Higher/lower close resume
          <input type="checkbox" id="ob-higher-close" checked />
        </label>
        <label>Resume closes
          <input type="number" id="ob-resume-closes" value="1" min="1" max="8" step="1" />
        </label>
        <label>Skip late short wait ≥
          <input type="number" id="ob-late-short-wait" value="7" min="0" max="20" step="1"
            title="Skip DOWN entries from this wait bar onward. 0 = off." />
        </label>
        <label>Skip late short if Asia &lt; (pts)
          <input type="number" id="ob-late-short-asia" value="3000" min="0" step="100"
            title="Only skip late shorts when Asia range is below this. 0 = any Asia size." />
        </label>
        <label>Side filter
          <select id="ob-side">
            <option value="both" selected>both</option>
            <option value="long">long only</option>
            <option value="short">short only</option>
          </select>
        </label>
        <label>Seasonal month
          <select id="ob-seasonal-mode"
            title="Bucharest month: Jan/Aug long bias, May/Jun short. Off = ignore. Tag = stamp only. Filter = skip the against-side Asia break.">
            <option value="off" selected>off</option>
            <option value="tag">tag only</option>
            <option value="filter">filter against-side</option>
          </select>
        </label>
        <label class="chk">Join inside box
          <input type="checkbox" id="ob-seasonal-join"
            title="If the combined bias has a side and Asia never printed a valid break, enter with that side instead of skipping no_break. Off when month and 2-week disagree." />
        </label>
        <label class="chk">2-week trend
          <input type="checkbox" id="ob-week2"
            title="Close-to-close over ~10 sessions before the Asia day. If it disagrees with the month, both are tagged and neither side is filtered." />
        </label>
        <label>Trend flat (pts)
          <input type="number" id="ob-trend-flat" value="1500" min="0" step="100"
            title="2-week net move below this is flat. Gold default 1500 pts = $15." />
        </label>
        <label>News days
          <select id="ob-news-mode"
            title="Days in backtest/xau_news_days.json (2023–2026). Off = ignore. Tag = stamp FOMC/CPI/NFP on the row. Filter = skip the whole local day.">
            <option value="off" selected>off</option>
            <option value="tag">tag only</option>
            <option value="filter">filter out</option>
          </select>
        </label>
        <label>News set
          <select id="ob-news-set"
            title="scheduled = FOMC + CPI + NFP + Jackson Hole. all = those plus unscheduled shocks (SVB, wars, tariffs, …).">
            <option value="scheduled" selected>scheduled (FOMC/CPI/NFP/JH)</option>
            <option value="all">all (incl. shocks)</option>
          </select>
        </label>
        <label>SL mode
          <select id="ob-sl-mode">
            <option value="asia_opposite" selected>asia opposite</option>
            <option value="fixed">fixed pts</option>
            <option value="range_width">range × mult</option>
          </select>
        </label>
        <label>SL fixed (pts)
          <input type="number" id="ob-sl-fixed" value="500" min="50" step="50" />
        </label>
        <label>SL range mult
          <input type="number" id="ob-sl-range-mult" value="1" min="0.1" step="0.1" />
        </label>
        <label>TP mode
          <select id="ob-tp-mode">
            <option value="range_mult" selected>range × mult</option>
            <option value="fixed">fixed pts</option>
            <option value="r_mult">R multiple</option>
          </select>
        </label>
        <label>TP fixed (pts)
          <input type="number" id="ob-tp-fixed" value="1000" min="50" step="50" />
        </label>
        <label>TP range mult
          <input type="number" id="ob-tp-range-mult" value="1.5" min="0.1" step="0.1" />
        </label>
        <label>TP R mult
          <input type="number" id="ob-tp-r-mult" value="2" min="0.5" step="0.1" />
        </label>
        <label>Trail arm mode
          <select id="ob-trail-arm-mode">
            <option value="fixed" selected>fixed pts</option>
            <option value="asia">Asia range (capped)</option>
          </select>
        </label>
        <label>Trail arm (pts profit)
          <input type="number" id="ob-trail-arm" value="400" min="0" step="50" />
        </label>
        <label>Trail arm cap (pts)
          <input type="number" id="ob-trail-arm-cap" value="2000" min="0" step="50"
            title="Max trail-arm when mode is Asia range. 0 = no cap." />
        </label>
        <label>Trail distance (pts)
          <input type="number" id="ob-trail" value="250" min="0" step="50" />
        </label>
        <label>Max hold (hours)
          <input type="number" id="ob-max-hold" value="10" min="1" max="24" step="0.5" />
        </label>
        <label>Flatten hour (Bucharest)
          <input type="number" id="ob-flatten" value="18" min="8" max="23" />
        </label>
        <label class="chk">One trade per day
          <input type="checkbox" id="ob-one-per-day" checked />
        </label>
        <label>Workers
          <input type="number" id="ob-workers" value="3" min="1" max="6" step="1"
            title="Parallel months (separate processes). Each worker holds one month of ticks." />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="ob-run">Run overnight break</button>
        <button type="button" class="secondary" id="ob-stop" disabled>Stop</button>
        <label class="chk force">
          <input type="checkbox" id="ob-force" /> Force re-download
        </label>
        <p class="table-note">
          Same dates reuse the tick pack (RAM + disk). Leave force off when you are only
          changing strategy params.
        </p>
      </div>
    </section>

    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap">
        <div class="progress-bar" id="ob-progress-bar" style="width:0%"></div>
      </div>
      <p class="progress-msg" id="ob-progress-msg">Idle</p>
      <div class="sf-lanes" id="ob-lanes" hidden></div>
    </section>

    <section class="card" id="ob-results-card">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="ob-saved" title="Open a saved overnight-break run from results/"></select>
          <button type="button" class="secondary" id="ob-load">Load</button>
        </div>
      </div>
      <p class="muted" id="ob-meta">No run yet.</p>
      <div class="hero-grid" id="ob-hero"></div>
      <p class="table-note" id="ob-skip-breakdown"></p>
      <h3>By month</h3>
      <p class="table-note">Same stats as the overall run, split by local-date month.</p>
      <div class="table-wrap">
        <table id="ob-months">
          <thead>
            <tr>
              <th>Month</th>
              <th>Trades</th>
              <th>Skipped</th>
              <th>Win %</th>
              <th>Sum pts</th>
              <th>Avg pts</th>
              <th>PF</th>
              <th>Avg win</th>
              <th>Avg loss</th>
              <th>Trail %</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Trades</h3>
      <p class="table-note">
        Entry = EMA touch, higher/lower close resume, or break close.
        Hover <strong>Decision</strong> for the full wait / EMA / close-vs-prev line.
        Max adv = worst mid against the trade after entry.
        Adv/SL = how much of the stop was used.
      </p>
      <div class="table-wrap">
        <table id="ob-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Side</th>
              <th>Asia range</th>
              <th>Break pts</th>
              <th>Entry</th>
              <th>Wait</th>
              <th>EMA</th>
              <th>Decision</th>
              <th>Fill</th>
              <th>SL</th>
              <th>SL pts</th>
              <th>Opp peak</th>
              <th>Max adv</th>
              <th>Adv/SL</th>
              <th>Max fav</th>
              <th>TP pts</th>
              <th>Exit</th>
              <th>Reason</th>
              <th>Arm</th>
              <th>Pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Skipped / failed days</h3>
      <p class="table-note">
        Every day that did not produce a trade, with the same decision factors
        (wait / EMA closest / best close vs prev). Opp peak after a break is from
        the break close until flatten.
      </p>
      <div class="table-wrap">
        <table id="ob-skips">
          <thead>
            <tr>
              <th>Date</th>
              <th>Reason</th>
              <th>Side</th>
              <th>Asia range</th>
              <th>Break</th>
              <th>Wait</th>
              <th>EMA</th>
              <th>Closest EMA</th>
              <th>Best resume</th>
              <th>Decision</th>
              <th>Opp peak</th>
              <th>Max adv</th>
              <th>Max fav</th>
              <th>Above Asia</th>
              <th>Below Asia</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;

    const foot = document.querySelector("footer.foot");
    if (foot) {
      foot.parentNode.insertBefore(panel, foot);
    } else {
      document.body.appendChild(panel);
    }

    // extend footer hint
    if (foot && foot.textContent.indexOf("Overnight") < 0) {
      foot.textContent += " Overnight break = Asia range + EMA/higher-close.";
    }
  }

  // Tab visibility: work with existing sweep.js handlers
  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-overnight");
        if (panel) panel.classList.toggle("hidden", tab !== "overnight");
        // when opening overnight, hide other known panels
        if (tab === "overnight") {
          ["tab-research", "tab-sweep", "tab-session", "tab-spikefade", "tab-micro", "tab-burst", "tab-cooloff"].forEach((id) => {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "overnight");
          } catch (e) {}
        }
      });
    });

    // restore last tab
    try {
      const tab = localStorage.getItem("strateg_tab");
      if (tab === "overnight") {
        const btn = document.querySelector('.main-tab[data-tab="overnight"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  const SKIP_REASONS = {
    no_candles: "No 15m candles",
    thin_asia: "Asia window too thin",
    asia_too_small: "Asia range below min",
    no_break: "No close outside Asia",
    side_filter: "Side filtered",
    no_entry_tick: "No tick at entry",
    no_pullback: "No EMA / close resume in wait",
    no_pullback_timeout: "Pullback timeout (skip)",
    late_short: "Late short on small/medium Asia",
    no_entry: "No entry",
    past_flatten: "Past flatten hour",
    seasonal_bias: "Season / 2-week bias",
    news_day: "News day",
  };

  const ENTRY_LABELS = {
    ema_touch: "EMA touch",
    higher_close: "Higher close resume",
    lower_close: "Lower close resume",
    break_close: "Break close",
    seasonal_join: "Seasonal join (inside box)",
    timeout_market: "Timeout market",
    timeout_worst: "Timeout worst",
  };

  function heroItem(label, value) {
    return (
      '<div class="hero"><div class="k">' +
      label +
      '</div><div class="v">' +
      (value == null ? "—" : value) +
      "</div></div>"
    );
  }

  function dash(v) {
    return v == null || v === "" ? "—" : v;
  }

  function pointSize(symbol) {
    const s = String(symbol || "").toUpperCase();
    if (s.indexOf("XAU") >= 0 || s.indexOf("GOLD") >= 0 || s.indexOf("BTC") >= 0) {
      return 0.01;
    }
    return 0.00001;
  }

  function oppPeakPrice(row, symbol) {
    if (row.max_adv_price != null) return row.max_adv_price;
    const pts = row.max_adv_pts;
    const entry = row.entry != null ? row.entry : row.break_price;
    if (pts == null || entry == null || !row.side) return null;
    const ps = pointSize(symbol);
    if (row.side === "UP") return Math.round((entry - pts * ps) * 1e5) / 1e5;
    if (row.side === "DOWN") return Math.round((entry + pts * ps) * 1e5) / 1e5;
    return null;
  }

  function advSlPct(row) {
    if (row.max_adv_pts == null || row.sl_pts == null || !(row.sl_pts > 0)) return null;
    return Math.round((100 * row.max_adv_pts) / row.sl_pts);
  }

  function skipLabel(code) {
    return SKIP_REASONS[code] || code || "—";
  }

  function entryLabel(row) {
    if (row.entry_label) return row.entry_label;
    if (row.entry_reason === "higher_close" && row.side === "DOWN") {
      return "Lower close resume";
    }
    return ENTRY_LABELS[row.entry_reason] || row.entry_reason || "—";
  }

  function waitCell(row) {
    if (row.wait_i == null && row.wait_n == null) return "—";
    const i = row.wait_i == null ? "—" : row.wait_i;
    const n = row.wait_n == null ? "—" : row.wait_n;
    return i + "/" + n;
  }

  function decisionCell(row) {
    return row.decision || entryLabel(row);
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function decisionTdHtml(text) {
    const t = text == null || text === "" ? "—" : String(text);
    if (t === "—") return '<td class="ob-decision">—</td>';
    return (
      '<td class="ob-decision" data-full="' +
      escapeAttr(t) +
      '">' +
      escapeHtml(t) +
      "</td>"
    );
  }

  function hideObTip() {
    const el = document.getElementById("ob-flytip");
    if (el) el.remove();
  }

  function showObTip(td) {
    hideObTip();
    const full = td && td.getAttribute("data-full");
    if (!full) return;
    const tip = document.createElement("div");
    tip.id = "ob-flytip";
    tip.className = "ob-flytip";
    const lines = full.split(" · ").filter(Boolean);
    tip.innerHTML =
      '<div class="k">Decision</div>' +
      lines.map(function (p) {
        return "<div>" + escapeHtml(p) + "</div>";
      }).join("");
    document.body.appendChild(tip);
    const r = td.getBoundingClientRect();
    const tw = tip.offsetWidth;
    const th = tip.offsetHeight;
    let left = r.left;
    let top = r.bottom + 6;
    if (left + tw > window.innerWidth - 8) left = window.innerWidth - tw - 8;
    if (left < 8) left = 8;
    if (top + th > window.innerHeight - 8) top = Math.max(8, r.top - th - 6);
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }

  function wireDecisionTips() {
    const card = $("ob-results-card");
    if (!card || card.dataset.tipWired) return;
    card.dataset.tipWired = "1";
    let current = null;
    card.addEventListener("pointerover", function (e) {
      const td = e.target.closest && e.target.closest("td.ob-decision");
      if (!td || !td.getAttribute("data-full")) return;
      if (td === current) return;
      current = td;
      showObTip(td);
    });
    card.addEventListener("pointerout", function (e) {
      const td = e.target.closest && e.target.closest("td.ob-decision");
      if (!td) return;
      const to = e.relatedTarget;
      if (to && td.contains(to)) return;
      if (current === td) current = null;
      hideObTip();
    });
    card.querySelectorAll(".table-wrap").forEach(function (w) {
      w.addEventListener("scroll", hideObTip);
    });
    window.addEventListener("scroll", hideObTip, true);
  }

  const LANE_HUES = [204, 158, 286, 22, 142, 338];

  function monthLabel(ln) {
    if (!ln || !ln.month) return "—";
    return String(ln.month).slice(0, 7);
  }

  function renderLanes(st) {
    const el = $("ob-lanes");
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

  function render(result) {
    const meta = $("ob-meta");
    const hero = $("ob-hero");
    const breakdown = $("ob-skip-breakdown");
    const mb = $("ob-months") && $("ob-months").querySelector("tbody");
    const tb = $("ob-table") && $("ob-table").querySelector("tbody");
    const sb = $("ob-skips") && $("ob-skips").querySelector("tbody");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (breakdown) breakdown.textContent = "";
      if (mb) mb.innerHTML = "";
      if (tb) tb.innerHTML = "";
      if (sb) sb.innerHTML = "";
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
        " skipped · avg " +
        (result.avg_pts != null ? result.avg_pts : "—") +
        " pts" +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("Avg pts", result.avg_pts) +
        heroItem("PF", result.profit_factor != null ? result.profit_factor : "—") +
        heroItem("Sum pts", result.sum_pts) +
        heroItem("Trail armed %", result.trail_armed_pct != null ? result.trail_armed_pct + "%" : "—") +
        heroItem("Avg win", result.avg_win_pts) +
        heroItem("Avg loss", result.avg_loss_pts) +
        heroItem("Skipped", result.skipped);
    }
    if (breakdown) {
      const entries = result.entries || {};
      const entryParts = Object.keys(entries)
        .sort()
        .map(function (k) {
          return entryLabel({ entry_reason: k }) + " " + entries[k];
        });
      const reasons = result.skip_reasons || {};
      const skipParts = Object.keys(reasons)
        .sort()
        .map(function (k) {
          return skipLabel(k) + " " + reasons[k];
        });
      const bits = [];
      if (entryParts.length) bits.push("Entries: " + entryParts.join(" · "));
      if (skipParts.length) bits.push("Skip reasons: " + skipParts.join(" · "));
      breakdown.textContent = bits.join("  |  ");
    }
    if (mb) {
      mb.innerHTML = "";
      const months = result.by_month || [];
      if (!months.length) {
        mb.innerHTML =
          '<tr><td colspan="10" class="muted">No months in this window</td></tr>';
      } else {
        months.forEach(function (m) {
          const tr = document.createElement("tr");
          const sum = m.sum_pts;
          const sumClass = sum > 0 ? "yes" : sum < 0 ? "no" : "";
          tr.innerHTML =
            "<td>" +
            dash(m.month) +
            "</td><td>" +
            dash(m.trades) +
            "</td><td>" +
            dash(m.skipped) +
            "</td><td>" +
            (m.win_pct != null ? m.win_pct + "%" : "—") +
            '</td><td class="' +
            sumClass +
            '">' +
            dash(sum) +
            "</td><td>" +
            dash(m.avg_pts) +
            "</td><td>" +
            dash(m.profit_factor) +
            "</td><td>" +
            dash(m.avg_win_pts) +
            "</td><td>" +
            dash(m.avg_loss_pts) +
            "</td><td>" +
            (m.trail_armed_pct != null ? m.trail_armed_pct + "%" : "—") +
            "</td>";
          mb.appendChild(tr);
        });
      }
    }
    if (tb) {
      tb.innerHTML = "";
      const rows = result.rows || [];
      if (!rows.length) {
        tb.innerHTML =
          '<tr><td colspan="20" class="muted">No trades in this window</td></tr>';
      } else {
        rows.forEach(function (t) {
          const tr = document.createElement("tr");
          const ptsClass = t.pts > 0 ? "yes" : t.pts < 0 ? "no" : "";
          const pct = advSlPct(t);
          const pctClass =
            pct == null ? "" : pct >= 80 ? "no" : pct >= 40 ? "ob-warn" : "";
          const entryClass =
            t.entry_reason === "ema_touch"
              ? "yes"
              : t.entry_reason === "higher_close" || t.entry_reason === "lower_close"
                ? "ob-warn"
                : "";
          tr.innerHTML =
            "<td>" +
            t.local_date +
            "</td><td>" +
            t.side +
            "</td><td>" +
            dash(t.asia_range_pts) +
            "</td><td>" +
            dash(t.break_pts) +
            '</td><td class="' +
            entryClass +
            '">' +
            entryLabel(t) +
            "</td><td>" +
            waitCell(t) +
            "</td><td>" +
            dash(t.ema) +
            "</td>" +
            decisionTdHtml(decisionCell(t)) +
            "<td>" +
            dash(t.entry) +
            "</td><td>" +
            dash(t.sl) +
            "</td><td>" +
            dash(t.sl_pts) +
            "</td><td>" +
            dash(oppPeakPrice(t, result.symbol)) +
            '</td><td class="ob-adv">' +
            dash(t.max_adv_pts) +
            '</td><td class="' +
            pctClass +
            '">' +
            (pct == null ? "—" : pct + "%") +
            "</td><td>" +
            dash(t.max_fav_pts) +
            "</td><td>" +
            dash(t.tp_pts) +
            "</td><td>" +
            dash(t.exit) +
            "</td><td>" +
            dash(t.exit_reason) +
            "</td><td>" +
            dash(t.trail_arm_used) +
            (t.trail_armed ? " Y" : "") +
            '</td><td class="' +
            ptsClass +
            '">' +
            t.pts +
            "</td>";
          tb.appendChild(tr);
        });
      }
    }
    if (!sb) return;
    sb.innerHTML = "";
    const skips = result.skips || [];
    if (!skips.length) {
      sb.innerHTML =
        '<tr><td colspan="15" class="muted">No skipped days in this window</td></tr>';
      return;
    }
    skips.forEach(function (s) {
      const tr = document.createElement("tr");
      tr.className = "ob-skip";
      const waitTxt = waitCell(s);
      tr.innerHTML =
        "<td>" +
        dash(s.local_date) +
        '</td><td class="ob-warn">' +
        skipLabel(s.reason) +
        "</td><td>" +
        dash(s.side) +
        "</td><td>" +
        dash(s.asia_range_pts) +
        "</td><td>" +
        dash(s.break_price) +
        "</td><td>" +
        waitTxt +
        "</td><td>" +
        dash(s.ema) +
        "</td><td>" +
        dash(s.closest_ema_pts) +
        "</td><td>" +
        dash(s.best_resume_pts) +
        "</td>" +
        decisionTdHtml(s.decision || s.detail) +
        "<td>" +
        dash(oppPeakPrice(s, result.symbol)) +
        '</td><td class="ob-adv">' +
        dash(s.max_adv_pts) +
        "</td><td>" +
        dash(s.max_fav_pts) +
        "</td><td>" +
        dash(s.max_above_asia_pts) +
        "</td><td>" +
        dash(s.max_below_asia_pts) +
        "</td>";
      sb.appendChild(tr);
    });
  }

  async function poll() {
    try {
      const r = await fetch("/api/overnight");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if ($("ob-progress-bar")) {
        $("ob-progress-bar").style.width = (p.pct || 0) + "%";
      }
      if ($("ob-progress-msg")) {
        $("ob-progress-msg").textContent =
          p.message || (running ? "Running…" : "Idle");
      }
      if ($("ob-run")) $("ob-run").disabled = running;
      if ($("ob-stop")) {
        $("ob-stop").disabled = !running;
        $("ob-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      renderLanes(st);
      if (st.result && !savedPicker.isViewingSaved()) render(st.result);
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "overnight";
        badge.className = "badge run";
      }
      if (wasRunning && !running && p.phase === "done") {
        if (badge) {
          badge.textContent = "done";
          badge.className = "badge done";
        }
        if (window.StrategSaved && window.StrategSaved.playDone) {
          window.StrategSaved.playDone();
        }
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

  function wireStop() {
    if (!$("ob-stop")) return;
    $("ob-stop").addEventListener("click", async () => {
      $("ob-stop").disabled = true;
      $("ob-stop").textContent = "Stopping…";
      try {
        const r = await fetch("/api/overnight/stop", { method: "POST" });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not stop");
          $("ob-stop").disabled = false;
          $("ob-stop").textContent = "Stop";
        }
        if (!pollTimer) {
          pollTimer = setInterval(poll, 800);
          poll();
        }
      } catch (e) {
        alert(String(e));
        $("ob-stop").disabled = false;
        $("ob-stop").textContent = "Stop";
      }
    });
  }

  function wireRun() {
    if (!$("ob-run")) return;
    $("ob-run").addEventListener("click", async () => {
      const body = {
        symbol: $("ob-symbol").value,
        date_from: $("ob-from").value,
        date_to: $("ob-to").value,
        asia_start_hour: Number($("ob-asia-start").value),
        asia_end_hour: Number($("ob-asia-end").value),
        min_asia_range_pts: Number($("ob-min-asia").value),
        min_break_pts_above: Number($("ob-break-up").value),
        min_break_pts_below: Number($("ob-break-dn").value),
        break_on_wick: $("ob-break-wick") && $("ob-break-wick").checked,
        max_break_candles_after: Number($("ob-max-break-candles").value),
        pullback_mode: $("ob-pullback-mode").value,
        ema_period: Number($("ob-ema").value),
        max_wait_candles: Number($("ob-max-wait").value),
        wait_from_break: $("ob-wait-from-break") && $("ob-wait-from-break").checked,
        timeout_action: $("ob-timeout").value,
        use_higher_close: $("ob-higher-close") && $("ob-higher-close").checked,
        resume_closes: Math.max(1, Number($("ob-resume-closes") && $("ob-resume-closes").value) || 1),
        skip_late_short_wait: Math.max(0, Number($("ob-late-short-wait") && $("ob-late-short-wait").value) || 0),
        skip_late_short_asia_pts: Number(($("ob-late-short-asia") && $("ob-late-short-asia").value) || 0),
        sl_mode: $("ob-sl-mode").value,
        sl_fixed_pts: Number($("ob-sl-fixed").value),
        sl_range_mult: Number($("ob-sl-range-mult").value),
        tp_mode: $("ob-tp-mode").value,
        tp_fixed_pts: Number($("ob-tp-fixed").value),
        tp_range_mult: Number($("ob-tp-range-mult").value),
        tp_r_mult: Number($("ob-tp-r-mult").value),
        trail_arm_mode: ($("ob-trail-arm-mode") && $("ob-trail-arm-mode").value) || "fixed",
        trail_arm_pts: Number($("ob-trail-arm").value),
        trail_arm_cap_pts: Number(($("ob-trail-arm-cap") && $("ob-trail-arm-cap").value) || 0),
        trail_pts: Number($("ob-trail").value),
        max_hold_hours: Number($("ob-max-hold").value),
        flatten_hour: Number($("ob-flatten").value),
        one_trade_per_day: $("ob-one-per-day") && $("ob-one-per-day").checked,
        side_filter: $("ob-side").value,
        seasonal_mode: ($("ob-seasonal-mode") && $("ob-seasonal-mode").value) || "off",
        seasonal_join: $("ob-seasonal-join") && $("ob-seasonal-join").checked,
        week2_trend: $("ob-week2") && $("ob-week2").checked,
        trend_flat_pts: Number($("ob-trend-flat") && $("ob-trend-flat").value) || 1500,
        news_mode: ($("ob-news-mode") && $("ob-news-mode").value) || "off",
        news_set: ($("ob-news-set") && $("ob-news-set").value) || "scheduled",
        workers: Math.max(1, Math.min(6, Number($("ob-workers") && $("ob-workers").value) || 3)),
        force_download: $("ob-force") && $("ob-force").checked,
      };
      saveForm();
      savedPicker.clearViewing();
      $("ob-run").disabled = true;
      $("ob-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/overnight/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("ob-run").disabled = false;
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
        $("ob-run").disabled = false;
      }
    });
  }

  // bootstrap
  ensureTab();
  loadForm();
  bindFormPersist();
  syncPullbackControls();
  syncTrailArmControls();
  const modeEl = $("ob-pullback-mode");
  if (modeEl) modeEl.addEventListener("change", syncPullbackControls);
  const resumeEl = $("ob-higher-close");
  if (resumeEl) resumeEl.addEventListener("change", syncPullbackControls);
  const trailModeEl = $("ob-trail-arm-mode");
  if (trailModeEl) trailModeEl.addEventListener("change", syncTrailArmControls);
  wireDecisionTips();
  wireTabs();
  wireRun();
  wireStop();
  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "overnight_break",
      selectId: "ob-saved",
      buttonId: "ob-load",
      onLoaded: function (json) {
        render(json);
      },
    });
  }
  poll();
})();
