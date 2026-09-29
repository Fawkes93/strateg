/* Asia box tab — not Asia liquidity, not Overnight break.
   Defaults: no entry before 03:30 local, continuation stop trails 2 fib steps,
   a signal candle wider than 40% of the box freezes every setup for 90 minutes.
   The Session rules paragraphs are fetched from /api/asia-box/setups and are
   the behavior of the next run. README section "Asia box tab" is the runbook.
*/
(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_asia_box_v1";
  let pollTimer = null;
  let wasRunning = false;
  let saveTimer = null;
  let descTimer = null;

  const FORM_IDS = [
    "ab-symbol",
    "ab-from",
    "ab-to",
    "ab-tz",
    "ab-min-mode",
    "ab-min-range",
    "ab-min-pct",
    "ab-ema",
    "ab-data",
    "ab-force",
    "ab-box-start",
    "ab-box-end",
    "ab-shallow-h",
    "ab-shallow-m",
    "ab-ema-retest-h",
    "ab-cutoff",
    "ab-flatten-h",
    "ab-flatten-m",
    "ab-shallow-near",
    "ab-cont-sl",
    "ab-cont-tp",
    "ab-rev-c-sl",
    "ab-rev-c-tp",
    "ab-rev-e-sl",
    "ab-rev-e-tp",
    "ab-sh-e-sl",
    "ab-sh-e-tp",
    "ab-sh-c-sl",
    "ab-sh-c-tp",
    "ab-retest-sl",
    "ab-retest-tp",
    "ab-retest-auto",
    "ab-retest-steps",
    "ab-trade-start-on",
    "ab-trade-start-h",
    "ab-trade-start-m",
    "ab-trail-on",
    "ab-trail-steps",
    "ab-freeze-on",
    "ab-freeze-pct",
    "ab-freeze-min",
    "ab-double-tp",
    "ab-bounce",
    "ab-en-cont",
    "ab-en-rev-c",
    "ab-en-rev-e",
    "ab-en-sh-e",
    "ab-en-sh-c",
    "ab-en-retest",
  ];

  const POINT_FIELDS = ["ab-min-range", "ab-shallow-near"];
  let symbolSwitching = false;

  function formSymbol(symbol) {
    return window.strategSymbols.formSymbol(symbol);
  }

  function pointScale(symbol) {
    return window.strategSymbols.pointScale(symbol);
  }

  function readCfg() {
    const cfg = {};
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      cfg[id] = el.type === "checkbox" ? !!el.checked : el.value;
    });
    return cfg;
  }

  function loadStore() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.v === 2 && parsed.bySymbol) return parsed;
    const sym = formSymbol(parsed && parsed["ab-symbol"]);
    const bySymbol = {};
    bySymbol[sym] = parsed;
    return { v: 2, active: sym, bySymbol: bySymbol };
  }

  function scalePoint(raw, ratio) {
    const n = parseFloat(raw);
    if (!Number.isFinite(n) || n === 0) return raw;
    const scaled = n * ratio;
    if (Math.abs(scaled) >= 10) return String(Math.round(scaled));
    return String(Math.round(scaled * 10) / 10);
  }

  function scaleCfg(cfg, fromSym, toSym) {
    const next = Object.assign({}, cfg);
    const ratio = pointScale(toSym) / pointScale(fromSym);
    next["ab-symbol"] = formSymbol(toSym);
    if (ratio === 1) return next;
    POINT_FIELDS.forEach(function (id) {
      if (next[id] == null || next[id] === "") return;
      next[id] = scalePoint(next[id], ratio);
    });
    return next;
  }

  function applyCfg(cfg) {
    if (!cfg) return;
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el || cfg[id] === undefined) return;
      if (el.type === "checkbox") el.checked = !!cfg[id];
      else if (id === "ab-symbol") el.value = formSymbol(cfg[id]);
      else el.value = cfg[id];
    });
  }

  function saveForm() {
    if (symbolSwitching) return;
    try {
      const store = loadStore() || { v: 2, active: "XAUUSD", bySymbol: {} };
      const sym = formSymbol($("ab-symbol") && $("ab-symbol").value);
      store.v = 2;
      store.active = sym;
      store.bySymbol[sym] = readCfg();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch (e) {
      console.warn("asia box save failed", e);
    }
  }

  function onSymbolChange() {
    const next = formSymbol($("ab-symbol") && $("ab-symbol").value);
    const store = loadStore() || { v: 2, active: next, bySymbol: {} };
    const prev = formSymbol(store.active || "XAUUSD");
    if (prev === next) return;
    const prevCfg = readCfg();
    prevCfg["ab-symbol"] = prev;
    store.bySymbol[prev] = prevCfg;
    const nextCfg = store.bySymbol[next] || scaleCfg(prevCfg, prev, next);
    nextCfg["ab-symbol"] = next;
    symbolSwitching = true;
    applyCfg(nextCfg);
    symbolSwitching = false;
    store.v = 2;
    store.active = next;
    store.bySymbol[next] = readCfg();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch (e) {
      console.warn("asia box symbol save failed", e);
    }
  }

  function loadForm() {
    try {
      const store = loadStore();
      if (!store) return;
      const sym = formSymbol(store.active);
      const cfg =
        (store.bySymbol && (store.bySymbol[sym] || store.bySymbol.XAUUSD)) || null;
      applyCfg(cfg);
    } catch (e) {
      console.warn("asia box load failed", e);
    }
  }

  function num(id, fallback) {
    const el = $(id);
    const n = parseFloat(el && el.value);
    return Number.isFinite(n) ? n : fallback;
  }

  function intv(id, fallback) {
    const el = $(id);
    const n = parseInt(el && el.value, 10);
    return Number.isFinite(n) ? n : fallback;
  }

  function chk(id) {
    const el = $(id);
    return !!(el && el.checked);
  }

  function payload() {
    return {
      symbol: ($("ab-symbol") && $("ab-symbol").value) || "XAUUSD",
      date_from: ($("ab-from") && $("ab-from").value) || "2025-05-01",
      date_to: ($("ab-to") && $("ab-to").value) || "2025-08-01",
      timezone: ($("ab-tz") && $("ab-tz").value) || "Europe/Chisinau",
      data_source: ($("ab-data") && $("ab-data").value) || "candles_5m",
      force_download: chk("ab-force"),
      workers: 1,
      min_range_mode: ($("ab-min-mode") && $("ab-min-mode").value) || "fixed",
      min_range_pts: num("ab-min-range", 3000),
      min_range_bps: (num("ab-min-pct", 1.4) || 0) / 100,
      ema_period: intv("ab-ema", 32),
      box_start_hour: intv("ab-box-start", 1),
      box_end_hour: intv("ab-box-end", 6),
      shallow_hour: intv("ab-shallow-h", 5),
      shallow_minute: intv("ab-shallow-m", 30),
      ema_retest_hour: intv("ab-ema-retest-h", 7),
      entry_cutoff_hour: intv("ab-cutoff", 10),
      flatten_hour: intv("ab-flatten-h", 13),
      flatten_minute: intv("ab-flatten-m", 30),
      shallow_ema_near_pts: num("ab-shallow-near", 100),
      continuation_sl_fib: num("ab-cont-sl", 0.786),
      continuation_tp_fib: num("ab-cont-tp", 0),
      reverse_confirm_sl_fib: num("ab-rev-c-sl", 0.5),
      reverse_confirm_tp_fib: num("ab-rev-c-tp", 1.5),
      reverse_ema_sl_fib: num("ab-rev-e-sl", 0.5),
      reverse_ema_tp_fib: num("ab-rev-e-tp", 1),
      shallow_ema_sl_fib: num("ab-sh-e-sl", 0.5),
      shallow_ema_tp_fib: num("ab-sh-e-tp", 0),
      shallow_confirm_sl_fib: num("ab-sh-c-sl", 0.5),
      shallow_confirm_tp_fib: num("ab-sh-c-tp", 0),
      ema_retest_sl_fib: num("ab-retest-sl", 0.382),
      ema_retest_tp_fib: num("ab-retest-tp", 0),
      ema_retest_auto_levels: chk("ab-retest-auto"),
      ema_retest_sl_steps: intv("ab-retest-steps", 2),
      trade_start_enabled: chk("ab-trade-start-on"),
      trade_start_hour: intv("ab-trade-start-h", 3),
      trade_start_minute: intv("ab-trade-start-m", 30),
      continuation_trail: chk("ab-trail-on"),
      continuation_trail_steps: intv("ab-trail-steps", 2),
      impulse_freeze: chk("ab-freeze-on"),
      impulse_freeze_frac: (num("ab-freeze-pct", 40) || 0) / 100,
      impulse_freeze_minutes: intv("ab-freeze-min", 90),
      tp_double_fib0: chk("ab-double-tp"),
      bounce_236: chk("ab-bounce"),
      enable_continuation: chk("ab-en-cont"),
      enable_reverse_confirm: chk("ab-en-rev-c"),
      enable_reverse_ema: chk("ab-en-rev-e"),
      enable_shallow_ema: chk("ab-en-sh-e"),
      enable_shallow_confirm: chk("ab-en-sh-c"),
      enable_ema_retest: chk("ab-en-retest"),
    };
  }

  async function refreshDescriptions() {
    try {
      const r = await fetch("/api/asia-box/setups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload()),
      });
      const data = await r.json();
      const host = $("ab-setups");
      if (!host) return;
      host.innerHTML = "";
      (data.setups || []).forEach(function (s) {
        const art = document.createElement("article");
        art.className = "ab-setup" + (s.enabled ? "" : " is-off");
        art.innerHTML =
          "<h3>" +
          s.title +
          (s.enabled ? "" : " <span class='ab-off'>off</span>") +
          "</h3><p>" +
          s.body +
          "</p>";
        host.appendChild(art);
      });
      (data.rules || []).forEach(function (rule) {
        const el = $("ab-rule-" + rule.id);
        if (el) el.textContent = rule.body || "";
      });
    } catch (e) {
      console.warn("asia box describe failed", e);
    }
  }

  function scheduleDesc() {
    if (descTimer) clearTimeout(descTimer);
    descTimer = setTimeout(refreshDescriptions, 200);
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="asia-box"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "asia-box");
      btn.textContent = "Asia box";
      nav.appendChild(btn);
    }
    if ($("tab-asia-box")) return;

    const panel = document.createElement("div");
    panel.id = "tab-asia-box";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Asia box Fibonacci</h2>
      <p class="hint">This is the 5-minute fib backtest. It is not the Asia liquidity tab and not Overnight break. Hours are Europe/Chisinau.</p>
      <ol>
        <li>The box is <strong>01:00–06:00</strong>. Fib 0 is the extreme that printed later. Fib 1 is the other side. Gold: 1 point = $0.01.</li>
        <li><strong>No entry before 03:30.</strong> The box and the arm flags still update, so a reverse can arm early and confirm at 03:30. Shallow waits until 05:30. EMA retest waits until 07:00. No new entry from 10:00. Flatten 13:30.</li>
        <li><strong>Continuation stop trails.</strong> It starts at .786. A new high (long) or new low (short) moves it 2 fib steps toward Fib 1, and only tighter. Fib 0 counts as a step, so a high through Fib 0 pulls the stop to .236.</li>
        <li><strong>A huge candle waits 90 minutes.</strong> If the 5m that would fill is wider than 40% of the box, skip it and block every setup for 90 minutes after that close. The box keeps updating. The two candles this is for: 2026-03-16 02:00 reverse long (−2528) and 2026-04-06 05:15 reverse long (−2998).</li>
        <li>EMA retest auto-stop is already those same 2 steps. The SL box showing 0.382 is used only when Auto is off. Steps = 3 puts a through-Fib-0 stop at .382.</li>
        <li>One open trade. A fill that exits before 06:00 can open a second, larger box. The sentences on the Session rules card are the exact rules of the next run.</li>
      </ol>
      <p class="hint">5m candles by default; ticks only change fill / SL / TP precision. Results live in SQLite — open the catalog to filter by setup and click a trade for the chart. FX majors use 0.1 pip per point. Moving from gold or bitcoin onto an FX major divides min range and shallow-near by 10, and moving back multiplies them by 10. Bitcoin uses $0.01 per point, the same as gold. Fib levels stay the same.</p>
    </section>
    <section class="card ab-rules">
      <h2>Session rules</h2>
      <p class="hint">On by default. The paragraph under each rule is the exact behavior the next run will use.</p>
      <div class="ab-rule" id="ab-rule-trade-start">
        <label class="chk"><input type="checkbox" id="ab-trade-start-on" checked /> No trade until</label>
        <div class="ab-rule-fields">
          <label>Hour
            <input type="number" id="ab-trade-start-h" value="3" min="0" max="23" />
            <span class="field-help">Local hour. 3 with minute 30 is 03:30.</span>
          </label>
          <label>Minute
            <input type="number" id="ab-trade-start-m" value="30" min="0" max="59" />
            <span class="field-help">Before this clock the box is only watched.</span>
          </label>
        </div>
        <p class="ab-rule-body" id="ab-rule-trade_start">No new entry before 03:30. The box still builds.</p>
      </div>
      <div class="ab-rule" id="ab-rule-trail">
        <label class="chk"><input type="checkbox" id="ab-trail-on" checked /> Continuation stop trails</label>
        <div class="ab-rule-fields">
          <label>Fib steps behind
            <input type="number" id="ab-trail-steps" value="2" min="1" max="8" />
            <span class="field-help">2 behind a new high through Fib 0 lands on .236.</span>
          </label>
        </div>
        <p class="ab-rule-body" id="ab-rule-continuation_trail">New highs and lows pull the continuation stop closer.</p>
      </div>
      <div class="ab-rule" id="ab-rule-freeze">
        <label class="chk"><input type="checkbox" id="ab-freeze-on" checked /> Huge-candle freeze</label>
        <div class="ab-rule-fields">
          <label>Wider than (%)
            <input type="number" id="ab-freeze-pct" value="40" min="1" max="100" step="1" />
            <span class="field-help">Signal candle high−low divided by the box high−low.</span>
          </label>
          <label>Wait (minutes)
            <input type="number" id="ab-freeze-min" value="90" min="0" step="5" />
            <span class="field-help">90 minutes is an hour and a half after that candle closes.</span>
          </label>
        </div>
        <p class="ab-rule-body" id="ab-rule-impulse_freeze">A candle bigger than 40% of the box pauses entries for 90 minutes.</p>
      </div>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ab-symbol" title="FX majors: 1 point = 0.1 pip. Moving from gold or bitcoin onto an FX major divides min range and shallow-near by 10.">
            ${window.strategSymbols.optionsHtml()}
          </select>
          <span class="field-help">Gold and bitcoin use $0.01 per point. Switching from either one onto an FX major divides min range and shallow-near by 10.</span>
        </label>
        <label>From (local date)
          <input type="date" id="ab-from" value="2025-05-01" />
          <span class="field-help">First local morning included in the run.</span>
        </label>
        <label>To (exclusive)
          <input type="date" id="ab-to" value="2025-08-01" />
          <span class="field-help">Stops before this date. 1 Aug means 31 Jul is the last day.</span>
        </label>
        <label>Timezone
          <input id="ab-tz" value="Europe/Chisinau" />
          <span class="field-help">Every hour on this tab is in this zone. Chisinau matches the live session.</span>
        </label>
        <label>Min range
          <select id="ab-min-mode">
            <option value="fixed" selected>fixed points</option>
            <option value="pct_price">percent of midpoint</option>
          </select>
          <span class="field-help">Fixed points is the same floor every day. Percent of midpoint scales with the price: a dearer market must build a wider box.</span>
        </label>
        <label>Min range (pts)
          <input type="number" id="ab-min-range" value="3000" step="100" />
          <span class="field-help">Used when the mode is fixed points. A smaller Asia high−low skips the day. Ignored in percent mode.</span>
        </label>
        <label>Min range (%)
          <input type="number" id="ab-min-pct" value="1.4" min="0" step="0.1" />
          <span class="field-help">Used when the mode is percent of midpoint. 1.4 means 1.4% of (high + low) / 2. At a $2500 mid that is 3500 points; at $2000 it is 2800. Ignored in fixed mode. The percent stays as entered when the symbol changes.</span>
        </label>
        <label>EMA period (5m)
          <input type="number" id="ab-ema" value="32" min="1" />
          <span class="field-help">Length of the 5-minute EMA used by Reverse EMA, Shallow EMA, and EMA Retest.</span>
        </label>
        <label>Data
          <select id="ab-data">
            <option value="candles_5m" selected>5m candles</option>
            <option value="ticks">Ticks</option>
          </select>
          <span class="field-help">5m candles decide the signal. Ticks only change how precisely the stop and target fill.</span>
        </label>
        <label>Box start hour
          <input type="number" id="ab-box-start" value="1" min="0" max="23" />
          <span class="field-help">Highs and lows before this hour are not part of the Asia box.</span>
        </label>
        <label>Box end hour
          <input type="number" id="ab-box-end" value="6" min="0" max="23" />
          <span class="field-help">The box stops extending here. A fill that exits before then can open a second, larger box.</span>
        </label>
        <label>Shallow hour
          <input type="number" id="ab-shallow-h" value="5" min="0" max="23" />
          <span class="field-help">Shallow EMA and Shallow Confirm cannot fire before this time.</span>
        </label>
        <label>Shallow minute
          <input type="number" id="ab-shallow-m" value="30" min="0" max="59" />
          <span class="field-help">Together with the hour. 5 and 30 means 05:30.</span>
        </label>
        <label>EMA retest hour
          <input type="number" id="ab-ema-retest-h" value="7" min="0" max="23" />
          <span class="field-help">EMA Retest cannot fire before this hour, even if the 03:30 clock has passed.</span>
        </label>
        <label>Entry cutoff hour
          <input type="number" id="ab-cutoff" value="10" min="0" max="23" />
          <span class="field-help">No new entry at or after this hour. Open trades stay open until flatten.</span>
        </label>
        <label>Flatten hour
          <input type="number" id="ab-flatten-h" value="13" min="0" max="23" />
          <span class="field-help">Open trades close at this time, at the bar's open.</span>
        </label>
        <label>Flatten minute
          <input type="number" id="ab-flatten-m" value="30" min="0" max="59" />
          <span class="field-help">Together with the hour. 13 and 30 means 13:30.</span>
        </label>
        <label>Shallow EMA near (pts)
          <input type="number" id="ab-shallow-near" value="100" step="10" />
          <span class="field-help">Shallow EMA fires only when the EMA is within this many points of Fib .382.</span>
        </label>
      </div>
      <div class="ab-setup-list">
        <span class="label">Setups</span>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-cont" checked /> Continuation</label>
          <div class="ab-setup-levels" data-for="ab-en-cont">
            <label>SL <input type="number" id="ab-cont-sl" value="0.786" step="0.001" />
              <span class="field-help">Starting stop. The trail rule can move it closer.</span></label>
            <label>TP <input type="number" id="ab-cont-tp" value="0" step="0.001" />
              <span class="field-help">0 is Fib 0, the later extreme of the box.</span></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-rev-c" checked /> Reverse Confirm</label>
          <div class="ab-setup-levels" data-for="ab-en-rev-c">
            <label>SL <input type="number" id="ab-rev-c-sl" value="0.5" step="0.001" />
              <span class="field-help">Fib level of the stop. .5 is the middle of the box.</span></label>
            <label>TP <input type="number" id="ab-rev-c-tp" value="1.5" step="0.001" />
              <span class="field-help">1.5 is half a box beyond Fib 1.</span></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-rev-e" checked /> Reverse EMA</label>
          <div class="ab-setup-levels" data-for="ab-en-rev-e">
            <label>SL <input type="number" id="ab-rev-e-sl" value="0.5" step="0.001" />
              <span class="field-help">Fib level of the stop after the EMA tag.</span></label>
            <label>TP <input type="number" id="ab-rev-e-tp" value="1" step="0.001" />
              <span class="field-help">1 is Fib 1, the far side of the box.</span></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-sh-e" checked /> Shallow EMA</label>
          <div class="ab-setup-levels" data-for="ab-en-sh-e">
            <label>SL <input type="number" id="ab-sh-e-sl" value="0.5" step="0.001" />
              <span class="field-help">Fib level of the stop. With the box, so .5 is behind a .382 tag.</span></label>
            <label>TP <input type="number" id="ab-sh-e-tp" value="0" step="0.001" />
              <span class="field-help">0 aims back at the later extreme.</span></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-sh-c" checked /> Shallow Confirm</label>
          <div class="ab-setup-levels" data-for="ab-en-sh-c">
            <label>SL <input type="number" id="ab-sh-c-sl" value="0.5" step="0.001" />
              <span class="field-help">Fib level of the stop after the confirming close.</span></label>
            <label>TP <input type="number" id="ab-sh-c-tp" value="0" step="0.001" />
              <span class="field-help">0 aims back at the later extreme.</span></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-retest" checked /> EMA Retest</label>
          <div class="ab-setup-levels" data-for="ab-en-retest">
            <label class="chk"><input type="checkbox" id="ab-retest-auto" checked /> Auto SL/TP
              <span class="field-help">On: stop is the steps field below, target is Fib 0 or an extension. The SL and TP numbers are used only when this is off. Two steps through Fib 0 is .236, which looks like one step inside the box because Fib 0 itself counts.</span></label>
            <label>Steps <input type="number" id="ab-retest-steps" value="2" min="1" max="8" />
              <span class="field-help">2 through Fib 0 → .236. 3 through Fib 0 → .382. Between 0 and .236, 2 steps → .382.</span></label>
            <label>SL <input type="number" id="ab-retest-sl" value="0.382" step="0.001" />
              <span class="field-help">Used only when Auto is off. 0.382 is not the live auto stop.</span></label>
            <label>TP <input type="number" id="ab-retest-tp" value="0" step="0.001" />
              <span class="field-help">Used only when Auto is off.</span></label>
          </div>
        </div>
      </div>
      <div class="engines">
        <span class="label">Reserved</span>
        <label class="chk ab-tip" title="With-trend only (Continuation, Shallow, EMA Retest). Replaces the Fib 0 target with twice the distance from entry to Fib 0. Reverse trades are unchanged." data-tip="With-trend only (Continuation, Shallow, EMA Retest). Replaces the Fib 0 target with twice the distance from entry to Fib 0. Reverse trades are unchanged."><input type="checkbox" id="ab-double-tp" /> 2× Fib 0 profit TP
          <span class="field-help">With-trend only. Replaces the Fib 0 target with twice the distance from entry to Fib 0. Reverse trades stay on their fib target.</span></label>
        <label class="chk ab-tip" title="After Fib .236 is tagged twice (separate touches), the open trade’s stop is pulled to Fib .618." data-tip="After Fib .236 is tagged twice (separate touches), the open trade’s stop is pulled to Fib .618."><input type="checkbox" id="ab-bounce" /> .236 bounce SL
          <span class="field-help">After Fib .236 is tagged twice, on separate touches, the open stop jumps to Fib .618.</span></label>
        <label class="chk"><input type="checkbox" id="ab-force" /> Force download
          <span class="field-help">Rebuild the month packs even when they are already on disk.</span></label>
      </div>
      <div class="row-actions" style="margin-top:1rem;display:flex;gap:0.6rem;flex-wrap:wrap;align-items:center">
        <button type="button" class="primary" id="ab-run">Run</button>
        <button type="button" id="ab-stop" disabled>Stop</button>
        <a id="ab-results-link" class="ab-btn" href="/asia-box/results" target="_blank" rel="noopener">Open results catalog</a>
      </div>
      <div class="ab-progress">
        <div class="ab-progress-track"><div id="ab-progress-bar"></div></div>
        <p id="ab-progress-msg" class="hint">Idle</p>
      </div>
    </section>
    <section class="card">
      <h2>How each setup works</h2>
      <p class="hint">Copy is built from the fields above — change a number and this text updates.</p>
      <div id="ab-setups" class="ab-setups"></div>
    </section>
    <section class="card" id="ab-last">
      <h2>Last run</h2>
      <p id="ab-last-msg" class="hint">No run in this session yet.</p>
    </section>`;
    document.querySelector("footer.foot")?.before(panel);
    if (!document.querySelector("footer.foot")) {
      document.body.appendChild(panel);
    }

    document.querySelectorAll(".main-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
        const el = document.getElementById("tab-" + tab);
        if (el) el.classList.remove("hidden");
      });
    });
  }

  async function poll() {
    try {
      const r = await fetch("/api/asia-box");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if ($("ab-progress-bar")) $("ab-progress-bar").style.width = (p.pct || 0) + "%";
      if ($("ab-progress-msg")) {
        $("ab-progress-msg").textContent = p.message || (running ? "Running…" : "Idle");
      }
      if ($("ab-run")) $("ab-run").disabled = running;
      if ($("ab-stop")) {
        $("ab-stop").disabled = !running;
        $("ab-stop").textContent = st.cancel_requested ? "Stopping…" : "Stop";
      }
      if (st.result) renderLast(st.result);
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "asia box";
        badge.className = "badge run";
      }
      if (wasRunning && !running && p.phase === "done") {
        if (badge) {
          badge.textContent = "done";
          badge.className = "badge done";
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

  function renderLast(result) {
    const el = $("ab-last-msg");
    if (!el) return;
    const n = result.trades || 0;
    const pts = result.sum_pts != null ? Math.round(result.sum_pts) : 0;
    const sid = result.sqlite_id;
    const href = sid ? "/asia-box/results?run=" + sid : "/asia-box/results";
    if ($("ab-results-link")) $("ab-results-link").href = href;
    const parts = Object.keys(result.by_setup || {})
      .map((k) => k + " " + (result.by_setup[k].n || 0))
      .join(" · ");
    const fz = (result.freezes || []).length;
    const freezeBit = fz ? " · " + fz + " huge-candle freeze" + (fz === 1 ? "" : "s") : "";
    if (!sid && n === 0) {
      el.textContent = "0 trades · not saved to the catalog." + freezeBit;
      return;
    }
    el.innerHTML =
      n +
      " trades · " +
      pts +
      " pts" +
      (parts ? " · " + parts : "") +
      freezeBit +
      (sid ? ' · <a href="' + href + '" target="_blank" rel="noopener">View in catalog</a>' : "");
  }

  function syncSetupLevels() {
    document.querySelectorAll(".ab-setup-levels").forEach(function (row) {
      const cb = $(row.getAttribute("data-for"));
      row.hidden = !(cb && cb.checked);
    });
    const auto = $("ab-retest-auto");
    const sl = $("ab-retest-sl");
    const tp = $("ab-retest-tp");
    const steps = $("ab-retest-steps");
    const locked = !!(auto && auto.checked);
    if (sl) sl.disabled = locked;
    if (tp) tp.disabled = locked;
    if (steps) steps.disabled = !locked;
    const pctMode = ($("ab-min-mode") && $("ab-min-mode").value) === "pct_price";
    const minPts = $("ab-min-range");
    const minPct = $("ab-min-pct");
    if (minPts) minPts.disabled = pctMode;
    if (minPct) minPct.disabled = !pctMode;
    function gate(boxId, on) {
      const box = $(boxId);
      if (!box) return;
      box.querySelectorAll("input[type='number']").forEach(function (el) {
        el.disabled = !on;
      });
    }
    gate("ab-rule-trade-start", chk("ab-trade-start-on"));
    gate("ab-rule-trail", chk("ab-trail-on"));
    gate("ab-rule-freeze", chk("ab-freeze-on"));
  }

  function wire() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", function () {
        if (id === "ab-symbol") onSymbolChange();
        saveForm();
        syncSetupLevels();
        scheduleDesc();
      });
      el.addEventListener("input", function () {
        saveForm();
        scheduleDesc();
      });
    });
    if ($("ab-run")) {
      $("ab-run").addEventListener("click", async () => {
        $("ab-run").disabled = true;
        try {
          const r = await fetch("/api/asia-box/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload()),
          });
          if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            alert(err.detail || "Could not start");
            $("ab-run").disabled = false;
            return;
          }
          if (!pollTimer) pollTimer = setInterval(poll, 800);
          poll();
        } catch (e) {
          alert(String(e));
          $("ab-run").disabled = false;
        }
      });
    }
    if ($("ab-stop")) {
      $("ab-stop").addEventListener("click", async () => {
        $("ab-stop").disabled = true;
        try {
          await fetch("/api/asia-box/stop", { method: "POST" });
          if (!pollTimer) pollTimer = setInterval(poll, 800);
          poll();
        } catch (e) {
          alert(String(e));
        }
      });
    }
  }

  ensureTab();
  loadForm();
  syncSetupLevels();
  wire();
  refreshDescriptions();
  poll();
})();
