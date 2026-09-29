(function () {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "strateg_dawn_cross_v1";
  let pollTimer = null;
  let wasRunning = false;
  let saveTimer = null;

  const FORM_IDS = [
    "dx-symbol",
    "dx-from",
    "dx-to",
    "dx-tz",
    "dx-start",
    "dx-start-min",
    "dx-end",
    "dx-end-min",
    "dx-fast",
    "dx-slow",
    "dx-pull",
    "dx-sl",
    "dx-tp",
    "dx-flat",
    "dx-one-per-day",
    "dx-force",
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
      console.warn("dawn cross save failed", e);
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
      console.warn("dawn cross load failed", e);
    }
  }

  function ensureTab() {
    const nav = document.querySelector(".main-tabs");
    if (nav && !document.querySelector('.main-tab[data-tab="dawn-cross"]')) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "main-tab";
      btn.setAttribute("data-tab", "dawn-cross");
      btn.textContent = "Dawn Cross";
      nav.appendChild(btn);
    }
    if ($("tab-dawn-cross")) return;

    const panel = document.createElement("div");
    panel.id = "tab-dawn-cross";
    panel.className = "tab-panel hidden";
    panel.innerHTML = `
    <section class="card pipeline">
      <h2>Dawn Cross</h2>
      <ol>
        <li>Watch the local window below (default <strong>02:00–06:00 Europe/Chisinau</strong>) on 5-minute candles.</li>
        <li>Fast EMA crossing above the slow EMA arms a buy. A downward cross arms a sell.</li>
        <li>The fill waits for a later bar in that window to tag the pullback EMA.</li>
        <li>Stop and target are fixed distances in points. Open trades flatten at the local hour below.</li>
      </ol>
      <p class="hint">One position at a time. If the pullback never tags the EMA before the window ends, that cross is dropped. Same-bar stop and target counts as a stop. On an FX major, 1 point is 0.1 pip. Gold and bitcoin use $0.01 per point. Stop and target stay as entered.</p>
    </section>
    <section class="card dawn-box">
      <h2>Parameters</h2>
      <div class="grid">
        <label>Symbol
          <select id="dx-symbol" title="FX majors: 1 point = 0.1 pip. Gold and bitcoin: 1 point = $0.01.">
            ${window.strategSymbols.optionsHtml()}
          </select>
        </label>
        <label>From
          <input type="date" id="dx-from" value="2025-05-01" />
        </label>
        <label>To (exclusive)
          <input type="date" id="dx-to" value="2025-08-01" />
        </label>
        <label>Timezone
          <input id="dx-tz" value="Europe/Chisinau" />
        </label>
        <label>Window start
          <span class="hm">
            <input type="number" id="dx-start" value="2" min="0" max="23" step="1" title="Hour" />
            <span class="hm-colon">:</span>
            <input type="number" id="dx-start-min" value="0" min="0" max="59" step="1" title="Minute" />
          </span>
        </label>
        <label>Window end
          <span class="hm">
            <input type="number" id="dx-end" value="6" min="0" max="23" step="1" title="Hour. The end is exclusive." />
            <span class="hm-colon">:</span>
            <input type="number" id="dx-end-min" value="0" min="0" max="59" step="1" title="Minute. 06:00 means the 06:00 bar is outside the window." />
          </span>
        </label>
        <label>Fast EMA
          <input type="number" id="dx-fast" value="9" min="1" max="200" />
        </label>
        <label>Slow EMA
          <input type="number" id="dx-slow" value="20" min="1" max="200" />
        </label>
        <label>Pullback EMA
          <input type="number" id="dx-pull" value="9" min="1" max="200"
            title="Fill when a later 5m bar in the window trades this EMA. Default is the fast EMA." />
        </label>
        <label>Stop (pts)
          <input type="number" id="dx-sl" value="400" min="1" step="10" />
        </label>
        <label>Target (pts)
          <input type="number" id="dx-tp" value="800" min="1" step="10" />
        </label>
        <label>Flatten hour
          <input type="number" id="dx-flat" value="12" min="0" max="23"
            title="Exit at the open of the first 5m bar in this local hour. 0 = hold for stop or target only." />
        </label>
        <label class="chk">One trade per day
          <input type="checkbox" id="dx-one-per-day" checked
            title="After a fill, ignore later crosses on that local date." />
        </label>
      </div>
      <div class="actions">
        <button type="button" class="primary" id="dx-run">Run Dawn Cross</button>
        <button type="button" class="secondary" id="dx-stop" disabled>Stop</button>
        <label class="chk force"><input type="checkbox" id="dx-force" /> Force re-download</label>
      </div>
    </section>
    <section class="card">
      <h2>Progress</h2>
      <div class="progress-wrap"><div class="progress-bar" id="dx-bar" style="width:0%"></div></div>
      <p class="progress-msg" id="dx-msg">Idle</p>
    </section>
    <section class="card" id="dx-results">
      <h2>Results</h2>
      <p class="muted" id="dx-meta">No run yet.</p>
      <div class="hero-grid" id="dx-hero"></div>
      <h3>Streaks</h3>
      <p class="table-note">
        Consecutive wins / losses in date order. A scratch (0 pts) breaks the run.
        Count = how many streaks of that length.
      </p>
      <div class="hero-grid" id="dx-streaks-hero"></div>
      <div class="table-wrap">
        <table id="dx-streaks">
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
        <table id="dx-months">
          <thead>
            <tr>
              <th>Month</th>
              <th>Trades</th>
              <th>Win %</th>
              <th>Sum pts</th>
              <th>Avg pts</th>
              <th>PF</th>
              <th>Avg win</th>
              <th>Avg loss</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <h3>Trades</h3>
      <p class="table-note">Entry and exit times are local to the run timezone.</p>
      <div class="table-wrap">
        <table id="dx-table">
          <thead>
            <tr>
              <th>Entry time</th><th>Side</th><th>Entry</th><th>SL</th><th>TP</th>
              <th>Exit time</th><th>Exit</th><th>Why</th><th>Pts</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>`;

    const foot = document.querySelector("footer.foot");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(panel, foot);
    else document.body.appendChild(panel);
    if (foot && foot.textContent.indexOf("Dawn Cross") < 0) {
      foot.textContent += " Dawn Cross = 2–6am Moldova EMA cross, pullback fill.";
    }
  }

  function wireTabs() {
    document.querySelectorAll(".main-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-tab");
        const panel = $("tab-dawn-cross");
        if (panel) panel.classList.toggle("hidden", tab !== "dawn-cross");
        if (tab === "dawn-cross") {
          [
            "tab-research",
            "tab-sweep",
            "tab-session",
            "tab-spikefade",
            "tab-micro",
            "tab-burst",
            "tab-cooloff",
            "tab-fvg",
            "tab-asia-liq",
            "tab-impulse-fork",
            "tab-overnight",
            "tab-asia-box",
          ].forEach(function (id) {
            const el = $(id);
            if (el) el.classList.add("hidden");
          });
          document.querySelectorAll(".main-tab").forEach(function (b) {
            b.classList.remove("active");
          });
          btn.classList.add("active");
          try {
            localStorage.setItem("strateg_tab", "dawn-cross");
          } catch (e) {}
        }
      });
    });
    try {
      if (localStorage.getItem("strateg_tab") === "dawn-cross") {
        const btn = document.querySelector('.main-tab[data-tab="dawn-cross"]');
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

  function clock(hour, minute) {
    const h = Number(hour);
    const m = Number(minute);
    return (
      String(Number.isFinite(h) ? h : 0).padStart(2, "0") +
      ":" +
      String(Number.isFinite(m) ? m : 0).padStart(2, "0")
    );
  }

  function windowLabel(params) {
    const p = params || {};
    if (p.window_start_hour == null && p.window_end_hour == null) return "";
    return clock(p.window_start_hour, p.window_start_minute) + "–" + clock(p.window_end_hour, p.window_end_minute);
  }

  function formatLocal(iso, tz) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso).replace("T", " ").slice(0, 16);
    try {
      const fmt = new Intl.DateTimeFormat("en-CA", {
        timeZone: tz || "Europe/Chisinau",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      });
      const parts = fmt.formatToParts(d);
      const get = function (type) {
        const hit = parts.find(function (p) {
          return p.type === type;
        });
        return hit ? hit.value : "";
      };
      return get("year") + "-" + get("month") + "-" + get("day") + " " + get("hour") + ":" + get("minute");
    } catch (e) {
      return String(iso).replace("T", " ").slice(0, 16);
    }
  }

  function tradeStamp(row, which, tz) {
    const localKey = which === "exit" ? "exit_local" : "entry_local";
    const isoKey = which === "exit" ? "exit_ts" : "entry_ts";
    if (row && row[localKey]) return row[localKey];
    const formatted = formatLocal(row && row[isoKey], tz);
    if (formatted) return formatted;
    return which === "exit" ? "" : (row && row.local_date) || "";
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

  function computeStreaks(rows) {
    const ordered = (rows || []).slice().sort(function (a, b) {
      const da = String(a.local_date || "");
      const db = String(b.local_date || "");
      if (da !== db) return da < db ? -1 : 1;
      const ea = String(a.entry_ts || "");
      const eb = String(b.entry_ts || "");
      if (ea !== eb) return ea < eb ? -1 : 1;
      return 0;
    });
    const winBy = {};
    const lossBy = {};
    let maxWin = 0;
    let maxLoss = 0;
    let curSide = null;
    let curLen = 0;
    function closeRun() {
      if (curSide === "win" && curLen) {
        winBy[curLen] = (winBy[curLen] || 0) + 1;
        if (curLen > maxWin) maxWin = curLen;
      } else if (curSide === "loss" && curLen) {
        lossBy[curLen] = (lossBy[curLen] || 0) + 1;
        if (curLen > maxLoss) maxLoss = curLen;
      }
    }
    ordered.forEach(function (t) {
      const pts = Number(t.pts) || 0;
      const kind = pts > 1e-9 ? "win" : pts < -1e-9 ? "loss" : null;
      if (!kind) {
        closeRun();
        curSide = null;
        curLen = 0;
        return;
      }
      if (kind === curSide) curLen += 1;
      else {
        closeRun();
        curSide = kind;
        curLen = 1;
      }
    });
    closeRun();
    const winStreaks = Object.keys(winBy).reduce(function (n, k) {
      return n + winBy[k];
    }, 0);
    const lossStreaks = Object.keys(lossBy).reduce(function (n, k) {
      return n + lossBy[k];
    }, 0);
    return {
      max_win: maxWin,
      max_loss: maxLoss,
      win_streaks: winStreaks,
      loss_streaks: lossStreaks,
      win_by_len: winBy,
      loss_by_len: lossBy,
      current: curSide && curLen ? { side: curSide, len: curLen } : null,
    };
  }

  function statsOf(rows) {
    let wins = 0;
    let losses = 0;
    let gross = 0;
    let loss = 0;
    let sum = 0;
    (rows || []).forEach(function (t) {
      const pts = Number(t.pts) || 0;
      sum += pts;
      if (pts > 1e-9) {
        wins += 1;
        gross += pts;
      } else if (pts < -1e-9) {
        losses += 1;
        loss += -pts;
      }
    });
    const n = (rows || []).length;
    let pf = 0;
    if (loss > 1e-9) pf = Math.round((gross / loss) * 100) / 100;
    else if (gross > 0) pf = null;
    return {
      trades: n,
      wins: wins,
      win_pct: n ? Math.round((1000 * wins) / n) / 10 : null,
      sum_pts: Math.round(sum * 10) / 10,
      avg_pts: n ? Math.round((sum / n) * 10) / 10 : 0,
      avg_win_pts: wins ? Math.round((gross / wins) * 10) / 10 : null,
      avg_loss_pts: losses ? Math.round((-loss / losses) * 10) / 10 : null,
      profit_factor: pf,
    };
  }

  function monthKey(row) {
    const s = String((row && (row.local_date || row.entry_local)) || "");
    return s.length >= 7 ? s.slice(0, 7) : "unknown";
  }

  function computeMonths(rows) {
    const groups = {};
    (rows || []).forEach(function (t) {
      const key = monthKey(t);
      if (!groups[key]) groups[key] = [];
      groups[key].push(t);
    });
    return Object.keys(groups)
      .sort()
      .map(function (ym) {
        const row = statsOf(groups[ym]);
        row.month = ym;
        return row;
      });
  }

  function renderStreaks(result, heroEl, tbody) {
    const s = (result && result.streaks) || computeStreaks(result && result.rows);
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
    const lengths = Object.keys(lens)
      .map(Number)
      .filter(function (n) {
        return n > 0;
      })
      .sort(function (a, b) {
        return a - b;
      });
    if (!lengths.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="muted">No win/loss streaks</td></tr>';
      return;
    }
    lengths.forEach(function (len) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + len + "</td><td>" + (wins[len] || 0) + "</td><td>" + (losses[len] || 0) + "</td>";
      tbody.appendChild(tr);
    });
  }

  function renderMonths(result, tbody) {
    if (!tbody) return;
    tbody.innerHTML = "";
    const months = result && result.by_month ? result.by_month : computeMonths(result && result.rows);
    if (!months.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="muted">No months in this window</td></tr>';
      return;
    }
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
        "</td>";
      tbody.appendChild(tr);
    });
  }

  function render(result) {
    if (!result) return;
    const sym = result.symbol || "";
    const tz = (result.params && result.params.timezone) || "Europe/Chisinau";
    if ($("dx-meta")) {
      const span = windowLabel(result.params);
      $("dx-meta").textContent =
        (result.name || "Dawn Cross") +
        " · " +
        sym +
        " · " +
        (result.date_from || "") +
        " → " +
        (result.date_to || "") +
        (span ? " · " + span : "") +
        (result.params && result.params.one_trade_per_day ? " · one/day" : "") +
        " · " +
        (result.bars || 0) +
        " bars";
    }
    const hero = $("dx-hero");
    if (hero) {
      const pf = result.profit_factor == null ? "—" : result.profit_factor;
      const winPct = result.win_pct != null
        ? result.win_pct
        : Math.round((result.win_rate || 0) * 100);
      hero.innerHTML =
        heroItem("Trades", result.trades || 0) +
        heroItem("Win %", winPct + "%") +
        heroItem("Points", result.sum_pts || 0) +
        heroItem("PF", pf);
    }
    renderStreaks(result, $("dx-streaks-hero"), document.querySelector("#dx-streaks tbody"));
    renderMonths(result, document.querySelector("#dx-months tbody"));
    const tb = document.querySelector("#dx-table tbody");
    if (!tb) return;
    tb.innerHTML = "";
    (result.rows || []).forEach(function (t) {
      const tr = document.createElement("tr");
      const pts = Number(t.pts) || 0;
      tr.innerHTML =
        "<td>" +
        tradeStamp(t, "entry", tz) +
        "</td><td>" +
        (t.side === "UP" ? "buy" : "sell") +
        "</td><td>" +
        px(sym, t.entry) +
        "</td><td>" +
        px(sym, t.sl) +
        "</td><td>" +
        px(sym, t.tp) +
        "</td><td>" +
        (tradeStamp(t, "exit", tz) || "—") +
        "</td><td>" +
        px(sym, t.exit) +
        "</td><td>" +
        (t.exit_reason || "") +
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
      const r = await fetch("/api/dawn-cross");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if ($("dx-bar")) $("dx-bar").style.width = (p.pct || 0) + "%";
      if ($("dx-msg")) $("dx-msg").textContent = p.message || (running ? "Running…" : "Idle");
      if ($("dx-run")) $("dx-run").disabled = running;
      if ($("dx-stop")) $("dx-stop").disabled = !running;
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "dawn";
        badge.className = "badge run";
      }
      if (wasRunning && !running && p.phase === "done") {
        if (badge) {
          badge.textContent = "done";
          badge.className = "badge done";
        }
        const full = await fetch("/api/dawn-cross?rows=1&limit=400");
        const done = await full.json();
        if (done.result) render(done.result);
        if (window.StrategSaved && window.StrategSaved.playDone) window.StrategSaved.playDone();
      } else if (!running && st.result && p.phase === "done" && !(st.result.rows || []).length) {
        const full = await fetch("/api/dawn-cross?rows=1&limit=400");
        const done = await full.json();
        if (done.result) render(done.result);
      } else if (st.result && (st.result.rows || []).length) {
        render(st.result);
      }
      if (p.phase === "error" && badge) {
        badge.textContent = "err";
        badge.className = "badge err";
      }
      wasRunning = running;
      if (!running && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    } catch (e) {
      console.warn("dawn poll", e);
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
  if ($("dx-run")) {
    $("dx-run").addEventListener("click", async function () {
      const body = {
        symbol: $("dx-symbol").value,
        date_from: $("dx-from").value,
        date_to: $("dx-to").value,
        timezone: $("dx-tz").value || "Europe/Chisinau",
        window_start_hour: num("dx-start", 2),
        window_start_minute: num("dx-start-min", 0),
        window_end_hour: num("dx-end", 6),
        window_end_minute: num("dx-end-min", 0),
        fast_ema: num("dx-fast", 9),
        slow_ema: num("dx-slow", 20),
        pullback_ema: num("dx-pull", 9),
        sl_pts: num("dx-sl", 400),
        tp_pts: num("dx-tp", 800),
        flatten_hour: num("dx-flat", 12),
        one_trade_per_day: !!($("dx-one-per-day") && $("dx-one-per-day").checked),
        force_download: $("dx-force") && $("dx-force").checked,
      };
      saveForm();
      $("dx-run").disabled = true;
      if ($("dx-msg")) $("dx-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/dawn-cross/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(function () {
            return {};
          });
          alert(err.detail || "Could not start");
          $("dx-run").disabled = false;
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
        $("dx-run").disabled = false;
      }
    });
  }
  if ($("dx-stop")) {
    $("dx-stop").addEventListener("click", async function () {
      $("dx-stop").disabled = true;
      try {
        await fetch("/api/dawn-cross/stop", { method: "POST" });
        if (!pollTimer) pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
      }
    });
  }
  poll();
})();
