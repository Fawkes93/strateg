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
    "if-fade",
    "if-join",
    "if-aside",
    "if-london",
    "if-risk",
    "if-equity",
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
        <li>Detect a 3s gold blast (≥ min pts).</li>
        <li>If it <strong>snaps back</strong> ≥ snap pts in 10s → <em>Fade</em> the extreme.</li>
        <li>If it holds, then retraces ~50% without taking the origin → <em>Join</em> the blast.</li>
        <li>Three one-way blasts → stand aside until a snapback. Never fade and join the same blast.</li>
      </ol>
      <p class="hint">
        Not an Asia box. News days are allowed. Optional skip 07:00–10:00 UTC so the live Asia bot owns London morning.
        Judge PF / avg R / max DD, and Fade vs Join split. Kill Join if its PF &lt; 1.
      </p>
    </section>
    <section class="card">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="if-symbol"><option value="XAUUSD" selected>XAUUSD (gold)</option></select>
        </label>
        <label>From <input type="date" id="if-from" value="2026-06-01" /></label>
        <label>To (exclusive) <input type="date" id="if-to" value="2026-07-01" /></label>
        <label>Min blast (pts)
          <input type="number" id="if-min-blast" value="1100" min="400" step="50" />
        </label>
        <label>Snapback (pts)
          <input type="number" id="if-snap" value="300" min="50" step="50" />
        </label>
        <label class="chk">Fade <input type="checkbox" id="if-fade" checked /></label>
        <label class="chk">Join <input type="checkbox" id="if-join" checked /></label>
        <label class="chk">Stand aside <input type="checkbox" id="if-aside" checked /></label>
        <label class="chk">Skip London 07–10 UTC
          <input type="checkbox" id="if-london" checked />
        </label>
        <label>Risk % equity
          <input type="number" id="if-risk" value="0.5" min="0.1" max="20" step="0.1" />
        </label>
        <label>Start equity
          <input type="number" id="if-equity" value="1000" min="100" step="100" />
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

  function collectBody() {
    return {
      symbol: ($("if-symbol") && $("if-symbol").value) || "XAUUSD",
      date_from: ($("if-from") && $("if-from").value) || "2026-06-01",
      date_to: ($("if-to") && $("if-to").value) || "2026-07-01",
      min_blast_pts: Number($("if-min-blast") && $("if-min-blast").value) || 1100,
      snap_pts: Number($("if-snap") && $("if-snap").value) || 300,
      fade_enabled: !!($("if-fade") && $("if-fade").checked),
      join_enabled: !!($("if-join") && $("if-join").checked),
      stand_aside_enabled: !!($("if-aside") && $("if-aside").checked),
      skip_london_utc: !!($("if-london") && $("if-london").checked),
      risk_pct: Number($("if-risk") && $("if-risk").value) || 0.5,
      start_equity: Number($("if-equity") && $("if-equity").value) || 1000,
      workers: Number($("if-workers") && $("if-workers").value) || 3,
      force_download: !!($("if-force") && $("if-force").checked),
    };
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
        render(json);
      },
    });
  }
  poll();
  if (!pollTimer) pollTimer = setInterval(poll, 2000);
})();
