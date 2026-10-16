(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_asia_pullback_v1";
  let pollTimer = null;
  let saveTimer = null;

  const FORM_IDS = [
    "ap-symbol", "ap-from", "ap-to", "ap-tz", "ap-source", "ap-workers",
    "ap-box-h", "ap-box-m", "ap-listen-h", "ap-listen-m", "ap-break",
    "ap-level", "ap-fib", "ap-ma", "ap-ema", "ap-ema-tf", "ap-kama-fast", "ap-kama-slow",
    "ap-confirm", "ap-rev", "ap-sr-days", "ap-sr-touches", "ap-sr-tol", "ap-sr-pdhl",
    "ap-sl-mode", "ap-sl-fixed", "ap-sl-range", "ap-sl-cap",
    "ap-tp-mode", "ap-tp-range", "ap-tp-fixed", "ap-tp-sl",
    "ap-flat", "ap-cost", "ap-force",
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
    if (nav && !document.querySelector('.main-tab[data-tab="asia-pullback"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "asia-pullback");
      btn.textContent = "Asia pullback";
      nav.appendChild(btn);
    }
    if ($("tab-asia-pullback")) return;
    const symbols = window.strategSymbols && window.strategSymbols.optionsHtml
      ? window.strategSymbols.optionsHtml()
      : '<option value="XAUUSD" selected>XAUUSD</option>';
    const panel = document.createElement("div");
    panel.id = "tab-asia-pullback";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Asia pullback</h2>
      <ol>
        <li>Lock the 15m box on bars that open from <strong>00:00</strong> until the box end (default <strong>04:30 Europe/Bucharest</strong>). The 04:15 bar is inside. The 04:30 bar can arm.</li>
        <li>The first later 15m close at least <strong>break frac × box range</strong> past an edge arms that side. The arming bar does not fill. A new extreme moves a leg-fib order and that bar does not enter. A 15m close through the opposite edge cancels.</li>
        <li>One level: a fib of the live leg (0 = extreme, 1 = broken edge), a fib of the box (0 = broken edge), or one moving average of the chosen timeframe. Touch fills on the first tag. Close 5m waits for a 5m close back through that level in the break direction.</li>
        <li>Stop is the far side of the box. Target is the box range from the entry. Flatten at the local hour. One trade a day. Weekday and box / H1 ATR are stamped. No Monday filter and no large-box filter.</li>
      </ol>
      <p class="hint">This is the experiment. A frozen rule in the study was about a 1.05 profit factor overall and lost 2023. Cost is a flat point charge subtracted from each trade. 0 leaves the overnight exit prices unchanged. The exit engine has no bid/ask model. Reversal is off unless the box is checked. It fades the first 15-minute rejection of a high or low shelf from the last few sessions, and that fill replaces the pullback for the day.</p>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ap-symbol">${symbols}</select>
        </label>
        <label>From
          <input type="date" id="ap-from" value="2025-03-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="ap-to" value="2025-06-01" />
        </label>
        <label>Timezone
          <input id="ap-tz" value="Europe/Bucharest" />
        </label>
        <label>Data
          <select id="ap-source">
            <option value="candles_5m" selected>5m candles</option>
            <option value="ticks">Ticks</option>
          </select>
        </label>
        <label>Workers
          <input type="number" id="ap-workers" value="2" min="1" max="6" step="1" />
        </label>
        <label>Box end
          <span class="hm">
            <input type="number" id="ap-box-h" value="4" min="0" max="23" title="Hour" />
            <span class="hm-colon">:</span>
            <input type="number" id="ap-box-m" value="30" min="0" max="59" title="Minute. The bar that opens here is outside the box." />
          </span>
        </label>
        <label>Listen end
          <span class="hm">
            <input type="number" id="ap-listen-h" value="9" min="0" max="23" title="Hour. Fills at this clock still count." />
            <span class="hm-colon">:</span>
            <input type="number" id="ap-listen-m" value="0" min="0" max="59" />
          </span>
        </label>
        <label>Break fraction
          <input type="number" id="ap-break" value="0.25" min="0" max="2" step="0.01"
            title="15m close must clear the box edge by this fraction of the box range." />
        </label>
        <label>Level
          <select id="ap-level">
            <option value="leg_fib" selected>Fib of the leg</option>
            <option value="box_fib">Fib of the box</option>
            <option value="ema">Moving average</option>
          </select>
        </label>
        <label>Fib level
          <input type="number" id="ap-fib" value="0.382" min="0" max="1" step="0.001" />
        </label>
        <label>Average
          <select id="ap-ma">
            <option value="ema" selected>EMA</option>
            <option value="kama">KAMA</option>
            <option value="hma">HMA</option>
            <option value="zlema">ZLEMA</option>
          </select>
        </label>
        <label>Average period
          <input type="number" id="ap-ema" value="20" min="1" max="500" />
        </label>
        <label>Average timeframe (min)
          <input type="number" id="ap-ema-tf" value="60" min="15" max="240" step="15" />
        </label>
        <label id="ap-kama-fast-wrap">KAMA fast
          <input type="number" id="ap-kama-fast" value="2" min="1" max="50" />
        </label>
        <label id="ap-kama-slow-wrap">KAMA slow
          <input type="number" id="ap-kama-slow" value="30" min="1" max="200" />
        </label>
        <label>Confirm
          <select id="ap-confirm">
            <option value="touch" selected>Touch</option>
            <option value="close5m">5m close back</option>
          </select>
        </label>
        <label class="chk">Reversal off a shelf
          <input type="checkbox" id="ap-rev"
            title="Off by default. When on, a 15m rejection of a high or low shelf from the last N sessions can take the day's trade instead of the pullback." />
        </label>
        <label>Shelf days
          <input type="number" id="ap-sr-days" value="5" min="1" max="30" step="1" />
        </label>
        <label>Min prints
          <input type="number" id="ap-sr-touches" value="2" min="1" max="10" step="1"
            title="How many daily highs, or daily lows, have to sit in the same band." />
        </label>
        <label>Shelf width (× H1 ATR)
          <input type="number" id="ap-sr-tol" value="0.25" min="0" max="2" step="0.05" />
        </label>
        <label class="chk">Yesterday's high and low
          <input type="checkbox" id="ap-sr-pdhl" checked
            title="Count yesterday's high and yesterday's low even when no other day lines up with them." />
        </label>
        <label>Stop
          <select id="ap-sl-mode">
            <option value="asia_opposite" selected>Far side of the box</option>
            <option value="fixed">Fixed points</option>
            <option value="range">Box range ×</option>
          </select>
        </label>
        <label>Stop points
          <input type="number" id="ap-sl-fixed" value="500" min="1" step="10"
            title="Used when stop is fixed, and when the far side of the box is on the wrong side of the entry." />
        </label>
        <label>Stop range ×
          <input type="number" id="ap-sl-range" value="1" min="0" step="0.1" />
        </label>
        <label>Stop cap (pts)
          <input type="number" id="ap-sl-cap" value="0" min="0" step="10" title="0 = no cap." />
        </label>
        <label>Target
          <select id="ap-tp-mode">
            <option value="range_mult" selected>Box range ×</option>
            <option value="fixed">Fixed points</option>
            <option value="sl_mult">Stop ×</option>
            <option value="fixed_cap">Fixed, capped by stop ×</option>
          </select>
        </label>
        <label>Target range ×
          <input type="number" id="ap-tp-range" value="1" min="0" step="0.1" />
        </label>
        <label>Target points
          <input type="number" id="ap-tp-fixed" value="1000" min="1" step="10" />
        </label>
        <label>Target stop ×
          <input type="number" id="ap-tp-sl" value="2" min="0" step="0.1" />
        </label>
        <label>Flatten hour
          <input type="number" id="ap-flat" value="23" min="0" max="23" />
        </label>
        <label>Cost / spread (pts)
          <input type="number" id="ap-cost" value="0" min="0" step="1"
            title="Subtracted from each trade. 0 = no cost." />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="ap-run">Run Asia pullback</button>
        <button type="button" class="secondary" id="ap-stop" disabled>Stop</button>
        <label class="chk force"><input type="checkbox" id="ap-force" /> Force re-download</label>
      </div>
    </section>
    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap"><div class="progress-bar" id="ap-bar" style="width:0%"></div></div>
      <p class="progress-msg" id="ap-msg">Idle</p>
    </section>
    <section class="card">
      <h2>Results</h2>
      <p class="muted" id="ap-meta">No run yet.</p>
      <div class="hero-grid" id="ap-hero"></div>
      <div class="table-wrap">
        <table id="ap-table">
          <thead>
            <tr>
              <th>Day</th><th>Wd</th><th>Side</th><th>Level</th><th>Entry</th>
              <th>SL</th><th>TP</th><th>Exit</th><th>Why</th><th>Pts</th><th>Box/H1</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;
    const foot = document.querySelector("footer.foot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("Asia pullback") < 0) {
      foot.textContent += " Asia pullback = 04:30 box, fractional close, one fib or average.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-asia-pullback");
        if (panel) panel.classList.toggle("hidden", tab !== "asia-pullback");
        if (tab === "asia-pullback") {
          [
            "tab-research", "tab-sweep", "tab-session", "tab-spikefade", "tab-micro",
            "tab-burst", "tab-cooloff", "tab-fvg", "tab-asia-liq", "tab-impulse-fork",
            "tab-overnight", "tab-asia-box", "tab-dawn-cross", "tab-stop-scalper",
          ].forEach(function (id) {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach(function (b) {
            b.classList.remove("active");
          });
          btn.classList.add("active");
          try { localStorage.setItem("strateg_tab", "asia-pullback"); } catch (e) {}
        }
      });
    });
    try {
      if (localStorage.getItem("strateg_tab") === "asia-pullback") {
        const btn = document.querySelector('.main-tab[data-tab="asia-pullback"]');
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
      symbol: $("ap-symbol").value,
      date_from: $("ap-from").value,
      date_to: $("ap-to").value,
      timezone: $("ap-tz").value || "Europe/Bucharest",
      data_source: $("ap-source").value,
      workers: num("ap-workers", 2),
      box_end_hour: num("ap-box-h", 4),
      box_end_minute: num("ap-box-m", 30),
      listen_end_hour: num("ap-listen-h", 9),
      listen_end_minute: num("ap-listen-m", 0),
      break_frac: num("ap-break", 0.25),
      level_ref: $("ap-level").value,
      fib_level: num("ap-fib", 0.382),
      ma_type: $("ap-ma").value,
      ema_period: num("ap-ema", 20),
      ema_tf_min: num("ap-ema-tf", 60),
      kama_fast: num("ap-kama-fast", 2),
      kama_slow: num("ap-kama-slow", 30),
      confirm_mode: $("ap-confirm").value,
      reversal: !!($("ap-rev") && $("ap-rev").checked),
      sr_days: num("ap-sr-days", 5),
      sr_min_touches: num("ap-sr-touches", 2),
      sr_tol_frac: num("ap-sr-tol", 0.25),
      sr_pdhl: !!($("ap-sr-pdhl") && $("ap-sr-pdhl").checked),
      sl_mode: $("ap-sl-mode").value,
      sl_fixed_pts: num("ap-sl-fixed", 500),
      sl_range_mult: num("ap-sl-range", 1),
      sl_cap_pts: num("ap-sl-cap", 0),
      tp_mode: $("ap-tp-mode").value,
      tp_range_mult: num("ap-tp-range", 1),
      tp_fixed_pts: num("ap-tp-fixed", 1000),
      tp_sl_mult: num("ap-tp-sl", 2),
      flatten_hour: num("ap-flat", 23),
      cost_pts: num("ap-cost", 0),
      force_download: !!($("ap-force") && $("ap-force").checked),
    };
  }

  function syncMa() {
    const kama = $("ap-ma") && $("ap-ma").value === "kama";
    ["ap-kama-fast-wrap", "ap-kama-slow-wrap"].forEach(function (id) {
      const el = $(id);
      if (el) el.hidden = !kama;
    });
  }

  function render(state) {
    const prog = (state && state.progress) || {};
    const bar = $("ap-bar");
    const msg = $("ap-msg");
    if (bar) bar.style.width = Math.max(0, Math.min(100, Number(prog.pct) || 0)) + "%";
    if (msg) msg.textContent = prog.message || prog.phase || "Idle";
    const running = !!(state && state.running);
    if ($("ap-run")) $("ap-run").disabled = running;
    if ($("ap-stop")) $("ap-stop").disabled = !running;
    const result = state && state.result;
    if (!result) return;
    const pf = result.profit_factor == null ? "—" : result.profit_factor;
    if ($("ap-meta")) {
      $("ap-meta").textContent =
        (result.trades || 0) + " trades · PF " + pf + " · " + (result.sum_pts || 0) +
        " pts · " + (result.skipped || 0) + " skipped" +
        (result.saved_to ? " · " + result.saved_to : "");
    }
    const hero = $("ap-hero");
    if (hero) {
      hero.innerHTML = [
        ["Trades", result.trades],
        ["Win %", result.win_pct],
        ["PF", pf],
        ["Sum pts", result.sum_pts],
        ["Avg pts", result.avg_pts],
      ].map(function (pair) {
        return "<div><span>" + pair[0] + "</span><strong>" + pair[1] + "</strong></div>";
      }).join("");
    }
    const body = document.querySelector("#ap-table tbody");
    if (!body) return;
    const rows = result.rows || [];
    body.innerHTML = rows.map(function (r) {
      return "<tr><td>" + r.local_date + "</td><td>" + (r.weekday || "").slice(0, 3) +
        "</td><td>" + r.side + "</td><td>" + r.level + "</td><td>" + r.entry +
        "</td><td>" + r.sl + "</td><td>" + r.tp + "</td><td>" + r.exit +
        "</td><td>" + r.exit_reason + "</td><td>" + r.pts +
        "</td><td>" + (r.box_h1_atr == null ? "—" : r.box_h1_atr) + "</td></tr>";
    }).join("");
  }

  async function poll() {
    const res = await fetch("/api/asia-pullback");
    const state = await res.json();
    render(state);
    const running = !!state.running;
    if (!running && pollTimer) {
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

  function wire() {
    ensureTab();
    loadForm();
    syncMa();
    wireTabs();
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", function () { scheduleSave(); syncMa(); });
      el.addEventListener("input", scheduleSave);
    });
    $("ap-run").addEventListener("click", function () {
      saveForm();
      if ($("ap-msg")) $("ap-msg").textContent = "Starting…";
      let body;
      try {
        body = JSON.stringify(payload());
      } catch (e) {
        if ($("ap-msg")) $("ap-msg").textContent = String(e.message || e);
        return;
      }
      fetch("/api/asia-pullback/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      }).then(function (res) {
        return res.text().then(function (text) {
          let data = null;
          try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
          if (!res.ok) {
            if (res.status === 404) {
              throw new Error("This server does not have Asia pullback yet. Restart webapp.py, then reload this page.");
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
        if ($("ap-msg")) $("ap-msg").textContent = String(e.message || e);
      });
    });
    $("ap-stop").addEventListener("click", function () {
      fetch("/api/asia-pullback/stop", { method: "POST" }).catch(function () {});
    });
    fetch("/api/asia-pullback").then(function (r) { return r.json(); }).then(function (state) {
      render(state);
      if (state.running) startPoll();
    }).catch(function () {});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();
