import { useId, useMemo, useState } from "react";
import { areaPath, envelope, extent, fmtInt, linePath, ticks, fmtTick } from "../lib/plot";
import { useWidth } from "../lib/hooks";

export interface Band {
  start: number;
  end: number;
  hit: boolean;
  id?: string;
}

interface Props {
  values: number[];
  n: number;
  /** Where the benchmark says a fault really happened. */
  truth: { start: number; end: number }[];
  /** Where this version of the detector raised an alarm. */
  alarms: Band[];
  height?: number;
  /** Thin marks for a second set of alarms drawn over the same trace. The
   *  legend names them; nothing is written on top of the data. */
  ghost?: { start: number; end: number }[];
  selected?: string | null;
  onSelect?: (id: string) => void;
  /** Restarts the entrance animation whenever it changes. */
  animationKey?: string | number;
  yLabel?: string;
  xLabel?: string;
}

const M = { top: 26, right: 14, bottom: 54, left: 56 };

/**
 * One recording, with every mark drawn directly on the trace.
 *
 * If the legend names a colour, that colour appears inside the plot.
 * A real fault is an amber column behind the line. An alarm is a coloured bar
 * along the top and bottom of the plot with a wash between them, bracketing
 * the stretch of line it covers.
 *
 * The line itself keeps its legend colour at all times. Repainting the line
 * inside an alarm fails when a wide alarm covers the whole recording, because
 * the trace vanishes into the alarm colour and hides the raw signal.
 *
 * Red and green are never the only difference between two marks. A false alarm
 * is hatched and a true one is solid, so the distinction survives a reader who
 * cannot tell the two colours apart.
 */
export function TraceChart({
  values,
  n,
  truth,
  alarms,
  height = 340,
  ghost,
  selected,
  onSelect,
  animationKey,
  yLabel = "Sensor reading",
  xLabel = "Reading number, first to last",
}: Props) {
  const [box, w] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<string | null>(null);
  const uid = useId().replace(/:/g, "");

  const innerW = Math.max(80, w - M.left - M.right);
  const innerH = Math.max(90, height - M.top - M.bottom);
  const BAR = 7;

  const yDomain = useMemo(() => extent(values, 0, n - 1), [values, n]);
  const xOf = (i: number) => M.left + (i / Math.max(1, n - 1)) * innerW;
  const yOf = (v: number) =>
    M.top + innerH - ((v - yDomain[0]) / Math.max(1e-9, yDomain[1] - yDomain[0])) * innerH;

  const base = useMemo(
    () => (w ? envelope(values, 0, n - 1, innerW) : null),
    [values, n, innerW, w],
  );

  const yTicks = useMemo(() => ticks(yDomain[0], yDomain[1], 4), [yDomain]);
  const xTicks = useMemo(() => ticks(0, n - 1, 5).filter((t) => t >= 0 && t <= n - 1), [n]);

  const caughtOf = (t: { start: number; end: number }) =>
    alarms.some((a) => a.start <= t.end && t.start <= a.end);

  return (
    <div ref={box}>
      {w > 0 && (
        <svg
          className="plot"
          viewBox={`0 0 ${w} ${height}`}
          width={w}
          height={height}
          role="img"
          aria-label={`Sensor readings across the recording, with ${truth.length} real ${
            truth.length === 1 ? "fault" : "faults"
          } and ${alarms.length} ${alarms.length === 1 ? "alarm" : "alarms"} marked on the line.`}
        >
          <defs>
            {/* The hatch pattern marks alarms where no real fault occurred. */}
            <pattern
              id={`hatch${uid}`}
              width="7"
              height="7"
              patternTransform="rotate(45)"
              patternUnits="userSpaceOnUse"
            >
              <rect width="7" height="7" fill="var(--miss)" fillOpacity={0.07} />
              <line x1="0" y1="0" x2="0" y2="7" stroke="var(--miss)" strokeWidth="2.5" strokeOpacity={0.4} />
            </pattern>
          </defs>

          <g key={animationKey}>
            {yTicks.map((t) => (
              <line
                key={`g${t}`}
                className="grid"
                x1={M.left}
                x2={M.left + innerW}
                y1={yOf(t)}
                y2={yOf(t)}
              />
            ))}

            {/* real faults: an amber column standing behind the line */}
            {truth.map((t, i) => {
              const x = xOf(t.start);
              const wide = Math.max(5, xOf(t.end) - x);
              const caught = caughtOf(t);
              return (
                <g key={`t${i}`} className="band-enter">
                  <rect
                    x={x}
                    y={M.top}
                    width={wide}
                    height={innerH}
                    fill="var(--truth)"
                    fillOpacity={0.22}
                  />
                  <rect
                    x={x}
                    y={M.top}
                    width={wide}
                    height={innerH}
                    fill="none"
                    stroke={caught ? "var(--truth)" : "var(--miss)"}
                    strokeWidth={2}
                    strokeDasharray={caught ? undefined : "5 4"}
                  />
                  <text
                    x={x + wide / 2}
                    y={M.top - 9}
                    textAnchor="middle"
                    fill={caught ? "var(--truth)" : "var(--miss)"}
                    style={{ fontSize: 12 }}
                  >
                    {caught ? "real fault" : "real fault, missed"}
                  </text>
                </g>
              );
            })}

            {/* alarms: a bar top and bottom with a wash between them */}
            {alarms.map((a, i) => {
              const x = xOf(a.start);
              const wide = Math.max(2.5, xOf(a.end) - x);
              const on = a.id != null && (a.id === selected || a.id === hover);
              const colour = a.hit ? "var(--hit)" : "var(--miss)";
              return (
                <g key={a.id ?? `a${i}`} className="band-enter">
                  <rect
                    x={x}
                    y={M.top}
                    width={wide}
                    height={innerH}
                    fill={a.hit ? "var(--hit)" : `url(#hatch${uid})`}
                    fillOpacity={a.hit ? (on ? 0.2 : 0.12) : on ? 1 : 0.75}
                  />
                  <rect
                    className={`marker${on ? " on" : ""}`}
                    x={x}
                    y={M.top}
                    width={wide}
                    height={on ? BAR + 2 : BAR}
                    fill={colour}
                  />
                  <rect
                    x={x}
                    y={M.top + innerH - (on ? BAR + 2 : BAR)}
                    width={wide}
                    height={on ? BAR + 2 : BAR}
                    fill={colour}
                  />
                </g>
              );
            })}

            {/* the trace: the full spread of readings, then a line through it.
                Drawn after the alarms so the reading is never painted over. */}
            {base && !base.sparse && (
              <path d={areaPath(base, xOf, yOf)} fill="var(--trace)" fillOpacity={0.28} />
            )}
            {base && (
              <path
                d={linePath(base, xOf, yOf)}
                fill="none"
                stroke="var(--trace)"
                strokeWidth={1.4}
                strokeLinejoin="round"
              />
            )}

            {/* click targets sit above the trace so the whole band is grabbable */}
            {onSelect &&
              alarms.map(
                (a, i) =>
                  a.id && (
                    <rect
                      key={`h${a.id ?? i}`}
                      className="hitbox"
                      x={xOf(a.start) - 4}
                      y={M.top}
                      width={Math.max(2.5, xOf(a.end) - xOf(a.start)) + 8}
                      height={innerH}
                      onMouseEnter={() => setHover(a.id!)}
                      onMouseLeave={() => setHover((h) => (h === a.id ? null : h))}
                      onClick={() => onSelect(a.id!)}
                    >
                      <title>{`Alarm at readings ${fmtInt.format(a.start)} to ${fmtInt.format(
                        a.end,
                      )}. ${a.hit ? "A real fault sits under it." : "Nothing was there."}`}</title>
                    </rect>
                  ),
              )}

            {/* Detections from an earlier detector version, shown along the bottom edge in purple. */}
            {ghost && ghost.length > 0 && (
              <g className="band-enter">
                <rect
                  x={M.left}
                  y={M.top + innerH - 30}
                  width={innerW}
                  height={30}
                  fill="#0a0e13"
                  fillOpacity={0.88}
                />
                {ghost.map((g, i) => (
                  <rect
                    key={`gh${i}`}
                    x={xOf(g.start)}
                    y={M.top + innerH - 15}
                    width={Math.max(1.5, xOf(g.end) - xOf(g.start))}
                    height={12}
                    fill="var(--past)"
                    shapeRendering="crispEdges"
                  />
                ))}
              </g>
            )}

            <rect className="frame" x={M.left} y={M.top} width={innerW} height={innerH} />

            {/* axes, always named in words */}
            {yTicks.map((t) => (
              <text key={`yt${t}`} x={M.left - 10} y={yOf(t) + 4} textAnchor="end">
                {fmtTick(t)}
              </text>
            ))}
            {xTicks.map((t) => (
              <text key={`xt${t}`} x={xOf(t)} y={M.top + innerH + 20} textAnchor="middle">
                {fmtInt.format(Math.round(t))}
              </text>
            ))}
            <text
              className="axis-label"
              x={M.left + innerW / 2}
              y={height - 12}
              textAnchor="middle"
            >
              {/* A narrow phone cannot hold the long version without clipping it. */}
              {innerW < 300 ? "Reading number" : xLabel}
            </text>
            <text
              className="axis-label"
              transform={`translate(14 ${M.top + innerH / 2}) rotate(-90)`}
              textAnchor="middle"
            >
              {yLabel}
            </text>
          </g>
        </svg>
      )}
    </div>
  );
}

/** The legend, displaying the count of each mark currently on the chart.
 *  An entry with no marks on the current chart displays zero so the count matches the plot. */
export function Legend({
  alarms,
  faults,
  past,
}: {
  alarms: Band[];
  faults: number;
  /** How many alarms the earlier version raised, when its row is drawn too. */
  past?: number;
}) {
  const hits = alarms.filter((a) => a.hit).length;
  const misses = alarms.length - hits;
  return (
    <div className="legend">
      <span className="key">
        <span className="swatch trace" /> the sensor reading
      </span>
      <span className={`key${faults === 0 ? " off" : ""}`}>
        <span className="swatch truth" /> {faults} {faults === 1 ? "fault" : "faults"} that really
        happened
      </span>
      <span className={`key${hits === 0 ? " off" : ""}`}>
        <span className="swatch hit" /> {hits} {hits === 1 ? "alarm" : "alarms"} with a real fault
        under {hits === 1 ? "it" : "them"}
      </span>
      <span className={`key${misses === 0 ? " off" : ""}`}>
        <span className="swatch miss" /> {misses} {misses === 1 ? "alarm" : "alarms"} with nothing
        under {misses === 1 ? "it" : "them"}
      </span>
      {past != null && (
        <span className="key">
          <span className="swatch past" /> {past} {past === 1 ? "alarm" : "alarms"} the first
          version raised
        </span>
      )}
    </div>
  );
}
