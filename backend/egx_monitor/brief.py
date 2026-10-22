"""Rule-based market commentary built from the current snapshot.

No AI service is called: the text is assembled from the numbers on screen, so it
can never invent prices. Swap `build_brief` for an LLM call if you want prose.
"""

from __future__ import annotations


def _fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.2f}%"


def _fmt_egp(x: float | None) -> str:
    if not x:
        return "n/a"
    for unit, div in (("bn", 1e9), ("m", 1e6), ("k", 1e3)):
        if x >= div:
            return f"EGP {x / div:,.2f}{unit}"
    return f"EGP {x:,.0f}"


def _names(rows: list[dict], n: int = 3) -> str:
    return ", ".join(f"{r['symbol']} {_fmt_pct(r['changePct'])}" for r in rows[:n]) or "none"


def build_brief(snap: dict, kind: str) -> str:
    idx = {q["symbol"]: q for q in snap["indices"]}
    egx30 = idx.get("EGX30")
    egx70 = idx.get("EGX70EWI")
    b = snap["breadth"]
    sectors = [s for s in snap["sectors"] if s["changePct"] is not None]
    usd = next((q for q in snap["fx"] if q["symbol"] == "USDEGP"), None)
    status = snap["market"]["state"].lower()

    if kind == "sectors":
        if not sectors:
            return "SECTOR READ — no sector data available yet."
        ranked = sorted(sectors, key=lambda s: s["changePct"], reverse=True)
        up = [s for s in ranked if s["changePct"] > 0]
        top, bottom = ranked[0], ranked[-1]
        return (
            f"SECTOR READ — {len(up)} of {len(ranked)} sectors are higher. "
            f"{top['sector']} leads at {_fmt_pct(top['changePct'])} (biggest name: {top['leader']}), "
            f"while {bottom['sector']} lags at {_fmt_pct(bottom['changePct'])} (led by {bottom['leader']}). "
            f"The heaviest sector by market cap, {sectors[0]['sector']}, is {_fmt_pct(sectors[0]['changePct'])} "
            f"and sets the tone for the EGX 30."
        )

    if kind == "risk":
        notes = []
        if egx30 and egx30["changePct"] is not None and abs(egx30["changePct"]) >= 1.5:
            notes.append(f"EGX 30 has moved {_fmt_pct(egx30['changePct'])} — a large daily swing for the benchmark.")
        if egx30 and egx70 and egx30["changePct"] is not None and egx70["changePct"] is not None:
            gap = egx30["changePct"] - egx70["changePct"]
            if abs(gap) >= 0.75:
                lead = "large caps" if gap > 0 else "small/mid caps"
                notes.append(f"Large caps and small caps diverge by {abs(gap):.2f} pts; {lead} are leading.")
        if usd and usd["changePct"] is not None and abs(usd["changePct"]) >= 0.3:
            notes.append(f"USD/EGP is {_fmt_pct(usd['changePct'])} at {usd['last']:.2f}; currency moves reprice dollar earners and importers.")
        spikes = [g for g in snap["gainers"] if g["changePct"] and g["changePct"] >= 15]
        if spikes:
            notes.append(f"Limit-style moves on {', '.join(s['symbol'] for s in spikes[:4])} — check liquidity before chasing.")
        if b["advancers"] + b["decliners"] and b["decliners"] > 2 * max(b["advancers"], 1):
            notes.append("Breadth is weak: decliners outnumber advancers more than 2 to 1.")
        if not notes:
            notes.append("No unusual moves flagged: index, breadth and currency are within normal ranges.")
        return "RISK NOTES — " + " ".join(notes)

    # default: market brief
    parts = [f"MARKET BRIEF — The market is {status}."]
    if egx30 and egx30["last"] is not None:
        parts.append(f"EGX 30 is at {egx30['last']:,.2f} ({_fmt_pct(egx30['changePct'])}).")
    if egx70 and egx70["last"] is not None:
        parts.append(f"The broader EGX 70 EWI is {_fmt_pct(egx70['changePct'])}.")
    if b["advancers"] or b["decliners"]:
        parts.append(
            f"Breadth: {b['advancers']} advancers vs {b['decliners']} decliners, "
            f"turnover around {_fmt_egp(b['turnover'])}."
        )
    parts.append(f"Top gainers: {_names(snap['gainers'])}. Top losers: {_names(snap['losers'])}.")
    if snap["active"]:
        a = snap["active"][0]
        parts.append(f"Most traded by value: {a['symbol']} ({_fmt_egp(a['value'])}).")
    if usd and usd["last"] is not None:
        parts.append(f"USD/EGP {usd['last']:.2f} ({_fmt_pct(usd['changePct'])}).")
    return " ".join(parts)
