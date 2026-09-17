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
    "ab-min-range",
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
    "ab-double-tp",
    "ab-bounce",
    "ab-en-cont",
    "ab-en-rev-c",
    "ab-en-rev-e",
    "ab-en-sh-e",
    "ab-en-sh-c",
    "ab-en-retest",
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
      console.warn("asia box save failed", e);
    }
  }

  function loadForm() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const cfg = JSON.parse(raw);
      FORM_IDS.forEach(function (id) {
        const el = $(id);
        if (!el || cfg[id] === undefined) return;
        if (el.type === "checkbox") el.checked = !!cfg[id];
        else el.value = cfg[id];
      });
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
      min_range_pts: num("ab-min-range", 3000),
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
      <ol>
        <li>Build the Asia box from <strong>01:00–06:00</strong> local. Fib 0 is the later extreme, Fib 1 the other side.</li>
        <li>Named setups (toggles below) hunt retracements until 10:00. One open trade; a fill that dies before 06:00 may unlock a second, larger box.</li>
        <li>Flatten 13:30. Independent of Overnight break — both can trade the same morning.</li>
      </ol>
      <p class="hint">5m candles by default; ticks only change fill / SL / TP precision. Results live in SQLite — open the catalog to filter by setup and click a trade for the chart.</p>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ab-symbol"><option value="XAUUSD" selected>XAUUSD (gold)</option></select>
        </label>
        <label>From (local date)
          <input type="date" id="ab-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="ab-to" value="2025-08-01" />
        </label>
        <label>Timezone
          <input id="ab-tz" value="Europe/Chisinau" />
        </label>
        <label>Min range (pts)
          <input type="number" id="ab-min-range" value="3000" step="100" />
        </label>
        <label>EMA period (5m)
          <input type="number" id="ab-ema" value="32" min="1" />
        </label>
        <label>Data
          <select id="ab-data">
            <option value="candles_5m" selected>5m candles</option>
            <option value="ticks">Ticks</option>
          </select>
        </label>
        <label>Box start hour
          <input type="number" id="ab-box-start" value="1" min="0" max="23" />
        </label>
        <label>Box end hour
          <input type="number" id="ab-box-end" value="6" min="0" max="23" />
        </label>
        <label>Shallow hour
          <input type="number" id="ab-shallow-h" value="5" min="0" max="23" />
        </label>
        <label>Shallow minute
          <input type="number" id="ab-shallow-m" value="30" min="0" max="59" />
        </label>
        <label>EMA retest hour
          <input type="number" id="ab-ema-retest-h" value="7" min="0" max="23" />
        </label>
        <label>Entry cutoff hour
          <input type="number" id="ab-cutoff" value="10" min="0" max="23" />
        </label>
        <label>Flatten hour
          <input type="number" id="ab-flatten-h" value="13" min="0" max="23" />
        </label>
        <label>Flatten minute
          <input type="number" id="ab-flatten-m" value="30" min="0" max="59" />
        </label>
        <label>Shallow EMA near (pts)
          <input type="number" id="ab-shallow-near" value="100" step="10" />
        </label>
      </div>
      <div class="ab-setup-list">
        <span class="label">Setups</span>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-cont" checked /> Continuation</label>
          <div class="ab-setup-levels" data-for="ab-en-cont">
            <label>SL <input type="number" id="ab-cont-sl" value="0.786" step="0.001" /></label>
            <label>TP <input type="number" id="ab-cont-tp" value="0" step="0.001" /></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-rev-c" checked /> Reverse Confirm</label>
          <div class="ab-setup-levels" data-for="ab-en-rev-c">
            <label>SL <input type="number" id="ab-rev-c-sl" value="0.5" step="0.001" /></label>
            <label>TP <input type="number" id="ab-rev-c-tp" value="1.5" step="0.001" /></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-rev-e" checked /> Reverse EMA</label>
          <div class="ab-setup-levels" data-for="ab-en-rev-e">
            <label>SL <input type="number" id="ab-rev-e-sl" value="0.5" step="0.001" /></label>
            <label>TP <input type="number" id="ab-rev-e-tp" value="1" step="0.001" /></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-sh-e" checked /> Shallow EMA</label>
          <div class="ab-setup-levels" data-for="ab-en-sh-e">
            <label>SL <input type="number" id="ab-sh-e-sl" value="0.5" step="0.001" /></label>
            <label>TP <input type="number" id="ab-sh-e-tp" value="0" step="0.001" /></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-sh-c" checked /> Shallow Confirm</label>
          <div class="ab-setup-levels" data-for="ab-en-sh-c">
            <label>SL <input type="number" id="ab-sh-c-sl" value="0.5" step="0.001" /></label>
            <label>TP <input type="number" id="ab-sh-c-tp" value="0" step="0.001" /></label>
          </div>
        </div>
        <div class="ab-setup-item">
          <label class="chk"><input type="checkbox" id="ab-en-retest" checked /> EMA Retest</label>
          <div class="ab-setup-levels" data-for="ab-en-retest">
            <label class="chk"><input type="checkbox" id="ab-retest-auto" checked /> Auto SL/TP</label>
            <label>SL <input type="number" id="ab-retest-sl" value="0.382" step="0.001" /></label>
            <label>TP <input type="number" id="ab-retest-tp" value="0" step="0.001" /></label>
          </div>
        </div>
      </div>
      <div class="engines">
        <span class="label">Reserved</span>
        <label class="chk ab-tip" title="With-trend only (Continuation, Shallow, EMA Retest). Replaces the Fib 0 target with twice the distance from entry to Fib 0. Reverse trades are unchanged." data-tip="With-trend only (Continuation, Shallow, EMA Retest). Replaces the Fib 0 target with twice the distance from entry to Fib 0. Reverse trades are unchanged."><input type="checkbox" id="ab-double-tp" /> 2× Fib 0 profit TP</label>
        <label class="chk ab-tip" title="After Fib .236 is tagged twice (separate touches), the open trade’s stop is pulled to Fib .618." data-tip="After Fib .236 is tagged twice (separate touches), the open trade’s stop is pulled to Fib .618."><input type="checkbox" id="ab-bounce" /> .236 bounce SL</label>
        <label class="chk"><input type="checkbox" id="ab-force" /> Force download</label>
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
    if (!sid && n === 0) {
      el.textContent = "0 trades · not saved to the catalog.";
      return;
    }
    const parts = Object.keys(result.by_setup || {})
      .map((k) => k + " " + (result.by_setup[k].n || 0))
      .join(" · ");
    el.innerHTML =
      n +
      " trades · " +
      pts +
      " pts" +
      (parts ? " · " + parts : "") +
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
    const locked = !!(auto && auto.checked);
    if (sl) sl.disabled = locked;
    if (tp) tp.disabled = locked;
  }

  function wire() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", function () {
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
