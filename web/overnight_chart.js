(function () {
  const params = new URLSearchParams(location.search);
  const tradeId = params.get("trade");
  const el = document.getElementById("ob-chart");
  const title = document.getElementById("ob-title");
  const sub = document.getElementById("ob-sub");
  const legend = document.getElementById("ob-legend");
  const decision = document.getElementById("ob-decision");

  if (!tradeId) {
    sub.textContent = "Missing trade id.";
    return;
  }

  function priceDigits(symbol) {
    const s = String(symbol || "").toUpperCase();
    if (s.indexOf("JPY") >= 0) return 3;
    if (s.indexOf("XAU") >= 0 || s.indexOf("GOLD") >= 0 || s.indexOf("BTC") >= 0) return 2;
    return 5;
  }

  function pointSize(symbol) {
    const s = String(symbol || "").toUpperCase();
    if (s.indexOf("JPY") >= 0) return 0.001;
    if (s.indexOf("XAU") >= 0 || s.indexOf("GOLD") >= 0 || s.indexOf("BTC") >= 0) return 0.01;
    return 0.00001;
  }

  fetch("/api/overnight/chart-data?trade_id=" + encodeURIComponent(tradeId))
    .then(function (r) {
      if (!r.ok) throw new Error("chart-data " + r.status);
      return r.json();
    })
    .then(function (data) {
      const t = data.trade || {};
      const run = data.run || {};
      const digits = priceDigits(run.symbol);
      const ps = pointSize(run.symbol);
      function px2(n) {
        const x = Number(n);
        if (!Number.isFinite(x)) return "—";
        return x.toFixed(digits);
      }
      const runId = run.id != null ? run.id : t.run_id;
      title.textContent =
        "Run #" +
        (runId != null ? runId : "—") +
        " · " +
        (t.local_date || "") +
        " · " +
        (t.side || "") +
        " · " +
        (t.entry_reason || "");
      document.title = title.textContent + " — Strateg";
      const ptsN = Number(t.pts);
      const reason = String(t.exit_reason || "").toUpperCase();
      const bits = [];
      if (reason) bits.push(reason);
      if (Number.isFinite(ptsN)) bits.push(Math.round(ptsN) + " pts");
      bits.push("entry " + px2(t.entry) + " → " + px2(t.exit));
      if (t.asia_high != null && t.asia_low != null) {
        bits.push("Asia " + px2(t.asia_low) + "–" + px2(t.asia_high));
      }
      const asia = data.asia || {};
      bits.push(
        "box " +
          String(asia.start_hour != null ? asia.start_hour : 0).padStart(2, "0") +
          ":00–" +
          String(asia.end_hour != null ? asia.end_hour : 7).padStart(2, "0") +
          ":00 · flatten " +
          (asia.flatten_hour != null ? asia.flatten_hour : 18) +
          ":00"
      );
      const zone = data.timezone || "Europe/Bucharest";
      bits.push((data.tf_min || 15) + "m candles · " + zone);
      if (run.data_source === "ticks") {
        bits.push("fills came from ticks; candles are the 15m view of those hours");
      }
      sub.textContent = bits.join(" · ");
      if (decision) {
        decision.textContent = data.decision
          ? data.decision
          : "Asia high and low are the locked box. SL and TP are this trade's prices. Break, entry, and exit sit on the 15m bar that contained them.";
      }
      const back = document.getElementById("ob-back");
      if (back && runId != null) {
        back.href = "/overnight/results?run=" + encodeURIComponent(runId);
      }
      if (typeof LightweightCharts === "undefined") {
        sub.textContent += " — chart library failed to load.";
        return;
      }
      if (!data.candles || !data.candles.length) {
        sub.textContent += " — no candles for this day.";
        return;
      }
      function localParts(ts) {
        const d = new Date(Number(ts) * 1000);
        const date = d.toLocaleDateString("en-GB", {
          timeZone: zone,
          day: "2-digit",
          month: "short",
        });
        const hm = d.toLocaleTimeString("en-GB", {
          timeZone: zone,
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        return { date: date, hm: hm };
      }
      function tickLabel(ts, tickMarkType) {
        const p = localParts(ts);
        if (tickMarkType === 0) {
          return new Date(Number(ts) * 1000).toLocaleDateString("en-GB", {
            timeZone: zone,
            year: "numeric",
          });
        }
        if (tickMarkType === 1 || tickMarkType === 2) return p.date;
        return p.hm;
      }
      const MAGNET_KEY = "strateg_overnight_magnet";
      const magnetEl = document.getElementById("ob-magnet");
      const magnetOn = (function () {
        try {
          return localStorage.getItem(MAGNET_KEY) === "1";
        } catch (e) {
          return false;
        }
      })();
      if (magnetEl) magnetEl.checked = magnetOn;
      function magnetMode(on) {
        if (!LightweightCharts.CrosshairMode) return {};
        return {
          crosshair: {
            mode: on
              ? LightweightCharts.CrosshairMode.Magnet
              : LightweightCharts.CrosshairMode.Normal,
          },
        };
      }
      const chart = LightweightCharts.createChart(el, Object.assign({
        autoSize: true,
        layout: { background: { color: "#0f1419" }, textColor: "#c5d0dc" },
        grid: { vertLines: { color: "#1e2832" }, horzLines: { color: "#1e2832" } },
        rightPriceScale: { borderColor: "#2a3542" },
        localization: {
          timeFormatter: function (ts) {
            const p = localParts(ts);
            return p.date + " " + p.hm;
          },
        },
        timeScale: {
          borderColor: "#2a3542",
          timeVisible: true,
          secondsVisible: false,
          tickMarkFormatter: tickLabel,
        },
      }, magnetMode(magnetOn)));
      if (magnetEl) {
        magnetEl.addEventListener("change", function () {
          const on = !!magnetEl.checked;
          try {
            localStorage.setItem(MAGNET_KEY, on ? "1" : "0");
          } catch (e) {}
          chart.applyOptions(magnetMode(on));
        });
      }
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#3ecf8e",
        downColor: "#f07178",
        borderVisible: false,
        wickUpColor: "#3ecf8e",
        wickDownColor: "#f07178",
        priceFormat: { type: "price", precision: digits, minMove: ps },
      });
      candleSeries.setData(data.candles);
      if (data.ema && data.ema.length) {
        const emaSeries = chart.addLineSeries({
          color: "#3d9cf0",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          priceFormat: { type: "price", precision: digits, minMove: ps },
        });
        emaSeries.setData(data.ema);
      }
      (data.lines || []).forEach(function (ln) {
        const px = Number(ln.price);
        if (!Number.isFinite(px)) return;
        candleSeries.createPriceLine({
          price: px,
          color: ln.color || "#8b9aab",
          lineWidth: 1,
          lineStyle: ln.dashed ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
          title: ln.title || "",
        });
      });
      if (data.markers && data.markers.length) {
        candleSeries.setMarkers(data.markers);
      }
      chart.timeScale().fitContent();
      legend.innerHTML = "";
      [
        ["#e6b450", "Asia high"],
        ["#8b9aab", "Asia low"],
        ["#f07178", "Stop"],
        ["#3ecf8e", "Target"],
        ["#3d9cf0", "EMA " + (data.ema_period || "")],
      ].forEach(function (item) {
        const li = document.createElement("li");
        li.innerHTML =
          '<span class="swatch" style="background:' + item[0] + '"></span>' + item[1];
        legend.appendChild(li);
      });
    })
    .catch(function (err) {
      sub.textContent = String(err && err.message ? err.message : err);
    });
})();
