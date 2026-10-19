(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_crt_v1";
  const POINT_FIELDS = ["crt-min-leg", "crt-min-range", "crt-min-sl", "crt-sl-buf", "crt-sl-fixed", "crt-cost", "crt-commission"];
  let pollTimer = null;
  let saveTimer = null;
  let lastSymbol = "XAUUSD";
  let symbolSwitching = false;

  const FORM_IDS = [
    "crt-symbol", "crt-from", "crt-to", "crt-tz",
    "crt-htf", "crt-ltf", "crt-struct", "crt-pd", "crt-eq",
    "crt-min-leg", "crt-min-range", "crt-side",
    "crt-entry", "crt-fvg-select", "crt-fvg-entry", "crt-max-fvg", "crt-fvg-wait",
    "crt-sl-mode", "crt-sl-buf", "crt-min-sl", "crt-sl-fixed",
    "crt-partial", "crt-partial-rr", "crt-runner", "crt-runner-rr", "crt-hold", "crt-max-concurrent",
    "crt-mode", "crt-ny-tz", "crt-ny-h", "crt-ny-m",
    "crt-session", "crt-sess-sh", "crt-sess-sm", "crt-sess-eh", "crt-sess-em",
    "crt-news", "crt-cost", "crt-commission", "crt-force",
  ];

  function formSymbol(symbol) {
    return window.strategSymbols ? window.strategSymbols.formSymbol(symbol) : symbol || "XAUUSD";
  }

  function pointScale(symbol) {
    return window.strategSymbols ? window.strategSymbols.pointScale(symbol) : 1;
  }

  function scalePoint(raw, ratio) {
    const n = parseFloat(raw);
    if (!Number.isFinite(n) || n === 0) return raw;
    const scaled = n * ratio;
    if (Math.abs(scaled) >= 10) return String(Math.round(scaled));
    return String(Math.round(scaled * 10) / 10);
  }

  function saveForm() {
    if (symbolSwitching) return;
    try {
      const cfg = {};
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el) return;
        cfg[id] = el.type === "checkbox" ? !!el.checked : el.value;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    } catch (e) {}
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
    } catch (e) {}
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="crt"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "crt");
      btn.textContent = "CRT";
      nav.appendChild(btn);
    }
    if ($("tab-crt")) return;
    const symbols = window.strategSymbols && window.strategSymbols.optionsHtml
      ? window.strategSymbols.optionsHtml()
      : '<option value="XAUUSD" selected>XAUUSD</option>';
    const panel = document.createElement("div");
    panel.id = "tab-crt";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Candle range, with the trend</h2>
      <ol id="crt-rules">
        <li>Find a dealing range on the higher timeframe. Up when the low prints before the high. Down when the high prints first.</li>
        <li>In an uptrend, mark only bearish candles inside that range, and only when they close in discount. Downtrend uses bullish candles in premium.</li>
        <li>The next candle must sweep the range and close back inside. A close through the range is invalid. Wait for that candle to finish.</li>
        <li>Enter on the lower timeframe at the fair value gap that forms after the sweep. Stop beyond the gap. Close half at 1:1 and let the rest run to the dealing-range extreme.</li>
      </ol>
      <p class="hint">This is the trend model from the CRT video. It does not fade the hour before New York. Fills are lower-timeframe OHLC built from 5-minute candles. A bar that trades the stop and a target takes the stop. Hours use the timezone field. <a href="/crt/results" target="_blank" rel="noopener">Catalog</a> · <a href="/api/crt/rules" target="_blank" rel="noopener">Rules JSON</a></p>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Mode
          <select id="crt-mode">
            <option value="hunt" selected>Hunt every setup</option>
            <option value="ny_open">New York open, one a day</option>
          </select>
        </label>
        <label>Max concurrent
          <input type="number" id="crt-max-concurrent" value="0" min="0" max="500" step="1"
            title="0 hunts with no cap. A positive number is how many trades may be open at the same time." />
        </label>
        <label id="crt-ny-tz-wrap">New York timezone
          <input id="crt-ny-tz" value="America/New_York" />
        </label>
        <label id="crt-ny-open-wrap">New York open
          <span class="hm">
            <input type="number" id="crt-ny-h" value="8" min="0" max="23" title="Hour the session opens. The range candle is the one that closes then." />
            <span class="hm-colon">:</span>
            <input type="number" id="crt-ny-m" value="0" min="0" max="59" title="Minute" />
          </span>
        </label>
        <label>Symbol
          <select id="crt-symbol">${symbols}</select>
        </label>
        <label>From
          <input type="date" id="crt-from" value="2025-03-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="crt-to" value="2025-04-01" />
        </label>
        <label>Timezone
          <input id="crt-tz" value="Europe/Bucharest" />
        </label>
        <label>Higher timeframe
          <select id="crt-htf">
            <option value="15">15m</option>
            <option value="30">30m</option>
            <option value="60" selected>60m</option>
            <option value="120">2h</option>
            <option value="240">4h</option>
          </select>
        </label>
        <label>Entry timeframe
          <select id="crt-ltf">
            <option value="5" selected>5m</option>
            <option value="15">15m</option>
            <option value="30">30m</option>
          </select>
        </label>
        <label>Structure bars
          <input type="number" id="crt-struct" value="24" min="4" max="200" step="1"
            title="Higher-timeframe bars before the range candle. The dealing range is their high and low." />
        </label>
        <label class="chk">Discount / premium
          <input type="checkbox" id="crt-pd" checked
            title="Longs only when the range candle closes at or below equilibrium. Shorts only at or above it." />
        </label>
        <label>Equilibrium
          <input type="number" id="crt-eq" value="0.5" min="0.05" max="0.95" step="0.05"
            title="0.5 is the middle of the dealing range." />
        </label>
        <label>Min leg (pts)
          <input type="number" id="crt-min-leg" value="0" min="0" step="10" title="0 = any dealing range. Used in Hunt and in New York open. Points use the symbol scale." />
        </label>
        <label>Min range candle (pts)
          <input type="number" id="crt-min-range" value="0" min="0" step="10" title="0 = any candle. High minus low of the range candle." />
        </label>
        <label>Direction
          <select id="crt-side" title="Long only, short only, or both. On gold the longs have carried the book. On EURUSD the shorts have.">
            <option value="both" selected>Both</option>
            <option value="long">Longs only</option>
            <option value="short">Shorts only</option>
          </select>
        </label>
        <label>Entry
          <select id="crt-entry">
            <option value="fvg" selected>Fair value gap</option>
            <option value="sweep_close">Sweep close</option>
          </select>
        </label>
        <label>Which gap
          <select id="crt-fvg-select">
            <option value="extreme" selected>Most discounted</option>
            <option value="first">First gap</option>
            <option value="all">Stack gaps</option>
          </select>
        </label>
        <label>Gap edge
          <select id="crt-fvg-entry">
            <option value="proximal" selected>Near edge</option>
            <option value="ce">Midpoint</option>
            <option value="distal">Far edge</option>
          </select>
        </label>
        <label>Max gaps
          <input type="number" id="crt-max-fvg" value="2" min="1" max="5" step="1"
            title="Used when Which gap is Stack. The video took two." />
        </label>
        <label>Gap wait (HTF bars)
          <input type="number" id="crt-fvg-wait" value="3" min="1" max="20" step="1"
            title="How long the limit stays working after the sweep candle closes." />
        </label>
        <label>Stop
          <select id="crt-sl-mode">
            <option value="beyond_fvg" selected>Beyond the gap</option>
            <option value="beyond_sweep">Beyond the sweep</option>
            <option value="fixed">Fixed points</option>
          </select>
        </label>
        <label>Stop buffer (pts)
          <input type="number" id="crt-sl-buf" value="0" min="0" step="1" />
        </label>
        <label>Min stop (pts)
          <input type="number" id="crt-min-sl" value="0" min="0" step="1"
            title="Skip a fill whose stop, after the buffer, is tighter than this. 0 allows any stop that is beyond the entry." />
        </label>
        <label>Fixed stop (pts)
          <input type="number" id="crt-sl-fixed" value="300" min="1" step="10" />
        </label>
        <label>Partial size
          <input type="number" id="crt-partial" value="0.5" min="0" max="1" step="0.05"
            title="Fraction closed at the partial. 0.5 and 1 R is the scratch when the rest stops." />
        </label>
        <label>Partial R
          <input type="number" id="crt-partial-rr" value="1" min="0.1" step="0.1" />
        </label>
        <label>Runner
          <select id="crt-runner">
            <option value="swing" selected>Dealing-range extreme</option>
            <option value="rr">Fixed R</option>
          </select>
        </label>
        <label>Runner R
          <input type="number" id="crt-runner-rr" value="2" min="0.1" step="0.1"
            title="Used when the runner is Fixed R, and when the dealing-range extreme is not beyond the partial." />
        </label>
        <label>Max hold (HTF bars)
          <input type="number" id="crt-hold" value="48" min="1" max="200" step="1" />
        </label>
        <label class="chk">Session filter
          <input type="checkbox" id="crt-session"
            title="Off by default. When on, the sweep candle must open inside the clock below." />
        </label>
        <label>Session start
          <span class="hm">
            <input type="number" id="crt-sess-sh" value="8" min="0" max="23" title="Hour" />
            <span class="hm-colon">:</span>
            <input type="number" id="crt-sess-sm" value="0" min="0" max="59" title="Minute" />
          </span>
        </label>
        <label>Session end
          <span class="hm">
            <input type="number" id="crt-sess-eh" value="17" min="0" max="23" />
            <span class="hm-colon">:</span>
            <input type="number" id="crt-sess-em" value="0" min="0" max="59" />
          </span>
        </label>
        <label class="chk">Skip gold news days
          <input type="checkbox" id="crt-news"
            title="Uses the gold news calendar on every symbol. Off by default." />
        </label>
        <label>Spread (pts)
          <input type="number" id="crt-cost" value="0" min="0" step="1"
            title="Charged once, on the entry. Not charged again on the partial or the runner." />
        </label>
        <label>Commission / fill (pts)
          <input type="number" id="crt-commission" value="0" min="0" step="1"
            title="Charged on the entry and on each exit. A partial and a runner are two exits, so this is paid three times. 0 = no commission." />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="crt-run">Run CRT</button>
        <button type="button" class="secondary" id="crt-stop" disabled>Stop</button>
        <label class="chk force"><input type="checkbox" id="crt-force" /> Force re-download</label>
      </div>
    </section>
    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap"><div class="progress-bar" id="crt-bar" style="width:0%"></div></div>
      <p class="progress-msg" id="crt-msg">Idle</p>
    </section>
    <section class="card">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="crt-saved" title="Open a saved CRT run from results/"></select>
          <button type="button" class="secondary" id="crt-load">Load</button>
        </div>
      </div>
      <p class="muted" id="crt-meta">No run yet.</p>
      <p class="table-note">Click a saved trade to open its entry-timeframe chart. <a id="crt-catalog" href="/crt/results" target="_blank" rel="noopener">Open catalog</a></p>
      <div class="hero-grid" id="crt-hero"></div>
      <div class="table-wrap">
        <table id="crt-table">
          <thead>
            <tr>
              <th>Day</th><th>Side</th><th>Entry</th><th>Fill</th>
              <th>SL</th><th>1:1</th><th>Runner</th><th>Exit</th><th>Why</th><th>Pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;
    const foot = document.querySelector("footer.foot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("CRT") < 0) {
      foot.textContent += " CRT = trend pullback, candle-range sweep, lower-timeframe gap.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-crt");
        if (tab === "crt") {
          document.querySelectorAll(".tab-panel").forEach(function (p) {
            p.classList.add("hidden");
          });
          if (panel) panel.classList.remove("hidden");
          document.querySelectorAll(".main-tab").forEach(function (b) {
            b.classList.remove("active");
          });
          btn.classList.add("active");
          try { localStorage.setItem("strateg_tab", "crt"); } catch (e) {}
          return;
        }
        if (panel) panel.classList.add("hidden");
      });
    });
    try {
      if (localStorage.getItem("strateg_tab") === "crt") {
        const btn = document.querySelector('.main-tab[data-tab="crt"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  function num(id, fallback) {
    const el = $(id);
    const n = el ? Number(el.value) : NaN;
    return Number.isFinite(n) ? n : fallback;
  }

  function payload() {
    return {
      symbol: $("crt-symbol").value,
      date_from: $("crt-from").value,
      date_to: $("crt-to").value,
      timezone: $("crt-tz").value || "Europe/Bucharest",
      htf_min: num("crt-htf", 60),
      ltf_min: num("crt-ltf", 5),
      structure_bars: num("crt-struct", 24),
      pd_filter: !!($("crt-pd") && $("crt-pd").checked),
      equilibrium: num("crt-eq", 0.5),
      min_leg_pts: num("crt-min-leg", 0),
      min_range_pts: num("crt-min-range", 0),
      min_sl_pts: num("crt-min-sl", 0),
      direction: $("crt-side").value,
      entry_mode: $("crt-entry").value,
      fvg_select: $("crt-fvg-select").value,
      fvg_entry: $("crt-fvg-entry").value,
      max_fvgs: num("crt-max-fvg", 2),
      fvg_wait_htf: num("crt-fvg-wait", 3),
      sl_mode: $("crt-sl-mode").value,
      sl_buffer_pts: num("crt-sl-buf", 0),
      sl_fixed_pts: num("crt-sl-fixed", 300),
      partial_frac: num("crt-partial", 0.5),
      partial_rr: num("crt-partial-rr", 1),
      runner_mode: $("crt-runner").value,
      runner_rr: num("crt-runner-rr", 2),
      max_hold_htf: num("crt-hold", 48),
      max_concurrent: num("crt-max-concurrent", 0),
      mode: $("crt-mode").value || "hunt",
      ny_timezone: ($("crt-ny-tz") && $("crt-ny-tz").value) || "America/New_York",
      ny_open_hour: num("crt-ny-h", 8),
      ny_open_minute: num("crt-ny-m", 0),
      session_enabled: !!($("crt-session") && $("crt-session").checked),
      session_start_hour: num("crt-sess-sh", 8),
      session_start_minute: num("crt-sess-sm", 0),
      session_end_hour: num("crt-sess-eh", 17),
      session_end_minute: num("crt-sess-em", 0),
      skip_news: !!($("crt-news") && $("crt-news").checked),
      cost_pts: num("crt-cost", 0),
      commission_pts: num("crt-commission", 0),
      force_download: !!($("crt-force") && $("crt-force").checked),
    };
  }

  function onSymbolChange() {
    const el = $("crt-symbol");
    if (!el) return;
    const next = formSymbol(el.value);
    const prev = formSymbol(lastSymbol);
    if (next === prev) return;
    symbolSwitching = true;
    const ratio = pointScale(next) / pointScale(prev);
    if (ratio !== 1) {
      POINT_FIELDS.forEach(function (id) {
        const field = $(id);
        if (!field) return;
        field.value = scalePoint(field.value, ratio);
      });
    }
    lastSymbol = next;
    symbolSwitching = false;
    scheduleSave();
  }

  function pfText(block) {
    if (!block) return "—";
    var pf = block.profit_factor == null ? "—" : block.profit_factor;
    return (block.trades || 0) + " PF " + pf;
  }

  function yearDirection(result) {
    var bits = [];
    var dirs = result.by_direction || {};
    if (dirs.long || dirs.short) {
      bits.push("long " + pfText(dirs.long) + " · short " + pfText(dirs.short));
    }
    (result.by_year || []).forEach(function (year) {
      bits.push(year.year + " " + pfText(year));
    });
    return bits.length ? " · " + bits.join(" · ") : "";
  }

  function render(state) {
    const prog = (state && state.progress) || {};
    const bar = $("crt-bar");
    const msg = $("crt-msg");
    if (bar) bar.style.width = Math.max(0, Math.min(100, Number(prog.pct) || 0)) + "%";
    if (msg) msg.textContent = prog.message || prog.phase || "Idle";
    const running = !!(state && state.running);
    if ($("crt-run")) $("crt-run").disabled = running;
    if ($("crt-stop")) $("crt-stop").disabled = !running;
    const result = state && state.result;
    if (!result || !result.rows && result && result.trades == null) return;
    if (!result) return;
    const pf = result.profit_factor == null ? "—" : result.profit_factor;
    if ($("crt-meta")) {
      $("crt-meta").textContent =
        (result.trades || 0) + " trades · PF " + pf + " · " + (result.sum_pts || 0) +
        " pts · " + (result.skipped || 0) + " skipped" +
        (result.skip_reasons && result.skip_reasons.invalidated_before_fill
          ? " · invalidated before fill " + result.skip_reasons.invalidated_before_fill
          : "") +
        (result.saved_to ? " · " + result.saved_to : "") +
        yearDirection(result);
    }
    const hero = $("crt-hero");
    if (hero) {
      hero.innerHTML = [
        ["Trades", result.trades],
        ["Win %", result.win_pct],
        ["PF", pf],
        ["Sum pts", result.sum_pts],
        ["Scratches", result.scratches],
        ["Max DD", result.max_dd_pts],
        ["Closed DD", result.max_dd_closed_pts],
      ].map(function (pair) {
        return "<div><span>" + pair[0] + "</span><strong>" + (pair[1] == null ? "—" : pair[1]) + "</strong></div>";
      }).join("");
    }
    const catalog = $("crt-catalog");
    if (catalog) {
      catalog.href = result.sqlite_id
        ? "/crt/results?run=" + encodeURIComponent(result.sqlite_id)
        : "/crt/results";
      catalog.textContent = result.sqlite_id
        ? "Open catalog #" + result.sqlite_id
        : "Open catalog";
    }
    const table = $("crt-table");
    const body = table ? table.querySelector("tbody") : null;
    if (!body) return;
    const rows = result.rows || [];
    const saved = rows.some(function (r) { return r.id; });
    if (table) table.classList.toggle("ab-table", saved);
    body.innerHTML = "";
    rows.forEach(function (r) {
      const tr = document.createElement("tr");
      const pts = Number(r.pts);
      const ptsClass = Number.isFinite(pts) ? (pts >= 0 ? "ab-win" : "ab-loss") : "";
      tr.innerHTML =
        "<td>" + r.local_date + "</td><td>" + r.side + "</td><td>" + (r.entry_reason || "") +
        "</td><td>" + r.entry + "</td><td>" + r.sl + "</td><td>" + (r.partial_px == null ? "—" : r.partial_px) +
        "</td><td>" + r.tp + "</td><td>" + r.exit + "</td><td>" + (r.exit_reason || "") +
        "</td><td class='" + ptsClass + "'>" + r.pts + "</td>";
      if (r.id) {
        tr.tabIndex = 0;
        function openChart() {
          window.open("/crt/chart?trade=" + r.id, "_blank");
        }
        tr.addEventListener("click", openChart);
        tr.addEventListener("keydown", function (ev) {
          if (ev.key === "Enter") openChart();
        });
      }
      body.appendChild(tr);
    });
  }

  function loadRules() {
    fetch("/api/crt/rules").then(function (r) { return r.json(); }).then(function (data) {
      const list = $("crt-rules");
      if (!list || !data.rules) return;
      list.innerHTML = data.rules.map(function (rule) {
        return "<li>" + rule.body + "</li>";
      }).join("");
    }).catch(function () {});
  }

  async function poll() {
    const res = await fetch("/api/crt");
    const state = await res.json();
    render(state);
    if (!state.running && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startPoll() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(function () {
      poll().catch(function (e) { console.warn(e); });
    }, 1000);
    poll().catch(function (e) { console.warn(e); });
  }

  function syncMode() {
    const ny = $("crt-mode") && $("crt-mode").value === "ny_open";
    ["crt-ny-tz-wrap", "crt-ny-open-wrap"].forEach(function (id) {
      const el = $(id);
      if (el) el.hidden = !ny;
    });
  }

  function wire() {
    ensureTab();
    loadForm();
    syncMode();
    lastSymbol = formSymbol($("crt-symbol") && $("crt-symbol").value);
    wireTabs();
    loadRules();
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", function () { scheduleSave(); syncMode(); });
      el.addEventListener("input", scheduleSave);
    });
    if ($("crt-symbol")) $("crt-symbol").addEventListener("change", onSymbolChange);
    $("crt-run").addEventListener("click", function () {
      saveForm();
      if ($("crt-msg")) $("crt-msg").textContent = "Starting…";
      fetch("/api/crt/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload()),
      }).then(function (res) {
        return res.text().then(function (text) {
          let data = null;
          try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
          if (!res.ok) {
            if (res.status === 404) {
              throw new Error("This server does not have CRT yet. Restart webapp.py, then reload this page.");
            }
            const detail = data && data.detail;
            throw new Error(
              typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : text || res.statusText
            );
          }
          return data;
        });
      }).then(function () {
        startPoll();
      }).catch(function (e) {
        if ($("crt-msg")) $("crt-msg").textContent = String(e.message || e);
      });
    });
    $("crt-stop").addEventListener("click", function () {
      fetch("/api/crt/stop", { method: "POST" }).catch(function () {});
    });
    if (window.StrategSaved) {
      window.StrategSaved.bindPicker({
        kind: "crt",
        selectId: "crt-saved",
        buttonId: "crt-load",
        onLoaded: function (json) {
          render({ result: json, progress: { message: "Loaded saved run", pct: 100 } });
        },
      });
    }
    fetch("/api/crt").then(function (r) { return r.json(); }).then(function (state) {
      render(state);
      if (state.running) startPoll();
    }).catch(function () {});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
