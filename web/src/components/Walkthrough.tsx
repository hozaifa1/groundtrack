import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CHAPTERS, type Chapter } from "../story";
import type { ChannelDetail, WalkStep, Walkthrough as WalkData } from "../types";
import { Legend, TraceChart } from "./TraceChart";
import { BenchmarkStrip } from "./BenchmarkStrip";
import { useReducedMotion } from "../lib/hooks";
import { fmtInt } from "../lib/plot";

interface Props {
  data: WalkData;
  channel: ChannelDetail;
  /** How many recordings there are in total, and how many were kept hidden.
   *  Passed in rather than written into the copy so the headings cannot go
   *  stale against the data the rest of the panel is reading. */
  recordings: number;
  hidden: number;
}

/** Counts from the previous value to the next one so a change reads as a move
 *  rather than as a different screen. */
function useCountUp(target: number, ms = 620): number {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(target);
  const from = useRef(target);
  const raf = useRef(0);

  useEffect(() => {
    if (reduced || from.current === target) {
      from.current = target;
      setValue(target);
      return;
    }
    const a = from.current;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      const e = 1 - Math.pow(1 - p, 3);
      const v = a + (target - a) * e;
      setValue(p >= 1 ? target : v);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else from.current = target;
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, ms, reduced]);

  return value;
}

function Delta({ value, goodWhen }: { value: number; goodWhen: "down" | "up" }) {
  if (!isFinite(value) || Math.abs(value) < 1e-9) {
    return <span className="delta flat">no change</span>;
  }
  const good = goodWhen === "down" ? value < 0 : value > 0;
  const size = Math.abs(value);
  // Three places, matching the score above it. At two, a reader who adds the
  // arrow to the old score lands one hundredth away from the new one.
  const shown = size < 1 ? size.toFixed(3) : fmtInt.format(Math.round(size));
  return (
    <span className={`delta ${good ? "up" : "down"}`}>
      {value > 0 ? "+" : "−"}
      {shown}
    </span>
  );
}

export function Walkthrough({ data, channel, recordings, hidden }: Props) {
  const reduced = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [started, setStarted] = useState(false);
  const host = useRef<HTMLDivElement>(null);

  const byKey = useMemo(() => {
    const map = new Map<string, WalkStep>();
    data.steps.forEach((s) => map.set(s.key, s));
    return map;
  }, [data]);

  const chapter: Chapter = CHAPTERS[index];
  const step = byKey.get(chapter.data)!;
  const before = chapter.baseline ? byKey.get(chapter.baseline) : undefined;
  const last = index === CHAPTERS.length - 1;

  // Autoplay starts when the player is actually on screen, so the story is not
  // half over by the time someone scrolls to it. Anyone who has asked their
  // system for less motion gets it paused instead, with the play button ready.
  useEffect(() => {
    const node = host.current;
    if (!node || started || reduced) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.intersectionRatio > 0.35)) {
          setStarted(true);
          setPlaying(true);
          io.disconnect();
        }
      },
      { threshold: [0.35] },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [started, reduced]);

  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) setPlaying(false);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    if (!playing) return;
    const ms = chapter.seconds * 1000;
    const t0 = performance.now() - progress * ms;
    let raf = 0;
    const tick = (now: number) => {
      const p = (now - t0) / ms;
      if (p >= 1) {
        if (last) {
          setProgress(1);
          setPlaying(false);
          return;
        }
        setProgress(0);
        setIndex((i) => i + 1);
        return;
      }
      setProgress(p);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // progress is deliberately not a dependency: it is the thing being written.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, index, chapter.seconds, last]);

  const go = useCallback((i: number) => {
    setIndex(Math.max(0, Math.min(CHAPTERS.length - 1, i)));
    setProgress(0);
  }, []);

  const alarms = useCountUp(step.alarms);
  const found = useCountUp(step.holdout.tp);
  const wrong = useCountUp(step.holdout.fp);
  const score = useCountUp(step.holdout.f1);
  const faults = step.holdout.tp + step.holdout.fn;

  const bands = step.showcase.windows.map((wnd, i) => ({ ...wnd, id: `${chapter.data}-${i}` }));

  // The last chapter puts the first version's alarms back on the same axis
  // underneath the one the detector ends with. Without it the closing frame is
  // the previous frame again, and the whole point of the ending is the gap.
  const ghost = chapter.ghost
    ? byKey.get(chapter.ghost)?.showcase.windows.map((wnd) => ({ start: wnd.start, end: wnd.end }))
    : undefined;

  // An alarm that swallows the recording still counts as correct, and saying so
  // where it happens is cheaper than letting someone notice it themselves.
  const widest = step.showcase.windows.reduce(
    (m, wnd) => Math.max(m, (wnd.end - wnd.start + 1) / data.showcase.n),
    0,
  );

  return (
    <div className="panel player" ref={host}>
      <div className="player-top">
        <div className="stage">
          <div className="chart-head">
            <p className="chart-title">
              One recording from the SMAP satellite, <strong>{data.showcase.channel}</strong>,{" "}
              {fmtInt.format(data.showcase.n)} readings long
            </p>
            <p className="here">
              <span className="num">{fmtInt.format(step.showcase.windows.length)}</span>{" "}
              {step.showcase.windows.length === 1 ? "alarm here" : "alarms here"}
            </p>
          </div>
          <TraceChart
            values={channel.values}
            n={channel.n}
            truth={data.showcase.truth}
            alarms={bands}
            ghost={ghost}
            animationKey={chapter.id}
            height={352}
          />
          <Legend alarms={bands} faults={data.showcase.truth.length} past={ghost?.length} />

          {widest > 0.5 && (
            <p className="chart-note">
              The widest alarm here covers {Math.round(widest * 100)}% of the recording. It counts
              as correct because a real fault falls inside it.
            </p>
          )}

          <BenchmarkStrip
            counts={step.alarms_by_channel}
            labels={data.channels}
            highlight={data.showcase.index}
          />
        </div>

        <div className="narration">
          <p className="eyebrow">{chapter.eyebrow}</p>
          <h3>{chapter.title}</h3>
          <p className="body">{chapter.body}</p>
          <span className={`verdict ${chapter.verdict}`}>
            <span className="dot" />
            {chapter.verdictText}
          </span>

          <div className="readouts">
            <div className="readout-group">
              <h4>All {recordings} recordings</h4>
              <div className="readout big">
                <span className="label">Alarms raised</span>
                <span className="value">
                  {fmtInt.format(Math.round(alarms))}
                  {before && <Delta value={step.alarms - before.alarms} goodWhen="down" />}
                </span>
              </div>
            </div>

            <div className="readout-group">
              <h4>Marked on the {hidden} recordings Bob never saw</h4>
              {chapter.unscored ? (
                <p className="empty">Nothing was graded in these two rounds.</p>
              ) : (
                <>
                  <div className="readout">
                    <span className="label">Real faults found</span>
                    <span className="value">
                      {Math.round(found)} of {faults}
                      {before && <Delta value={step.holdout.tp - before.holdout.tp} goodWhen="up" />}
                    </span>
                  </div>
                  <div className="readout">
                    <span className="label">Alarms with nothing there</span>
                    <span className="value">
                      {fmtInt.format(Math.round(wrong))}
                      {before && <Delta value={step.holdout.fp - before.holdout.fp} goodWhen="down" />}
                    </span>
                  </div>
                  <div className="readout">
                    <span className="label">Score out of 1</span>
                    <span className="value">
                      {score.toFixed(3)}
                      {before && <Delta value={step.holdout.f1 - before.holdout.f1} goodWhen="up" />}
                    </span>
                  </div>
                  <p className="fine">
                    The score puts the two rows above together. One would mean every fault found
                    and no alarm wasted.
                  </p>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="transport">
        <button
          className="tbtn primary"
          onClick={() => {
            if (last && progress >= 1) {
              go(0);
              setPlaying(true);
              return;
            }
            setPlaying((p) => !p);
          }}
        >
          {last && progress >= 1 ? "Play again" : playing ? "Pause" : "Play"}
        </button>
        <button className="tbtn" onClick={() => go(index - 1)} disabled={index === 0}>
          Back
        </button>
        <button
          className="tbtn"
          onClick={() => go(index + 1)}
          disabled={index === CHAPTERS.length - 1}
        >
          Next
        </button>

        <div className="steps" role="tablist" aria-label="Steps">
          {CHAPTERS.map((c, i) => (
            <button
              key={c.id}
              role="tab"
              aria-selected={i === index}
              aria-label={`Step ${i + 1}: ${c.title}`}
              title={c.title}
              className={`step-dot${i < index ? " done" : ""}${i === index ? " current" : ""}`}
              onClick={() => go(i)}
            >
              <span className="rail">
                <span
                  className="fill"
                  style={i === index ? { width: `${Math.round(progress * 100)}%` } : undefined}
                />
              </span>
            </button>
          ))}
        </div>

        <span className="counter">
          <span className="num">
            {index + 1} / {CHAPTERS.length}
          </span>
          <span className="state">{playing ? "moving on its own" : "paused"}</span>
        </span>
      </div>
    </div>
  );
}
