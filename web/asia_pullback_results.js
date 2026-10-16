(function () {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  let tzByRun = {};
  let symbolByRun = {};

  const ENTRY = {
    leg_fib: "Fib of the leg",
    box_fib: "Fib of the box",
    ema: "Moving average",
    close5m: "5m close",
    reversal: "Reversal",
  };

  function digitsFor(symbol) {
    const s = String(symbol || "").toUpperCase();
    if (s.indexOf("JPY") >= 0) return 3;
    if (s.indexOf("XAU") >= 0 || s.indexOf("GOLD") >= 0 || s.indexOf("BTC") >= 0) return 2;
    return 5;
  }

  function localClock(iso, tz) {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("en-GB", {
      timeZone: tz || "UTC",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }

  function fmt(n, d) {
    if (n == null || n === "") return "—";
    const x = Number(n);
    if (!Number.isFinite(x)) return String(n);
    return x.toFixed(d == null ? 1 : d);
  }

  function syncDeleteBtn() {
    const btn = $("ap-delete-run");
    if (!btn) return;
    btn.disabled = !$("ap-run").value;
  }

  async function loadRuns(prefer) {
    const r = await fetch("/api/asia-pullback/runs");
    const data = await r.json();
    const sel = $("ap-run");
    const current = prefer != null ? String(prefer) : sel.value || params.get("run") || "";
    sel.innerHTML = '<option value="">All runs</option>';
    tzByRun = {};
    symbolByRun = {};
    (data.runs || []).forEach(function (run) {
      tzByRun[String(run.id)] = run.timezone || (run.params && run.params.timezone) || "UTC";
      symbolByRun[String(run.id)] = run.symbol || "";
      const opt = document.createElement("option");
      opt.value = String(run.id);
      const sum = run.summary || {};
      const src =
        run.data_source === "ticks"
          ? "ticks"
          : run.data_source === "candles_5m"
            ? "5m candles"
            : "";
      opt.textContent =
        "#" +
        run.id +
        " " +
        (run.symbol || "") +
        (src ? " " + src : "") +
        " " +
        run.date_from +
        "→" +
        run.date_to +
        " · " +
        (sum.trades || 0) +
        " trades";
      if (String(run.id) === current) opt.selected = true;
      sel.appendChild(opt);
    });
    syncDeleteBtn();
  }

  function query() {
    const q = new URLSearchParams();
    const run = $("ap-run").value;
    const side = $("ap-side").value;
    const entry = $("ap-entry").value;
    const exit = $("ap-exit").value;
    const from = $("ap-from").value;
    const to = $("ap-to").value;
    if (run) q.set("run_id", run);
    if (side) q.set("side", side);
    if (entry) q.set("entry_reason", entry);
    if (exit) q.set("exit_reason", exit);
    if (from) q.set("date_from", from);
    if (to) q.set("date_to", to);
    return q;
  }

  async function loadTrades() {
    const r = await fetch("/api/asia-pullback/trades?" + query().toString());
    const data = await r.json();
    const rows = data.trades || [];
    const tb = document.querySelector("#ap-table tbody");
    tb.innerHTML = "";
    let sum = 0;
    let wins = 0;
    rows.forEach(function (t) {
      sum += Number(t.pts) || 0;
      if ((t.pts || 0) > 0) wins += 1;
      const tz = tzByRun[String(t.run_id)] || "UTC";
      const digits = digitsFor(symbolByRun[String(t.run_id)]);
      const level = t.level != null ? t.level : (t.extras && t.extras.level);
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.innerHTML =
        "<td>" +
        t.local_date +
        "</td><td>" +
        localClock(t.entry_ts, tz) +
        "</td><td>" +
        t.side +
        "</td><td>" +
        (ENTRY[t.entry_reason] || t.entry_reason || "—") +
        "</td><td>" +
        fmt(level, digits) +
        "</td><td>" +
        fmt(t.entry, digits) +
        "</td><td>" +
        fmt(t.exit, digits) +
        "</td><td class='" +
        ((t.pts || 0) >= 0 ? "ab-win" : "ab-loss") +
        "'>" +
        fmt(t.pts, 0) +
        "</td><td>" +
        (t.exit_reason || "") +
        "</td>";
      function openChart() {
        window.open("/asia-pullback/chart?trade=" + t.id, "_blank");
      }
      tr.addEventListener("click", openChart);
      tr.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") openChart();
      });
      tb.appendChild(tr);
    });
    const wr = rows.length ? Math.round((100 * wins) / rows.length) : 0;
    $("ap-summary").textContent =
      rows.length + " trades · " + wr + "% wins · " + Math.round(sum) + " pts";
  }

  ["ap-run", "ap-side", "ap-entry", "ap-exit", "ap-from", "ap-to"].forEach(function (id) {
    $(id).addEventListener("change", function () {
      if (id === "ap-run") syncDeleteBtn();
      loadTrades();
    });
  });

  if ($("ap-delete-run")) {
    $("ap-delete-run").addEventListener("click", async function () {
      const id = $("ap-run").value;
      if (!id) return;
      if (!window.confirm("Delete Asia pullback run #" + id + " and all of its trades?")) return;
      $("ap-delete-run").disabled = true;
      try {
        const r = await fetch("/api/asia-pullback/runs/" + encodeURIComponent(id), { method: "DELETE" });
        if (!r.ok) {
          const err = await r.json().catch(function () { return {}; });
          alert(err.detail || "Could not delete");
          syncDeleteBtn();
          return;
        }
        if (window.history && window.history.replaceState) {
          const u = new URL(location.href);
          u.searchParams.delete("run");
          window.history.replaceState({}, "", u);
        }
        params.delete("run");
        await loadRuns("");
        await loadTrades();
      } catch (e) {
        alert(String(e));
        syncDeleteBtn();
      }
    });
  }

  loadRuns().then(loadTrades).catch(function (e) {
    $("ap-summary").textContent = String(e);
  });
})();
