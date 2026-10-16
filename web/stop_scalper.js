(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_stop_scalper_v1";
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
    "ss-symbol",
    "ss-from",
    "ss-to",
    "ss-tz",
    "ss-entry",
    "ss-sl",
    "ss-trail",
    "ss-arm",
    "ss-be",
    "ss-lock-arm",
    "ss-lock",
    "ss-tp",
    "ss-spread",
    "ss-max-spread",
    "ss-reverse-on",
    "ss-force",
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
      console.warn("stop scalper save failed", e);
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
      console.warn("stop scalper load failed", e);
    }
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="stop-scalper"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "stop-scalper");
      btn.textContent = "Stop Scalper";
      nav.appendChild(btn);
    }
    if ($("tab-stop-scalper")) return;

    const panel = document.createElement("div");
    panel.id = "tab-stop-scalper";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Stop Scalper</h2>
      <ol>
        <li>On each new 1-minute bar, while flat, place a <strong>buy stop</strong> and a <strong>sell stop</strong> the entry distance from that bar's open.</li>
        <li>The first stop the bar trades is the fill. The other order is deleted.</li>
        <li>The safety stop is the SL. Auto BE moves it to the entry. The profit lock moves it past the entry after a larger gain. Trailing starts after the arm. A fixed target closes at that profit. <strong>0</strong> turns a rule off. The tighter stop wins.</li>
        <li>Reversal can follow any close, or only a safety-stop exit. A target, lock, break-even, or trail exit then waits for the next bar. A spread above the cap skips new entries. The candle test uses one spread for the whole run and charges it on the entry.</li>
      </ol>
      <p class="hint">The tester walks each 1-minute bar open → low → high → close when the close is at or above the open, and open → high → low → close otherwise. Fills are on the candle price. On gold and bitcoin, 1 point is $0.01. On an FX major, 1 point is 0.1 pip. The same rules are in <code>mql5/ScalperProV2.mq5</code>.</p>
    </section>
    <section class="card scalp-box">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="ss-symbol" title="FX majors: 1 point = 0.1 pip. Gold and bitcoin: 1 point = $0.01.">
            ${window.strategSymbols.optionsHtml()}
          </select>
        </label>
        <label>From
          <input type="date" id="ss-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="ss-to" value="2025-06-01" />
        </label>
        <label>Timezone
          <input id="ss-tz" value="Europe/Chisinau" title="Entry and exit stamps use this zone. The strategy itself trades whenever the market is open." />
        </label>
        <label>Entry distance (pts)
          <input type="number" id="ss-entry" value="50" min="1" step="1"
            title="Buy stop this many points above the bar open. Sell stop the same distance below." />
        </label>
        <label>Safety SL (pts)
          <input type="number" id="ss-sl" value="500" min="1" step="10"
            title="Initial stop. Default 500 points." />
        </label>
        <label>Trailing stop (pts)
          <input type="number" id="ss-trail" value="100" min="0" step="10"
            title="Distance behind the best price once the trail is armed. 0 = off." />
        </label>
        <label>Trailing arm (pts)
          <input type="number" id="ss-arm" value="200" min="0" step="10"
            title="Profit required before the trail starts. 0 = arm once profit reaches the trailing distance." />
        </label>
        <label>Auto BE (pts)
          <input type="number" id="ss-be" value="0" min="0" step="10"
            title="Move the stop to the entry after this much profit. 0 = off." />
        </label>
        <label>Lock arm (pts)
          <input type="number" id="ss-lock-arm" value="300" min="0" step="10"
            title="Profit required before the stop locks in profit. 0 = off." />
        </label>
        <label>Lock profit (pts)
          <input type="number" id="ss-lock" value="100" min="0" step="10"
            title="Once the lock arms, park the stop this many points past the entry." />
        </label>
        <label>Target (pts)
          <input type="number" id="ss-tp" value="0" min="0" step="10"
            title="Fixed take profit. 0 = off. Try 250, then 400, with the trail off." />
        </label>
        <label>Spread (pts)
          <input type="number" id="ss-spread" value="20" min="0" step="1"
            title="Charged on every entry. Candles have no live spread, so this one number is used for the whole run." />
        </label>
        <label>Max spread (pts)
          <input type="number" id="ss-max-spread" value="20" min="0" step="1"
            title="Skip new entries when the spread is wider than this. 0 = no cap." />
        </label>
        <label>Reversal
          <select id="ss-reverse-on" title="A reversal does not reverse again.">
            <option value="sl" selected>Only after safety stop</option>
            <option value="close">After any close</option>
            <option value="off">Off</option>
          </select>
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="ss-run">Run Stop Scalper</button>
        <button type="button" class="secondary" id="ss-stop" disabled>Stop</button>
        <label class="chk force"><input type="checkbox" id="ss-force" /> Force re-download</label>
      </div>
    </section>
    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap"><div class="progress-bar" id="ss-bar" style="width:0%"></div></div>
      <p class="progress-msg" id="ss-msg">Idle</p>
    </section>
    <section class="card" id="ss-results">
      <div class="results-head">
        <h2>Results</h2>
        <div class="saved-load">
          <select id="ss-saved" title="Open a saved Stop Scalper run from results/"></select>
          <button type="button" class="secondary" id="ss-load">Load</button>
        </div>
      </div>
      <p class="muted" id="ss-meta">No run yet.</p>
      <div class="hero-grid" id="ss-hero"></div>
      <h3>Stop entry vs reversal</h3>
      <div class="table-wrap">
        <table id="ss-origin">
          <thead>
            <tr>
              <th>Origin</th><th>Trades</th><th>Win %</th><th>Sum pts</th><th>Avg pts</th><th>PF</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Streaks</h3>
      <p class="table-note">Consecutive wins / losses in fill order. A scratch (0 pts) breaks the run.</p>
      <div class="hero-grid" id="ss-streaks-hero"></div>
      <h3>By month</h3>
      <div class="table-wrap">
        <table id="ss-months">
          <thead>
            <tr>
              <th>Month</th><th>Trades</th><th>Win %</th><th>Sum pts</th><th>Avg pts</th><th>PF</th>
              <th>Avg win</th><th>Avg loss</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Trades</h3>
      <p class="table-note" id="ss-rows-note">Entry and exit times are local to the run timezone. Stop is the stop that was active at the exit.</p>
      <div class="table-wrap">
        <table id="ss-table">
          <thead>
            <tr>
              <th>Entry time</th><th>Origin</th><th>Side</th><th>Entry</th><th>Stop</th>
              <th>Exit time</th><th>Exit</th><th>Why</th><th>Fav</th><th>Pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;

    const foot = document.querySelector("footer.foot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("Stop Scalper") < 0) {
      foot.textContent += " Stop Scalper = buy and sell stops near price, then one reversal.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-stop-scalper");
        if (tab === "stop-scalper") {
          document.querySelectorAll(".tab-panel").forEach(function (p) {
            p.classList.add("hidden");
          });
          if (panel) panel.classList.remove("hidden");
          document.querySelectorAll(".main-tab").forEach(function (b) {
            b.classList.remove("active");
          });
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "stop-scalper");
          } catch (e) {}
          return;
        }
        if (panel) panel.classList.add("hidden");
      });
    });
    try {
      if (localStorage.getItem("strateg_tab") === "stop-scalper") {
        const btn = document.querySelector('.main-tab[data-tab="stop-scalper"]');
        if (btn) btn.click();
      }
    } catch (e) {}
  }

  function px(symbol, n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return "—";
    const s = String(symbol || "").toUpperCase();
    const d = s.indexOf("JPY") >= 0 ? 3 : s.indexOf("XAU") >= 0 || s.indexOf("BTC") >= 0 ? 2 : 5;
    return x.toFixed(d);
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

  function dash(v) {
    return v == null || v === "" ? "—" : v;
  }

  function sideLabel(side) {
    return side === "UP" ? "buy" : side === "DOWN" ? "sell" : side || "";
  }

  function render(result) {
    if (!result) return;
    const sym = result.symbol || "";
    const p = result.params || {};
    if ($("ss-meta")) {
      $("ss-meta").textContent =
        (result.name || "Stop Scalper") +
        " · " +
        sym +
        " · " +
        (result.date_from || "") +
        " → " +
        (result.date_to || "") +
        " · entry " +
        (p.entry_pts != null ? p.entry_pts : "—") +
        " · SL " +
        (p.sl_pts != null ? p.sl_pts : "—") +
        " · trail " +
        (p.trail_pts != null ? p.trail_pts : "—") +
        " / arm " +
        (p.trail_arm_pts != null ? p.trail_arm_pts : "—") +
        " · BE " +
        (p.be_pts != null ? p.be_pts : "—") +
        " · lock " +
        (p.lock_arm_pts || 0) +
        "/" +
        (p.lock_pts || 0) +
        " · TP " +
        (p.tp_pts || 0) +
        " · spread " +
        (p.spread_pts || 0) +
        "/" +
        (p.max_spread_pts || 0) +
        (p.reverse === false ? " · no reverse" : p.reverse_on === "sl" ? " · reverse on stop" : " · reverse") +
        " · " +
        (result.bars || 0) +
        " bars";
    }
    const hero = $("ss-hero");
    if (hero) {
      const pf = result.profit_factor == null ? "—" : result.profit_factor;
      const winPct = result.win_pct != null ? result.win_pct : Math.round((result.win_rate || 0) * 100);
      hero.innerHTML =
        heroItem("Trades", result.trades || 0) +
        heroItem("Win %", winPct + "%") +
        heroItem("Points", result.sum_pts || 0) +
        heroItem("PF", pf);
    }
    const streaks = result.streaks || {};
    const streakHero = $("ss-streaks-hero");
    if (streakHero) {
      const current = streaks.current;
      streakHero.innerHTML =
        heroItem("Max win streak", streaks.max_win || 0) +
        heroItem("Max loss streak", streaks.max_loss || 0) +
        heroItem("Win streaks", streaks.win_streaks || 0) +
        heroItem(
          "Current",
          current ? current.len + " " + current.side : "—"
        );
    }
    const originBody = document.querySelector("#ss-origin tbody");
    if (originBody) {
      originBody.innerHTML = "";
      (result.by_origin || []).forEach(function (row) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          (row.origin === "stop" ? "Stop entry" : "Reversal") +
          "</td><td>" +
          (row.trades || 0) +
          "</td><td>" +
          dash(row.win_pct) +
          "</td><td>" +
          dash(row.sum_pts) +
          "</td><td>" +
          dash(row.avg_pts) +
          "</td><td>" +
          dash(row.profit_factor) +
          "</td>";
        originBody.appendChild(tr);
      });
    }
    const monthBody = document.querySelector("#ss-months tbody");
    if (monthBody) {
      monthBody.innerHTML = "";
      (result.by_month || []).forEach(function (m) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          (m.month || "") +
          "</td><td>" +
          (m.trades || 0) +
          "</td><td>" +
          dash(m.win_pct) +
          "</td><td>" +
          dash(m.sum_pts) +
          "</td><td>" +
          dash(m.avg_pts) +
          "</td><td>" +
          dash(m.profit_factor) +
          "</td><td>" +
          dash(m.avg_win_pts) +
          "</td><td>" +
          dash(m.avg_loss_pts) +
          "</td>";
        monthBody.appendChild(tr);
      });
    }
    const note = $("ss-rows-note");
    if (note) {
      const shown = (result.rows || []).length;
      const total = result.row_count || result.trades || shown;
      note.textContent = result.rows_truncated
        ? "Showing the first " +
          shown +
          " of " +
          total +
          " trades. Totals above use the full run. Entry and exit times are local to the run timezone."
        : "Entry and exit times are local to the run timezone. Stop is the stop that was active at the exit.";
    }
    const tb = document.querySelector("#ss-table tbody");
    if (!tb) return;
    tb.innerHTML = "";
    (result.rows || []).forEach(function (t) {
      const tr = document.createElement("tr");
      const pts = Number(t.pts) || 0;
      tr.innerHTML =
        "<td>" +
        (t.entry_local || "") +
        "</td><td>" +
        (t.origin === "reverse" ? "reversal" : "stop") +
        "</td><td>" +
        sideLabel(t.side) +
        "</td><td>" +
        px(sym, t.entry) +
        "</td><td>" +
        px(sym, t.sl) +
        "</td><td>" +
        (t.exit_local || "—") +
        "</td><td>" +
        px(sym, t.exit) +
        "</td><td>" +
        (t.exit_reason || "") +
        "</td><td>" +
        dash(t.max_fav_pts) +
        '</td><td class="' +
        (pts >= 0 ? "ab-win" : "ab-loss") +
        '">' +
        pts +
        "</td>";
      tb.appendChild(tr);
    });
  }

  async function poll() {
    try {
      const r = await fetch("/api/stop-scalper");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if ($("ss-bar")) $("ss-bar").style.width = (p.pct || 0) + "%";
      if ($("ss-msg")) $("ss-msg").textContent = p.message || (running ? "Running…" : "Idle");
      if ($("ss-run")) $("ss-run").disabled = running;
      if ($("ss-stop")) $("ss-stop").disabled = !running;
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "scalp";
        badge.className = "badge run";
      }
      if (wasRunning && !running && p.phase === "done") {
        if (badge) {
          badge.textContent = "done";
          badge.className = "badge done";
        }
        const full = await fetch("/api/stop-scalper?rows=1&limit=2000");
        const done = await full.json();
        if (done.result) render(done.result);
        if (window.StrategSaved && window.StrategSaved.playDone) window.StrategSaved.playDone();
        if (savedPicker.refresh) savedPicker.refresh();
      } else if (!running && st.result && p.phase === "done" && !(st.result.rows || []).length) {
        const full = await fetch("/api/stop-scalper?rows=1&limit=2000");
        const done = await full.json();
        if (done.result) render(done.result);
      } else if (st.result && (st.result.rows || []).length) {
        render(st.result);
      }
      if (p.phase === "error" && badge) {
        badge.textContent = "err";
        badge.className = "badge err";
        if ($("ss-msg")) $("ss-msg").textContent = p.message || "Error";
      }
      wasRunning = running;
      if (!running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (e) {
      console.warn("stop scalper poll", e);
    }
  }

  function num(id, fallback) {
    const n = parseFloat($(id) && $(id).value);
    return Number.isFinite(n) ? n : fallback;
  }

  ensureTab();
  loadForm();
  FORM_IDS.forEach(function (id) {
    const el = $(id);
    if (!el) return;
    el.addEventListener("change", scheduleSave);
    el.addEventListener("input", scheduleSave);
  });
  wireTabs();
  if (window.StrategSaved) {
    savedPicker = window.StrategSaved.bindPicker({
      kind: "stop_scalper",
      selectId: "ss-saved",
      buttonId: "ss-load",
      onLoaded: function (json) {
        render(json);
        if ($("ss-msg")) $("ss-msg").textContent = "Loaded saved run";
      },
    });
  }
  if ($("ss-run")) {
    $("ss-run").addEventListener("click", async function () {
      const body = {
        symbol: $("ss-symbol").value,
        date_from: $("ss-from").value,
        date_to: $("ss-to").value,
        timezone: $("ss-tz").value || "Europe/Chisinau",
        entry_pts: num("ss-entry", 50),
        sl_pts: num("ss-sl", 500),
        trail_pts: num("ss-trail", 100),
        trail_arm_pts: num("ss-arm", 200),
        be_pts: num("ss-be", 0),
        lock_arm_pts: num("ss-lock-arm", 300),
        lock_pts: num("ss-lock", 100),
        tp_pts: num("ss-tp", 0),
        spread_pts: num("ss-spread", 20),
        max_spread_pts: num("ss-max-spread", 20),
        reverse: ($("ss-reverse-on") ? $("ss-reverse-on").value : "sl") !== "off",
        reverse_on: ($("ss-reverse-on") && $("ss-reverse-on").value === "close") ? "close" : "sl",
        force_download: !!($("ss-force") && $("ss-force").checked),
      };
      saveForm();
      if (savedPicker.clearViewing) savedPicker.clearViewing();
      $("ss-run").disabled = true;
      if ($("ss-msg")) $("ss-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/stop-scalper/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(function () {
            return {};
          });
          alert(err.detail || "Could not start");
          $("ss-run").disabled = false;
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
        $("ss-run").disabled = false;
      }
    });
  }
  if ($("ss-stop")) {
    $("ss-stop").addEventListener("click", async function () {
      $("ss-stop").disabled = true;
      try {
        await fetch("/api/stop-scalper/stop", { method: "POST" });
        if (!pollTimer) pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
      }
    });
  }
  poll();
})();
