(function () {
  const $ = (id) => document.getElementById(id);
  let pollTimer = null;
  let wasRunning = false;

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
    const meta = $("sc-meta");
    const hero = $("sc-hero");
    const tb = $("sc-table") && $("sc-table").querySelector("tbody");
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
        heroItem("SL %", result.sl_pct != null ? result.sl_pct + "%" : "—") +
        heroItem(
          "09:00 close %",
          result.eval_flat_pct != null ? result.eval_flat_pct + "%" : "—"
        ) +
        heroItem("BE close %", result.be_pct != null ? result.be_pct + "%" : "—") +
        heroItem("Noon %", result.noon_pct != null ? result.noon_pct + "%" : "—") +
        heroItem("Avg pts", result.avg_pts) +
        heroItem("PF", result.profit_factor != null ? result.profit_factor : "—") +
        heroItem("Sum pts", result.sum_pts);
    }
    if (!tb) return;
    tb.innerHTML = "";
    const rows = result.rows || [];
    if (!rows.length) {
      tb.innerHTML =
        '<tr><td colspan="10" class="muted">No trades in this window</td></tr>';
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
        t.defining_hour +
        "</td><td>" +
        t.defining_range_usd +
        "</td><td>" +
        t.entry +
        "</td><td>" +
        t.sl +
        "</td><td>" +
        t.sl_pts +
        "</td><td>" +
        (t.exit != null ? t.exit : "—") +
        "</td><td>" +
        (t.exit_reason || "—") +
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
      const r = await fetch("/api/session");
      const st = await r.json();
      const p = st.progress || {};
      const running = !!st.running;
      if ($("sc-progress-bar")) {
        $("sc-progress-bar").style.width = (p.pct || 0) + "%";
      }
      if ($("sc-progress-msg")) {
        $("sc-progress-msg").textContent =
          p.message || (running ? "Running…" : "Idle");
      }
      if ($("sc-run")) $("sc-run").disabled = running;
      if (st.result) render(st.result);
      const badge = $("status-badge");
      if (badge && running) {
        badge.textContent = "session";
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

  if ($("sc-run")) {
    $("sc-run").addEventListener("click", async () => {
      const body = {
        symbol: $("sc-symbol").value,
        date_from: $("sc-from").value,
        date_to: $("sc-to").value,
        timezone: $("sc-tz").value || "Europe/Chisinau",
        min_range_usd: Number($("sc-min-range").value),
        min_body_pts: Number($("sc-min-body").value),
        sl_floor_pts: Number($("sc-sl-floor").value),
        flatten_hour: Number($("sc-flatten").value),
        force_download: $("sc-force") && $("sc-force").checked,
      };
      $("sc-run").disabled = true;
      $("sc-progress-msg").textContent = "Starting…";
      try {
        const r = await fetch("/api/session/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          alert(err.detail || "Could not start");
          $("sc-run").disabled = false;
          return;
        }
        wasRunning = true;
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(poll, 800);
        poll();
      } catch (e) {
        alert(String(e));
        $("sc-run").disabled = false;
      }
    });
  }

  poll();
})();
