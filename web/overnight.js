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

  if ($("ob-run")) {
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

  poll();
})();
