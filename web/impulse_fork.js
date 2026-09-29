(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_impulse_fork_v1";
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
    "if-symbol",
    "if-from",
    "if-to",
    "if-min-blast",
    "if-snap",
    "if-window",
    "if-snap-sec",
    "if-chase",
    "if-cooldown",
    "if-london",
    "if-london-start",
    "if-london-end",
    "if-fade",
    "if-fade-lag",
    "if-fade-sl-pct",
    "if-fade-sl-cap",
    "if-fade-tp-pct",
    "if-fade-tp-cap",
    "if-fade-trail",
    "if-fade-arm",
    "if-fade-hold",
    "if-join",
    "if-join-stop",
    "if-join-tp1",
    "if-join-tp2",
    "if-join-be",
    "if-join-hold",
    "if-join-retrace",
    "if-join-wait",
    "if-aside",
    "if-aside-n",
    "if-risk",
    "if-equity",
    "if-daily-halt",
    "if-weekly-halt",
    "if-workers",
    "if-force",
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
  function bindFormPersist() {
    FORM_IDS.forEach(function (id) {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", scheduleSave);
      el.addEventListener("input", scheduleSave);
    });
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="impulse-fork"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "impulse-fork");
      btn.textContent = "Impulse fork";
      nav.appendChild(btn);
    }
    if ($("tab-impulse-fork")) return;
    const panel = document.createElement("div");
    panel.id = "tab-impulse-fork";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Impulse fork</h2>
      <ol>
        <li>Detect a 3s blast (≥ min pts).</li>
        <li>If it <strong>snaps back</strong> ≥ snap pts in 10s → <em>Fade</em> the extreme.</li>
        <li>If it holds, then retraces ~50% without taking the origin → <em>Join</em> the blast.</li>
        <li>Three one-way blasts → stand aside until a snapback. Never fade and join the same blast.</li>
      </ol>
      <p class="hint">
        Not an Asia box. News days are allowed. Optional skip 07:00–10:00 UTC so the live Asia bot owns London morning.
        Point distances stay as entered. On an FX major, 1 point is 0.1 pip, so the gold blast defaults are large there. Gold and bitcoin use $0.01 per point.
        Judge PF / avg R / max DD, and Fade vs Join split. Kill Join if its PF &lt; 1.
      </p>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="if-symbol" title="FX majors: 1 point = 0.1 pip. Gold and bitcoin: 1 point = $0.01. Point fields stay as entered.">${window.strategSymbols.optionsHtml()}</select>
        </label>
        <label>From <input type="date" id="if-from" value="2026-06-01" /></label>
        <label>To (exclusive) <input type="date" id="if-to" value="2026-07-01" /></label>
        <label>Min blast (pts)
          <input type="number" id="if-min-blast" value="1100" min="400" step="50" />
        </label>
        <label>Snapback (pts)
          <input type="number" id="if-snap" value="300" min="50" step="50" />
        </label>
        <label>Window (sec)
          <input type="number" id="if-window" value="3" min="0.5" step="0.5" />
        </label>
        <label>Snap window (sec)
          <input type="number" id="if-snap-sec" value="10" min="1" step="1" />
        </label>
        <label>Chase extension (× blast)
          <input type="number" id="if-chase" value="0.5" min="0" step="0.1" />
        </label>
        <label>Cooldown (sec)
          <input type="number" id="if-cooldown" value="30" min="0" step="5" />
        </label>
        <label class="chk">Skip London hours UTC
          <input type="checkbox" id="if-london" checked />
        </label>
        <label>London start hour UTC
          <input type="number" id="if-london-start" value="7" min="0" max="23" />
        </label>
        <label>London end hour UTC
          <input type="number" id="if-london-end" value="10" min="1" max="23" />
        </label>
        <label class="chk">Fade <input type="checkbox" id="if-fade" checked /></label>
        <label>Fade lag (sec)
          <input type="number" id="if-fade-lag" value="1" min="0" step="0.5" />
        </label>
        <label>Fade SL % of blast
          <input type="number" id="if-fade-sl-pct" value="100" min="0" step="10" />
        </label>
        <label>Fade SL cap (pts)
          <input type="number" id="if-fade-sl-cap" value="1500" min="0" step="50" />
        </label>
        <label>Fade TP % of blast
          <input type="number" id="if-fade-tp-pct" value="200" min="0" step="10" />
        </label>
        <label>Fade TP cap (pts)
          <input type="number" id="if-fade-tp-cap" value="3000" min="0" step="50" />
        </label>
        <label>Fade trail (pts)
          <input type="number" id="if-fade-trail" value="600" min="0" step="50" />
        </label>
        <label>Fade trail arm (pts)
          <input type="number" id="if-fade-arm" value="750" min="0" step="50" />
        </label>
        <label>Fade hold (sec)
          <input type="number" id="if-fade-hold" value="250" min="10" step="10" />
        </label>
        <label class="chk">Join <input type="checkbox" id="if-join" checked /></label>
        <label>Join stop beyond (× blast)
          <input type="number" id="if-join-stop" value="0.15" min="0" step="0.05" />
        </label>
        <label>Join TP1 R
          <input type="number" id="if-join-tp1" value="1" min="0.1" step="0.1" />
        </label>
        <label>Join TP2 R
          <input type="number" id="if-join-tp2" value="1.5" min="0.1" step="0.1" />
        </label>
        <label>Join BE offset R
          <input type="number" id="if-join-be" value="0.1" min="0" step="0.05" />
        </label>
        <label>Join hold (sec)
          <input type="number" id="if-join-hold" value="1200" min="30" step="30" />
        </label>
        <label>Join retrace
          <input type="number" id="if-join-retrace" value="0.5" min="0.1" max="0.9" step="0.05" />
        </label>
        <label>Join wait (sec)
          <input type="number" id="if-join-wait" value="90" min="10" step="10" />
        </label>
        <label class="chk">Stand aside <input type="checkbox" id="if-aside" checked /></label>
        <label>Stand aside after N
          <input type="number" id="if-aside-n" value="3" min="1" max="10" />
        </label>
        <label>Risk % equity
          <input type="number" id="if-risk" value="0.5" min="0.1" max="20" step="0.1" />
        </label>
        <label>Start equity
          <input type="number" id="if-equity" value="1000" min="100" step="100" />
        </label>
        <label>Daily halt (R)
          <input type="number" id="if-daily-halt" value="1.5" min="0" step="0.5" />
        </label>
        <label>Weekly halt (R)
          <input type="number" id="if-weekly-halt" value="4" min="0" step="0.5" />
        </label>
        <label>Workers
          <input type="number" id="if-workers" value="3" min="1" max="6" />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="if-run">Run impulse fork</button>
        <button type="button" class="secondary" id="if-stop" disabled>Stop</button>
        <label class="chk force"><input type="checkbox" id="if-force" /> Force re-download</label>
      </div>
    </section>
    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap"><div class="progress-bar" id="if-progress-bar" style="width:0%"></div></div>
      <p class="progress-msg" id="if-progress-msg">Idle</p>
    </section>
    <section class="card">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="if-saved"></select>
          <button type="button" class="secondary" id="if-load">Load</button>
        </div>
      </div>
      <p class="muted" id="if-meta">No run yet.</p>
      <div class="hero-grid" id="if-hero"></div>
      <h3>Fade vs Join</h3>
      <div class="hero-grid" id="if-mode-hero"></div>
      <p class="table-note" id="if-skips"></p>
      <h3>Trades</h3>
      <div class="table-wrap">
        <table id="if-table">
          <thead>
            <tr>
              <th>Time</th><th>Mode</th><th>Side</th><th>Blast</th>
              <th>Entry</th><th>SL</th><th>Exit</th><th>Reason</th><th>Pts</th><th>R</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;
    const foot = document.querySelector("footer.foot");
    if (foot) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("Impulse fork") < 0) {
      foot.textContent += " Impulse fork = fade a snapback or join a held blast.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-impulse-fork");
        if (panel) panel.classList.toggle("hidden", tab !== "impulse-fork");
        if (tab === "impulse-fork") {
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
            "tab-asia-liq",
          ].forEach(function (id) {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "impulse-fork");
          } catch (e) {}
        }
      });
    });
    try {
      if (localStorage.getItem("strateg_tab") === "impulse-fork") {
        const btn = document.querySelector('.main-tab[data-tab="impulse-fork"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  function dash(v) {
    return v == null || v === "" ? "—" : v;
  }
  function heroItem(label, value) {
    return '<div class="hero"><div class="k">' + label + '</div><div class="v">' + (value == null ? "—" : value) + "</div></div>";
  }

  function render(result) {
    const meta = $("if-meta");
    const hero = $("if-hero");
    const modeHero = $("if-mode-hero");
    const skipEl = $("if-skips");
    const tb = $("if-table") && $("if-table").querySelector("tbody");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
      if (modeHero) modeHero.innerHTML = "";
      if (skipEl) skipEl.textContent = "";
      if (tb) tb.innerHTML = "";
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
        " skipped" +
        ((window.StrategSaved && window.StrategSaved.loadedNote(result)) || "");
    }
    if (hero) {
      hero.innerHTML =
        heroItem("Win %", result.win_pct != null ? result.win_pct + "%" : "—") +
        heroItem("PF", result.profit_factor) +
        heroItem("Avg R", result.avg_r) +
        heroItem("Sum R", result.sum_r) +
        heroItem("Max DD", result.max_dd_pct != null ? result.max_dd_pct + "%" : "—") +
        heroItem("Equity", result.equity) +
        heroItem("Trades", result.trades) +
        heroItem("Skipped", result.skipped);
    }
    if (modeHero) {
      const f = (result.by_mode && result.by_mode.fade) || {};
      const j = (result.by_mode && result.by_mode.join) || {};
      modeHero.innerHTML =
        heroItem("Fade n", f.trades) +
        heroItem("Fade PF", f.profit_factor) +
        heroItem("Fade avg R", f.avg_r) +
        heroItem("Join n", j.trades) +
        heroItem("Join PF", j.profit_factor) +
        heroItem("Join avg R", j.avg_r);
    }
    if (skipEl) {
      const reasons = result.skip_reasons || {};
      skipEl.textContent = Object.keys(reasons)
        .sort()
        .map(function (k) {
          return k + " " + reasons[k];
        })
        .join(" · ");
    }
    if (tb) {
      tb.innerHTML = "";
      (result.rows || []).forEach(function (r) {
        const tr = document.createElement("tr");
        const cls = r.r > 0 ? "yes" : r.r < 0 ? "no" : "";
        tr.innerHTML =
          "<td>" +
          dash(r.entry_ts) +
          "</td><td>" +
          dash(r.mode) +
          "</td><td>" +
          dash(r.side) +
          "</td><td>" +
          dash(r.blast_pts) +
          "</td><td>" +
          dash(r.entry) +
          "</td><td>" +
          dash(r.sl) +
          "</td><td>" +
          dash(r.exit) +
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
          "</td>";
        tb.appendChild(tr);
      });
    }
  }

  function num(id, fallback) {
    const el = $(id);
    const v = el ? Number(el.value) : NaN;
    return Number.isFinite(v) ? v : fallback;
  }
  function chk(id, fallback) {
    const el = $(id);
    return el ? !!el.checked : fallback;
  }

  function collectBody() {
    return {
      symbol: ($("if-symbol") && $("if-symbol").value) || "XAUUSD",
      date_from: ($("if-from") && $("if-from").value) || "2026-06-01",
      date_to: ($("if-to") && $("if-to").value) || "2026-07-01",
      min_blast_pts: num("if-min-blast", 1100),
      snap_pts: num("if-snap", 300),
      window_sec: num("if-window", 3),
      snap_sec: num("if-snap-sec", 10),
      chase_ext: num("if-chase", 0.5),
      cooldown_sec: num("if-cooldown", 30),
      skip_london_utc: chk("if-london", true),
      london_start_hour: num("if-london-start", 7),
      london_end_hour: num("if-london-end", 10),
      fade_enabled: chk("if-fade", true),
      fade_lag_sec: num("if-fade-lag", 1),
      fade_sl_pct: num("if-fade-sl-pct", 100),
      fade_sl_cap_pts: num("if-fade-sl-cap", 1500),
      fade_tp_pct: num("if-fade-tp-pct", 200),
      fade_tp_cap_pts: num("if-fade-tp-cap", 3000),
      fade_trail_pts: num("if-fade-trail", 600),
      fade_trail_arm_pts: num("if-fade-arm", 750),
      fade_hold_sec: num("if-fade-hold", 250),
      join_enabled: chk("if-join", true),
      join_stop_beyond: num("if-join-stop", 0.15),
      join_tp1_r: num("if-join-tp1", 1),
      join_tp2_r: num("if-join-tp2", 1.5),
      join_be_r: num("if-join-be", 0.1),
      join_hold_sec: num("if-join-hold", 1200),
      join_retrace: num("if-join-retrace", 0.5),
      join_wait_sec: num("if-join-wait", 90),
      stand_aside_enabled: chk("if-aside", true),
      stand_aside_n: num("if-aside-n", 3),
      risk_pct: num("if-risk", 0.5),
      start_equity: num("if-equity", 1000),
      daily_halt_r: num("if-daily-halt", 1.5),
      weekly_halt_r: num("if-weekly-halt", 4),
      workers: num("if-workers", 3),
      force_download: chk("if-force", false),
    };
  }

  function applyFormFromResult(result) {
    if (!result) return;
    const p = result.params || {};
    if (result.date_from && $("if-from")) $("if-from").value = String(result.date_from).slice(0, 10);
    if (result.date_to && $("if-to")) $("if-to").value = String(result.date_to).slice(0, 10);
    const map = {
      min_blast_pts: "if-min-blast",
      snap_pts: "if-snap",
      window_sec: "if-window",
      snap_sec: "if-snap-sec",
      chase_ext: "if-chase",
      cooldown_sec: "if-cooldown",
      london_start_hour: "if-london-start",
      london_end_hour: "if-london-end",
      fade_lag_sec: "if-fade-lag",
      fade_sl_pct: "if-fade-sl-pct",
      fade_sl_cap_pts: "if-fade-sl-cap",
      fade_tp_pct: "if-fade-tp-pct",
      fade_tp_cap_pts: "if-fade-tp-cap",
      fade_trail_pts: "if-fade-trail",
      fade_trail_arm_pts: "if-fade-arm",
      fade_hold_sec: "if-fade-hold",
      join_stop_beyond: "if-join-stop",
      join_tp1_r: "if-join-tp1",
      join_tp2_r: "if-join-tp2",
      join_be_r: "if-join-be",
      join_hold_sec: "if-join-hold",
      join_retrace: "if-join-retrace",
      join_wait_sec: "if-join-wait",
      stand_aside_n: "if-aside-n",
      risk_pct: "if-risk",
      start_equity: "if-equity",
      daily_halt_r: "if-daily-halt",
      weekly_halt_r: "if-weekly-halt",
    };
    Object.keys(map).forEach(function (k) {
      if (p[k] == null || !$(map[k])) return;
      $(map[k]).value = String(p[k]);
    });
    if ($("if-fade")) $("if-fade").checked = p.fade_enabled !== false;
    if ($("if-join")) $("if-join").checked = p.join_enabled !== false;
    if ($("if-aside")) $("if-aside").checked = p.stand_aside_enabled !== false;
    if ($("if-london")) $("if-london").checked = p.skip_london_utc !== false;
    scheduleSave();
  }

  async function poll() {
    try {
      const r = await fetch("/api/impulse-fork");
      const data = await r.json();
      const running = !!data.running;
      const prog = data.progress || {};
      if ($("if-progress-bar")) $("if-progress-bar").style.width = (prog.pct || 0) + "%";
      if ($("if-progress-msg")) $("if-progress-msg").textContent = prog.message || (running ? "Running…" : "Idle");
      if ($("if-run")) $("if-run").disabled = running;
      if ($("if-stop")) $("if-stop").disabled = !running;
      if (data.result && (!running || wasRunning) && !savedPicker.isViewingSaved()) render(data.result);
      if (wasRunning && !running) {
        if (prog.phase === "done" && window.StrategSaved && window.StrategSaved.playDone) {
          window.StrategSaved.playDone();
        }
        if (savedPicker.refresh) savedPicker.refresh();
      }
      wasRunning = running;
    } catch (e) {
      console.error(e);
    }
  }

  function wireRun() {
    if ($("if-run")) {
      $("if-run").addEventListener("click", async function () {
        if (savedPicker.clearViewing) savedPicker.clearViewing();
        $("if-run").disabled = true;
        try {
          const r = await fetch("/api/impulse-fork/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(collectBody()),
          });
          if (!r.ok) {
            const err = await r.json().catch(function () {
              return {};
            });
            alert(err.detail || "Could not start");
            $("if-run").disabled = false;
            return;
          }
          wasRunning = true;
          if (pollTimer) clearInterval(pollTimer);
          pollTimer = setInterval(poll, 800);
          poll();
        } catch (e) {
          alert(String(e));
          $("if-run").disabled = false;
        }
      });
    }
    if ($("if-stop")) {
      $("if-stop").addEventListener("click", async function () {
        try {
          await fetch("/api/impulse-fork/stop", { method: "POST" });
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
      kind: "impulse_fork",
      selectId: "if-saved",
      buttonId: "if-load",
      onLoaded: function (json) {
        applyFormFromResult(json);
        render(json);
      },
    });
  }
  poll();
  if (!pollTimer) pollTimer = setInterval(poll, 2000);
})();
