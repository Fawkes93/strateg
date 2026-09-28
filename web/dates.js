/* Date fields always show day.month.year. The hidden value stays yyyy-mm-dd
   so every existing reader keeps working on Windows and Mac. */
(function () {
  var proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");

  function isoToDmy(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return "";
    return m[3] + "." + m[2] + "." + m[1];
  }

  function dmyToIso(text) {
    var raw = String(text || "").trim();
    var digits = raw.replace(/\D/g, "");
    var d;
    var mo;
    var y;
    var m = /^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$/.exec(raw);
    if (m) {
      d = m[1];
      mo = m[2];
      y = m[3];
    } else if (digits.length === 8) {
      d = digits.slice(0, 2);
      mo = digits.slice(2, 4);
      y = digits.slice(4);
    } else {
      return "";
    }
    d = d.padStart(2, "0");
    mo = mo.padStart(2, "0");
    var dt = new Date(Date.UTC(+y, +mo - 1, +d));
    if (
      dt.getUTCFullYear() !== +y ||
      dt.getUTCMonth() !== +mo - 1 ||
      dt.getUTCDate() !== +d
    ) {
      return "";
    }
    return y + "-" + mo + "-" + d;
  }

  function bind(input) {
    if (!input || input.dataset.dmyBound) return;
    if (input.type !== "date") return;
    input.dataset.dmyBound = "1";
    var text = document.createElement("input");
    text.type = "text";
    text.className = "dmy-date";
    text.placeholder = "dd.mm.yyyy";
    text.spellcheck = false;
    text.autocomplete = "off";
    text.maxLength = 10;
    text.title = "Day.month.year. Same order on Windows and Mac. Example: 01.05.2025";
    text.value = isoToDmy(proto.get.call(input));
    input.classList.add("dmy-native");
    input.insertAdjacentElement("afterend", text);

    function writeIso(iso) {
      if (proto.get.call(input) === iso) return;
      proto.set.call(input, iso);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    text.addEventListener("input", function () {
      var iso = dmyToIso(text.value);
      if (iso) writeIso(iso);
      else if (!text.value.trim()) writeIso("");
    });
    text.addEventListener("blur", function () {
      var iso = dmyToIso(text.value);
      if (!text.value.trim()) {
        writeIso("");
        text.classList.remove("dmy-bad");
        return;
      }
      if (!iso) {
        text.classList.add("dmy-bad");
        text.value = isoToDmy(proto.get.call(input));
        text.classList.remove("dmy-bad");
        return;
      }
      text.classList.remove("dmy-bad");
      text.value = isoToDmy(iso);
      writeIso(iso);
    });

    Object.defineProperty(input, "value", {
      configurable: true,
      get: function () {
        return proto.get.call(input);
      },
      set: function (v) {
        proto.set.call(input, v == null ? "" : String(v));
        text.value = isoToDmy(proto.get.call(input));
      },
    });
  }

  function scan(root) {
    var list = [];
    if (root && root.matches && root.matches("input[type='date']")) list.push(root);
    if (root && root.querySelectorAll) {
      root.querySelectorAll("input[type='date']").forEach(function (el) {
        list.push(el);
      });
    }
    list.forEach(bind);
  }

  scan(document);
  var obs = new MutationObserver(function (records) {
    records.forEach(function (rec) {
      rec.addedNodes.forEach(function (node) {
        if (node.nodeType === 1) scan(node);
      });
    });
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });
})();
