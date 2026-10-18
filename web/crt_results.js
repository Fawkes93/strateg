(function () {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  let tzByRun = {};
  let symbolByRun = {};

  const ENTRY = { fvg: "Fair value gap", sweep_close: "Sweep close" };

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
    const btn = $("crt-delete-run");
    if (!btn) return;
    btn.disabled = !$("crt-run").value;
  }

  async function loadRuns(prefer) {
    const r = await fetch("/api/crt/runs");
    const data = await r.json();
    const sel = $("crt-run");
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
      const htf = run.params && run.params.htf_min ? run.params.htf_min + "m" : "";
      opt.textContent =
        "#" + run.id + " " + (run.symbol || "") +
        (htf ? " " + htf : "") +
        " " + run.date_from + "→" + run.date_to +
        " · " + (sum.trades || 0) + " trades";
      if (String(run.id) === current) opt.selected = true;
      sel.appendChild(opt);
    });
    syncDeleteBtn();
  }

  function query() {
    const q = new URLSearchParams();
    const run = $("crt-run").value;
    const side = $("crt-side").value;
    const entry = $("crt-entry").value;
    const exit = $("crt-exit").value;
    const from = $("crt-from").value;
    const to = $("crt-to").value;
    if (run) q.set("run_id", run);
    if (side) q.set("side", side);
    if (entry) q.set("entry_reason", entry);
    if (exit) q.set("exit_reason", exit);
    if (from) q.set("date_from", from);
    if (to) q.set("date_to", to);
    return q;
  }

  async function loadTrades() {
    const r = await fetch("/api/crt/trades?" + query().toString());
    const data = await r.json();
    const rows = data.trades || [];
    const tb = document.querySelector("#crt-table tbody");
    tb.innerHTML = "";
    let sum = 0;
    let wins = 0;
    rows.forEach(function (t) {
      sum += Number(t.pts) || 0;
      if ((t.pts || 0) > 0) wins += 1;
      const tz = tzByRun[String(t.run_id)] || "UTC";
      const digits = digitsFor(symbolByRun[String(t.run_id)]);
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.innerHTML =
        "<td>" + t.local_date + "</td><td>" + localClock(t.entry_ts, tz) +
        "</td><td>" + t.side + "</td><td>" + (ENTRY[t.entry_reason] || t.entry_reason || "—") +
        "</td><td>" + fmt(t.entry, digits) + "</td><td>" + fmt(t.exit, digits) +
        "</td><td class='" + ((t.pts || 0) >= 0 ? "ab-win" : "ab-loss") + "'>" +
        fmt(t.pts, 0) + "</td><td>" + (t.exit_reason || "") + "</td>";
      function openChart() {
        window.open("/crt/chart?trade=" + t.id, "_blank");
      }
      tr.addEventListener("click", openChart);
      tr.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") openChart();
      });
      tb.appendChild(tr);
    });
    const wr = rows.length ? Math.round((100 * wins) / rows.length) : 0;
    $("crt-summary").textContent =
      rows.length + " trades · " + wr + "% wins · " + Math.round(sum) + " pts";
  }

  ["crt-run", "crt-side", "crt-entry", "crt-exit", "crt-from", "crt-to"].forEach(function (id) {
    $(id).addEventListener("change", function () {
      if (id === "crt-run") syncDeleteBtn();
      loadTrades();
    });
  });

  if ($("crt-delete-run")) {
    $("crt-delete-run").addEventListener("click", async function () {
      const id = $("crt-run").value;
      if (!id) return;
      if (!window.confirm("Delete CRT run #" + id + " and all of its trades?")) return;
      $("crt-delete-run").disabled = true;
      try {
        const r = await fetch("/api/crt/runs/" + encodeURIComponent(id), { method: "DELETE" });
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
    $("crt-summary").textContent = String(e);
  });
})();
