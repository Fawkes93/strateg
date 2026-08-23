(function () {
  const $ = (id) => document.getElementById(id);
  let pollTimer = null;
  let wasRunning = false;

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
        <li>First completed 15m close outside the range by min break pts = break signal.</li>
        <li>Entry = first of: <em>EMA touch</em> or <em>higher/lower close resume</em> during the wait window (or break close if pullback = off).</li>
        <li>No partial TP. Trail arms after profit, then trails. Flatten at local hour.</li>
      </ol>
      <p class="hint">
        Mid fill. One trade per day by default. Skips days with no valid break / no pullback (required mode).
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
        <label>Side filter
          <select id="ob-side">
            <option value="both" selected>both</option>
            <option value="long">long only</option>
            <option value="short">short only</option>
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
        <label>Trail arm (pts profit)
          <input type="number" id="ob-trail-arm" value="400" min="0" step="50" />
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
      </div>
      <div class="actions">
        <button type="button" class="primary" id="ob-run">Run overnight break</button>
        <label class="chk force">
          <input type="checkbox" id="ob-force" /> Force re-download
        </label>
      </div>
    </section>

    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap">
        <div class="progress-bar" id="ob-progress-bar" style="width:0%"></div>
      </div>
      <p class="progress-msg" id="ob-progress-msg">Idle</p>
    </section>

    <section class="card" id="ob-results-card">
      <h2>Results</h2>
      <p class="muted" id="ob-meta">No run yet.</p>
      <div class="hero-grid" id="ob-hero"></div>
      <h3>Trades</h3>
      <div class="table-wrap">
        <table id="ob-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Side</th>
              <th>Asia range</th>
              <th>Entry reason</th>
              <th>Entry</th>
              <th>SL pts</th>
              <th>TP pts</th>
              <th>Exit</th>
              <th>Reason</th>
              <th>Trail</th>
              <th>Max fav</th>
              <th>Pts</th>
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
          ["tab-research", "tab-sweep", "tab-session", "tab-spikefade"].forEach((id) => {
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

  function heroItem(label, value) {
    return (
      '<div class="hero"><div class="k">' +
      label +
      '</div><div class="v">' +
      (value == null ? "—" : value) +
      "</div></div>"
    );
  }

  function render(result) {
    const meta = $("ob-meta");
    const hero = $("ob-hero");
    const tb = $("ob-table") && $("ob-table").querySelector("tbody");
    if (!result) {
      if (meta) meta.textContent = "No run yet.";
      if (hero) hero.innerHTML = "";
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
        " skipped · avg " +
        (result.avg_pts != null ? result.avg_pts : "—") +
        " pts";
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
    if (!tb) return;
    tb.innerHTML = "";
    const rows = result.rows || [];
    if (!rows.length) {
      tb.innerHTML =
        '<tr><td colspan="12" class="muted">No trades in this window</td></tr>';
      return;
    }
    rows.forEach(function (t) {
      const tr = document.createElement("tr");
      const ptsClass = t.pts > 0 ? "yes" : t.pts < 0 ? "no" : "";
      tr.innerHTML =
        "<td>" +
        t.local_date +
        "</td><td>" +
        t.side +
        "</td><td>" +
        t.asia_range_pts +
        "</td><td>" +
        (t.entry_reason || "—") +
        "</td><td>" +
        t.entry +
        "</td><td>" +
        t.sl_pts +
        "</td><td>" +
        t.tp_pts +
        "</td><td>" +
        (t.exit != null ? t.exit : "—") +
        "</td><td>" +
        (t.exit_reason || "—") +
        "</td><td>" +
        (t.trail_armed ? "Y" : "") +
        "</td><td>" +
        (t.max_fav_pts != null ? t.max_fav_pts : "—") +
        '</td><td class="' +
        ptsClass +
        '">' +
        t.pts +
        "</td>";
      tb.appendChild(tr);
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
      if (st.result) render(st.result);
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
        max_break_candles_after: Number($("ob-max-break-candles").value),
        pullback_mode: $("ob-pullback-mode").value,
        ema_period: Number($("ob-ema").value),
        max_wait_candles: Number($("ob-max-wait").value),
        timeout_action: $("ob-timeout").value,
        use_higher_close: $("ob-higher-close") && $("ob-higher-close").checked,
        sl_mode: $("ob-sl-mode").value,
        sl_fixed_pts: Number($("ob-sl-fixed").value),
        sl_range_mult: Number($("ob-sl-range-mult").value),
        tp_mode: $("ob-tp-mode").value,
        tp_fixed_pts: Number($("ob-tp-fixed").value),
        tp_range_mult: Number($("ob-tp-range-mult").value),
        tp_r_mult: Number($("ob-tp-r-mult").value),
        trail_arm_pts: Number($("ob-trail-arm").value),
        trail_pts: Number($("ob-trail").value),
        max_hold_hours: Number($("ob-max-hold").value),
        flatten_hour: Number($("ob-flatten").value),
        one_trade_per_day: $("ob-one-per-day") && $("ob-one-per-day").checked,
        side_filter: $("ob-side").value,
        force_download: $("ob-force") && $("ob-force").checked,
      };
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
  wireTabs();
  wireRun();
  poll();
})();
