(function (global) {
  const pickers = [];

  function loadedNote(result) {
    if (!result || !result.loaded_from) return "";
    return " · loaded " + result.loaded_from;
  }

  function optionLabel(f) {
    return f.label || f.name || "saved run";
  }

  async function listKind(kind) {
    const r = await fetch("/api/results?kind=" + encodeURIComponent(kind));
    if (!r.ok) {
      const err = await r.json().catch(function () {
        return {};
      });
      throw new Error(err.detail || "Could not list saved runs");
    }
    return r.json();
  }

  async function refreshSelect(sel, kind) {
    if (!sel) return;
    const prev = sel.value;
    let files = [];
    try {
      const data = await listKind(kind);
      files = data.files || [];
    } catch (e) {
      sel.innerHTML = "";
      const o = document.createElement("option");
      o.value = "";
      o.textContent = "Saved runs unavailable";
      sel.appendChild(o);
      return;
    }
    sel.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = files.length ? "Saved runs…" : "No saved runs";
    sel.appendChild(ph);
    files.forEach(function (f) {
      const o = document.createElement("option");
      o.value = f.name;
      o.textContent = optionLabel(f);
      sel.appendChild(o);
    });
    if (prev) sel.value = prev;
  }

  function bindPicker(opts) {
    const sel = document.getElementById(opts.selectId);
    const btn = document.getElementById(opts.buttonId);
    const state = { viewingSaved: false, kind: opts.kind };
    if (!sel || !btn) {
      return {
        isViewingSaved: function () {
          return false;
        },
        clearViewing: function () {},
        refresh: function () {
          return Promise.resolve();
        },
      };
    }
    pickers.push({ sel: sel, kind: opts.kind, state: state });
    refreshSelect(sel, opts.kind).catch(function () {});

    btn.addEventListener("click", async function () {
      const name = sel.value;
      if (!name) {
        alert("Pick a saved run first.");
        return;
      }
      btn.disabled = true;
      try {
        const r = await fetch(
          "/api/results/file?name=" + encodeURIComponent(name)
        );
        if (!r.ok) {
          const err = await r.json().catch(function () {
            return {};
          });
          alert(err.detail || "Could not load that file");
          return;
        }
        const json = await r.json();
        json.loaded_from = name;
        state.viewingSaved = true;
        if (opts.onLoaded) opts.onLoaded(json, { name: name });
        fetch("/api/results/load", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: opts.kind, name: name }),
        }).catch(function () {});
      } catch (e) {
        alert(String(e));
      } finally {
        btn.disabled = false;
      }
    });

    return {
      isViewingSaved: function () {
        return state.viewingSaved;
      },
      clearViewing: function () {
        state.viewingSaved = false;
      },
      refresh: function () {
        return refreshSelect(sel, opts.kind);
      },
    };
  }

  const nav = document.querySelector("nav.main-tabs");
  if (nav) {
    nav.addEventListener("click", function (e) {
      const btn = e.target && e.target.closest && e.target.closest(".main-tab");
      if (!btn) return;
      pickers.forEach(function (p) {
        refreshSelect(p.sel, p.kind).catch(function () {});
      });
    });
  }

  function playDone() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = playDone._ctx || new Ctx();
      playDone._ctx = ctx;
      if (ctx.state === "suspended") ctx.resume();
      var now = ctx.currentTime;
      [523.25, 659.25].forEach(function (freq, i) {
        var o = ctx.createOscillator();
        var g = ctx.createGain();
        o.type = "sine";
        o.frequency.value = freq;
        g.gain.setValueAtTime(0.0001, now);
        g.gain.exponentialRampToValueAtTime(0.12, now + 0.02 + i * 0.12);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.35 + i * 0.15);
        o.connect(g);
        g.connect(ctx.destination);
        o.start(now + i * 0.12);
        o.stop(now + 0.45 + i * 0.15);
      });
    } catch (e) {
      /* autoplay policies / no audio — ignore */
    }
  }

  global.StrategSaved = {
    bindPicker: bindPicker,
    loadedNote: loadedNote,
    playDone: playDone,
  };
})(window);
