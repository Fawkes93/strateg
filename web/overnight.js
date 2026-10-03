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
    "ob-pullback-ref",
    "ob-pullback-fib",
    "ob-fib-anchor",
    "ob-ma-type",
    "ob-ema",
    "ob-kama-er",
    "ob-kama-fast",
    "ob-kama-slow",
    "ob-hma",
    "ob-zlema",
    "ob-max-wait",
    "ob-wait-from-break",
    "ob-timeout",
    "ob-timeout-ema-dist",
    "ob-timeout-min-break",
    "ob-timeout-min-pullback",
    "ob-near-bars",
    "ob-near-pts",
    "ob-near-trend",
    "ob-near-min-range",
    "ob-higher-close",
    "ob-resume-closes",
    "ob-resume-max-break",
    "ob-late-short-wait",
    "ob-late-short-asia",
    "ob-side",
    "ob-seasonal-mode",
    "ob-seasonal-join",
    "ob-week2-mode",
    "ob-trend-flat",
    "ob-trend-eff",
    "ob-news-mode",
    "ob-news-set",
    "ob-sl-mode",
    "ob-sl-fixed",
    "ob-sl-range-mult",
    "ob-sl-cap",
    "ob-sl-m12-frac",
    "ob-tp-mode",
    "ob-tp-fixed",
    "ob-tp-range-mult",
    "ob-tp-sl-mult",
    "ob-trail-arm-mode",
    "ob-trail-arm",
    "ob-trail-arm-cap",
    "ob-trail",
    "ob-be-arm",
    "ob-max-hold",
    "ob-flatten",
    "ob-one-per-day",
    "ob-workers",
    "ob-data",
    "ob-force",
  ];

  // Absolute point inputs. FX majors are 0.1 pip per point, so the first
  // switch between gold or bitcoin and an FX major scales these by 10.
  // Multipliers and hour fields stay.
  const POINT_FIELDS = [
    "ob-min-asia",
    "ob-break-up",
    "ob-break-dn",
    "ob-timeout-ema-dist",
    "ob-timeout-min-break",
    "ob-timeout-min-pullback",
    "ob-near-pts",
    "ob-near-min-range",
    "ob-resume-max-break",
    "ob-late-short-asia",
    "ob-trend-flat",
    "ob-sl-fixed",
    "ob-sl-cap",
    "ob-tp-fixed",
    "ob-trail-arm",
    "ob-trail-arm-cap",
    "ob-trail",
    "ob-be-arm",
  ];
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
    const sym = formSymbol(parsed && parsed["ob-symbol"]);
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
    next["ob-symbol"] = formSymbol(toSym);
    if (ratio === 1) return next;
    POINT_FIELDS.forEach(function (id) {
      if (next[id] == null || next[id] === "") return;
      next[id] = scalePoint(next[id], ratio);
    });
    return next;
  }

  function saveForm() {
    if (symbolSwitching) return;
    try {
      const store = loadStore() || { v: 2, active: "XAUUSD", bySymbol: {} };
      const sym = formSymbol($("ob-symbol") && $("ob-symbol").value);
      store.v = 2;
      store.active = sym;
      store.bySymbol[sym] = readCfg();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch (e) {
      console.warn("overnight save failed", e);
    }
  }

  function onSymbolChange() {
    const next = formSymbol($("ob-symbol") && $("ob-symbol").value);
    const store = loadStore() || { v: 2, active: next, bySymbol: {} };
    const prev = formSymbol(store.active || "XAUUSD");
    if (prev === next) return;
    const prevCfg = readCfg();
    prevCfg["ob-symbol"] = prev;
    store.bySymbol[prev] = prevCfg;
    const nextCfg = store.bySymbol[next] || scaleCfg(prevCfg, prev, next);
    nextCfg["ob-symbol"] = next;
    symbolSwitching = true;
    applyCfg(nextCfg);
    symbolSwitching = false;
    store.v = 2;
    store.active = next;
    store.bySymbol[next] = readCfg();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch (e) {
      console.warn("overnight symbol save failed", e);
    }
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveForm, 200);
  }

  function applyCfg(cfg) {
    if (!cfg) return;
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el || cfg[id] == null) return;
      if (el.type === "checkbox") el.checked = !!cfg[id];
      else if (id === "ob-symbol") el.value = formSymbol(cfg[id]);
      else el.value = cfg[id];
    });
    // Removed pullback mode "ema" (= required + resume off).
    if (cfg["ob-pullback-mode"] === "ema") {
      if ($("ob-pullback-mode")) $("ob-pullback-mode").value = "required";
      if ($("ob-higher-close")) $("ob-higher-close").checked = false;
    }
    // Removed timeout "worst" (hindsight fill). Live chase = market at last wait close.
    if ($("ob-timeout") && $("ob-timeout").value === "worst") {
      $("ob-timeout").value = "market";
    }
    if ($("ob-tp-mode") && $("ob-tp-mode").value === "r_mult") {
      $("ob-tp-mode").value = "sl_mult";
    }
    if (
      $("ob-tp-sl-mult") &&
      (cfg["ob-tp-sl-mult"] == null || cfg["ob-tp-sl-mult"] === "") &&
      cfg["ob-tp-r-mult"] != null
    ) {
      $("ob-tp-sl-mult").value = cfg["ob-tp-r-mult"];
    }
    // Legacy 2-week checkbox → off/tag/filter select.
    if ($("ob-sl-mode") && $("ob-sl-mode").value === "range_width") {
      $("ob-sl-mode").value = "range";
    }
    if ($("ob-week2-mode") && cfg["ob-week2-mode"] == null && cfg["ob-week2"] != null) {
      const on = !!cfg["ob-week2"];
      $("ob-week2-mode").value = on
        ? cfg["ob-seasonal-mode"] === "filter"
          ? "filter"
          : "tag"
        : "off";
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
      console.warn("overnight load failed", e);
    }
  }

  function bindFormPersist() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", function () {
        if (id === "ob-symbol") onSymbolChange();
        scheduleSave();
      });
      el.addEventListener("input", scheduleSave);
    });
  }

  function syncPullbackControls() {
    const mode = $("ob-pullback-mode") && $("ob-pullback-mode").value;
    const resume = $("ob-higher-close");
    const resumeCloses = $("ob-resume-closes");
    const resumeMaxBreak = $("ob-resume-max-break");
    const timeout = $("ob-timeout");
    const timeoutEma = $("ob-timeout-ema-dist");
    const timeoutBreak = $("ob-timeout-min-break");
    const timeoutPullback = $("ob-timeout-min-pullback");
    if (resume) resume.disabled = mode === "off";
    if (resumeCloses) {
      resumeCloses.disabled = mode === "off" || (resume && !resume.checked);
    }
    if (resumeMaxBreak) {
      resumeMaxBreak.disabled = mode === "off" || (resume && !resume.checked);
    }
    const timeoutOff = mode !== "preferred";
    if (timeout) timeout.disabled = timeoutOff;
    if (timeoutEma) timeoutEma.disabled = timeoutOff;
    if (timeoutBreak) timeoutBreak.disabled = timeoutOff;
    if (timeoutPullback) timeoutPullback.disabled = timeoutOff;
    const fib = $("ob-pullback-fib");
    const anchor = $("ob-fib-anchor");
    const ref = $("ob-pullback-ref") && $("ob-pullback-ref").value;
    const usesFib = ref === "fib" || ref === "both";
    const fibWrap = $("ob-fib-level-wrap");
    const anchorWrap = $("ob-fib-anchor-wrap");
    if (fibWrap) fibWrap.hidden = !usesFib;
    if (anchorWrap) anchorWrap.hidden = !usesFib;
    if (fib) fib.disabled = mode === "off" || !usesFib;
    if (anchor) anchor.disabled = mode === "off" || !usesFib;
    syncMaFields();
    const nearOff = mode !== "required";
    ["ob-near-bars", "ob-near-pts", "ob-near-trend", "ob-near-min-range"].forEach(function (id) {
      const el = $(id);
      if (el) el.disabled = nearOff;
    });
  }

  function syncSlControls() {
    const mode = $("ob-sl-mode") && $("ob-sl-mode").value;
    const fixed = $("ob-sl-fixed");
    const mult = $("ob-sl-range-mult");
    const cap = $("ob-sl-cap");
    const frac = $("ob-sl-m12-frac");
    if (fixed) {
      fixed.disabled = mode !== "fixed";
      fixed.title =
        mode === "fixed"
          ? "Stop distance in pts."
          : "Used as fallback when Asia opposite is on the wrong side of entry.";
    }
    if (mult) {
      mult.disabled = mode !== "range";
      mult.title =
        mode === "range"
          ? "SL distance = Asia width × this. 1 = the range itself."
          : "Used when SL mode is Asia range.";
    }
    if (frac) {
      frac.disabled = mode !== "m12_frac";
      frac.title =
        mode === "m12_frac"
          ? "Stop = this fraction of the last-12-month average daily-close range, rounded up to 50 pts."
          : "Used when SL mode is 12m avg × frac.";
    }
    if (cap) {
      cap.disabled = mode === "fixed";
      cap.title =
        mode === "fixed"
          ? "Cap is for asia opposite, Asia range, and 12m frac. 0 = off."
          : "Max SL distance (pts). 0 = off. Pulls a too-wide SL in to this many pts.";
    }
  }

  function syncMaFields() {
    const kind = ($("ob-ma-type") && $("ob-ma-type").value) || "ema";
    [
      ["ob-ema-wrap", kind === "ema"],
      ["ob-kama-er-wrap", kind === "kama"],
      ["ob-kama-fast-wrap", kind === "kama"],
      ["ob-kama-slow-wrap", kind === "kama"],
      ["ob-hma-wrap", kind === "hma"],
      ["ob-zlema-wrap", kind === "zlema"],
    ].forEach(function (pair) {
      const el = $(pair[0]);
      if (el) el.hidden = !pair[1];
    });
  }

  function syncTpControls() {
    const mode = $("ob-tp-mode") && $("ob-tp-mode").value;
    const fixed = $("ob-tp-fixed");
    const rangeMult = $("ob-tp-range-mult");
    const rMult = $("ob-tp-sl-mult");
    const cap = mode === "fixed_cap";
    if (fixed) {
      fixed.disabled = mode !== "fixed" && !cap;
      fixed.title = cap
        ? "Ceiling. The target is this distance, unless the stop is small enough that this would be more than SL mult R away."
        : mode === "fixed"
          ? "Take-profit distance in pts."
          : "Used when TP mode is fixed pts or fixed, cap at R.";
    }
    if (rangeMult) {
      rangeMult.disabled = mode !== "range_mult";
      rangeMult.title =
        mode === "range_mult"
          ? "TP distance = Asia width × this."
          : "Used when TP mode is range × mult.";
    }
    if (rMult) {
      rMult.disabled = mode !== "sl_mult" && !cap;
      rMult.title = cap
        ? "Max R. Target = min(fixed pts, stop × this). 2 with a 4000 ceiling leaves any stop of 2000 or wider at 4000."
        : mode === "sl_mult"
          ? "Target distance = stop distance × this. 2 means the target is twice the stop."
          : "Used when TP mode is SL multiple or fixed, cap at R.";
    }
    const help = $("ob-tp-sl-mult-help");
    if (help) {
      help.textContent = cap
        ? "Quiet stops: target shrinks to stop × this. Wide stops stay at the fixed ceiling."
        : "Target distance = stop distance × this. 2 means the target is twice the stop.";
    }
  }

  function syncTrailArmControls() {
    const mode = $("ob-trail-arm-mode") && $("ob-trail-arm-mode").value;
    const fixed = $("ob-trail-arm");
    const cap = $("ob-trail-arm-cap");
    const dist = $("ob-trail");
    const fromFill = mode === "from_fill";
    const trailOff = mode === "off";
    if (fixed) {
      fixed.disabled = trailOff || fromFill || mode === "asia";
      fixed.title = trailOff
        ? "Ignored: trail is off."
        : fromFill
          ? "Ignored: trail starts at the fill."
          : mode === "asia"
            ? "Ignored when Trail arm mode is Asia range (arm = Asia range, capped)."
            : "Profit (pts) before the trail turns on. 0 = off.";
    }
    if (cap) {
      cap.disabled = trailOff || fromFill || mode !== "asia";
      cap.title = trailOff
        ? "Ignored: trail is off."
        : fromFill
          ? "Ignored: from-fill has no arm cap."
          : mode === "asia"
            ? "Max trail-arm when using Asia range. 0 = no cap."
            : "Cap is used when Trail arm mode is Asia range. 0 = no cap.";
    }
    if (dist) {
      dist.disabled = trailOff;
      dist.title = trailOff
        ? "Ignored: trail is off."
        : fromFill
          ? "Gap behind the best price from the fill. 0 = use the initial SL (up 100 → remaining risk 1900 if SL was 2000)."
          : "Gap behind the best price once the trail has armed.";
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
        <li>Entry = first of: the selected moving average (EMA, KAMA, HMA, or ZLEMA), a fib of the Asia box, or both — whichever price tags first — or a <em>higher/lower close resume</em>. Pullback off enters on the break close. Preferred timeout <em>market</em> waits the full window then fills the last wait-bar close. <em>Wait from break</em> counts max wait from the break bar. A rolling fib waits from the bar that locks the window.</li>
        <li>No partial TP. Optional BE moves SL to entry after a profit threshold. Trail arms after a profit threshold (fixed pts, or Asia range with a cap), then trails. Flatten at local hour.</li>
      </ol>
      <p class="hint">
        Mid fill. One trade per day by default. Skips days with no valid break / no pullback (required mode).
        Seasonal month (optional): Jan/Aug long, May/Jun short. Filter skips the against-side break.
        FX majors use 0.1 pip per point. Moving from gold or bitcoin onto an FX major divides point fields by 10, and moving back multiplies them by 10. Bitcoin uses $0.01 per point, the same as gold. News days are the gold calendar.
        Join inside box takes the combined bias side when price never left the Asia range.
        2-week trend (optional, works without the month table): last close vs daily EMA, skip two-way paths (low efficiency). Filter skips the against-side. If month and 2-week both filter and disagree, neither side is skipped.
      </p>
    </section>

    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ob-symbol" title="FX majors: 1 point = 0.1 pip. Moving from gold or bitcoin onto an FX major divides point fields by 10.">
            ${window.strategSymbols.optionsHtml()}
          </select>
        </label>
        <label>From (local date)
          <input type="date" id="ob-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="ob-to" value="2025-08-01" />
        </label>
        <label>Workers
          <input type="number" id="ob-workers" value="3" min="1" max="6" step="1"
            title="Parallel months (separate processes). Each worker holds one month of ticks or 5m candles." />
        </label>
        <label>Data
          <select id="ob-data"
            title="5m candles are built from ticks once and cached in data/candles/5m/. Signals stay 15m. Fills/exits are conservative vs ticks (level fill at the level; same-bar SL beats TP).">
            <option value="candles_5m" selected>5m candles (cached)</option>
            <option value="ticks">Tick data (precise)</option>
          </select>
        </label>

        <div class="ob-group">
          <div class="ob-group-title">Asia box</div>
          <div class="ob-group-fields">
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
          </div>
        </div>

        <div class="ob-group">
          <div class="ob-group-title">Pullback</div>
          <div class="ob-group-fields">
            <label>Pullback mode
              <select id="ob-pullback-mode">
                <option value="required" selected>required (level or higher-close)</option>
                <option value="preferred">preferred (timeout action)</option>
                <option value="off">off (enter on break close)</option>
              </select>
              <span class="field-help">Required waits for the level or a higher/lower close. Preferred can still fill at the timeout. Off enters on the break close.</span>
            </label>
            <label>Pullback level
              <select id="ob-pullback-ref">
                <option value="ema" selected>Moving average</option>
                <option value="fib">Fib of the Asia box</option>
                <option value="both">Both, whichever comes first</option>
              </select>
              <span class="field-help">Moving average uses whichever MA you pick below: EMA, KAMA, HMA, or ZLEMA. Both enters on the first tag of that MA or the fib. Higher/lower close still runs beside this.</span>
            </label>
            <label id="ob-fib-level-wrap" hidden>Fib level
              <input type="number" id="ob-pullback-fib" value="0.5" min="0" max="1" step="0.001" />
              <span class="field-help">0 is the edge in the trade direction. 0.5 is the midpoint. 0.618 is a deeper pullback, closer to the far side of the box.</span>
            </label>
            <label id="ob-fib-anchor-wrap" hidden>Fib window
              <select id="ob-fib-anchor">
                <option value="asia" selected>Asia session</option>
                <option value="roll">Roll while expanding</option>
              </select>
              <span class="field-help">Asia session uses the start-to-end high and low. Roll keeps that length and slides both edges forward 15 minutes while price makes a new extreme, up to Max break candles. The first bar that stops extending locks the fib and arms the level.</span>
            </label>
            <label>Moving average
              <select id="ob-ma-type">
                <option value="ema" selected>EMA</option>
                <option value="kama">KAMA</option>
                <option value="hma">HMA</option>
                <option value="zlema">ZLEMA</option>
              </select>
              <span class="field-help">Only this average's settings are shown. Both and the moving-average pullback use this one, not a fixed EMA.</span>
            </label>
            <label id="ob-ema-wrap">EMA period (15m)
              <input type="number" id="ob-ema" value="21" min="1" max="200" />
            </label>
            <label id="ob-kama-er-wrap" hidden>KAMA ER length
              <input type="number" id="ob-kama-er" value="10" min="1" max="100" />
              <span class="field-help">Efficiency-ratio window. Kaufman default is 10.</span>
            </label>
            <label id="ob-kama-fast-wrap" hidden>KAMA fast
              <input type="number" id="ob-kama-fast" value="2" min="1" max="50" />
            </label>
            <label id="ob-kama-slow-wrap" hidden>KAMA slow
              <input type="number" id="ob-kama-slow" value="30" min="1" max="200" />
            </label>
            <label id="ob-hma-wrap" hidden>HMA period
              <input type="number" id="ob-hma" value="21" min="2" max="200" />
            </label>
            <label id="ob-zlema-wrap" hidden>ZLEMA period
              <input type="number" id="ob-zlema" value="21" min="1" max="200" />
            </label>
            <label>Max wait candles
              <input type="number" id="ob-max-wait" value="8" min="1" max="20" />
            </label>
            <label class="chk">Wait from break
              <input type="checkbox" id="ob-wait-from-break"
                title="Off = wait only inside leftover max-break-after-Asia bars. On = count max wait candles from the actual break bar (not clipped by a late break). A rolling fib always waits from the lock bar." />
            </label>
            <label class="chk">Higher/lower close resume
              <input type="checkbox" id="ob-higher-close" checked />
            </label>
            <label>Resume closes
              <input type="number" id="ob-resume-closes" value="1" min="1" max="8" step="1" />
            </label>
            <label>Resume max from break (pts)
              <input type="number" id="ob-resume-max-break" value="0" min="0" step="50"
                title="Higher/lower close resume only: wait-bar close may not extend more than this many pts past the break close (long: above, short: below). 0 = off. Pullback side of the break always allowed. The level touch ignores this." />
            </label>
          </div>
        </div>

        <div class="ob-group">
          <div class="ob-group-title">Timeout</div>
          <div class="ob-group-fields">
            <label>Timeout action (preferred)
              <select id="ob-timeout"
                title="After max wait with no level or resume: skip, or market at the last wait-bar close (live chase). A rolling fib that never tags its level uses this same ending.">
                <option value="skip" selected>skip</option>
                <option value="market">market</option>
              </select>
            </label>
            <label>Timeout max level dist (pts)
              <input type="number" id="ob-timeout-ema-dist" value="0" min="0" step="50"
                title="Preferred timeout only: skip if the wait never got this close to the active level (the selected MA, the fib, or the closer of the two). 0 = off. A missing level also skips." />
            </label>
            <label>Timeout min break (pts)
              <input type="number" id="ob-timeout-min-break" value="0" min="0" step="50"
                title="Preferred timeout only: extra break size vs Asia. A level touch ignores this. 0 = no extra." />
            </label>
            <label>Timeout min pullback (pts)
              <input type="number" id="ob-timeout-min-pullback" value="0" min="0" step="50"
                title="Preferred timeout only: last wait candle close must be this many pts back from the break close (long: below, short: above). 0 = off. Level and resume fills ignore this." />
            </label>
          </div>
        </div>

        <div class="ob-near-box">
          <div class="ob-near-box-title">Near box</div>
          <div class="ob-near-box-fields">
            <label>Bars
              <input type="number" id="ob-near-bars" value="0" min="0" max="20" step="1"
                title="Required pullback only. 0 = off. If the wait ends with no level or close-resume, fill when the last N wait closes all sit within Near-box dist of the broken Asia edge." />
            </label>
            <label>Distance (pts)
              <input type="number" id="ob-near-pts" value="500" min="0" step="50"
                title="Max distance from Asia high (long) or Asia low (short) for each of the last N wait closes. 1 pt = 0.1 pip on an FX major." />
            </label>
            <label>Trend
              <select id="ob-near-trend" title="Extra gate after the distance check. Outside = last close still beyond Asia by the min break. Breakout = that, and the last close extended further than the first of the N.">
                <option value="off" selected>off (distance only)</option>
                <option value="closes_dir">closes step with the break</option>
                <option value="net_ext">net extension</option>
                <option value="outside">still outside</option>
                <option value="breakout">breakout (extend + outside)</option>
              </select>
            </label>
            <label>Min Asia range (pts)
              <input type="number" id="ob-near-min-range" value="0" min="0" step="50"
                title="Near-box fill only when Asia high-low is at least this many points. 0 = off. Level touches and close-resume ignore this." />
            </label>
          </div>
        </div>

        <div class="ob-group">
          <div class="ob-group-title">Filters</div>
          <div class="ob-group-fields">
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
            <label>2-week trend
              <select id="ob-week2-mode"
                title="Last close vs ~10-session EMA of daily closes, plus path efficiency. Off = ignore. Tag = stamp only. Filter = skip the against-side Asia break even if Seasonal month is off. If both filter and they disagree, no skip.">
                <option value="off" selected>off</option>
                <option value="tag">tag only</option>
                <option value="filter">filter against-side</option>
              </select>
            </label>
            <label>Trend flat (pts)
              <input type="number" id="ob-trend-flat" value="1500" min="0" step="100"
                title="2-week net close-to-close below this is flat (too small to care). Gold default 1500 pts = $15." />
            </label>
            <label>Trend efficiency min
              <input type="number" id="ob-trend-eff" value="0.35" min="0" max="1" step="0.05"
                title="|net| / sum of |daily changes| over the 2-week window. Below this = two-way chop, no side. 0 = off." />
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
          </div>
        </div>

        <div class="ob-group">
          <div class="ob-group-title">Stop and target</div>
          <div class="ob-group-fields">
            <label>SL mode
              <select id="ob-sl-mode">
                <option value="asia_opposite" selected>asia opposite</option>
                <option value="range">Asia range</option>
                <option value="fixed">fixed pts</option>
                <option value="m12_frac">12m avg × frac</option>
              </select>
            </label>
            <label>SL fixed (pts)
              <input type="number" id="ob-sl-fixed" value="500" min="50" step="50" />
            </label>
            <label>SL range mult
              <input type="number" id="ob-sl-range-mult" value="1" min="0.1" step="0.1"
                title="Asia range mode: SL distance = Asia width × this. 1 = the range itself." />
            </label>
            <label>SL 12m frac
              <select id="ob-sl-m12-frac"
                title="Stop = this fraction of the last-12-month average daily-close range, rounded up to 50 pts.">
                <option value="0.25">1/4</option>
                <option value="0.333333" selected>1/3</option>
                <option value="0.5">1/2</option>
              </select>
            </label>
            <label>SL cap (pts)
              <input type="number" id="ob-sl-cap" value="0" min="0" step="50"
                title="Max SL distance for asia opposite, Asia range, and 12m frac. 0 = off. If the raw SL is farther, it is pulled in to this many pts." />
            </label>
            <label>TP mode
              <select id="ob-tp-mode">
                <option value="range_mult" selected>range × mult</option>
                <option value="fixed">fixed pts</option>
                <option value="fixed_cap">fixed, cap at R</option>
                <option value="sl_mult">SL multiple</option>
                <option value="m12">12m avg (daily closes)</option>
              </select>
            </label>
            <label>TP fixed (pts)
              <input type="number" id="ob-tp-fixed" value="1000" min="50" step="50" />
            </label>
            <label>TP range mult
              <input type="number" id="ob-tp-range-mult" value="1.5" min="0.1" step="0.1" />
            </label>
            <label>SL mult
              <input type="number" id="ob-tp-sl-mult" value="2" min="0.5" step="0.1" />
              <span class="field-help" id="ob-tp-sl-mult-help">Target distance = stop distance × this. 2 means the target is twice the stop.</span>
            </label>
          </div>
        </div>

        <div class="ob-group">
          <div class="ob-group-title">Trail and time stop</div>
          <div class="ob-group-fields">
            <label>Trail arm mode
              <select id="ob-trail-arm-mode">
                <option value="off">off (no trail)</option>
                <option value="fixed" selected>fixed pts</option>
                <option value="asia">Asia range (capped)</option>
                <option value="from_fill">from fill (walk SL with price)</option>
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
              <input type="number" id="ob-trail" value="250" min="0" step="50"
                title="Gap behind the best price once the trail is on. From-fill + 0 = use the initial SL (up 100 pts → remaining risk 1900 if SL was 2000)." />
            </label>
            <label>BE arm (pts)
              <input type="number" id="ob-be-arm" value="0" min="0" step="50"
                title="Move SL to entry once profit reaches this many pts. 0 = off. Trail still tightens independently." />
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
          </div>
        </div>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="ob-run">Run overnight break</button>
        <button type="button" class="secondary" id="ob-stop" disabled>Stop</button>
        <label class="chk force">
          <input type="checkbox" id="ob-force" /> Force re-download
        </label>
        <p class="table-note">
          5m candles: first run builds <code>data/candles/5m/</code>; later runs reuse it.
          Tick data: same dates reuse the tick pack (RAM + disk). Force also rebuilds 5m months
          from ticks. Leave force off when you are only changing strategy params.
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
      <div class="ob-params" id="ob-run-params" hidden></div>
      <p class="table-note" id="ob-skip-breakdown"></p>
      <h3>Streaks</h3>
      <p class="table-note">
        Consecutive wins / losses in date order. A scratch (0 pts) breaks the run.
        Count = how many streaks of that length.
      </p>
      <div class="hero-grid" id="ob-streaks-hero"></div>
      <div class="table-wrap">
        <table id="ob-streaks">
          <thead>
            <tr>
              <th>Length</th>
              <th>Win streaks</th>
              <th>Loss streaks</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
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
        Entry = the selected moving average, a fib level, higher/lower close resume, or break close.
        Click a row to open the 15m chart in a new tab once the run is in the catalog.
        Hover <strong>Decision</strong> for the full wait / level / close-vs-prev line.
        Max fav / max adv = best and worst mid vs fill (break close on skips) until flatten hour, even if the trade already exited.
        Adv/SL = max adv vs SL pts (can exceed 100% when price kept going after the stop).
      </p>
      <div class="table-wrap table-sticky">
        <table id="ob-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Side</th>
              <th>Asia range</th>
              <th>Break pts</th>
              <th>Entry</th>
              <th>Wait</th>
              <th>Level</th>
              <th>Closest</th>
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
        (wait / closest level / best close vs prev). Max fav / max adv after a break
        are from the break close until flatten hour.
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
              <th>Level</th>
              <th>Closest</th>
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
      foot.textContent += " Overnight break = Asia range, then the selected moving average, a fib of the Asia session or a rolling window, or whichever tags first.";
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
          ["tab-research", "tab-sweep", "tab-session", "tab-spikefade", "tab-micro", "tab-burst", "tab-cooloff", "tab-fvg", "tab-asia-liq", "tab-impulse-fork"].forEach((id) => {
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
    no_pullback: "No level / close resume in wait",
    no_pullback_timeout: "Pullback timeout (skip)",
    late_short: "Late short on small/medium Asia",
    no_entry: "No entry",
    past_flatten: "Past flatten hour",
    seasonal_bias: "Season / 2-week bias",
    news_day: "News day",
    no_m12: "No 12m daily-close range",
  };

  const ENTRY_LABELS = {
    ema_touch: "EMA touch",
    fib_touch: "Fib touch",
    reentry: "Second trade",
    higher_close: "Higher close resume",
    lower_close: "Lower close resume",
    break_close: "Break close",
    seasonal_join: "Seasonal join (inside box)",
    timeout_market: "Timeout market",
    near_box_timeout: "Near-box timeout",
  };

  const PARAM_FIELDS = [
    ["timezone", "Timezone"],
    ["asia_start_hour", "Asia start"],
    ["asia_end_hour", "Asia end"],
    ["min_asia_range_pts", "Min Asia pts"],
    ["min_break_pts_above", "Min break up"],
    ["min_break_pts_below", "Min break down"],
    ["break_on_wick", "Wick break"],
    ["max_break_candles_after", "Max break bars"],
    ["pullback_mode", "Pullback"],
    ["pullback_ref", "Pullback level"],
    ["pullback_fib", "Fib level"],
    ["fib_anchor", "Fib window"],
    ["ma_type", "Moving average"],
    ["ema_period", "EMA"],
    ["kama_er", "KAMA ER"],
    ["kama_fast", "KAMA fast"],
    ["kama_slow", "KAMA slow"],
    ["hma_period", "HMA"],
    ["zlema_period", "ZLEMA"],
    ["max_wait_candles", "Max wait"],
    ["wait_from_break", "Wait from break"],
    ["timeout_action", "Timeout action"],
    ["timeout_max_ema_dist_pts", "Timeout max level dist"],
    ["timeout_min_break_pts", "Timeout min break"],
    ["timeout_min_pullback_pts", "Timeout min pullback"],
    ["near_box_bars", "Near-box bars"],
    ["near_box_pts", "Near-box dist"],
    ["near_box_trend", "Near-box trend"],
    ["near_box_min_range_pts", "Near-box min Asia"],
    ["use_higher_close", "Close resume"],
    ["resume_closes", "Resume closes"],
    ["resume_max_break_pts", "Resume max from break"],
    ["skip_late_short_wait", "Late short wait ≥"],
    ["skip_late_short_asia_pts", "Late short Asia <"],
    ["side_filter", "Side"],
    ["seasonal_mode", "Seasonal month"],
    ["seasonal_join", "Join inside box"],
    ["week2_mode", "2-week trend"],
    ["trend_flat_pts", "Trend flat pts"],
    ["trend_sessions", "Trend sessions"],
    ["trend_efficiency_min", "Trend efficiency min"],
    ["news_mode", "News"],
    ["news_set", "News set"],
    ["sl_mode", "SL mode"],
    ["sl_fixed_pts", "SL fixed"],
    ["sl_range_mult", "SL range ×"],
    ["sl_cap_pts", "SL cap"],
    ["sl_m12_frac", "SL 12m frac"],
    ["tp_mode", "TP mode"],
    ["tp_fixed_pts", "TP fixed"],
    ["tp_range_mult", "TP range ×"],
    ["tp_sl_mult", "SL multiple"],
    ["trail_arm_mode", "Trail arm mode"],
    ["trail_arm_pts", "Trail arm pts"],
    ["trail_arm_cap_pts", "Trail arm cap"],
    ["trail_pts", "Trail pts"],
    ["be_arm_pts", "BE arm pts"],
    ["max_hold_hours", "Max hold h"],
    ["flatten_hour", "Flatten hour"],
    ["one_trade_per_day", "One per day"],
  ];

  const PARAM_FORM_IDS = {
    asia_start_hour: "ob-asia-start",
    asia_end_hour: "ob-asia-end",
    min_asia_range_pts: "ob-min-asia",
    min_break_pts_above: "ob-break-up",
    min_break_pts_below: "ob-break-dn",
    break_on_wick: "ob-break-wick",
    max_break_candles_after: "ob-max-break-candles",
    pullback_mode: "ob-pullback-mode",
    pullback_ref: "ob-pullback-ref",
    pullback_fib: "ob-pullback-fib",
    fib_anchor: "ob-fib-anchor",
    ma_type: "ob-ma-type",
    ema_period: "ob-ema",
    kama_er: "ob-kama-er",
    kama_fast: "ob-kama-fast",
    kama_slow: "ob-kama-slow",
    hma_period: "ob-hma",
    zlema_period: "ob-zlema",
    max_wait_candles: "ob-max-wait",
    wait_from_break: "ob-wait-from-break",
    timeout_action: "ob-timeout",
    timeout_max_ema_dist_pts: "ob-timeout-ema-dist",
    timeout_min_break_pts: "ob-timeout-min-break",
    timeout_min_pullback_pts: "ob-timeout-min-pullback",
    near_box_bars: "ob-near-bars",
    near_box_pts: "ob-near-pts",
    near_box_trend: "ob-near-trend",
    near_box_min_range_pts: "ob-near-min-range",
    use_higher_close: "ob-higher-close",
    resume_closes: "ob-resume-closes",
    resume_max_break_pts: "ob-resume-max-break",
    skip_late_short_wait: "ob-late-short-wait",
    skip_late_short_asia_pts: "ob-late-short-asia",
    side_filter: "ob-side",
    seasonal_mode: "ob-seasonal-mode",
    seasonal_join: "ob-seasonal-join",
    week2_mode: "ob-week2-mode",
    trend_flat_pts: "ob-trend-flat",
    trend_efficiency_min: "ob-trend-eff",
    news_mode: "ob-news-mode",
    news_set: "ob-news-set",
    sl_mode: "ob-sl-mode",
    sl_fixed_pts: "ob-sl-fixed",
    sl_range_mult: "ob-sl-range-mult",
    sl_cap_pts: "ob-sl-cap",
    sl_m12_frac: "ob-sl-m12-frac",
    tp_mode: "ob-tp-mode",
    tp_fixed_pts: "ob-tp-fixed",
    tp_range_mult: "ob-tp-range-mult",
    tp_sl_mult: "ob-tp-sl-mult",
    trail_arm_mode: "ob-trail-arm-mode",
    trail_arm_pts: "ob-trail-arm",
    trail_arm_cap_pts: "ob-trail-arm-cap",
    trail_pts: "ob-trail",
    be_arm_pts: "ob-be-arm",
    max_hold_hours: "ob-max-hold",
    flatten_hour: "ob-flatten",
    one_trade_per_day: "ob-one-per-day",
  };

  function fmtParam(key, raw) {
    if (raw == null || raw === "") return "—";
    if (typeof raw === "boolean") return raw ? "yes" : "no";
    if (key === "week2_mode" && (raw === "off" || raw === false)) return "off";
    if (key === "sl_m12_frac") {
      const x = Number(raw);
      if (Math.abs(x - 0.25) < 0.03) return "1/4";
      if (Math.abs(x - 0.5) < 0.03) return "1/2";
      return "1/3";
    }
    if (key === "tp_mode" && raw === "m12") return "12m avg";
    if (key === "tp_mode" && (raw === "sl_mult" || raw === "r_mult")) return "SL multiple";
    if (key === "tp_mode" && (raw === "fixed_cap" || raw === "fixed_r" || raw === "cap")) return "fixed, cap at R";
    if (key === "sl_mode" && raw === "m12_frac") return "12m × frac";
    if (key === "pullback_ref" && raw === "ema") return "moving average";
    if (key === "pullback_ref" && raw === "both") return "both";
    if (key === "ma_type") return String(raw).toUpperCase();
    if (key === "fib_anchor" && raw === "roll") return "roll while expanding";
    if (key === "fib_anchor") return "Asia session";
    return String(raw);
  }

  function runParams(result) {
    const p = Object.assign({}, (result && result.params) || {});
    if (p.week2_mode == null) {
      p.week2_mode = p.week2_trend ? "tag" : "off";
    }
    if (p.break_on_wick == null && p.require_close_outside != null) {
      p.break_on_wick = !p.require_close_outside;
    }
    if (p.sl_mode === "range_width" || p.sl_mode === "asia_range") {
      p.sl_mode = "range";
    }
    if (p.tp_mode === "r_mult" || p.tp_mode === "r" || p.tp_mode === "sl") {
      p.tp_mode = "sl_mult";
    }
    if (p.tp_sl_mult == null && p.tp_r_mult != null) {
      p.tp_sl_mult = p.tp_r_mult;
    }
    if (p.ma_type == null) p.ma_type = "ema";
    if (p.fib_anchor == null) p.fib_anchor = "asia";
    return p;
  }

  function paramEq(a, b) {
    if (a === b) return true;
    if (a == null && b == null) return true;
    if (typeof a === "boolean" || typeof b === "boolean") return !!a === !!b;
    if (a == null || b == null) return false;
    const na = Number(a);
    const nb = Number(b);
    if (a !== "" && b !== "" && !Number.isNaN(na) && !Number.isNaN(nb)) {
      return na === nb;
    }
    return String(a) === String(b);
  }

  function rangeKey(result) {
    return (
      dash(result && result.symbol) +
      " · " +
      dash(result && result.date_from) +
      " → " +
      dash(result && result.date_to)
    );
  }

  let lastRunParamSnap = null;

  function renderRunParams(result) {
    const el = $("ob-run-params");
    if (!el) return;
    const p = runParams(result);
    if (!result || !Object.keys(p).length) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    const snap = { __range: rangeKey(result) };
    PARAM_FIELDS.forEach(function (pair) {
      snap[pair[0]] = p[pair[0]];
    });
    const prev = lastRunParamSnap;
    const canDiff = prev != null;
    const bits = [
      '<div class="ob-params-title">Run settings</div>',
    ];
    if (result.symbol || result.date_from) {
      bits.push(
        '<div class="ob-param ob-param-wide' +
          (canDiff && !paramEq(prev.__range, snap.__range) ? " is-changed" : "") +
          '"><div class="k">Range</div><div class="v">' +
          snap.__range +
          "</div></div>"
      );
    }
    PARAM_FIELDS.forEach(function (pair) {
      const key = pair[0];
      if (!Object.prototype.hasOwnProperty.call(p, key) && key !== "week2_mode") {
        return;
      }
      const changed = canDiff && !paramEq(prev[key], snap[key]);
      bits.push(
        '<div class="ob-param' +
          (changed ? " is-changed" : "") +
          '"><div class="k">' +
          pair[1] +
          '</div><div class="v">' +
          fmtParam(key, p[key]) +
          "</div></div>"
      );
    });
    el.innerHTML = bits.join("");
    el.hidden = false;
    lastRunParamSnap = snap;
  }

  function applyFormFromResult(result) {
    if (!result) return;
    const p = runParams(result);
    if (result.symbol && $("ob-symbol")) $("ob-symbol").value = formSymbol(result.symbol);
    if (result.date_from && $("ob-from")) $("ob-from").value = String(result.date_from).slice(0, 10);
    if (result.date_to && $("ob-to")) $("ob-to").value = String(result.date_to).slice(0, 10);
    if (result.data_source && $("ob-data")) $("ob-data").value = String(result.data_source);
    Object.keys(PARAM_FORM_IDS).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(p, key)) return;
      const el = $(PARAM_FORM_IDS[key]);
      if (!el) return;
      const v = p[key];
      if (el.type === "checkbox") el.checked = !!v;
      else if (key === "timeout_action" && v === "worst") el.value = "market";
      else if (key === "sl_m12_frac") {
        const x = Number(v);
        if (Math.abs(x - 0.25) < 0.03) el.value = "0.25";
        else if (Math.abs(x - 0.5) < 0.03) el.value = "0.5";
        else el.value = "0.333333";
      } else el.value = v == null ? "" : String(v);
    });
    syncPullbackControls();
    syncTrailArmControls();
    syncSlControls();
    syncTpControls();
    scheduleSave();
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

  function streakLenMap(raw) {
    const out = {};
    if (!raw || typeof raw !== "object") return out;
    Object.keys(raw).forEach(function (k) {
      const n = Number(k);
      if (!(n > 0)) return;
      out[n] = Number(raw[k]) || 0;
    });
    return out;
  }

  function renderStreaks(result, heroEl, tbody) {
    const s = (result && result.streaks) || {};
    const cur = s.current;
    const curLabel = cur && cur.side && cur.len
      ? cur.len +
        " " +
        (cur.side === "win"
          ? cur.len === 1
            ? "win"
            : "wins"
          : cur.len === 1
            ? "loss"
            : "losses")
      : "—";
    if (heroEl) {
      heroEl.innerHTML =
        heroItem("Max win streak", s.max_win != null ? s.max_win : "—") +
        heroItem("Max loss streak", s.max_loss != null ? s.max_loss : "—") +
        heroItem("Win streaks", s.win_streaks != null ? s.win_streaks : "—") +
        heroItem("Loss streaks", s.loss_streaks != null ? s.loss_streaks : "—") +
        heroItem("Current", curLabel);
    }
    if (!tbody) return;
    tbody.innerHTML = "";
    const wins = streakLenMap(s.win_by_len);
    const losses = streakLenMap(s.loss_by_len);
    const lens = {};
    Object.keys(wins).forEach(function (k) {
      lens[k] = true;
    });
    Object.keys(losses).forEach(function (k) {
      lens[k] = true;
    });
    const rows = Object.keys(lens)
      .map(Number)
      .filter(function (n) {
        return n > 0;
      })
      .sort(function (a, b) {
        return a - b;
      });
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="3" class="muted">No win/loss streaks</td></tr>';
      return;
    }
    rows.forEach(function (len) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        len +
        "</td><td>" +
        (wins[len] || 0) +
        "</td><td>" +
        (losses[len] || 0) +
        "</td>";
      tbody.appendChild(tr);
    });
  }

  function dash(v) {
    return v == null || v === "" ? "—" : v;
  }

  function pointSize(symbol) {
    const s = String(symbol || "").toUpperCase();
    if (s.indexOf("JPY") >= 0) return 0.001;
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

  function lanePct(ln) {
    return Math.max(0, Math.min(100, Number(ln && ln.pct) || 0));
  }

  function laneSignature(lanes) {
    return lanes
      .map(function (ln, i) {
        const slot = ln.slot != null ? ln.slot : i;
        const phase = ln.phase || "idle";
        const detail = ln.detail || (phase === "idle" ? "waiting" : "");
        const trades = ln.trades && phase !== "idle" ? String(ln.trades) : "";
        return [slot, phase, monthLabel(ln), detail, trades].join("\u0001");
      })
      .join("\u0002");
  }

  function paintLaneMeters(el, lanes) {
    const bars = el.querySelectorAll(".sf-lane-bar");
    const pcts = el.querySelectorAll(".sf-lane-pct");
    lanes.forEach(function (ln, i) {
      const pct = lanePct(ln);
      if (bars[i]) bars[i].style.width = pct + "%";
      if (pcts[i]) pcts[i].textContent = pct.toFixed(0) + "%";
    });
  }

  function renderLanes(st) {
    const el = $("ob-lanes");
    if (!el) return;
    const p = st.progress || {};
    let lanes = p.lanes || [];
    const running = !!st.running;
    el.classList.toggle("is-live", running);
    if (running && !lanes.length) {
      const n = Number(st.params && st.params.workers) || 3;
      lanes = [];
      for (let i = 0; i < n; i++) {
        lanes.push({ slot: i, phase: "idle", pct: 0, detail: "starting…" });
      }
    }
    if (!lanes.length) {
      el.innerHTML = "";
      el.dataset.sig = "";
      el.hidden = true;
      return;
    }
    el.hidden = false;
    const sig = laneSignature(lanes);
    if (el.dataset.sig === sig && el.children.length === lanes.length) {
      paintLaneMeters(el, lanes);
      return;
    }
    el.dataset.sig = sig;
    el.innerHTML = lanes
      .map(function (ln, i) {
        const slot = ln.slot != null ? ln.slot : i;
        const hue = LANE_HUES[slot % LANE_HUES.length];
        const phase = ln.phase || "idle";
        const pct = lanePct(ln);
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
          '<span class="sf-lane-pct">' +
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
    const streakHero = $("ob-streaks-hero");
    const stb = $("ob-streaks") && $("ob-streaks").querySelector("tbody");
    const mb = $("ob-months") && $("ob-months").querySelector("tbody");
    const tb = $("ob-table") && $("ob-table").querySelector("tbody");
    const sb = $("ob-skips") && $("ob-skips").querySelector("tbody");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      renderRunParams(null);
      if (breakdown) breakdown.textContent = "";
      if (streakHero) streakHero.innerHTML = "";
      if (stb) stb.innerHTML = "";
      if (mb) mb.innerHTML = "";
      if (tb) tb.innerHTML = "";
      if (sb) sb.innerHTML = "";
      return;
    }
    if (meta) {
      const monthErrs = result.month_errors || [];
      const srcLabel =
        result.data_source === "candles_5m"
          ? " · 5m candles"
          : result.data_source === "ticks"
            ? " · ticks"
            : "";
      meta.textContent =
        (result.symbol || "") +
        " · " +
        (result.date_from || "") +
        " → " +
        (result.date_to || "") +
        srcLabel +
        " · " +
        (result.trades || 0) +
        " trades · " +
        (result.skipped || 0) +
        " skipped · avg " +
        (result.avg_pts != null ? result.avg_pts : "—") +
        " pts" +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "") +
        (monthErrs.length
          ? " · " + monthErrs.length + " month error(s): " + monthErrs.join("; ").slice(0, 240)
          : "");
      if (result.sqlite_id) {
        meta.appendChild(document.createTextNode(" · "));
        const a = document.createElement("a");
        a.href = "/overnight/results?run=" + encodeURIComponent(result.sqlite_id);
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "Open catalog #" + result.sqlite_id;
        meta.appendChild(a);
      }
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("Avg pts", result.avg_pts) +
        heroItem("PF", result.profit_factor != null ? result.profit_factor : "—") +
        heroItem("Sum pts", result.sum_pts) +
        heroItem("Trail armed %", result.trail_armed_pct != null ? result.trail_armed_pct + "%" : "—") +
        heroItem("BE armed %", result.be_armed_pct != null ? result.be_armed_pct + "%" : "—") +
        heroItem("Avg win", result.avg_win_pts) +
        heroItem("Avg loss", result.avg_loss_pts) +
        heroItem("Skipped", result.skipped);
    }
    renderRunParams(result);
    renderStreaks(result, streakHero, stb);
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
          '<tr><td colspan="21" class="muted">No trades in this window</td></tr>';
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
          if (t.id) {
            tr.className = "ob-trade-link";
            tr.tabIndex = 0;
            tr.title = "Open the 15m chart";
            function openChart() {
              window.open("/overnight/chart?trade=" + t.id, "_blank");
            }
            tr.addEventListener("click", openChart);
            tr.addEventListener("keydown", function (ev) {
              if (ev.key === "Enter") openChart();
            });
          }
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
            "</td><td>" +
            dash(t.closest_ema_pts) +
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
            (t.be_armed ? " BE" : "") +
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
        fib_anchor: ($("ob-fib-anchor") && $("ob-fib-anchor").value) || "asia",
        ma_type: ($("ob-ma-type") && $("ob-ma-type").value) || "ema",
        ema_period: Number($("ob-ema").value),
        kama_er: Math.max(1, Number(($("ob-kama-er") && $("ob-kama-er").value) || 10)),
        kama_fast: Math.max(1, Number(($("ob-kama-fast") && $("ob-kama-fast").value) || 2)),
        kama_slow: Math.max(1, Number(($("ob-kama-slow") && $("ob-kama-slow").value) || 30)),
        hma_period: Math.max(2, Number(($("ob-hma") && $("ob-hma").value) || 21)),
        zlema_period: Math.max(1, Number(($("ob-zlema") && $("ob-zlema").value) || 21)),
        max_wait_candles: Number($("ob-max-wait").value),
        wait_from_break: $("ob-wait-from-break") && $("ob-wait-from-break").checked,
        timeout_action: ($("ob-timeout").value === "worst") ? "market" : $("ob-timeout").value,
        timeout_max_ema_dist_pts: Number(($("ob-timeout-ema-dist") && $("ob-timeout-ema-dist").value) || 0),
        timeout_min_break_pts: Number(($("ob-timeout-min-break") && $("ob-timeout-min-break").value) || 0),
        timeout_min_pullback_pts: Number(($("ob-timeout-min-pullback") && $("ob-timeout-min-pullback").value) || 0),
        near_box_bars: Math.max(0, Number(($("ob-near-bars") && $("ob-near-bars").value) || 0)),
        near_box_pts: Number(($("ob-near-pts") && $("ob-near-pts").value) || 0),
        near_box_trend: ($("ob-near-trend") && $("ob-near-trend").value) || "off",
        near_box_min_range_pts: Math.max(0, Number(($("ob-near-min-range") && $("ob-near-min-range").value) || 0)),
        pullback_ref: ($("ob-pullback-ref") && $("ob-pullback-ref").value) || "ema",
        pullback_fib: Number(($("ob-pullback-fib") && $("ob-pullback-fib").value) || 0.5),
        use_higher_close: $("ob-higher-close") && $("ob-higher-close").checked,
        resume_closes: Math.max(1, Number($("ob-resume-closes") && $("ob-resume-closes").value) || 1),
        resume_max_break_pts: Number(($("ob-resume-max-break") && $("ob-resume-max-break").value) || 0),
        skip_late_short_wait: Math.max(0, Number($("ob-late-short-wait") && $("ob-late-short-wait").value) || 0),
        skip_late_short_asia_pts: Number(($("ob-late-short-asia") && $("ob-late-short-asia").value) || 0),
        sl_mode: $("ob-sl-mode").value,
        sl_fixed_pts: Number($("ob-sl-fixed").value),
        sl_range_mult: Number($("ob-sl-range-mult").value),
        sl_cap_pts: Number(($("ob-sl-cap") && $("ob-sl-cap").value) || 0),
        sl_m12_frac: Number(($("ob-sl-m12-frac") && $("ob-sl-m12-frac").value) || 1 / 3),
        tp_mode: $("ob-tp-mode").value,
        tp_fixed_pts: Number($("ob-tp-fixed").value),
        tp_range_mult: Number($("ob-tp-range-mult").value),
        tp_sl_mult: Number($("ob-tp-sl-mult").value),
        trail_arm_mode: ($("ob-trail-arm-mode") && $("ob-trail-arm-mode").value) || "fixed",
        trail_arm_pts: Number($("ob-trail-arm").value),
        trail_arm_cap_pts: Number(($("ob-trail-arm-cap") && $("ob-trail-arm-cap").value) || 0),
        trail_pts: Number($("ob-trail").value),
        be_arm_pts: Number(($("ob-be-arm") && $("ob-be-arm").value) || 0),
        max_hold_hours: Number($("ob-max-hold").value),
        flatten_hour: Number($("ob-flatten").value),
        one_trade_per_day: $("ob-one-per-day") && $("ob-one-per-day").checked,
        side_filter: $("ob-side").value,
        seasonal_mode: ($("ob-seasonal-mode") && $("ob-seasonal-mode").value) || "off",
        seasonal_join: $("ob-seasonal-join") && $("ob-seasonal-join").checked,
        week2_mode: ($("ob-week2-mode") && $("ob-week2-mode").value) || "off",
        week2_trend: ($("ob-week2-mode") && $("ob-week2-mode").value) !== "off",
        trend_flat_pts: Number($("ob-trend-flat") && $("ob-trend-flat").value) || 1500,
        trend_efficiency_min: Number($("ob-trend-eff") && $("ob-trend-eff").value) || 0,
        news_mode: ($("ob-news-mode") && $("ob-news-mode").value) || "off",
        news_set: ($("ob-news-set") && $("ob-news-set").value) || "scheduled",
        workers: Math.max(1, Math.min(6, Number($("ob-workers") && $("ob-workers").value) || 3)),
        force_download: $("ob-force") && $("ob-force").checked,
        data_source: ($("ob-data") && $("ob-data").value) || "candles_5m",
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
  syncSlControls();
  syncTpControls();
  const modeEl = $("ob-pullback-mode");
  if (modeEl) modeEl.addEventListener("change", syncPullbackControls);
  const refEl = $("ob-pullback-ref");
  if (refEl) refEl.addEventListener("change", syncPullbackControls);
  const maEl = $("ob-ma-type");
  if (maEl) maEl.addEventListener("change", syncMaFields);
  const resumeEl = $("ob-higher-close");
  if (resumeEl) resumeEl.addEventListener("change", syncPullbackControls);
  const trailModeEl = $("ob-trail-arm-mode");
  if (trailModeEl) trailModeEl.addEventListener("change", syncTrailArmControls);
  const slModeEl = $("ob-sl-mode");
  if (slModeEl) slModeEl.addEventListener("change", syncSlControls);
  const tpModeEl = $("ob-tp-mode");
  if (tpModeEl) tpModeEl.addEventListener("change", syncTpControls);
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
        applyFormFromResult(json);
        render(json);
      },
    });
  }
  poll();
})();
