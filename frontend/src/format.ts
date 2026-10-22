// Number formatting. Every helper tolerates null / NaN / Infinity and prints "—"
// instead, so a bad tick can never show up as "+Infinity%".

const ok = (x: number | null | undefined): x is number => typeof x === "number" && Number.isFinite(x);

export function price(x: number | null | undefined, digits?: number): string {
  if (!ok(x)) return "—";
  const d = digits ?? (Math.abs(x) >= 1000 ? 2 : Math.abs(x) < 10 ? 3 : 2);
  return x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

export function pct(x: number | null | undefined): string {
  return ok(x) ? `${x > 0 ? "+" : ""}${x.toFixed(2)}%` : "—";
}

export function signed(x: number | null | undefined, digits = 2): string {
  return ok(x) ? `${x > 0 ? "+" : ""}${x.toFixed(digits)}` : "—";
}

export function compact(x: number | null | undefined): string {
  if (!ok(x)) return "—";
  const units: [number, string][] = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];
  for (const [div, u] of units) if (Math.abs(x) >= div) return `${(x / div).toFixed(2)}${u}`;
  return x.toFixed(0);
}

export function dir(x: number | null | undefined): "up" | "down" | "flat" {
  if (!ok(x) || x === 0) return "flat";
  return x > 0 ? "up" : "down";
}

export function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}
