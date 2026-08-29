/** Plotting primitives.
 *
 *  A telemetry channel is up to 8640 samples wide and the plot is around 700
 *  pixels. Emitting one SVG command per sample would be twelve times more path
 *  data than the screen can resolve, so the series is reduced to a per-pixel
 *  min/max envelope first. That is also the honest reduction for this data:
 *  averaging would flatten exactly the single-sample excursions the detector
 *  fires on, and the operator would see a calm trace next to an alarm.
 */

export interface Envelope {
  /** Flat quads of [sampleIndex, low, high, middle], one per pixel column. */
  cols: Float64Array;
  n: number;
  /** True when the domain is zoomed in far enough that every sample owns more
   *  than one pixel. The envelope then has no thickness and the caller must
   *  stroke a polyline rather than fill an area. */
  sparse: boolean;
}

export function envelope(values: number[], d0: number, d1: number, innerW: number): Envelope {
  const iw = Math.max(1, Math.floor(innerW));
  const lo = Math.max(0, Math.floor(d0));
  const hi = Math.min(values.length - 1, Math.ceil(d1));
  const span = Math.max(0, hi - lo);
  const sparse = span < iw;

  if (sparse) {
    const n = span + 1;
    const cols = new Float64Array(n * 4);
    for (let k = 0; k < n; k++) {
      const v = values[lo + k];
      cols[k * 4] = lo + k;
      cols[k * 4 + 1] = v;
      cols[k * 4 + 2] = v;
      cols[k * 4 + 3] = v;
    }
    return { cols, n, sparse };
  }

  const cols = new Float64Array(iw * 4);
  for (let k = 0; k < iw; k++) {
    const a = lo + Math.floor((k * span) / iw);
    const b = lo + Math.floor(((k + 1) * span) / iw);
    let mn = Infinity;
    let mx = -Infinity;
    let sum = 0;
    let count = 0;
    for (let i = a; i <= Math.max(a, b - 1); i++) {
      const v = values[i];
      if (v < mn) mn = v;
      if (v > mx) mx = v;
      sum += v;
      count++;
    }
    cols[k * 4] = a;
    cols[k * 4 + 1] = mn;
    cols[k * 4 + 2] = mx;
    // The middle of the column, drawn as the line. A channel that swings
    // between two states ten times per pixel is a solid block of ink if only
    // the envelope is drawn; the mean gives the eye something to follow
    // through it, and the envelope behind it keeps the full range visible.
    cols[k * 4 + 3] = count ? sum / count : mn;
  }
  return { cols, n: iw, sparse };
}

type Scale = (v: number) => number;

/** Along the maxima, back along the minima, closed. */
export function areaPath(env: Envelope, xOf: Scale, yOf: Scale): string {
  const { cols, n } = env;
  if (n === 0) return "";
  const parts: string[] = [];
  for (let k = 0; k < n; k++) {
    parts.push(
      `${k === 0 ? "M" : "L"}${xOf(cols[k * 4]).toFixed(1)},${yOf(cols[k * 4 + 2]).toFixed(1)}`,
    );
  }
  for (let k = n - 1; k >= 0; k--) {
    parts.push(`L${xOf(cols[k * 4]).toFixed(1)},${yOf(cols[k * 4 + 1]).toFixed(1)}`);
  }
  parts.push("Z");
  return parts.join("");
}

/** The line through the middle of the envelope, or the samples themselves when
 *  the plot is zoomed in far enough for the envelope to have no thickness. */
export function linePath(env: Envelope, xOf: Scale, yOf: Scale): string {
  const { cols, n } = env;
  if (n === 0) return "";
  const parts: string[] = [];
  for (let k = 0; k < n; k++) {
    parts.push(
      `${k === 0 ? "M" : "L"}${xOf(cols[k * 4]).toFixed(1)},${yOf(cols[k * 4 + 3]).toFixed(1)}`,
    );
  }
  return parts.join("");
}

/** Round tick values on the usual 1 / 2 / 5 progression. */
export function ticks(min: number, max: number, count: number): number[] {
  if (!isFinite(min) || !isFinite(max) || min === max) return [min];
  const raw = (max - min) / Math.max(1, count);
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    out.push(Math.abs(v) < step / 1e6 ? 0 : v);
  }
  return out;
}

export function extent(values: number[], lo: number, hi: number): [number, number] {
  let mn = Infinity;
  let mx = -Infinity;
  for (let i = Math.max(0, lo); i <= Math.min(values.length - 1, hi); i++) {
    const v = values[i];
    if (v < mn) mn = v;
    if (v > mx) mx = v;
  }
  if (!isFinite(mn)) return [0, 1];
  if (mn === mx) return [mn - 0.5, mx + 0.5];
  const pad = (mx - mn) * 0.08;
  return [mn - pad, mx + pad];
}

export const fmtInt = new Intl.NumberFormat("en-US");

export function fmtTick(v: number): string {
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1000) return fmtInt.format(Math.round(v));
  if (a >= 10) return v.toFixed(0);
  if (a >= 1) return v.toFixed(1);
  return v.toFixed(2);
}
