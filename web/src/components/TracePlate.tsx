import { useMemo } from "react";
import type { Detection, TruthWindow } from "../types";
import { areaPath, envelope, extent, fmtInt, fmtTick, linePath, ticks } from "../lib/plot";

interface Band {
  id: string;
  start: number;
  end: number;
  /** filled: the mark is asserted and supported. hollow: asserted, unsupported. */
  tone: "truth" | "missed" | "engine" | "false-alarm" | "baseline";
}

interface Rail {
  key: string;
  label: string;
  bands: Band[];
  interactive?: boolean;
}

interface Props {
  values: number[];
  n: number;
  domain: [number, number];
  height: number;
  truth: TruthWindow[];
  detections: Detection[];
  baseline: { start: number; end: number }[] | null;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  /** Draws a horizontal cut-off rule; used by the deviation plate. */
  threshold?: number;
  yLabel: string;
  width: number;
}

const TONE_FILL: Record<Band["tone"], string> = {
  truth: "var(--truth)",
  missed: "var(--alarm)",
  engine: "var(--signal)",
  "false-alarm": "var(--paper-plate)",
  baseline: "var(--signal)",
};

const RAIL_H = 22;
const RAIL_GAP = 10;

export function TracePlate({
  values,
  n,
  domain,
  height,
  truth,
  detections,
  baseline,
  selectedId,
  onSelect,
  threshold,
  yLabel,
  width,
}: Props) {
  const [d0, d1] = domain;

  /* Below roughly 560px the 124px label gutter would eat a third of a phone
     screen, so the rail labels move above their rails and the gutter shrinks
     to what the y ticks alone need. Type sizes never change; the layout does. */
  const compact = width < 500;
  const pad = {
    l: compact ? 54 : 124,
    r: compact ? 12 : 22,
    t: 18,
    b: 36,
  };
  const railBlock = RAIL_H + RAIL_GAP + (compact ? 24 : 0);
  const iw = Math.max(1, width - pad.l - pad.r);

  const xOf = (i: number) => pad.l + ((i - d0) / Math.max(1e-9, d1 - d0)) * iw;

  const rails: Rail[] = useMemo(() => {
    const out: Rail[] = [];
    if (truth.length > 0) {
      out.push({
        key: "truth",
        label: "Labelled",
        bands: truth.map((t, i) => ({
          id: `t${i}`,
          start: t.start,
          end: t.end,
          tone: t.caught ? "truth" : "missed",
        })),
      });
    }
    out.push({
      key: "engine",
      label: "Engine",
      interactive: true,
      bands: detections.map((d) => ({
        id: d.id,
        start: d.start,
        end: d.end,
        tone: d.hit ? "engine" : "false-alarm",
      })),
    });
    if (baseline) {
      out.push({
        key: "baseline",
        label: "Iteration 0",
        bands: baseline.map((b, i) => ({
          id: `b${i}`,
          start: b.start,
          end: b.end,
          tone: "baseline",
        })),
      });
    }
    return out;
  }, [truth, detections, baseline]);

  const railsH = rails.length * railBlock;
  const totalH = pad.t + height + pad.b + railsH + 8;

  const [vmin, vmax] = useMemo(() => {
    if (threshold === undefined) return extent(values, Math.floor(d0), Math.ceil(d1));
    const [, hi] = extent(values, Math.floor(d0), Math.ceil(d1));
    return [0, Math.max(threshold * 1.3, hi)] as [number, number];
  }, [values, d0, d1, threshold]);

  const yOf = (v: number) => pad.t + (1 - (v - vmin) / (vmax - vmin || 1)) * height;

  const env = useMemo(() => envelope(values, d0, d1, iw), [values, d0, d1, iw]);

  /* A per-pixel min/max envelope is a filled area. Zoomed in past one sample
     per pixel the envelope collapses to a single value per column, and a
     filled path between a line and itself has no area and draws nothing, so
     the trace becomes a stroked polyline instead. */
  const d = useMemo(
    () => (env.sparse ? linePath(env, xOf, yOf) : areaPath(env, xOf, yOf)),
    [env, d0, d1, iw, vmin, vmax, height],
  );

  const yTicks = ticks(vmin, vmax, 4);
  // Roughly one tick per 110px, the density Observable Plot targets. At
  // 160 an 8,600-sample channel got two labels and the axis stopped being
  // readable as a scale.
  const xTicks = ticks(d0, d1, Math.max(2, Math.round(iw / 110)));
  const selected = detections.find((x) => x.id === selectedId) ?? null;

  if (width < 60) return <svg width="100%" height={totalH} aria-hidden="true" />;

  return (
    <svg
      width={width}
      height={totalH}
      viewBox={`0 0 ${width} ${totalH}`}
      role="img"
      aria-label={`${yLabel} against sample index for ${fmtInt.format(n)} samples, with labelled anomalies and the engine's detections aligned beneath.`}
    >
      {selected && (
        <rect
          x={xOf(selected.start)}
          y={pad.t}
          width={Math.max(2, xOf(selected.end) - xOf(selected.start))}
          height={height + pad.b + railsH}
          fill="var(--signal-wash)"
        />
      )}

      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line
            x1={pad.l}
            x2={width - pad.r}
            y1={yOf(t)}
            y2={yOf(t)}
            stroke="var(--rule-faint)"
            shapeRendering="crispEdges"
          />
          <text
            x={pad.l - 10}
            y={yOf(t)}
            textAnchor="end"
            dominantBaseline="central"
            fontSize={16}
            fill="var(--ink-2)"
          >
            {fmtTick(t)}
          </text>
        </g>
      ))}

      {threshold !== undefined && threshold <= vmax && (
        <g>
          <line
            x1={pad.l}
            x2={width - pad.r}
            y1={yOf(threshold)}
            y2={yOf(threshold)}
            stroke="var(--alarm)"
            strokeWidth={1.5}
            strokeDasharray="7 5"
          />
          <text
            x={width - pad.r}
            y={yOf(threshold) - 8}
            textAnchor="end"
            fontSize={16}
            fontWeight={600}
            fill="var(--alarm)"
          >
            {threshold.toFixed(1)} sigma
          </text>
        </g>
      )}

      <path
        d={d}
        fill={env.sparse ? "none" : "var(--ink)"}
        fillOpacity={env.sparse ? 1 : 0.88}
        stroke={env.sparse ? "var(--ink)" : "none"}
        strokeWidth={env.sparse ? 1.5 : 0}
        strokeLinejoin="round"
      />

      <line
        x1={pad.l}
        x2={width - pad.r}
        y1={pad.t + height}
        y2={pad.t + height}
        stroke="var(--rule-strong)"
        shapeRendering="crispEdges"
      />
      <line
        x1={pad.l}
        x2={pad.l}
        y1={pad.t}
        y2={pad.t + height}
        stroke="var(--rule-strong)"
        shapeRendering="crispEdges"
      />

      {xTicks.map((t) => (
        <text
          key={`x${t}`}
          x={xOf(t)}
          y={pad.t + height + 24}
          textAnchor="middle"
          fontSize={16}
          fill="var(--ink-2)"
        >
          {fmtInt.format(Math.round(t))}
        </text>
      ))}

      {!compact && (
        <text x={pad.l - 10} y={pad.t - 3} textAnchor="end" fontSize={16} fontWeight={600} fill="var(--ink-2)">
          {yLabel}
        </text>
      )}

      {rails.map((rail, ri) => {
        const top = pad.t + height + pad.b + ri * railBlock;
        const y = top + (compact ? 24 : 0);
        return (
          <g key={rail.key}>
            {compact ? (
              <text x={pad.l} y={top + 12} fontSize={16} fill="var(--ink-2)">
                {rail.label}
              </text>
            ) : (
              <text
                x={pad.l - 10}
                y={y + RAIL_H / 2}
                textAnchor="end"
                dominantBaseline="central"
                fontSize={16}
                fill="var(--ink-2)"
              >
                {rail.label}
              </text>
            )}
            <line
              x1={pad.l}
              x2={width - pad.r}
              y1={y + RAIL_H}
              y2={y + RAIL_H}
              stroke="var(--rule-faint)"
              shapeRendering="crispEdges"
            />
            {rail.bands.map((b) => {
              const x = xOf(b.start);
              const w = Math.max(2.5, xOf(b.end) - x);
              if (x + w < pad.l - 1 || x > width - pad.r + 1) return null;
              const isSel = b.id === selectedId;
              const hollow = b.tone === "false-alarm";
              const inset = rail.key === "baseline" ? 5 : 2;
              return (
                <rect
                  key={b.id}
                  x={Math.max(pad.l, x)}
                  y={y + inset}
                  width={Math.min(w, width - pad.r - Math.max(pad.l, x))}
                  height={RAIL_H - inset * 2}
                  fill={TONE_FILL[b.tone]}
                  fillOpacity={rail.key === "baseline" ? 0.5 : 1}
                  stroke={hollow ? "var(--signal)" : isSel ? "var(--ink)" : "none"}
                  strokeWidth={hollow ? 1.5 : isSel ? 2 : 0}
                  style={rail.interactive ? { cursor: "pointer" } : undefined}
                  onClick={
                    rail.interactive ? () => onSelect(b.id === selectedId ? null : b.id) : undefined
                  }
                >
                  <title>
                    {rail.label}: samples {fmtInt.format(b.start)} to {fmtInt.format(b.end)}
                    {b.tone === "missed" ? ". No detection overlapped this." : ""}
                    {b.tone === "false-alarm" ? ". No labelled anomaly here." : ""}
                  </title>
                </rect>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
