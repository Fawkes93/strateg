(function () {
  const $ = (id) => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  let tzByRun = {};

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
    const btn = $("ab-delete-run");
    if (!btn) return;
    btn.disabled = !$("ab-run").value;
  }

  async function loadRuns(prefer) {
    const r = await fetch("/api/asia-box/runs");
    const data = await r.json();
    const sel = $("ab-run");
    const current = prefer != null ? String(prefer) : sel.value || params.get("run") || "";
    sel.innerHTML = '<option value="">All runs</option>';
    tzByRun = {};
    (data.runs || []).forEach(function (run) {
      tzByRun[String(run.id)] = run.timezone || (run.params && run.params.timezone) || "UTC";
      const opt = document.createElement("option");
      opt.value = String(run.id);
      const sum = run.summary || {};
      opt.textContent =
        "#" +
        run.id +
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
    const run = $("ab-run").value;
    const setup = $("ab-setup").value;
    const side = $("ab-side").value;
    const box = $("ab-box").value;
    const exit = $("ab-exit").value;
    const from = $("ab-from").value;
    const to = $("ab-to").value;
    if (run) q.set("run_id", run);
    if (setup) q.set("setup", setup);
    if (side) q.set("side", side);
    if (box) q.set("box_n", box);
    if (exit) q.set("exit_reason", exit);
    if (from) q.set("date_from", from);
    if (to) q.set("date_to", to);
    return q;
  }

  async function loadTrades() {
    const r = await fetch("/api/asia-box/trades?" + query().toString());
    const data = await r.json();
    const rows = data.trades || [];
    const tb = document.querySelector("#ab-table tbody");
    tb.innerHTML = "";
    let sum = 0;
    let wins = 0;
    const by = {};
    rows.forEach(function (t) {
      sum += Number(t.pts) || 0;
      if ((t.pts || 0) > 0) wins += 1;
      by[t.setup] = (by[t.setup] || 0) + 1;
      const tz = tzByRun[String(t.run_id)] || "UTC";
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.innerHTML =
        "<td>" +
        t.local_date +
        "</td><td>" +
        localClock(t.entry_ts, tz) +
        "</td><td>" +
        t.setup +
        "</td><td>" +
        t.box_n +
        "</td><td>" +
        t.side +
        "</td><td>" +
        fmt(t.entry, 2) +
        "</td><td>" +
        fmt(t.exit, 2) +
        "</td><td class='" +
        ((t.pts || 0) >= 0 ? "ab-win" : "ab-loss") +
        "'>" +
        fmt(t.pts, 0) +
        "</td><td>" +
        (t.exit_reason || "") +
        "</td>";
      tr.addEventListener("click", function () {
        window.open("/asia-box/chart?trade=" + t.id, "_blank");
      });
      tr.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") window.open("/asia-box/chart?trade=" + t.id, "_blank");
      });
      tb.appendChild(tr);
    });
    const wr = rows.length ? Math.round((100 * wins) / rows.length) : 0;
    const parts = Object.keys(by)
      .map((k) => k + " " + by[k])
      .join(" · ");
    $("ab-summary").textContent =
      rows.length +
      " trades · " +
      wr +
      "% wins · " +
      Math.round(sum) +
      " pts" +
      (parts ? " · " + parts : "");
  }

  ["ab-run", "ab-setup", "ab-side", "ab-box", "ab-exit", "ab-from", "ab-to"].forEach(
    function (id) {
      $(id).addEventListener("change", function () {
        if (id === "ab-run") syncDeleteBtn();
        loadTrades();
      });
    }
  );

  if ($("ab-delete-run")) {
    $("ab-delete-run").addEventListener("click", async function () {
      const id = $("ab-run").value;
      if (!id) return;
      if (!window.confirm("Delete run #" + id + " and all of its trades?")) return;
      $("ab-delete-run").disabled = true;
      try {
        const r = await fetch("/api/asia-box/runs/" + encodeURIComponent(id), {
          method: "DELETE",
        });
        if (!r.ok) {
          const err = await r.json().catch(function () {
            return {};
          });
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
    $("ab-summary").textContent = String(e);
  });
})();
