(function () {
  const params = new URLSearchParams(location.search);
  const tradeId = params.get("trade");
  const el = document.getElementById("ab-chart");
  const title = document.getElementById("ab-title");
  const sub = document.getElementById("ab-sub");
  const legend = document.getElementById("ab-legend");

  if (!tradeId) {
    sub.textContent = "Missing trade id.";
    return;
  }

  function toDayTime(ts) {
    // lightweight-charts wants UTCTimestamp (seconds)
    return Number(ts);
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

  fetch("/api/asia-box/chart-data?trade_id=" + encodeURIComponent(tradeId))
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
      const priceFormat = {
        type: "price",
        precision: digits,
        minMove: ps,
      };
      const tz = data.timezone || run.timezone || "UTC";
      const box = data.box || {};
      const boxH = box.start_hour != null ? box.start_hour : 1;
      const boxE = box.end_hour != null ? box.end_hour : 6;
      const runId = run.id != null ? run.id : t.run_id;
      const runLabel = runId != null ? "Run #" + runId : "Run";
      title.textContent =
        runLabel +
        " · " +
        (t.local_date || "") +
        " · " +
        (t.setup || "") +
        " · " +
        (t.side || "");
      document.title = title.textContent + " — Strateg";
      const ptsN = Number(t.pts);
      const pts =
        t.pts == null || !Number.isFinite(ptsN) ? "" : Math.round(ptsN) + " pts";
      const boxPts = Number(t.range_pts);
      const boxPx =
        t.box_high != null && t.box_low != null
          ? Math.abs(Number(t.box_high) - Number(t.box_low))
          : NaN;
      const boxBit = Number.isFinite(boxPts)
        ? "box " +
          (Number.isFinite(boxPx) ? px2(boxPx) + " / " : "") +
          Math.round(boxPts) +
          " pts"
        : "";
      const reason = String(t.exit_reason || "").toUpperCase();
      const reasonCls = reason === "TP" ? "ab-win" : reason === "SL" ? "ab-loss" : "";
      const ptsCls = ptsN > 0 ? "ab-win" : ptsN < 0 ? "ab-loss" : "";
      const bits = [];
      if (reason) {
        bits.push(
          reasonCls
            ? '<span class="' + reasonCls + '">' + reason + "</span>"
            : reason
        );
      }
      if (pts) {
        bits.push(
          ptsCls ? '<span class="' + ptsCls + '">' + pts + "</span>" : pts
        );
      }
      bits.push("entry " + px2(t.entry) + " → " + px2(t.exit));
      const sl0 = t.extras && t.extras.sl_initial;
      const trailed =
        sl0 != null &&
        t.sl != null &&
        Math.abs(Number(sl0) - Number(t.sl)) > 1e-8;
      if (trailed) bits.push("SL " + px2(sl0) + " → " + px2(t.sl) + " trailed");
      if (boxBit) bits.push(boxBit);
      sub.innerHTML = bits.join(" · ");
      const back = document.getElementById("ab-back");
      if (back && runId != null) {
        back.href = "/asia-box/results?run=" + encodeURIComponent(runId);
      }

      if (typeof LightweightCharts === "undefined") {
        sub.textContent += " — chart library failed to load.";
        return;
      }

      function clock(ts) {
        return new Date(Number(ts) * 1000).toLocaleTimeString("en-GB", {
          timeZone: tz,
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
      }

      const MAGNET_KEY = "strateg_asia_box_magnet";
      const magnetEl = document.getElementById("ab-magnet");
      const magnetOn = (function () {
        try {
          return localStorage.getItem(MAGNET_KEY) === "1";
        } catch (e) {
          return false;
        }
      })();
      if (magnetEl) magnetEl.checked = magnetOn;
      const magnetMode = function (on) {
        if (!LightweightCharts.CrosshairMode) return {};
        return {
          crosshair: {
            mode: on
              ? LightweightCharts.CrosshairMode.Magnet
              : LightweightCharts.CrosshairMode.Normal,
          },
        };
      };

      const chart = LightweightCharts.createChart(
        el,
        Object.assign(
          {
            width: el.clientWidth || 800,
            height: el.clientHeight || 560,
            layout: {
              background: { color: "#0f1419" },
              textColor: "#e7eef6",
            },
            grid: {
              vertLines: { color: "#2a3542" },
              horzLines: { color: "#2a3542" },
            },
            rightPriceScale: { borderColor: "#2a3542" },
            localization: { timeFormatter: clock },
            timeScale: {
              borderColor: "#2a3542",
              timeVisible: true,
              secondsVisible: false,
              tickMarkFormatter: clock,
            },
          },
          magnetMode(magnetOn)
        )
      );
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
        priceFormat: priceFormat,
      });
      const candles = (data.candles || []).map(function (c) {
        return {
          time: toDayTime(c.time),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        };
      });
      if (candles.length) candleSeries.setData(candles);

      if (box.high != null && box.low != null && box.start_unix && box.end_unix) {
        let t0 = Number(box.start_unix);
        let t1 = Number(box.end_unix);
        if (candles.length) {
          const first = candles[0].time;
          const last = candles[candles.length - 1].time;
          t0 = Math.max(first, Math.min(last, t0));
          t1 = Math.max(first, Math.min(last, t1));
        }
        if (t1 > t0) {
          const boxStyle = {
            color: "#3d9cf0",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            priceFormat: priceFormat,
          };
          chart.addLineSeries(Object.assign({ title: "Box H" }, boxStyle)).setData([
            { time: t0, value: box.high },
            { time: t1, value: box.high },
          ]);
          chart.addLineSeries(Object.assign({ title: "Box L" }, boxStyle)).setData([
            { time: t0, value: box.low },
            { time: t1, value: box.low },
          ]);
          const li = document.createElement("li");
          li.innerHTML =
            '<span class="swatch" style="background:#3d9cf0"></span>Asia box ' +
            String(boxH).padStart(2, "0") +
            ":00–" +
            String(boxE).padStart(2, "0") +
            ":00 " +
            tz +
            " · " +
            px2(box.high) +
            " / " +
            px2(box.low);
          legend.appendChild(li);
        }
      }

      const emaSeries = chart.addLineSeries({
        color: "#e6b450",
        lineWidth: 1,
        title: "EMA",
        lastValueVisible: false,
        priceLineVisible: false,
        priceFormat: priceFormat,
      });
      emaSeries.setData(
        (data.ema || []).map(function (p) {
          return { time: toDayTime(p.time), value: p.value };
        })
      );

      let fibT0 = null;
      let fibT1 = null;
      if (box.start_unix && box.end_unix) {
        fibT0 = Number(box.start_unix);
        fibT1 = Number(box.end_unix);
        if (candles.length) {
          const first = candles[0].time;
          const last = candles[candles.length - 1].time;
          fibT0 = Math.max(first, Math.min(last, fibT0));
          fibT1 = Math.max(first, Math.min(last, fibT1));
        }
      } else if (candles.length) {
        fibT0 = candles[0].time;
        fibT1 = candles[candles.length - 1].time;
      }

      const fibSeries = [];
      (data.fibs || []).forEach(function (lv) {
        if (fibT0 != null && fibT1 != null && fibT1 > fibT0) {
          const s = chart.addLineSeries({
            color: lv.color,
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
            title: String(lv.level),
            priceFormat: priceFormat,
          });
          s.setData([
            { time: fibT0, value: lv.price },
            { time: fibT1, value: lv.price },
          ]);
          fibSeries.push({ series: s, level: lv });
        }
        const li = document.createElement("li");
        li.innerHTML =
          '<span class="swatch" style="background:' +
          lv.color +
          '"></span>' +
          lv.level +
          " · " +
          px2(lv.price);
        legend.appendChild(li);
      });

      function placeFibTags() {
        const host = document.getElementById("ab-fib-labels");
        if (!host) return;
        host.innerHTML = "";
        const ts = chart.timeScale();
        fibSeries.forEach(function (item) {
          const x = ts.timeToCoordinate(fibT0);
          const y = item.series.priceToCoordinate(item.level.price);
          if (x == null || y == null) return;
          const tag = document.createElement("span");
          tag.className = "ab-fib-tag";
          tag.style.left = Math.round(x) + "px";
          tag.style.top = Math.round(y) + "px";
          tag.style.color = item.level.color;
          tag.textContent = String(item.level.level);
          host.appendChild(tag);
        });
      }

      if (t.sl != null) {
        const sl0 = t.extras && t.extras.sl_initial;
        const trailed =
          sl0 != null && Math.abs(Number(sl0) - Number(t.sl)) > 1e-8;
        candleSeries.createPriceLine({
          price: t.sl,
          color: "#f07178",
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          title: trailed ? "SL trailed" : "SL",
        });
      }
      if (t.tp != null) {
        candleSeries.createPriceLine({
          price: t.tp,
          color: "#3ecf8e",
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Dashed,
          title: "TP",
        });
      }

      const markers = [];
      if (t.entry_ts) {
        const et = Math.floor(Date.parse(t.entry_ts) / 1000);
        if (Number.isFinite(et)) {
          markers.push({
            time: et,
            position: t.side === "UP" ? "belowBar" : "aboveBar",
            color: "#3d9cf0",
            shape: t.side === "UP" ? "arrowUp" : "arrowDown",
            text: "Entry",
          });
        }
      }
      if (t.exit_ts) {
        const xt = Math.floor(Date.parse(t.exit_ts) / 1000);
        if (Number.isFinite(xt)) {
          markers.push({
            time: xt,
            position: t.side === "UP" ? "aboveBar" : "belowBar",
            color: "#e6b450",
            shape: "circle",
            text: t.exit_reason || "Exit",
          });
        }
      }
      if (markers.length) candleSeries.setMarkers(markers);
      chart.timeScale().fitContent();
      requestAnimationFrame(placeFibTags);
      chart.timeScale().subscribeVisibleLogicalRangeChange(placeFibTags);

      const wrap = el.parentElement;
      const measureSvg = document.getElementById("ab-measure-svg");
      const measureLabel = document.getElementById("ab-measure-label");
      const measureEl = document.getElementById("ab-measure");
      const MEASURE_KEY = "strateg_asia_box_measure";
      let measureOn = true;
      try {
        if (localStorage.getItem(MEASURE_KEY) === "0") measureOn = false;
      } catch (e) {}
      if (measureEl) measureEl.checked = measureOn;

      function setMeasureMode(on) {
        measureOn = !!on;
        if (wrap) wrap.classList.toggle("is-measuring", measureOn);
        chart.applyOptions({
          handleScroll: { pressedMouseMove: !measureOn },
        });
        if (!measureOn) clearMeasure();
      }

      function clearMeasure() {
        if (measureSvg) measureSvg.innerHTML = "";
        if (measureLabel) {
          measureLabel.hidden = true;
          measureLabel.textContent = "";
        }
      }

      function localXY(ev) {
        const r = el.getBoundingClientRect();
        return { x: ev.clientX - r.left, y: ev.clientY - r.top };
      }

      function snapPrice(time, price) {
        if (!magnetEl || !magnetEl.checked || time == null || price == null) return price;
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
        if (!measureSvg || !a || !b) return;
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
          '<rect x="' +
          rx +
          '" y="' +
          ry +
          '" width="' +
          w +
          '" height="' +
          h +
          '" fill="' +
          stroke +
          '" fill-opacity="0.08" stroke="' +
          stroke +
          '" stroke-opacity="0.55" />' +
          '<line x1="' +
          x0 +
          '" y1="' +
          y0 +
          '" x2="' +
          x1 +
          '" y2="' +
          y1 +
          '" stroke="' +
          stroke +
          '" stroke-width="1.5" />';
        const dPrice = b.price - a.price;
        const dPts = Math.round(dPrice / ps);
        let bars = 0;
        if (a.time != null && b.time != null) {
          bars = Math.round(Math.abs(b.time - a.time) / 300);
        }
        const pct = a.price ? (dPrice / a.price) * 100 : 0;
        const sign = dPts > 0 ? "+" : "";
        measureLabel.hidden = false;
        measureLabel.classList.toggle("is-up", up);
        measureLabel.classList.toggle("is-down", !up);
        measureLabel.innerHTML =
          sign +
          dPts +
          " pts · " +
          (dPrice >= 0 ? "+" : "") +
          px2(dPrice) +
          " · " +
          (pct >= 0 ? "+" : "") +
          pct.toFixed(2) +
          "%<br>" +
          bars +
          " bars · " +
          bars * 5 +
          "m";
        const lx = (x0 + x1) / 2;
        const ly = Math.max(y0, y1);
        measureLabel.style.left = Math.round(lx) + "px";
        measureLabel.style.top = Math.round(ly) + "px";
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

      window.addEventListener("resize", function () {
        chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
        requestAnimationFrame(placeFibTags);
        clearMeasure();
      });
    })
    .catch(function (e) {
      sub.textContent = String(e);
    });
})();
