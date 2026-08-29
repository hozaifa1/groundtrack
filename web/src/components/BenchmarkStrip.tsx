import { useEffect, useRef, useState } from "react";
import { useReducedMotion, useWidth } from "../lib/hooks";
import { fmtInt } from "../lib/plot";

interface Props {
  /** One count per recording, in the order the exporter wrote them. */
  counts: number[];
  labels: string[];
  /** The recording the big chart above is showing. */
  highlight: number;
}

/** Slides every bar from where it was to where it now is. Four of the rounds
 *  barely move the one recording drawn above, and this is where they are
 *  visible: the whole benchmark reacts to each attempt at once. */
function useTween(target: number[], ms = 700): number[] {
  const reduced = useReducedMotion();
  const [values, setValues] = useState(target);
  const from = useRef(target);
  const raf = useRef(0);

  useEffect(() => {
    if (reduced) {
      from.current = target;
      setValues(target);
      return;
    }
    const a = from.current;
    if (a.length !== target.length) {
      from.current = target;
      setValues(target);
      return;
    }
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      const e = 1 - Math.pow(1 - p, 3);
      const next = target.map((v, i) => a[i] + (v - a[i]) * e);
      setValues(p >= 1 ? target : next);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else from.current = target;
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, ms, reduced]);

  return values;
}

const H = 96;
const TOP = 8;
const FLOOR = H - 20;
// The tallest bar any version of the detector produces, so the bars can be
// compared across steps rather than rescaling under the reader.
const CEILING = 88;

export function BenchmarkStrip({ counts, labels, highlight }: Props) {
  const [box, w] = useWidth<HTMLDivElement>();
  const eased = useTween(counts);
  const slot = w / Math.max(1, counts.length);
  const barW = Math.max(2, slot - 2);
  // Square root, so a recording with 88 alarms does not flatten the 60 that
  // have a handful. The axis is labelled with what that means.
  const yOf = (v: number) => FLOOR - (Math.sqrt(Math.max(0, v)) / Math.sqrt(CEILING)) * (FLOOR - TOP);

  return (
    <div ref={box} className="strip">
      {w > 0 && (
        <svg viewBox={`0 0 ${w} ${H}`} width={w} height={H} role="img" aria-label="Alarms raised on each of the 81 recordings">
          <line className="grid" x1={0} x2={w} y1={FLOOR} y2={FLOOR} />
          {eased.map((v, i) => {
            const x = i * slot + 1;
            const y = yOf(v);
            const on = i === highlight;
            return (
              <rect
                key={labels[i]}
                x={x}
                y={y}
                width={barW}
                height={Math.max(0, FLOOR - y)}
                rx={1}
                shapeRendering="crispEdges"
                fill={on ? "var(--accent)" : "var(--trace)"}
                fillOpacity={on ? 1 : 0.6}
              />
            );
          })}
          <text x={highlight * slot + barW / 2} y={FLOOR + 14} textAnchor="middle" fill="var(--accent)">
            {labels[highlight]}
          </text>
        </svg>
      )}
      <p className="chart-note">
        One bar for each of the {fmtInt.format(counts.length)} recordings, showing how many alarms
        this version raised on it. The blue bar is the recording drawn above. Bar height follows a
        square root scale: a bar twice as tall stands for four times as many alarms.
      </p>
    </div>
  );
}
