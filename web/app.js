(function () {
  const $ = (id) => document.getElementById(id);

  const DEFAULT_THRESHOLDS = [100, 200, 500, 800, 1000, 1200, 1500, 2000, 3000];
  const KIND_LABEL = {
    all: "All types",
    candle: "Range live",
    spike: "Spike",
    spike_neo: "Spike Neo",
    impulse_retrace: "Impulse retrace (all)",
    impulse_retrace_50: "Impulse retrace 50%",
    impulse_retrace_75: "Impulse retrace 75%",
    candle_wick: "Range wick",
    range_wick: "Range wick",
    cooloff: "Cool-off",
    liquidity_sweep: "Liq. sweep",
  };

  let pollTimer = null;
  let lastResult = null;
  let savedPicker = {
    isViewingSaved: function () {
      return false;
    },
    clearViewing: function () {},
  };
  let lastRenderedKey = null;
  let pendingFreshResults = false;
  let alertListFilter = "all"; // all | candle | spike | …
  let signalDocs = {
    range: {},
    spike: {},
    spike_neo: {},
    impulse_retrace: {},
    range_wick: {},
    filters: {},
    suggestions: [],
  };
  let signalDefaults = null;
  let wasRunning = false;
  const RESEARCH_KEY = "strateg_research_v1";
  const ENGINE_IDS = [
    "eng_candle",
    "eng_spike",
    "eng_spike_neo",
    "eng_impulse_retrace",
    "eng_range_wick",
  ];
  let persistReady = false;
  let saveTimer = null;
  let lastSymbol = null;

  const RANGE_FIELDS = [
    "range_mult",
    "min_directed_points",
    "min_body_points",
    "hold_sec",
    "structure_break_lookback",
    "breakout_buffer_points",
    "cooldown_min",
    "lookback",
  ];
  const RANGE_WICK_FIELDS = RANGE_FIELDS.slice();
  const SPIKE_FIELDS = [
    "enabled",
    "min_points",
    "window_sec",
    "cooldown_min",
    "relative_enabled",
    "relative_lookback",
    "relative_mult",
    "point_size",
  ];
  const SPIKE_NEO_FIELDS = [
    "enabled",
    "compression_lookback",
    "compression_swing_max_points",
    "compression_size_max_ratio",
    "expansion_lookback",
    "expansion_dynamic",
    "expansion_mult_min",
    "expansion_mult_max",
    "expansion_context_lookback",
    "min_forming_points",
    "structure_lookback",
    "break_min_points",
    "hold_sec",
    "cooldown_min",
    "require_body_direction",
  ];
  const IMPULSE_FIELDS = [
    "enabled",
    "impulse_lookback",
    "min_impulse_points",
    "extreme_recent_bars",
    { key: "retrace_fractions", type: "text", label: "retrace_fractions" },
    "min_pullback_points",
    "max_retrace_depth",
    "max_retrace_age_sec",
    "hold_sec",
    "cooldown_min",
    "require_quiet",
    "quiet_lookback",
    "quiet_swing_max_points",
  ];
  const FILTER_FIELDS = [
    { key: "market_open_blackout_enabled", type: "bool", label: "Market-open blackout (Factor)" },
    { key: "market_open_time", type: "text", label: "Open time (HH:MM local)" },
    { key: "market_open_tz", type: "text", label: "Open timezone" },
    { key: "market_open_blackout_minutes", type: "num", label: "Blackout minutes" },
    { key: "market_open_weekdays", type: "text", label: "Weekdays 0=Mon…6=Sun" },
    { key: "candle_ignore_enabled", type: "bool", label: "Candle ignore window" },
    { key: "candle_ignore_local_hour_start", type: "num", label: "Ignore local hour start" },
    { key: "candle_ignore_local_hour_end", type: "num", label: "Ignore local hour end" },
    { key: "candle_lookback", type: "num", label: "Candle lookback (bars)" },
    { key: "display_tz", type: "text", label: "Display TZ (ignore window)" },
  ];

  /** Extra plain-language blurbs (on top of API docs). */
  const PARAM_HELP = {
    range_mult:
      "How strong the expansion must be vs recent bars. Live move from the 15m open must be at least this × the median one-sided range of the lookback bars. Higher = fewer, stronger alerts.",
    min_directed_points:
      "Hard floor in MT points (XAU: 1 pt = $0.01). Even if the ratio to the median is high enough, the directed move must still be at least this large.",
    min_body_points:
      "Hard floor on |live price − bar open| in points. Stops weak “ratio-only” fires when the absolute move is tiny.",
    hold_sec:
      "Conditions must stay true continuously for this many seconds before the alert fires. Filters one-tick spikes through the levels.",
    structure_break_lookback:
      "Must break the high (UP) or low (DOWN) of the last N completed 15m candles. 0 turns structure off. Higher N = harder breakout.",
    breakout_buffer_points:
      "Extra points beyond that prior high/low required to count as a structure break. 0 = touch is enough.",
    cooldown_min:
      "After a range alert on this symbol, no further range alerts for this many minutes (independent of spike cooldown).",
    lookback:
      "How many completed 15m bars feed the range median baseline (and history gate). Independent of Filters → candle_lookback. More bars = smoother baseline, slower to adapt.",
    enabled: "Master switch for the spike engine. Off = no spike alerts.",
    min_points:
      "Absolute MT-point floor inside the rolling window. Spike size must reach at least this (and the relative floor if enabled).",
    window_sec:
      "Length of the rolling price window in seconds (e.g. 60 ≈ 1 minute). Spike = excursion from the oldest price in that window.",
    relative_enabled:
      "If on, effective floor = max(min_points, relative_mult × median H−L of the last relative_lookback completed 15m candles). Adapts to quiet vs busy sessions.",
    relative_lookback:
      "Exactly how many fully closed 15m candles are used: the most recent N completed bars only (not the forming bar). XAU default N=2 → last two finished 15m candles (~up to 30 minutes of closed history). EUR default N=3.",
    relative_mult:
      "Multiplier on the median high−low of those last N completed 15m bars (N = relative_lookback). Example with default XAU (N=2, mult=2.0): take the H−L of the previous two closed 15m candles, take their median, multiply by 2; spike must reach max(min_points, that value). The current (still open) 15m bar is not included.",
    point_size:
      "Price distance of one MT point. XAU/USD = 0.01 ($0.01). Do not change unless the symbol’s tick size differs.",
    compression_lookback:
      "Spike Neo: how many completed 15m bars form the coil window.",
    compression_swing_max_points:
      "Spike Neo: max overall swing (pts) of the coil. Wider = easier coil pass.",
    compression_size_max_ratio:
      "Spike Neo: max bar size / median bar size in the coil (similarity).",
    expansion_lookback:
      "Spike Neo: recent completed bars whose max H−L sets expansion need.",
    expansion_dynamic:
      "Spike Neo: soft/hard expansion mult from recent context (on = recommended).",
    expansion_mult_min:
      "Spike Neo: softest expansion mult when the coil is quiet/uniform.",
    expansion_mult_max:
      "Spike Neo: strictest expansion mult when recent bars are choppy.",
    expansion_context_lookback:
      "Spike Neo: bars used to decide soft vs hard expansion mult.",
    min_forming_points:
      "Spike Neo: absolute floor on the forming 15m bar’s H−L in points.",
    structure_lookback:
      "Spike Neo: prior high/low from last K completed 15m bars.",
    break_min_points:
      "Spike Neo: points beyond prior high/low required to count as structure break.",
    require_body_direction:
      "Spike Neo: live price must be on the correct side of the bar open for the break side.",
    impulse_lookback:
      "Impulse retrace: how many 15m bars (completed+forming) to search for the blast swing.",
    min_impulse_points:
      "Impulse retrace: minimum size of the directional blast (H−L of the leg) in points.",
    extreme_recent_bars:
      "Impulse retrace: the swing extreme must fall in the last N bars of the window.",
    retrace_fractions:
      "Impulse retrace: pullback depths to fire (comma list, e.g. 0.5,0.75 = 50% then 75%).",
    min_pullback_points:
      "Impulse retrace: ignore tiny noise off the extreme before counting a pullback.",
    max_retrace_depth:
      "Impulse retrace: no alert if pullback is deeper than this fraction of the blast (default 0.85).",
    max_retrace_age_sec:
      "Impulse retrace: pullback must hit a level within this many seconds of the blast extreme (default 120; 0 = off).",
    require_quiet:
      "Impulse retrace: optional gate — bars before the blast must be a tight coil.",
    quiet_lookback:
      "Impulse retrace: how many pre-extreme bars for the quiet check.",
    quiet_swing_max_points:
      "Impulse retrace: max pre-blast swing if require_quiet is on.",
    market_open_blackout_enabled:
      "Factor rule: ignore alerts for a short window after the local market open (default Monday weekly reopen). Candles still build; no range/spike fires.",
    market_open_time:
      "Local clock time of the open (HH:MM), e.g. 01:05 Bucharest for gold weekly reopen.",
    market_open_tz:
      "Timezone used to interpret open time (usually Europe/Bucharest).",
    market_open_blackout_minutes:
      "How long after open to suppress alerts (15 = first quarter-hour).",
    market_open_weekdays:
      "Which weekdays apply: 0=Mon … 6=Sun, comma-separated. Default 0 = Monday only (not every day at 01:05).",
    candle_ignore_enabled:
      "Reaktor rule: do not form/use 15m bars whose open falls in a local hour window (thin Asia open).",
    candle_ignore_local_hour_start:
      "Start hour (inclusive) in Display TZ for ignored bars. Default 0 = midnight.",
    candle_ignore_local_hour_end:
      "End hour (exclusive). Default 1 = skip 00:00–01:00 local only.",
    candle_lookback:
      "Global default bar history depth (CANDLE_LOOKBACK). Does not override Range → lookback; that field wins for range alerts.",
    display_tz:
      "Timezone for the candle-ignore window only. Candle math and DB times stay UTC.",
  };

  function fillGrid(gridId, fields, values, docs, prefix) {
    const grid = $(gridId);
    grid.innerHTML = "";
    fields.forEach((f) => {
      const key = typeof f === "string" ? f : f.key;
      const type =
        typeof f === "string"
          ? typeof values[key] === "boolean"
            ? "bool"
            : "num"
          : f.type;
      const labelText = typeof f === "string" ? key : f.label || key;
      const help =
        PARAM_HELP[key] || (docs && docs[key]) || "No description available.";

      const wrap = document.createElement("div");
      wrap.className = "field";

      const head = document.createElement("div");
      head.className = "field-head";

      const title = document.createElement("label");
      title.htmlFor = prefix + key;
      title.className = "field-label";
      title.textContent = labelText;

      const info = document.createElement("button");
      info.type = "button";
      info.className = "info-icon";
      info.setAttribute("aria-label", "About " + labelText);
      info.setAttribute("data-tip", help);
      info.innerHTML = "i";
      info.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showParamTip(info, help, labelText);
      });

      head.appendChild(title);
      head.appendChild(info);
      wrap.appendChild(head);

      let input;
      if (type === "bool") {
        input = document.createElement("select");
        input.innerHTML =
          '<option value="true">true</option><option value="false">false</option>';
        input.value = values[key] ? "true" : "false";
      } else {
        input = document.createElement("input");
        input.type = type === "text" ? "text" : "number";
        if (type !== "text") {
          input.step =
            key.indexOf("mult") >= 0 || key === "point_size" ? "0.01" : "1";
        }
        input.value = values[key] != null ? values[key] : "";
      }
      input.id = prefix + key;
      input.dataset.sig = prefix.replace(/-$/, "");
      input.dataset.key = key;
      input.title = help;
      wrap.appendChild(input);

      const h = document.createElement("div");
      h.className = "field-help";
      h.textContent = help;
      wrap.appendChild(h);

      grid.appendChild(wrap);
    });
  }

  let openTipEl = null;
  function showParamTip(anchor, text, title) {
    // Toggle off if same icon
    if (openTipEl && openTipEl._anchor === anchor) {
      openTipEl.remove();
      openTipEl = null;
      return;
    }
    if (openTipEl) {
      openTipEl.remove();
      openTipEl = null;
    }
    const tip = document.createElement("div");
    tip.className = "param-tip";
    tip.innerHTML =
      "<strong>" +
      (title || "").replace(/</g, "&lt;") +
      "</strong><p>" +
      String(text).replace(/</g, "&lt;") +
      "</p>";
    tip._anchor = anchor;
    document.body.appendChild(tip);
    const r = anchor.getBoundingClientRect();
    const tw = Math.min(320, window.innerWidth - 24);
    let left = r.left + window.scrollX - tw / 2 + r.width / 2;
    left = Math.max(12, Math.min(left, window.scrollX + window.innerWidth - tw - 12));
    let top = r.bottom + window.scrollY + 8;
    tip.style.width = tw + "px";
    tip.style.left = left + "px";
    tip.style.top = top + "px";
    openTipEl = tip;
    const closer = (ev) => {
      if (tip.contains(ev.target) || anchor.contains(ev.target)) return;
      tip.remove();
      openTipEl = null;
      document.removeEventListener("click", closer);
    };
    setTimeout(() => document.addEventListener("click", closer), 0);
  }

  function readSignalFromForm() {
    const range = {};
    const spike = {};
    const spike_neo = {};
    const filters = {};
    RANGE_FIELDS.forEach((k) => {
      const el = $("range-" + k);
      if (!el) return;
      range[k] = el.type === "number" || el.tagName === "INPUT" ? Number(el.value) : el.value;
      if (k === "range_mult" || k === "point_size") range[k] = Number(el.value);
      else range[k] = Number(el.value);
    });
    SPIKE_FIELDS.forEach((k) => {
      const el = $("spike-" + k);
      if (!el) return;
      if (el.tagName === "SELECT") spike[k] = el.value === "true";
      else if (k === "point_size" || k === "relative_mult") spike[k] = Number(el.value);
      else if (k === "enabled" || k === "relative_enabled") spike[k] = el.value === "true" || el.value === true;
      else spike[k] = Number(el.value);
    });
    ["enabled", "relative_enabled"].forEach((k) => {
      const el = $("spike-" + k);
      if (el && el.tagName === "SELECT") spike[k] = el.value === "true";
    });
    SPIKE_NEO_FIELDS.forEach((k) => {
      const el = $("neo-" + k);
      if (!el) return;
      if (el.tagName === "SELECT") spike_neo[k] = el.value === "true";
      else if (
        k === "compression_size_max_ratio" ||
        k === "expansion_mult" ||
        k === "expansion_mult_min" ||
        k === "expansion_mult_max" ||
        k === "expansion_tight_relative_swing" ||
        k === "expansion_loose_relative_swing"
      )
        spike_neo[k] = Number(el.value);
      else if (
        k === "enabled" ||
        k === "expansion_dynamic" ||
        k === "require_body_direction"
      )
        spike_neo[k] = el.value === "true" || el.checked === true;
      else spike_neo[k] = Number(el.value);
    });
    ["enabled", "expansion_dynamic", "require_body_direction"].forEach((k) => {
      const el = $("neo-" + k);
      if (el && el.tagName === "SELECT") spike_neo[k] = el.value === "true";
    });
    const impulse_retrace = {};
    IMPULSE_FIELDS.forEach((f) => {
      const k = typeof f === "string" ? f : f.key;
      const el = $("ir-" + k);
      if (!el) return;
      if (el.tagName === "SELECT") impulse_retrace[k] = el.value === "true";
      else if (k === "retrace_fractions" || (f && f.type === "text"))
        impulse_retrace[k] = el.value;
      else if (k === "max_retrace_depth") impulse_retrace[k] = Number(el.value);
      else if (k === "enabled" || k === "require_quiet")
        impulse_retrace[k] = el.value === "true" || el.checked === true;
      else impulse_retrace[k] = Number(el.value);
    });
    ["enabled", "require_quiet"].forEach((k) => {
      const el = $("ir-" + k);
      if (el && el.tagName === "SELECT") impulse_retrace[k] = el.value === "true";
    });
    FILTER_FIELDS.forEach((f) => {
      const el = $("filt-" + f.key);
      if (!el) return;
      if (f.type === "bool") filters[f.key] = el.value === "true";
      else if (f.type === "text") filters[f.key] = el.value;
      else filters[f.key] = Number(el.value);
    });
    const range_wick = {};
    RANGE_WICK_FIELDS.forEach((k) => {
      const el = $("wick-" + k);
      if (!el) return;
      range_wick[k] = Number(el.value);
    });
    return { range, spike, spike_neo, impulse_retrace, range_wick, filters };
  }

  function loadSavedResearch() {
    try {
      const raw = localStorage.getItem(RESEARCH_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function normalizeImpulse(ir) {
    const out = Object.assign({}, ir || {});
    if (Array.isArray(out.retrace_fractions)) {
      out.retrace_fractions = out.retrace_fractions.join(",");
    }
    return out;
  }

  function overlaySignal(base, overlay) {
    return Object.assign({}, base || {}, overlay || {});
  }

  function saveResearchForSymbol(sym) {
    if (!persistReady) return;
    try {
      const prev = loadSavedResearch() || {};
      const signalBySymbol = prev.signalBySymbol || {};
      const key = sym || ($("symbol") && $("symbol").value) || "XAUUSD";
      signalBySymbol[key] = readSignalFromForm();
      const engines = {};
      ENGINE_IDS.forEach((id) => {
        engines[id] = !!( $(id) && $(id).checked );
      });
      const cfg = {
        symbol: ($("symbol") && $("symbol").value) || key,
        date_from: $("date_from") && $("date_from").value,
        date_to: $("date_to") && $("date_to").value,
        hours: $("hours") && $("hours").value,
        threshold: $("threshold") && $("threshold").value,
        adverse_pct: $("adverse_pct") && $("adverse_pct").value,
        sl_manage: $("sl_manage") && $("sl_manage").value,
        sl_manage_lock_pts: $("sl_manage_lock_pts") && $("sl_manage_lock_pts").value,
        engines: engines,
        signalBySymbol: signalBySymbol,
      };
      localStorage.setItem(RESEARCH_KEY, JSON.stringify(cfg));
    } catch (e) {
      console.warn("research save failed", e);
    }
  }

  function saveResearch() {
    saveResearchForSymbol(($("symbol") && $("symbol").value) || "XAUUSD");
  }

  function scheduleSave() {
    if (!persistReady) return;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveResearch, 200);
  }

  function applySavedMain(saved) {
    if (!saved) return;
    [
      "symbol",
      "date_from",
      "date_to",
      "hours",
      "threshold",
      "adverse_pct",
      "sl_manage",
      "sl_manage_lock_pts",
    ].forEach((id) => {
      if (saved[id] != null && $(id)) $(id).value = saved[id];
    });
  }

  function applySavedEngines(engines) {
    if (!engines) return;
    ENGINE_IDS.forEach((id) => {
      const el = $(id);
      if (!el) return;
      if (Object.prototype.hasOwnProperty.call(engines, id)) {
        el.checked = !!engines[id];
      }
    });
    syncEngineSections();
  }

  async function loadSignalDefaults(opts) {
    const applySaved = !opts || opts.applySaved !== false;
    const skipEngines = !!(opts && opts.skipEngines);
    const sym = $("symbol").value || "XAUUSD";
    const r = await fetch("/api/signal-defaults?symbol=" + encodeURIComponent(sym));
    const data = await r.json();
    signalDefaults = data;
    signalDocs = data.docs || {};
    const saved = applySaved ? loadSavedResearch() : null;
    const overlay =
      saved && saved.signalBySymbol && saved.signalBySymbol[sym]
        ? saved.signalBySymbol[sym]
        : null;
    fillGrid(
      "grid-range",
      RANGE_FIELDS,
      overlaySignal(data.range || {}, overlay && overlay.range),
      signalDocs.range,
      "range-"
    );
    fillGrid(
      "grid-spike",
      SPIKE_FIELDS,
      overlaySignal(data.spike || {}, overlay && overlay.spike),
      signalDocs.spike,
      "spike-"
    );
    fillGrid(
      "grid-spike-neo",
      SPIKE_NEO_FIELDS,
      overlaySignal(data.spike_neo || {}, overlay && overlay.spike_neo),
      signalDocs.spike_neo || {},
      "neo-"
    );
    const ir = normalizeImpulse(
      overlaySignal(data.impulse_retrace || {}, overlay && overlay.impulse_retrace)
    );
    fillGrid(
      "grid-impulse",
      IMPULSE_FIELDS,
      ir,
      signalDocs.impulse_retrace || {},
      "ir-"
    );
    fillGrid(
      "grid-range-wick",
      RANGE_WICK_FIELDS,
      overlaySignal(data.range_wick || {}, overlay && overlay.range_wick),
      signalDocs.range_wick || {},
      "wick-"
    );
    fillGrid(
      "grid-filters",
      FILTER_FIELDS,
      overlaySignal(data.filters || {}, overlay && overlay.filters),
      {
      market_open_blackout_enabled:
        "Factor: ignore alerts in first N min after local open (candles still build)",
      market_open_time: "Local open clock (default 01:05 = XAU weekly reopen)",
      market_open_tz: "Timezone for open time (default Europe/Bucharest)",
      market_open_blackout_minutes: "Duration of blackout after open (default 15)",
      market_open_weekdays:
        "Comma weekdays 0=Mon…6=Sun (default 0 = Monday only, like Factor)",
      candle_ignore_enabled: "Skip 15m bars opening in local hour window (Reaktor)",
      candle_ignore_local_hour_start: "Local hour start (inclusive), DISPLAY_TZ",
      candle_ignore_local_hour_end: "Local hour end (exclusive)",
      candle_lookback: "Completed 15m bars for median baseline",
      display_tz: "Timezone for candle ignore window only",
    }, "filt-");
    const tips = (signalDocs.suggestions || []).join(" · ");
    $("signal-hints").textContent =
      "Range/spike defaults = Reaktor XAU. Market-open blackout = Factor " +
      "(Mon 01:05 Bucharest, 15 min). " +
      (tips || "");
    if (applySaved && !skipEngines && saved && saved.engines) {
      applySavedEngines(saved.engines);
    }
  }

  function selectedEngines() {
    const out = [];
    if ($("eng_candle") && $("eng_candle").checked) out.push("candle");
    if ($("eng_spike") && $("eng_spike").checked) out.push("spike");
    if ($("eng_spike_neo") && $("eng_spike_neo").checked) out.push("spike_neo");
    if ($("eng_impulse_retrace") && $("eng_impulse_retrace").checked)
      out.push("impulse_retrace");
    if ($("eng_range_wick") && $("eng_range_wick").checked)
      out.push("candle_wick");
    return out;
  }

  function syncEngineSections() {
    let any = false;
    document.querySelectorAll(".sig-block").forEach((el) => {
      const cb = $(el.dataset.eng);
      const on = !!(cb && cb.checked);
      el.classList.toggle("hidden", !on);
      if (on) any = true;
    });
    const empty = $("sig-empty");
    const shared = $("sig-shared");
    if (empty) empty.classList.toggle("hidden", any);
    if (shared) shared.classList.toggle("hidden", !any);
  }
  function multiThresholds(selected) {
    const t = Number(selected);
    const set = new Set(DEFAULT_THRESHOLDS);
    if (isFinite(t)) set.add(t);
    return Array.from(set).sort((a, b) => a - b);
  }

  function fmtPct(v) {
    if (v == null || v === undefined) return "—";
    return Number(v).toFixed(1) + "%";
  }

  function fmtPts(v) {
    if (v == null || v === "" || !isFinite(Number(v))) return "—";
    return Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 });
  }

  function hardSlRealized(a, T, adverseMult, slManage) {
    if (a.pending || a.realized_pts == null || a.realized_pts === "") return null;
    var v = Number(a.realized_pts);
    if (!isFinite(v)) return null;
    var unmanaged = !slManage || slManage === "off";
    // Dirty hit: price reached T after tagging the opposite stop. Count as −SL.
    if (unmanaged && a.hit && !a.clean) {
      var sl = Number(T) * Number(adverseMult || 1);
      if (isFinite(sl) && sl > 0) return -sl;
    }
    return v;
  }

  function sumRealizedPts(s, detailRows, kind, T, adverseMult, slManage) {
    var rows = detailRows || [];
    if (kind && kind !== "all") {
      rows = rows.filter(function (a) {
        if (a.kind === kind) return true;
        if (kind.indexOf("impulse_retrace_") === 0) {
          var pct = Number(kind.split("_").pop());
          var frac = a.retrace_fraction;
          return frac != null && Math.round(Number(frac) * 100) === pct;
        }
        return false;
      });
    }
    var tot = 0;
    var any = false;
    var n = 0;
    rows.forEach(function (a) {
      var v = hardSlRealized(a, T, adverseMult, slManage);
      if (v == null) return;
      tot += v;
      n += 1;
      any = true;
    });
    if (any) return { sum: Math.round(tot * 10) / 10, n: n };
    if (s && s.realized_mode === "hard_sl" && s.sum_realized_pts != null) {
      return { sum: Number(s.sum_realized_pts), n: s.n };
    }
    if (s && s.sum_realized_pts != null && isFinite(Number(s.sum_realized_pts))) {
      return {
        sum: hardSlCorrectSum(s, T, adverseMult),
        n: s.n,
      };
    }
    if (s && s.avg_realized_pts != null && s.n) {
      return {
        sum: Math.round(Number(s.avg_realized_pts) * Number(s.n) * 10) / 10,
        n: s.n,
      };
    }
    return null;
  }

  function hardSlCorrectSum(s, T, adverseMult) {
    var sum = Number(s.sum_realized_pts);
    if (!isFinite(sum)) return sum;
    if (s.realized_mode === "hard_sl") return sum;
    var n = Number(s.n) || 0;
    var hits =
      s.hits != null
        ? Number(s.hits)
        : Math.round((n * Number(s.hit_rate_pct || 0)) / 100);
    var cleans =
      s.cleans != null
        ? Number(s.cleans)
        : Math.round((n * Number(s.clean_rate_pct || 0)) / 100);
    var dirty = Math.max(0, hits - cleans);
    if (!dirty) return Math.round(sum * 10) / 10;
    var t = Number(T);
    var sl = t * Number(adverseMult || 1);
    if (!isFinite(t) || !isFinite(sl)) return Math.round(sum * 10) / 10;
    return Math.round((sum - dirty * (t + sl)) * 10) / 10;
  }

  function fmtSumPts(agg) {
    if (agg == null || agg.sum == null || !isFinite(Number(agg.sum))) return "—";
    return fmtPts(agg.sum);
  }

  function fmtAvgPts(agg, fallback) {
    if (agg && agg.sum != null && agg.n) {
      return (Math.round((Number(agg.sum) / Number(agg.n)) * 10) / 10).toFixed(1);
    }
    if (fallback != null && isFinite(Number(fallback))) return Number(fallback).toFixed(1);
    return "—";
  }

  function slManageLabel(obj) {
    const mode = (obj && obj.sl_manage) || "off";
    if (mode === "be") return " · SL: ½T → BE";
    if (mode === "lock") {
      const n = obj.sl_manage_lock_pts != null ? obj.sl_manage_lock_pts : 100;
      return " · SL: ½T → lock +" + n;
    }
    return "";
  }

  /** Time from alert to first touch of T (seconds → minutes). */
  function fmtDuration(sec) {
    if (sec == null || sec === "" || !isFinite(Number(sec))) return "—";
    var m = Number(sec) / 60;
    if (m < 10) return m.toFixed(1) + " min";
    return Math.round(m) + " min";
  }

  function kindLabel(k) {
    return KIND_LABEL[k] || k;
  }

  function setBadge(phase) {
    const el = $("status-badge");
    el.className = "badge";
    if (phase === "done") {
      el.textContent = "done";
      el.classList.add("done");
    } else if (phase === "error") {
      el.textContent = "error";
      el.classList.add("err");
    } else if (phase && phase !== "idle") {
      el.textContent = phase;
      el.classList.add("run");
    } else {
      el.textContent = "idle";
    }
  }

  function renderProgress(state) {
    const p = state.progress || {};
    const pct = Number(p.pct) || 0;
    $("progress-bar").style.width = Math.min(100, Math.max(0, pct)) + "%";
    $("progress-msg").textContent = p.message || (state.running ? "Working…" : "Idle");
    setBadge(p.phase || (state.running ? "run" : "idle"));

    const bits = [];
    if (p.hours_total)
      bits.push(`hours ${p.hours_done || 0}/${p.hours_total}`);
    if (p.ticks) bits.push(`${Number(p.ticks).toLocaleString()} ticks`);
    if (p.alerts != null) bits.push(`${p.alerts} alerts`);
    if (p.candles) bits.push(`${p.candles} candles`);
    if (p.replay_ticks_done)
      bits.push(`replay ${Number(p.replay_ticks_done).toLocaleString()}`);
    $("progress-stats").textContent = bits.join(" · ");

    $("btn-run").disabled = !!state.running;
  }

  /** Build { all: overallBlock, candle: …, spike: … } */
  function blocksByKind(result) {
    const out = { all: result.overall || {} };
    const byEng = result.by_engine || {};
    Object.keys(byEng).forEach((k) => {
      out[k] = byEng[k] || {};
    });
    // Ensure engines with zero alerts still appear if they were requested
    (result.engines || []).forEach((k) => {
      if (!out[k]) out[k] = {};
    });
    return out;
  }

  function rowAtT(block, selectedT) {
    if (!block) return null;
    const tKey = String(Math.round(selectedT));
    return block[tKey] || block[String(selectedT)] || null;
  }

  function renderHero(result, selectedT) {
    const grid = $("hero-grid");
    grid.innerHTML = "";
    const blocks = blocksByKind(result);
    // Order: all, then known engines, then anything else
    const order = ["all"]
      .concat(result.engines || [])
      .concat(Object.keys(blocks).filter((k) => k !== "all" && !(result.engines || []).includes(k)));
    const seen = new Set();

    order.forEach((kind) => {
      if (seen.has(kind)) return;
      seen.add(kind);
      const block = blocks[kind];
      if (!block || !Object.keys(block).length) {
        // zero alerts for this engine
        if (kind !== "all") {
          const card = document.createElement("div");
          card.className = "hero-card muted-card";
          card.innerHTML = `
            <div class="hero-label">${kindLabel(kind)}</div>
            <div class="hero-value sm">—</div>
            <div class="hero-sub">n=0 alerts</div>`;
          grid.appendChild(card);
        }
        return;
      }
      const row = rowAtT(block, selectedT);
      if (!row) return;
      const clean = row.clean_rate_pct;
      const card = document.createElement("div");
      card.className = "hero-card" + (kind === "all" ? " hero-all" : "");
      const cls =
        clean != null && clean >= 55
          ? "good"
          : clean != null
            ? "bad"
            : "";
      const sumPts = sumRealizedPts(
        row,
        detailForT(result, String(Math.round(selectedT))),
        kind,
        selectedT,
        result.adverse_mult,
        result.sl_manage
      );
      card.innerHTML = `
        <div class="hero-label">${kindLabel(kind)} · T=${Math.round(selectedT)}</div>
        <div class="hero-value sm ${cls}">${fmtPct(clean)} <span class="hero-unit">clean</span></div>
        <div class="hero-sub">
          sum ${fmtSumPts(sumPts)} pts · hit ${fmtPct(row.hit_rate_pct)} · n=${row.n}
          · clean ${row.cleans != null ? row.cleans : "—"} / hit ${row.hits != null ? row.hits : "—"}
        </div>`;
      grid.appendChild(card);
    });
  }

  /**
   * Avg minutes alert → first T among clean hits.
   * Computed from detail rows so it works even when summary JSON
   * was produced before avg_clean_hit_min existed server-side.
   */
  function avgCleanDurMin(detailRows, kindFilter) {
    var rows = detailRows || [];
    if (kindFilter && kindFilter !== "all") {
      rows = rows.filter(function (a) {
        return a.kind === kindFilter;
      });
    }
    var secs = [];
    rows.forEach(function (a) {
      if (!a.clean) return;
      if (a.first_hit_sec == null || a.first_hit_sec === "") return;
      var v = Number(a.first_hit_sec);
      if (isFinite(v)) secs.push(v);
    });
    if (!secs.length) return null;
    var avg = secs.reduce(function (a, b) {
      return a + b;
    }, 0) / secs.length;
    return Math.round((avg / 60) * 10) / 10;
  }

  function detailForT(result, tKey) {
    var d = (result && result.detail_by_threshold) || {};
    return d[tKey] || d[String(tKey)] || [];
  }

  function renderByTypeTable(result, selectedT) {
    const tb = $("table-by-type").querySelector("tbody");
    tb.innerHTML = "";
    const blocks = blocksByKind(result);
    const kinds = ["all"].concat(
      Object.keys(blocks)
        .filter((k) => k !== "all")
        .sort()
    );

    kinds.forEach((kind) => {
      const block = blocks[kind] || {};
      const keys = Object.keys(block).sort((a, b) => Number(a) - Number(b));
      if (!keys.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${kindLabel(kind)}</td>
          <td colspan="12" class="muted">no alerts</td>`;
        tb.appendChild(tr);
        return;
      }
      keys.forEach((k) => {
        const s = block[k];
        const tr = document.createElement("tr");
        if (Number(k) === Number(selectedT)) tr.className = "highlight";
        // Prefer server field; fall back to detail rows (always have first_hit_sec)
        var dur = s.avg_clean_hit_min;
        if (dur == null) {
          dur = avgCleanDurMin(detailForT(result, k), kind);
        }
        var ptsAgg = sumRealizedPts(
          s,
          detailForT(result, k),
          kind,
          Number(k),
          result.adverse_mult,
          result.sl_manage
        );
        tr.innerHTML = `
          <td>${kindLabel(kind)}</td>
          <td>${k}</td>
          <td>${s.n}</td>
          <td>${fmtPct(s.hit_rate_pct)}</td>
          <td>${fmtPct(s.clean_rate_pct)}</td>
          <td title="Average minutes from alert to first T among clean hits only">${
            dur != null ? dur : "—"
          }</td>
          <td>${s.avg_max_fav != null ? s.avg_max_fav : "—"}</td>
          <td>${s.avg_max_adv != null ? s.avg_max_adv : "—"}</td>
          <td>${fmtPct(s.manage_armed_pct)}</td>
          <td>${fmtPct(s.stopped_manage_pct)}</td>
          <td>${fmtAvgPts(ptsAgg, s.avg_realized_pts)}</td>
          <td>${fmtSumPts(ptsAgg)}</td>`;
        tb.appendChild(tr);
      });
    });
  }

  function fmtKv(obj, keys) {
    if (!obj) return "";
    return keys
      .filter((k) => obj[k] != null && obj[k] !== "")
      .map((k) => k + "=" + obj[k])
      .join(" · ");
  }

  function renderConfigSummary(result) {
    const el = $("results-config");
    if (!el) return;
    const sc = result && result.signal_config;
    if (!sc) {
      el.classList.add("hidden");
      el.innerHTML = "";
      return;
    }
    el.classList.remove("hidden");
    const r = sc.range || {};
    const s = sc.spike || {};
    const f = sc.filters || {};
    const defs = signalDefaults || {};
    const dr = (defs.range || {});
    const ds = (defs.spike || {});
    const df = (defs.filters || {});

    function valsDiffer(a, b) {
      if (a == null || b == null) return a != b;
      var na = Number(a),
        nb = Number(b);
      if (isFinite(na) && isFinite(nb)) return Math.abs(na - nb) > 1e-9;
      return String(a) !== String(b);
    }
    function diffs(curr, base, keys) {
      const out = [];
      keys.forEach((k) => {
        if (curr[k] == null && base[k] == null) return;
        if (valsDiffer(curr[k], base[k])) {
          out.push(
            "<span class=\"cfg-changed\">" +
              k +
              "=" +
              curr[k] +
              " <span class=\"cfg-was\">(default " +
              base[k] +
              ")</span></span>"
          );
        }
      });
      return out;
    }

    const rangeKeys = [
      "range_mult",
      "min_directed_points",
      "min_body_points",
      "hold_sec",
      "structure_break_lookback",
      "breakout_buffer_points",
      "cooldown_min",
      "lookback",
    ];
    const spikeKeys = [
      "enabled",
      "min_points",
      "window_sec",
      "cooldown_min",
      "relative_enabled",
      "relative_lookback",
      "relative_mult",
    ];
    const filterKeys = [
      "market_open_blackout_enabled",
      "market_open_time",
      "market_open_tz",
      "market_open_blackout_minutes",
      "market_open_weekdays",
      "candle_ignore_enabled",
      "candle_ignore_local_hour_start",
      "candle_ignore_local_hour_end",
      "candle_lookback",
    ];

    const changed = []
      .concat(diffs(r, dr, rangeKeys).map((x) => "range: " + x))
      .concat(diffs(s, ds, spikeKeys).map((x) => "spike: " + x))
      .concat(diffs(f, df, filterKeys).map((x) => "filter: " + x));

    const rangeLine = fmtKv(r, rangeKeys);
    const spikeLine = fmtKv(s, spikeKeys);
    const filterLine =
      "blackout=" +
      f.market_open_blackout_enabled +
      " @" +
      (f.market_open_time || "—") +
      " " +
      (f.market_open_tz || "") +
      " " +
      (f.market_open_blackout_minutes != null
        ? f.market_open_blackout_minutes + "m"
        : "") +
      " wd=" +
      (f.market_open_weekdays || "—") +
      " · ignore=" +
      f.candle_ignore_enabled +
      " " +
      f.candle_ignore_local_hour_start +
      "–" +
      f.candle_ignore_local_hour_end +
      " " +
      (f.display_tz || "");

    el.innerHTML =
      "<div class=\"cfg-block\"><span class=\"cfg-label\">Range live</span> " +
      rangeLine +
      "</div>" +
      "<div class=\"cfg-block\"><span class=\"cfg-label\">Spike</span> " +
      spikeLine +
      "</div>" +
      "<div class=\"cfg-block\"><span class=\"cfg-label\">Filters</span> " +
      filterLine +
      "</div>" +
      (changed.length
        ? "<div class=\"cfg-block cfg-alts\"><span class=\"cfg-label\">Changed vs defaults</span> " +
          changed.join(" · ") +
          "</div>"
        : "<div class=\"cfg-block cfg-alts muted\"><span class=\"cfg-label\">Changed vs defaults</span> none (all defaults)</div>");
  }

  function renderAlertTabs(result, detail) {
    const tabs = $("alert-type-tabs");
    tabs.innerHTML = "";
    const kinds = ["all"];
    const counts = { all: detail.length };
    detail.forEach((a) => {
      const k = a.kind || "?";
      counts[k] = (counts[k] || 0) + 1;
      if (!kinds.includes(k)) kinds.push(k);
    });
    // Prefer stable order
    const ordered = ["all", "candle", "spike"].filter((k) => kinds.includes(k));
    kinds.forEach((k) => {
      if (!ordered.includes(k)) ordered.push(k);
    });

    if (!ordered.includes(alertListFilter)) alertListFilter = "all";

    ordered.forEach((k) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "type-tab" + (alertListFilter === k ? " active" : "");
      btn.textContent = `${kindLabel(k)} (${counts[k] || 0})`;
      btn.addEventListener("click", () => {
        alertListFilter = k;
        renderResults(lastResult, Number($("threshold").value));
      });
      tabs.appendChild(btn);
    });
  }

  function renderAlertList(detail) {
    const ta = $("table-alerts").querySelector("tbody");
    ta.innerHTML = "";
    const filtered =
      alertListFilter === "all"
        ? detail
        : detail.filter((a) => a.kind === alertListFilter);

    if (!filtered.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="11" class="muted">No alerts for this type</td>`;
      ta.appendChild(tr);
      return;
    }

    filtered.forEach((a) => {
      const tr = document.createElement("tr");
      const pending = !!a.pending || a.hit == null;
      const hitCell = pending ? "…" : a.hit ? "yes" : "no";
      const cleanCell = pending ? "…" : a.clean ? "yes" : "no";
      const dur = !pending && a.hit ? fmtDuration(a.first_hit_sec) : "—";
      const pts = hardSlRealized(
        a,
        Number($("threshold") && $("threshold").value),
        lastResult && lastResult.adverse_mult,
        lastResult && lastResult.sl_manage
      );
      tr.innerHTML = `
        <td>${(a.alert_ts || "").replace("T", " ").slice(0, 19)}</td>
        <td>${kindLabel(a.kind)}</td>
        <td>${a.side}</td>
        <td>${a.entry != null ? Number(a.entry).toFixed(2) : "—"}</td>
        <td class="${pending ? "muted" : a.hit ? "yes" : "no"}">${hitCell}</td>
        <td class="${pending ? "muted" : a.clean ? "yes" : "no"}">${cleanCell}</td>
        <td>${pending ? "…" : a.exit || "—"}</td>
        <td title="${a.first_hit_sec != null ? (Number(a.first_hit_sec) / 60).toFixed(2) + " min to T" : pending ? "waiting for look-ahead" : "did not reach T"}">${dur}</td>
        <td>${pending || a.max_fav == null ? "—" : a.max_fav}</td>
        <td>${pending || a.max_adv_until_hit == null ? "—" : a.max_adv_until_hit}</td>
        <td>${pts == null ? "—" : pts}</td>`;
      ta.appendChild(tr);
    });
  }

  function resultKey(result) {
    if (!result) return "";
    return [
      result.partial ? "1" : "0",
      result.finished_at || "",
      result.replay_ticks_done || "",
      result.alerts,
      result.scored_alerts,
      (result.engines || []).join(","),
      (result.thresholds || []).join(","),
    ].join("|");
  }

  function clearResults(msg) {
    lastResult = null;
    lastRenderedKey = null;
    $("results-meta").textContent = msg || "No run yet.";
    $("hero-grid").innerHTML = "";
    renderConfigSummary(null);
    const byType = $("table-by-type");
    if (byType && byType.querySelector("tbody")) byType.querySelector("tbody").innerHTML = "";
    const alerts = $("table-alerts");
    if (alerts && alerts.querySelector("tbody")) alerts.querySelector("tbody").innerHTML = "";
    const tabs = $("alert-type-tabs");
    if (tabs) tabs.innerHTML = "";
    const pdfBtn = $("btn-pdf");
    if (pdfBtn) pdfBtn.disabled = true;
    const card = $("results-card");
    if (card) card.classList.remove("is-fresh");
  }

  function flashResultsCard() {
    const card = $("results-card");
    if (!card) return;
    card.classList.remove("is-fresh");
    void card.offsetWidth;
    card.classList.add("is-fresh");
  }

  function renderResults(result, selectedT, opts) {
    lastResult = result;
    const pdfBtn = $("btn-pdf");
    if (!result) {
      clearResults("No run yet.");
      return;
    }
    lastRenderedKey = resultKey(result);
    if (pdfBtn) pdfBtn.disabled = false;

    const tKey = String(Math.round(selectedT));
    const finished = result.finished_at
      ? String(result.finished_at).replace("T", " ").slice(0, 19) + " UTC"
      : "";

    const scoredN = result.scored_alerts != null ? result.scored_alerts : result.alerts;
    $("results-meta").textContent =
      `${result.duka_symbol || result.symbol} · ` +
      `${(result.from || "").slice(0, 10)} → ${(result.to || "").slice(0, 10)} · ` +
      `${Number(result.ticks || 0).toLocaleString()} ticks` +
      (result.partial && result.replay_ticks_done
        ? ` (${Number(result.replay_ticks_done).toLocaleString()} replayed)`
        : "") +
      ` · ${result.alerts || 0} alerts` +
      (result.partial ? ` · ${scoredN} scored` : "") +
      (result.alerts_by_kind
        ? " (" +
          Object.entries(result.alerts_by_kind)
            .map(([k, v]) => kindLabel(k) + ":" + v)
            .join(", ") +
          ")"
        : "") +
      ` · look-ahead ${result.hours}h · opp ≤ ${Math.round((result.adverse_mult || 1) * 100)}% T` +
      slManageLabel(result) +
      ` · selected T=${Math.round(selectedT)}` +
      (result.partial ? " · live" : finished ? " · " + finished : "") +
      ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");

    renderConfigSummary(result);
    renderHero(result, selectedT);
    renderByTypeTable(result, selectedT);

    const detail =
      (result.detail_by_threshold &&
        (result.detail_by_threshold[tKey] ||
          result.detail_by_threshold[String(selectedT)])) ||
      [];
    renderAlertTabs(result, detail);
    renderAlertList(detail);
    if (opts && opts.fresh) flashResultsCard();
  }

  /** Short pleasant chime when a research job finishes (Web Audio, no asset file). */
  function playDoneSound() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = playDoneSound._ctx || new Ctx();
      playDoneSound._ctx = ctx;
      if (ctx.state === "suspended") ctx.resume();
      var now = ctx.currentTime;
      // two soft tones
      [523.25, 659.25].forEach(function (freq, i) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.setValueAtTime(0.0001, now);
        g.gain.exponentialRampToValueAtTime(0.12, now + 0.02 + i * 0.12);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.35 + i * 0.15);
        o.connect(g);
        g.connect(ctx.destination);
        o.start(now + i * 0.12);
        o.stop(now + 0.45 + i * 0.15);
      });
    } catch (e) {
      /* autoplay policies / no audio — ignore */
    }
  }

  async function poll() {
    try {
      const r = await fetch("/api/job");
      const state = await r.json();
      const running = !!state.running;
      const phase = (state.progress && state.progress.phase) || "";

      // Fire once when a job transitions running → finished successfully
      if (wasRunning && !running && phase === "done") {
        playDoneSound();
      }
      wasRunning = running;

      renderProgress(state);
      const holdSaved = savedPicker.isViewingSaved();
      if (!holdSaved) {
        if (state.result) {
          const key = resultKey(state.result);
          if (key !== lastRenderedKey) {
            const isFinal = !state.result.partial;
            const fresh = pendingFreshResults && isFinal;
            if (isFinal) pendingFreshResults = false;
            renderResults(state.result, Number($("threshold").value), { fresh: fresh });
          }
        } else if (running && (lastResult || lastRenderedKey)) {
          clearResults("Replay in progress — results update as alerts score.");
        }
      }
      if (!running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function runJob() {
    const engines = selectedEngines();
    if (!engines.length) {
      alert("Tick at least one engine.");
      return;
    }
    const t = Number($("threshold").value);
    if (!isFinite(t) || t <= 0) {
      alert("Target T must be a positive number of points.");
      $("threshold").focus();
      return;
    }
    const adversePct = Number($("adverse_pct").value);
    const body = {
      symbol: $("symbol").value,
      date_from: $("date_from").value,
      date_to: $("date_to").value,
      engines,
      hours: Number($("hours").value),
      thresholds: multiThresholds(t),
      adverse_mult: isFinite(adversePct) ? adversePct / 100 : 1,
      signal_price: "mid",
      sl_manage: ($("sl_manage") && $("sl_manage").value) || "off",
      sl_manage_at_frac: 0.5,
      sl_manage_lock_pts: Number(($("sl_manage_lock_pts") && $("sl_manage_lock_pts").value) || 100),
      force_download: $("force_download").checked,
      signal: readSignalFromForm(),
    };

    savedPicker.clearViewing();
    $("btn-run").disabled = true;
    $("progress-msg").textContent = "Starting job…";
    try {
      const r = await fetch("/api/job/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(err.detail || "Could not start job (another run may still be active)");
        $("btn-run").disabled = false;
        return;
      }
      wasRunning = true; // arm done-sound for this run
      pendingFreshResults = true;
      clearResults("Replay in progress — results update as alerts score.");
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(poll, 800);
      poll();
    } catch (e) {
      alert(String(e));
      $("btn-run").disabled = false;
    }
  }

  $("btn-run").addEventListener("click", runJob);
  ENGINE_IDS.forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("change", () => {
      syncEngineSections();
      scheduleSave();
    });
  });
  ["change", "input"].forEach((ev) => {
    $("threshold").addEventListener(ev, () => {
      if (lastResult) renderResults(lastResult, Number($("threshold").value));
      scheduleSave();
    });
  });
  [
    "date_from",
    "date_to",
    "hours",
    "adverse_pct",
    "sl_manage",
    "sl_manage_lock_pts",
  ].forEach((id) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("change", scheduleSave);
    el.addEventListener("input", scheduleSave);
  });
  const signalPanel = $("signal-panel");
  if (signalPanel) {
    signalPanel.addEventListener("input", scheduleSave);
    signalPanel.addEventListener("change", scheduleSave);
  }
  $("symbol").addEventListener("change", () => {
    const prev = lastSymbol;
    lastSymbol = $("symbol").value || "XAUUSD";
    if (prev && prev !== lastSymbol) saveResearchForSymbol(prev);
    loadSignalDefaults({ applySaved: true, skipEngines: true }).catch((e) =>
      console.error(e)
    );
  });
  $("btn-reset-signals").addEventListener("click", () => {
    loadSignalDefaults({ applySaved: false, skipEngines: true })
      .then(() => saveResearch())
      .catch((e) => console.error(e));
  });
  $("btn-pdf").addEventListener("click", () => {
    if (!lastResult) return;
    document.body.classList.add("print-results");
    const prev = document.title;
    const r = lastResult;
    document.title =
      "Strateg " +
      (r.duka_symbol || r.symbol || "") +
      " " +
      (r.from || "").slice(0, 10) +
      "_" +
      (r.to || "").slice(0, 10);
    window.print();
    document.title = prev;
    document.body.classList.remove("print-results");
  });

  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "research",
      selectId: "rs-saved",
      buttonId: "rs-load",
      onLoaded: function (json) {
        renderResults(json, Number($("threshold").value), { fresh: true });
      },
    });
  }

  (function initResearchForm() {
    const saved = loadSavedResearch();
    applySavedMain(saved);
    lastSymbol = ($("symbol") && $("symbol").value) || "XAUUSD";
    loadSignalDefaults({ applySaved: true })
      .then(() => {
        if (saved && saved.engines) applySavedEngines(saved.engines);
        else syncEngineSections();
        persistReady = true;
      })
      .catch((e) => {
        console.error(e);
        persistReady = true;
      });
  })();
  poll();
})();
