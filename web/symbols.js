/* Shared symbol list for overnight break, Asia box, Asia liquidity, impulse fork, and dawn cross. */
(function () {
  // Dukascopy fx majors, plus gold and bitcoin. Order is the dropdown order.
  const SYMBOLS = [
    ["XAUUSD", "XAUUSD (gold)"],
    ["EURUSD", "EURUSD"],
    ["GBPUSD", "GBPUSD"],
    ["USDJPY", "USDJPY"],
    ["AUDUSD", "AUDUSD"],
    ["NZDUSD", "NZDUSD"],
    ["USDCAD", "USDCAD"],
    ["USDCHF", "USDCHF"],
    ["BTCUSD", "BTCUSD"],
  ];
  // 1 point = 0.1 pip. Gold and bitcoin stay at 1 ($0.01 per point).
  const FX_POINT_SCALE = {
    EURUSD: 0.1,
    GBPUSD: 0.1,
    USDJPY: 0.1,
    AUDUSD: 0.1,
    NZDUSD: 0.1,
    USDCAD: 0.1,
    USDCHF: 0.1,
  };

  function formSymbol(symbol) {
    const s = String(symbol || "")
      .toUpperCase()
      .replace(/[^A-Z]/g, "");
    for (let i = 0; i < SYMBOLS.length; i++) {
      if (SYMBOLS[i][0] === s) return s;
    }
    return "XAUUSD";
  }

  function pointScale(symbol) {
    return FX_POINT_SCALE[formSymbol(symbol)] || 1;
  }

  function optionsHtml() {
    return SYMBOLS.map(function (row) {
      const selected = row[0] === "XAUUSD" ? " selected" : "";
      return '<option value="' + row[0] + '"' + selected + ">" + row[1] + "</option>";
    }).join("");
  }

  window.strategSymbols = {
    formSymbol: formSymbol,
    pointScale: pointScale,
    optionsHtml: optionsHtml,
  };
})();
