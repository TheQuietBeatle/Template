import {
  AreaSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Bar } from "./types";

// lightweight-charts renders timestamps as UTC, so shift each bar into Cairo time.
const cairoParts = new Intl.DateTimeFormat("en-US", {
  timeZone: "Africa/Cairo",
  hourCycle: "h23",
  year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
});
function toCairo(t: number): UTCTimestamp {
  const p = Object.fromEntries(cairoParts.formatToParts(new Date(t * 1000)).map((x) => [x.type, x.value]));
  return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) / 1000) as UTCTimestamp;
}

function css(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export class PriceChart {
  private chart: IChartApi;
  private area: ISeriesApi<"Area">;
  private ma: ISeriesApi<"Line">;
  private vol: ISeriesApi<"Histogram">;
  private prevLine: IPriceLine | null = null;

  constructor(el: HTMLElement) {
    this.chart = createChart(el, { autoSize: true });
    this.area = this.chart.addSeries(AreaSeries, { lineWidth: 2, priceLineVisible: false });
    this.ma = this.chart.addSeries(LineSeries, {
      lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    });
    this.vol = this.chart.addSeries(HistogramSeries, { priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false });
    this.chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    this.chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.25 } });
    this.applyTheme();
  }

  applyTheme(): void {
    const text = css("--muted");
    const grid = css("--grid");
    this.chart.applyOptions({
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: text, fontFamily: "JetBrains Mono, monospace" },
      grid: { vertLines: { color: grid, style: LineStyle.Dotted }, horzLines: { color: grid, style: LineStyle.Dotted } },
      rightPriceScale: { borderColor: grid },
      timeScale: { borderColor: grid, timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: text }, horzLine: { color: text } },
    });
    this.ma.applyOptions({ color: css("--accent") });
  }

  setData(bars: Bar[], prevClose: number | null, intraday: boolean): void {
    const last = bars.at(-1)?.c ?? 0;
    const base = intraday && prevClose ? prevClose : bars[0]?.o ?? last;
    const up = last >= base;
    const color = up ? css("--up") : css("--down");
    this.area.applyOptions({ lineColor: color, topColor: `${color}55`, bottomColor: `${color}05` });

    const times = bars.map((b) => toCairo(b.t));
    this.area.setData(bars.map((b, i) => ({ time: times[i], value: b.c })));
    this.vol.setData(bars.map((b, i) => ({
      time: times[i], value: b.v, color: b.c >= b.o ? `${css("--up")}88` : `${css("--down")}88`,
    })));
    // Running VWAP for intraday stocks, 20-bar moving average otherwise (indices have no volume).
    const vwap = intraday && bars.some((b) => b.v > 0);
    let pv = 0, vv = 0;
    this.ma.setData(bars.map((b, i) => {
      if (vwap) {
        pv += ((b.h + b.l + b.c) / 3) * b.v; vv += b.v;
        return { time: times[i], value: vv ? pv / vv : b.c };
      }
      const win = bars.slice(Math.max(0, i - 19), i + 1);
      return { time: times[i], value: win.reduce((s, x) => s + x.c, 0) / win.length };
    }));

    if (this.prevLine) this.area.removePriceLine(this.prevLine);
    this.prevLine = intraday && prevClose
      ? this.area.createPriceLine({ price: prevClose, color: css("--muted"), lineStyle: LineStyle.Dashed, lineWidth: 1, title: "PREV" })
      : null;
    this.chart.timeScale().fitContent();
  }

  clear(): void {
    this.area.setData([]); this.vol.setData([]); this.ma.setData([]);
  }
}
