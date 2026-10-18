(function () {
  const params = new URLSearchParams(location.search);
  const tradeId = params.get("trade");
  const el = document.getElementById("crt-chart");
  const title = document.getElementById("crt-title");
  const sub = document.getElementById("crt-sub");
  const legend = document.getElementById("crt-legend");
  const decision = document.getElementById("crt-decision");

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

  fetch("/api/crt/chart-data?trade_id=" + encodeURIComponent(tradeId))
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
        "Run #" + (runId != null ? runId : "—") +
        " · " + (t.local_date || "") +
        " · " + (t.side || "") +
        " · " + (t.entry_reason || "");
      document.title = title.textContent + " — Strateg";
      const ptsN = Number(t.pts);
      const bits = [];
      if (t.exit_reason) bits.push(String(t.exit_reason).toUpperCase());
      if (Number.isFinite(ptsN)) bits.push(Math.round(ptsN) + " pts");
      bits.push("entry " + px2(t.entry) + " → " + px2(t.exit));
      const crl = t.crl != null ? t.crl : (t.extras && t.extras.crl);
      const crh = t.crh != null ? t.crh : (t.extras && t.extras.crh);
      if (crl != null && crh != null) bits.push("CRL " + px2(crl) + " · CRH " + px2(crh));
      const zone = data.timezone || "Europe/Bucharest";
      bits.push((data.tf_min || 5) + "m candles · HTF " + (data.htf_min || 60) + "m · " + zone);
      sub.textContent = bits.join(" · ");
      if (decision) decision.textContent = data.decision || "";
      const back = document.getElementById("crt-back");
      if (back && runId != null) back.href = "/crt/results?run=" + encodeURIComponent(runId);
      if (typeof LightweightCharts === "undefined") {
        sub.textContent += " — chart library failed to load.";
        return;
      }
      if (!data.candles || !data.candles.length) {
        sub.textContent += " — no candles for this trade.";
        return;
      }
      function localParts(ts) {
        const d = new Date(Number(ts) * 1000);
        return {
          date: d.toLocaleDateString("en-GB", { timeZone: zone, day: "2-digit", month: "short" }),
          hm: d.toLocaleTimeString("en-GB", { timeZone: zone, hour: "2-digit", minute: "2-digit", hour12: false }),
        };
      }
      function tickLabel(ts, tickMarkType) {
        const p = localParts(ts);
        if (tickMarkType === 0) {
          return new Date(Number(ts) * 1000).toLocaleDateString("en-GB", { timeZone: zone, year: "numeric" });
        }
        if (tickMarkType === 1 || tickMarkType === 2) return p.date;
        return p.hm;
      }
      const MAGNET_KEY = "strateg_crt_magnet";
      const magnetEl = document.getElementById("crt-magnet");
      let magnetOn = false;
      try { magnetOn = localStorage.getItem(MAGNET_KEY) === "1"; } catch (e) {}
      if (magnetEl) magnetEl.checked = magnetOn;
      function magnetMode(on) {
        if (!LightweightCharts.CrosshairMode) return {};
        return {
          crosshair: {
            mode: on ? LightweightCharts.CrosshairMode.Magnet : LightweightCharts.CrosshairMode.Normal,
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
          try { localStorage.setItem(MAGNET_KEY, on ? "1" : "0"); } catch (e) {}
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
      (data.lines || []).forEach(function (ln) {
        const px = Number(ln.price);
        if (!Number.isFinite(px)) return;
        candleSeries.createPriceLine({
          price: px,
          color: ln.color || "#8b9aab",
          lineWidth: 1,
          lineStyle: ln.dashed ? LightweightCharts.LineStyle.Dashed : LightweightCharts.LineStyle.Solid,
          axisLabelVisible: true,
          title: ln.title || "",
        });
      });
      if (data.markers && data.markers.length) candleSeries.setMarkers(data.markers);
      chart.timeScale().fitContent();

      const wrap = el.parentElement;
      const measureSvg = document.getElementById("crt-measure-svg");
      const measureLabel = document.getElementById("crt-measure-label");
      const measureEl = document.getElementById("crt-measure");
      const barSec = (data.tf_min || 5) * 60;
      const MEASURE_KEY = "strateg_crt_measure";
      let measureOn = true;
      try { if (localStorage.getItem(MEASURE_KEY) === "0") measureOn = false; } catch (e) {}
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
          if (candles[i].time === time) { bar = candles[i]; break; }
        }
        if (!bar) return price;
        const opts = [bar.open, bar.high, bar.low, bar.close];
        let best = opts[0];
        let bestD = Math.abs(price - opts[0]);
        for (let i = 1; i < opts.length; i++) {
          const d = Math.abs(price - opts[i]);
          if (d < bestD) { best = opts[i]; bestD = d; }
        }
        return best;
      }
      function drawMeasure(a, b) {
        if (!measureSvg || !measureLabel || !a || !b) return;
        const up = b.price > a.price;
        const stroke = up ? "#3ecf8e" : "#f07178";
        const rx = Math.min(a.x, b.x);
        const ry = Math.min(a.y, b.y);
        measureSvg.setAttribute("viewBox", "0 0 " + el.clientWidth + " " + el.clientHeight);
        measureSvg.setAttribute("width", String(el.clientWidth));
        measureSvg.setAttribute("height", String(el.clientHeight));
        measureSvg.innerHTML =
          '<rect x="' + rx + '" y="' + ry + '" width="' + Math.abs(b.x - a.x) + '" height="' + Math.abs(b.y - a.y) +
          '" fill="' + stroke + '" fill-opacity="0.08" stroke="' + stroke + '" stroke-opacity="0.55" />' +
          '<line x1="' + a.x + '" y1="' + a.y + '" x2="' + b.x + '" y2="' + b.y +
          '" stroke="' + stroke + '" stroke-width="1.5" />';
        const dPrice = b.price - a.price;
        const dPts = Math.round(dPrice / ps);
        let bars = 0;
        if (a.time != null && b.time != null) bars = Math.round(Math.abs(b.time - a.time) / barSec);
        const pct = a.price ? (dPrice / a.price) * 100 : 0;
        const sign = dPts > 0 ? "+" : "";
        measureLabel.hidden = false;
        measureLabel.classList.toggle("is-up", up);
        measureLabel.classList.toggle("is-down", !up);
        measureLabel.innerHTML =
          sign + dPts + " pts · " +
          (dPrice >= 0 ? "+" : "") + px2(dPrice) + " · " +
          (pct >= 0 ? "+" : "") + pct.toFixed(2) + "%<br>" +
          bars + " bars · " + bars * (data.tf_min || 5) + "m";
        measureLabel.style.left = Math.round((a.x + b.x) / 2) + "px";
        measureLabel.style.top = Math.round(Math.max(a.y, b.y)) + "px";
      }
      let drag = null;
      if (measureSvg) {
        measureSvg.addEventListener("pointerdown", function (ev) {
          if (!measureOn || ev.button !== 0) return;
          const p = localXY(ev);
          const time = chart.timeScale().coordinateToTime(p.x);
          let price = snapPrice(time, candleSeries.coordinateToPrice(p.y));
          const y = candleSeries.priceToCoordinate(price);
          const x = time != null ? chart.timeScale().timeToCoordinate(time) : p.x;
          drag = { time: time, price: price, x: x == null ? p.x : x, y: y == null ? p.y : y };
          measureSvg.setPointerCapture(ev.pointerId);
          ev.preventDefault();
        });
        measureSvg.addEventListener("pointermove", function (ev) {
          if (!drag) return;
          const p = localXY(ev);
          const time = chart.timeScale().coordinateToTime(p.x);
          let price = snapPrice(time, candleSeries.coordinateToPrice(p.y));
          const y = candleSeries.priceToCoordinate(price);
          const x = time != null ? chart.timeScale().timeToCoordinate(time) : p.x;
          drawMeasure(drag, { time: time, price: price, x: x == null ? p.x : x, y: y == null ? p.y : y });
        });
        measureSvg.addEventListener("pointerup", function () { drag = null; });
        measureSvg.addEventListener("pointercancel", function () { drag = null; });
      }
      window.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") clearMeasure();
      });
      if (measureEl) {
        measureEl.addEventListener("change", function () {
          const on = !!measureEl.checked;
          try { localStorage.setItem(MEASURE_KEY, on ? "1" : "0"); } catch (e) {}
          setMeasureMode(on);
        });
      }
      setMeasureMode(measureOn);
      legend.innerHTML = "";
      [
        ["#d98a3a", "Dealing range"],
        ["#e6b450", "CRH"],
        ["#8b9aab", "CRL"],
        ["#c084fc", "Fair value gap"],
        ["#f07178", "Stop"],
        ["#3d9cf0", "1:1"],
        ["#3ecf8e", "Runner"],
      ].forEach(function (item) {
        const li = document.createElement("li");
        li.innerHTML = '<span class="swatch" style="background:' + item[0] + '"></span>' + item[1];
        legend.appendChild(li);
      });
    })
    .catch(function (err) {
      sub.textContent = String(err && err.message ? err.message : err);
    });
})();
