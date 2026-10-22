import "./style.css";
import { api } from "./api";
import { PriceChart } from "./chart";
import { compact, dir, esc, pct, price, signed } from "./format";
import type { Quote, Snapshot } from "./types";

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

const state = {
  snap: null as Snapshot | null,
  selected: localStorage.getItem("egx.selected") || "EGX30",
  range: "1D",
  leftTab: "watch",
  rightTab: "gainers",
  briefKind: "market",
  tapePaused: false,
};

const chart = new PriceChart($("chart"));

// ---------------------------------------------------------------- helpers
function findQuote(symbol: string): Quote | undefined {
  const s = state.snap;
  if (!s) return undefined;
  return [...s.indices, ...s.watchlist, ...s.tape, ...s.gainers, ...s.losers, ...s.active, ...s.fx].find(
    (q) => q.symbol === symbol,
  );
}

function row(q: Quote, opts: { removable?: boolean; extra?: string } = {}): string {
  const d = dir(q.changePct);
  return `
    <div class="row ${q.symbol === state.selected ? "selected" : ""}" data-symbol="${esc(q.symbol)}" data-kind="${q.kind}">
      <span class="chg ${d} mono">${pct(q.changePct)}</span>
      <span class="who"><b class="mono">${esc(q.symbol)}</b><small>${esc(q.name)}</small></span>
      <span class="px mono">${price(q.last)}${opts.extra ? `<small>${opts.extra}</small>` : ""}</span>
      ${opts.removable ? `<button class="rm" data-remove="${esc(q.symbol)}" title="Remove">×</button>` : ""}
    </div>`;
}

// ---------------------------------------------------------------- renderers
function renderHeader(s: Snapshot): void {
  $("indices").innerHTML = s.indices
    .map((q) => `
      <button class="index-card ${q.symbol === state.selected ? "selected" : ""}" data-symbol="${q.symbol}">
        <span class="muted">${esc(q.name)}</span>
        <b class="${dir(q.changePct)}">${price(q.last, 2)}</b>
        <small class="${dir(q.changePct)}">${pct(q.changePct)}</small>
      </button>`)
    .join("");

  const src = $("source");
  src.className = `chip mono ${s.source.live ? "live" : "sim"}`;
  src.textContent = s.source.live ? `Live · ${s.source.name}` : "Data shown is simulated";
  src.title = s.source.error ? `Live source failed: ${s.source.error}` : `Updated ${new Date(s.updatedAt * 1000).toLocaleTimeString()}`;

  const st = $("status");
  st.className = `status mono ${s.market.state.toLowerCase().replace("-", "")}`;
  st.innerHTML = `<i></i>${s.market.state}`;
  st.title = `EGX session: ${s.market.session}`;
}

function renderTape(s: Snapshot): void {
  const items = s.tape
    .map((q) => `<span><b>${esc(q.symbol)}</b> ${price(q.last)} <em class="${dir(q.changePct)}">${pct(q.changePct)}</em></span>`)
    .join("");
  // Duplicate the content so the CSS marquee loops seamlessly.
  $("tape").innerHTML = items + items;
}

function renderLeft(s: Snapshot): void {
  $("watch-count").textContent = `${s.watchlistSymbols.length} / ${s.maxWatchlist}`;
  $("add-form").style.display = state.leftTab === "watch" ? "" : "none";
  $("add-msg").style.display = state.leftTab === "watch" ? "" : "none";
  if (state.leftTab === "fx") {
    $("left-list").innerHTML = s.fx.map((q) => row(q)).join("");
    return;
  }
  const missing = s.watchlistSymbols.filter((sym) => !s.watchlist.some((q) => q.symbol === sym));
  $("left-list").innerHTML =
    s.watchlist.map((q) => row(q, { removable: true })).join("") +
    missing.map((m) => `<div class="row dim"><span></span><span class="who"><b class="mono">${esc(m)}</b><small>not found on EGX</small></span><span></span><button class="rm" data-remove="${esc(m)}">×</button></div>`).join("");
  $<HTMLDataListElement>("universe").innerHTML = s.universe
    .map((u) => `<option value="${esc(u.symbol)}">${esc(u.name)}</option>`)
    .join("");
}

function renderRight(s: Snapshot): void {
  const el = $("right-list");
  if (state.rightTab === "breadth") {
    const b = s.breadth;
    const total = Math.max(1, b.advancers + b.decliners + b.unchanged);
    el.innerHTML = `
      <div class="breadth">
        <div class="bar"><i class="up-bg" style="width:${(b.advancers / total) * 100}%"></i><i class="flat-bg" style="width:${(b.unchanged / total) * 100}%"></i><i class="down-bg" style="width:${(b.decliners / total) * 100}%"></i></div>
        <dl class="mono">
          <dt>Advancers</dt><dd class="up">${b.advancers}</dd>
          <dt>Decliners</dt><dd class="down">${b.decliners}</dd>
          <dt>Unchanged</dt><dd>${b.unchanged}</dd>
          <dt>Listed</dt><dd>${b.listed}</dd>
          <dt>Turnover</dt><dd>EGP ${compact(b.turnover)}</dd>
          <dt>A/D ratio</dt><dd>${b.decliners ? (b.advancers / b.decliners).toFixed(2) : "—"}</dd>
        </dl>
      </div>`;
    return;
  }
  const list = state.rightTab === "gainers" ? s.gainers : state.rightTab === "losers" ? s.losers : s.active;
  el.innerHTML = list
    .map((q) => row(q, { extra: state.rightTab === "active" ? `EGP ${compact(q.value)}` : `vol ${compact(q.volume)}` }))
    .join("");
}

function renderHeat(s: Snapshot): void {
  const max = Math.max(1, ...s.sectors.map((x) => Math.abs(x.changePct)));
  $("heat").innerHTML = s.sectors
    .slice(0, 12)
    .map((x) => {
      const strength = Math.min(1, Math.abs(x.changePct) / max);
      const color = x.changePct >= 0 ? "var(--up-rgb)" : "var(--down-rgb)";
      return `
        <div class="tile" style="background: rgba(${color}, ${0.08 + strength * 0.32})" data-symbol="${esc(x.leader)}" title="${x.count} stocks · biggest: ${esc(x.leader)} · click to chart it">
          <span class="mono small">${esc(x.sector)}</span>
          <span class="muted mono small">${x.count} stocks · ${esc(x.leader)}</span>
          <b class="mono ${dir(x.changePct)}">${pct(x.changePct)}</b>
        </div>`;
    })
    .join("");
}

function renderSelected(): void {
  const q = findQuote(state.selected);
  $("sel-symbol").textContent = state.selected;
  $("sel-name").textContent = q ? `· ${q.name}` : "";
  const d = dir(q?.changePct);
  $("sel-price").className = `price mono ${d}`;
  $("sel-price").textContent = price(q?.last);
  $("sel-change").className = `mono ${d}`;
  $("sel-change").textContent = q ? `${pct(q.changePct)}  ${signed(q.change)}` : "";
  $("sel-stats").innerHTML = q
    ? `O ${price(q.open)} &nbsp; H ${price(q.high)} &nbsp; L ${price(q.low)} &nbsp; <span class="muted">PREV</span> ${price(q.prevClose)}` +
      (q.volume ? ` &nbsp; <span class="muted">VOL</span> ${compact(q.volume)}` : "") +
      (q.sector ? ` &nbsp; <span class="muted">${esc(q.sector)}</span>` : "")
    : "";
}

function renderAll(): void {
  const s = state.snap;
  if (!s) return;
  renderHeader(s);
  renderTape(s);
  renderLeft(s);
  renderRight(s);
  renderHeat(s);
  renderSelected();
}

// ---------------------------------------------------------------- data loading
async function loadSnapshot(force = false): Promise<void> {
  try {
    state.snap = await api.snapshot(force);
    renderAll();
  } catch (err) {
    $("source").className = "chip mono sim";
    $("source").textContent = "Backend not reachable";
    console.error(err);
  }
}

let chartReq = 0;
async function loadChart(): Promise<void> {
  const req = ++chartReq;
  const msg = $("chart-msg");
  msg.textContent = "Loading…";
  try {
    const data = await api.chart(state.selected, state.range);
    if (req !== chartReq) return; // a newer request superseded this one
    if (!data.bars.length) {
      chart.clear();
      msg.textContent = "No price history for this symbol.";
      return;
    }
    const q = findQuote(state.selected);
    chart.setData(data.bars, q?.prevClose ?? null, state.range === "1D" || state.range === "1W");
    msg.textContent = data.source.live ? "" : "Simulated chart";
  } catch (err) {
    if (req !== chartReq) return;
    chart.clear();
    msg.textContent = `Chart unavailable: ${(err as Error).message.slice(0, 120)}`;
  }
}

async function loadBrief(): Promise<void> {
  const el = $("brief");
  el.classList.add("loading");
  try {
    const { text } = await api.brief(state.briefKind);
    el.textContent = text;
  } catch {
    el.textContent = "Analysis unavailable.";
  } finally {
    el.classList.remove("loading");
  }
}

function select(symbol: string): void {
  if (!symbol || symbol === state.selected) return;
  state.selected = symbol;
  localStorage.setItem("egx.selected", symbol);
  renderAll();
  void loadChart();
}

async function saveWatchlist(symbols: string[]): Promise<void> {
  await api.setWatchlist(symbols);
  await loadSnapshot(true);
}

// ---------------------------------------------------------------- events
document.body.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  const remove = target.closest<HTMLElement>("[data-remove]");
  if (remove && state.snap) {
    e.stopPropagation();
    void saveWatchlist(state.snap.watchlistSymbols.filter((s) => s !== remove.dataset.remove));
    return;
  }
  const sym = target.closest<HTMLElement>("[data-symbol]");
  if (sym && sym.dataset.kind !== "fx") select(sym.dataset.symbol!);
});

function tabs(navId: string, attr: string, onChange: (value: string) => void): void {
  $(navId).addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(`button[data-${attr}]`);
    if (!btn) return;
    $(navId).querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
    onChange(btn.dataset[attr]!);
  });
}
tabs("left-tabs", "tab", (v) => { state.leftTab = v; renderAll(); });
tabs("right-tabs", "tab", (v) => { state.rightTab = v; renderAll(); });
tabs("ranges", "range", (v) => { state.range = v; void loadChart(); });
tabs("brief-kinds", "kind", (v) => { state.briefKind = v; void loadBrief(); });
$("regen").addEventListener("click", async () => { await loadSnapshot(true); void loadBrief(); });

$("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const s = state.snap;
  const input = $<HTMLInputElement>("add-input");
  const msg = $("add-msg");
  const q = input.value.trim().toUpperCase();
  if (!s || !q) return;
  const match =
    s.universe.find((u) => u.symbol === q) ??
    s.universe.find((u) => u.name.toUpperCase().includes(q));
  if (!match) { msg.textContent = `No EGX listing matches “${input.value}”.`; return; }
  if (s.watchlistSymbols.includes(match.symbol)) { msg.textContent = `${match.symbol} is already on the list.`; return; }
  if (s.watchlistSymbols.length >= s.maxWatchlist) { msg.textContent = "Watchlist is full."; return; }
  input.value = "";
  msg.textContent = `Added ${match.symbol} · ${match.name}`;
  await saveWatchlist([...s.watchlistSymbols, match.symbol]);
  select(match.symbol);
});

$("tape-toggle").addEventListener("click", () => {
  state.tapePaused = !state.tapePaused;
  $("tape").classList.toggle("paused", state.tapePaused);
  $("tape-toggle").textContent = state.tapePaused ? "Play tape" : "Pause tape";
});

function setTheme(theme: string): void {
  document.documentElement.dataset.theme = theme;
  $("theme").textContent = theme === "dark" ? "☀" : "☾";
  chart.applyTheme();
}
$("theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  setTheme(next);
  void api.setTheme(next);
  void loadChart();
});

// Cairo clock ticks every second, independent of data refreshes.
const clockFmt = new Intl.DateTimeFormat("en-GB", { timeZone: "Africa/Cairo", hour: "2-digit", minute: "2-digit", second: "2-digit" });
setInterval(() => { $("clock").textContent = `${clockFmt.format(new Date())} CAI`; }, 1000);
$("clock").textContent = `${clockFmt.format(new Date())} CAI`;

// ---------------------------------------------------------------- boot + refresh loop
async function boot(): Promise<void> {
  api.settings().then((s) => setTheme(s.theme)).catch(() => setTheme("dark"));
  await loadSnapshot();
  await Promise.all([loadChart(), loadBrief()]);
  scheduleRefresh();
}

function scheduleRefresh(): void {
  // Refresh quickly while EGX is trading, slowly otherwise (the backend caches too).
  const open = state.snap?.market.isOpen ?? false;
  setTimeout(async () => {
    await loadSnapshot();
    if (open) { void loadChart(); void loadBrief(); }
    scheduleRefresh();
  }, open ? 15_000 : 120_000);
}

void boot();
