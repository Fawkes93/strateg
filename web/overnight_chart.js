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

      const wrap = el.parentElement;
      const measureSvg = document.getElementById("ob-measure-svg");
      const measureLabel = document.getElementById("ob-measure-label");
      const measureEl = document.getElementById("ob-measure");
      const barSec = (data.tf_min || 15) * 60;
      const MEASURE_KEY = "strateg_overnight_measure";
      let measureOn = true;
      try {
        if (localStorage.getItem(MEASURE_KEY) === "0") measureOn = false;
      } catch (e) {}
      if (measureEl) measureEl.checked = measureOn;

      function clearMeasure() {
        if (measureSvg) measureSvg.innerHTML = "";
        if (measureLabel) {
          measureLabel.hidden = true;
          measureLabel.textContent = "";
        }
      }

      function setMeasureMode(on) {
        measureOn = !!on;
        if (wrap) wrap.classList.toggle("is-measuring", measureOn);
        chart.applyOptions({ handleScroll: { pressedMouseMove: !measureOn } });
        if (!measureOn) clearMeasure();
      }

      function localXY(ev) {
        const r = el.getBoundingClientRect();
        return { x: ev.clientX - r.left, y: ev.clientY - r.top };
      }

      function snapPrice(time, price) {
        if (!magnetEl || !magnetEl.checked || time == null || price == null) return price;
        const candles = data.candles || [];
        let bar = null;
        for (let i = 0; i < candles.length; i++) {
          if (candles[i].time === time) {
            bar = candles[i];
            break;
          }
        }
        if (!bar) return price;
        const opts = [bar.open, bar.high, bar.low, bar.close];
        let best = opts[0];
        let bestD = Math.abs(price - opts[0]);
        for (let i = 1; i < opts.length; i++) {
          const d = Math.abs(price - opts[i]);
          if (d < bestD) {
            best = opts[i];
            bestD = d;
          }
        }
        return best;
      }

      function drawMeasure(a, b) {
        if (!measureSvg || !measureLabel || !a || !b) return;
        const x0 = a.x;
        const y0 = a.y;
        const x1 = b.x;
        const y1 = b.y;
        const up = b.price > a.price;
        const stroke = up ? "#3ecf8e" : "#f07178";
        const w = Math.abs(x1 - x0);
        const h = Math.abs(y1 - y0);
        const rx = Math.min(x0, x1);
        const ry = Math.min(y0, y1);
        measureSvg.setAttribute("viewBox", "0 0 " + el.clientWidth + " " + el.clientHeight);
        measureSvg.setAttribute("width", String(el.clientWidth));
        measureSvg.setAttribute("height", String(el.clientHeight));
        measureSvg.innerHTML =
          '<rect x="' + rx + '" y="' + ry + '" width="' + w + '" height="' + h +
          '" fill="' + stroke + '" fill-opacity="0.08" stroke="' + stroke + '" stroke-opacity="0.55" />' +
          '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + x1 + '" y2="' + y1 +
          '" stroke="' + stroke + '" stroke-width="1.5" />';
        const dPrice = b.price - a.price;
        const dPts = Math.round(dPrice / ps);
        let bars = 0;
        if (a.time != null && b.time != null) {
          bars = Math.round(Math.abs(b.time - a.time) / barSec);
        }
        const pct = a.price ? (dPrice / a.price) * 100 : 0;
        const sign = dPts > 0 ? "+" : "";
        measureLabel.hidden = false;
        measureLabel.classList.toggle("is-up", up);
        measureLabel.classList.toggle("is-down", !up);
        measureLabel.innerHTML =
          sign + dPts + " pts · " +
          (dPrice >= 0 ? "+" : "") + px2(dPrice) + " · " +
          (pct >= 0 ? "+" : "") + pct.toFixed(2) + "%<br>" +
          bars + " bars · " + bars * (data.tf_min || 15) + "m";
        measureLabel.style.left = Math.round((x0 + x1) / 2) + "px";
        measureLabel.style.top = Math.round(Math.max(y0, y1)) + "px";
      }

      let drag = null;
      if (measureSvg) {
        measureSvg.addEventListener("pointerdown", function (ev) {
          if (!measureOn || ev.button !== 0) return;
          const p = localXY(ev);
          const time = chart.timeScale().coordinateToTime(p.x);
          let price = candleSeries.coordinateToPrice(p.y);
          price = snapPrice(time, price);
          const y = candleSeries.priceToCoordinate(price);
          const x = time != null ? chart.timeScale().timeToCoordinate(time) : p.x;
          drag = {
            time: time,
            price: price,
            x: x == null ? p.x : x,
            y: y == null ? p.y : y,
          };
          measureSvg.setPointerCapture(ev.pointerId);
          ev.preventDefault();
        });
        measureSvg.addEventListener("pointermove", function (ev) {
          if (!drag) return;
          const p = localXY(ev);
          const time = chart.timeScale().coordinateToTime(p.x);
          let price = candleSeries.coordinateToPrice(p.y);
          price = snapPrice(time, price);
          const y = candleSeries.priceToCoordinate(price);
          const x = time != null ? chart.timeScale().timeToCoordinate(time) : p.x;
          drawMeasure(drag, {
            time: time,
            price: price,
            x: x == null ? p.x : x,
            y: y == null ? p.y : y,
          });
        });
        measureSvg.addEventListener("pointerup", function () {
          drag = null;
        });
        measureSvg.addEventListener("pointercancel", function () {
          drag = null;
        });
      }
      window.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") clearMeasure();
      });
      if (measureEl) {
        measureEl.addEventListener("change", function () {
          const on = !!measureEl.checked;
          try {
            localStorage.setItem(MEASURE_KEY, on ? "1" : "0");
          } catch (e) {}
          setMeasureMode(on);
        });
      }
      setMeasureMode(measureOn);
      legend.innerHTML = "";
      const legendItems = [
        ["#e6b450", "Asia high"],
        ["#8b9aab", "Asia low"],
        ["#f07178", "Stop"],
        ["#3ecf8e", "Target"],
        ["#3d9cf0", data.ma_label || ("EMA " + (data.ema_period || ""))],
      ];
      (data.lines || []).forEach(function (ln) {
        if (ln && ln.title && String(ln.title).indexOf("Fib") === 0) {
          legendItems.push([ln.color || "#c084fc", ln.title]);
        }
      });
      legendItems.forEach(function (item) {
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
