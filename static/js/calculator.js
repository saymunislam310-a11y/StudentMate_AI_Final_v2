(() => {
  "use strict";

  const screen = document.getElementById("calcExpression");
  const result = document.getElementById("calcResult");
  const status = document.getElementById("calcStatus");
  const angleLabel = document.getElementById("angleLabel");
  const shiftLabel = document.getElementById("shiftLabel");
  if (!screen || !result) return;

  let angleMode = "DEG";
  let shift = false;
  let memory = 0;
  let ans = 0;
  let formatMode = "NORM";

  const fact = (n) => {
    if (!Number.isFinite(n) || n < 0 || Math.floor(n) !== n || n > 170) throw new Error("Factorial: whole numbers 0–170 only");
    let out = 1;
    for (let i = 2; i <= n; i++) out *= i;
    return out;
  };
  const toRad = (x) => angleMode === "DEG" ? x * Math.PI / 180 : angleMode === "GRAD" ? x * Math.PI / 200 : x;
  const fromRad = (x) => angleMode === "DEG" ? x * 180 / Math.PI : angleMode === "GRAD" ? x * 200 / Math.PI : x;
  const root = (x, n) => Math.sign(x) * Math.pow(Math.abs(x), 1 / n);

  const f = {
    sin: x => Math.sin(toRad(x)), cos: x => Math.cos(toRad(x)), tan: x => Math.tan(toRad(x)),
    asin: x => fromRad(Math.asin(x)), acos: x => fromRad(Math.acos(x)), atan: x => fromRad(Math.atan(x)),
    log: x => Math.log10(x), ln: x => Math.log(x), sqrt: x => Math.sqrt(x), cbrt: x => Math.cbrt(x),
    exp: x => Math.exp(x), pow10: x => Math.pow(10, x), abs: x => Math.abs(x),
    root: (x, n) => root(x, n), fact, pct: x => x / 100
  };

  function normalize(raw) {
    let s = String(raw || "").trim();
    if (!s) return "0";
    s = s.replace(/[×]/g, "*").replace(/[÷]/g, "/").replace(/[−–—]/g, "-");
    s = s.replace(/π/g, "PI").replace(/\be\b/g, "E").replace(/Ans/g, "ANS");
    s = s.replace(/√\s*\(/g, "sqrt(");
    s = s.replace(/\^2\b/g, "**2").replace(/\^3\b/g, "**3");
    s = s.replace(/(\d+(?:\.\d+)?)%/g, "pct($1)");
    s = s.replace(/(\d+(?:\.\d+)?)!/g, "fact($1)");
    s = s.replace(/1\/(?![*/])/g, "1/ ");
    s = s.replace(/\^/g, "**");
    s = s.replace(/\s+/g, " ").trim();
    return s;
  }

  function evaluate(raw) {
    let s = normalize(raw);
    if (!/^[0-9+\-*/().,\sA-Za-z_]+$/.test(s)) throw new Error("Invalid characters");
    if (/\b(?:constructor|prototype|window|document|globalThis|Function|eval|fetch|XMLHttpRequest|import|require)\b/i.test(s)) throw new Error("Unsupported expression");
    const names = ["sin","cos","tan","asin","acos","atan","log","ln","sqrt","cbrt","exp","pow10","abs","root","fact","pct"];
    const fn = new Function(...names, "PI", "E", "ANS", `return (${s});`);
    const value = fn(...names.map(k => f[k]), Math.PI, Math.E, ans);
    if (!Number.isFinite(value)) throw new Error("Math error");
    return value;
  }

  function format(value) {
    if (!Number.isFinite(value)) return "Error";
    let v = Math.abs(value) < 1e-12 ? 0 : value;
    if (formatMode === "FIX") return v.toFixed(6);
    if (formatMode === "SCI") return v.toExponential(8).replace(/\.0+e/, "e");
    return Number(v.toPrecision(12)).toString();
  }

  function setStatus(message = "") {
    angleLabel.textContent = angleMode;
    shiftLabel.textContent = `SHIFT: ${shift ? "ON" : "OFF"}`;
    status.textContent = `${angleMode} · ${formatMode} · ${memory !== 0 ? "M" : ""}${message ? " · " + message : ""}`;
  }

  function calculate() {
    try {
      const value = evaluate(screen.textContent === "0" ? "0" : screen.textContent);
      ans = value;
      result.textContent = format(value);
      result.dataset.error = "";
      setStatus();
    } catch (e) {
      result.textContent = e?.message || "Error";
      result.dataset.error = "1";
      setStatus("ERROR");
    }
  }

  function insert(value) {
    if (screen.textContent === "0") screen.textContent = "";
    screen.textContent += value;
    if (shift) toggleShift(false);
  }

  function toggleShift(force) {
    shift = typeof force === "boolean" ? force : !shift;
    document.querySelector('[data-action="shift"]').classList.toggle("shift-on", shift);
    document.querySelectorAll('[data-action="shiftable"]').forEach(btn => {
      const label = shift ? btn.dataset.shift : btn.dataset.normal;
      if (label === "Ans") btn.textContent = "Ans";
      else if (label) {
        if (label === "asin(") btn.textContent = "sin⁻¹";
        else if (label === "acos(") btn.textContent = "cos⁻¹";
        else if (label === "atan(") btn.textContent = "tan⁻¹";
        else if (label === "^3") btn.textContent = "x³";
        else if (label === "pow10(") btn.textContent = "10ˣ";
        else if (label === "cbrt(") btn.textContent = "∛";
        else if (label === "root(") btn.textContent = "ʸ√x";
        else if (label === "%") btn.textContent = "%";
        else if (label === "exp(") btn.textContent = "eˣ";
        else if (label === "abs(") btn.textContent = "abs";
        else btn.textContent = label.replace("(", "");
      }
    });
    setStatus();
  }

  function handleShiftable(btn) {
    const value = shift ? btn.dataset.shift : btn.dataset.normal;
    if (!value) return;
    if (value === "Ans") insert("Ans");
    else if (value === "1/") insert("(1/");
    else if (value === "^") insert("^");
    else if (value === "root(") insert("root(");
    else if (value === "%") insert("%");
    else insert(value);
  }

  document.querySelectorAll("[data-angle]").forEach(btn => btn.addEventListener("click", () => {
    angleMode = btn.dataset.angle;
    document.querySelectorAll("[data-angle]").forEach(b => b.classList.toggle("active", b === btn));
    setStatus();
  }));

  document.querySelectorAll("[data-mode]").forEach(btn => btn.addEventListener("click", () => {
    formatMode = btn.dataset.mode;
    if (formatMode === "FIX") formatMode = "FIX";
    setStatus();
    if (screen.textContent !== "0") calculate();
  }));

  document.querySelectorAll(".calc-key").forEach(btn => btn.addEventListener("click", () => {
    const action = btn.dataset.action;
    if (action === "shift") { toggleShift(); return; }
    if (action === "clear") { screen.textContent = "0"; result.textContent = "0"; result.dataset.error=""; toggleShift(false); return; }
    if (action === "back") { screen.textContent = screen.textContent.length <= 1 ? "0" : screen.textContent.slice(0,-1); return; }
    if (action === "equals") { calculate(); return; }
    if (action === "shiftable") { handleShiftable(btn); return; }
    if (action === "sign") {
      const s = screen.textContent;
      screen.textContent = s.startsWith("-") ? s.slice(1) : `-(${s})`;
      return;
    }
    if (action === "memory-clear") { memory = 0; setStatus(); return; }
    if (action === "memory-recall") { insert(format(memory)); return; }
    if (action === "memory-add") { memory += evaluate(screen.textContent); setStatus(); return; }
    if (action === "memory-sub") { memory -= evaluate(screen.textContent); setStatus(); return; }
    if (action === "memory-store") { memory = evaluate(screen.textContent); setStatus(); return; }
    if (action === "reset-format") { formatMode = "NORM"; setStatus(); calculate(); return; }
    if (action === "copy") {
      navigator.clipboard?.writeText(result.textContent).then(() => setStatus("COPIED")).catch(() => setStatus("COPY BLOCKED"));
      return;
    }
    if (btn.dataset.value) insert(btn.dataset.value);
  }));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); calculate(); return; }
    if (e.key === "Escape") { screen.textContent = "0"; result.textContent = "0"; return; }
    const allowed = "0123456789.+-*/()%^";
    if (allowed.includes(e.key)) { e.preventDefault(); insert(e.key); }
    if (e.key.toLowerCase() === "s" && !e.ctrlKey && !e.metaKey) { e.preventDefault(); toggleShift(); }
  });

  setStatus();
})();
