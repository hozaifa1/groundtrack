import { useEffect, useMemo, useState } from "react";
import type { ChannelDetail, ChannelSummary, Detection } from "../types";
import { Legend, TraceChart } from "./TraceChart";
import { fmtInt } from "../lib/plot";

interface Props {
  channels: ChannelSummary[];
  initial: ChannelDetail;
  /** How many write-ups exist, so the note about them cannot go stale. */
  briefs: number;
}

/** The four patterns the write-up rules can name, said the way a person says
 *  them. The original wording stays in the repository; this is what goes on
 *  screen. */
const PATTERN: Record<string, string> = {
  level_shift: "The signal shifted to a new baseline and remained there",
  transient_spike: "The signal spiked briefly and returned to baseline",
  noise_burst: "Signal variance jumped sharply while the average remained steady",
  unclassified: "The signal shape does not match any standard pattern",
};

/** Said so the rating carries its own source. */
const URGENCY: Record<string, string> = {
  high: "The detector rates it high urgency",
  medium: "The detector rates it moderate urgency",
  low: "The detector rates it low urgency",
};

export function Explorer({ channels, initial, briefs }: Props) {
  const [id, setId] = useState(initial.id);
  const [detail, setDetail] = useState<ChannelDetail>(initial);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [picked, setPicked] = useState<string | null>(
    initial.detections[0]?.id ?? null,
  );
  const [compare, setCompare] = useState(false);

  useEffect(() => {
    if (id === detail.id) return;
    let live = true;
    setLoading(true);
    setFailed(false);
    fetch(`data/channel/${id}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((next: ChannelDetail) => {
        if (!live) return;
        setDetail(next);
        setPicked(next.detections[0]?.id ?? null);
        setLoading(false);
      })
      .catch(() => {
        if (!live) return;
        setFailed(true);
        setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [id, detail.id]);

  const selected: Detection | null = useMemo(
    () => detail.detections.find((d) => d.id === picked) ?? detail.detections[0] ?? null,
    [detail, picked],
  );

  const bands = detail.detections.map((d) => ({
    start: d.start,
    end: d.end,
    hit: d.hit,
    id: d.id,
  }));

  return (
    <div className="panel explorer">
      <div className="picker">
        <label htmlFor="chan">Recording</label>
        <select id="chan" value={id} onChange={(e) => setId(e.target.value)}>
          {channels.map((c) => (
            <option key={c.id} value={c.id}>
              {c.id}: {c.detections === 0 ? "no alarms" : `${c.detections} alarm${c.detections === 1 ? "" : "s"}`}
              , {c.truth} real {c.truth === 1 ? "fault" : "faults"}
            </option>
          ))}
        </select>
        <button
          className={`toggle${compare ? " on" : ""}`}
          onClick={() => setCompare((c) => !c)}
          aria-pressed={compare}
        >
          <span className="box" />
          Show alarms flagged by the initial baseline version
        </button>
      </div>

      {failed ? (
        <p className="empty">That recording did not load. Pick another one.</p>
      ) : (
        <>
          <div className="chart-head">
            <p className="chart-title">
              <strong>{detail.id}</strong> from the {detail.spacecraft} satellite,{" "}
              {fmtInt.format(detail.n)} readings,{" "}
              {detail.split === "holdout" ? "held out from Bob" : "available to Bob during development"}
              {loading ? ", loading" : ""}
            </p>
          </div>
          <TraceChart
            values={detail.values}
            n={detail.n}
            truth={detail.truth}
            alarms={bands}
            ghost={compare ? detail.baseline : undefined}
            selected={selected?.id ?? null}
            onSelect={setPicked}
            animationKey={detail.id + String(compare)}
            height={340}
          />
          <Legend alarms={bands} faults={detail.truth.length} past={compare ? detail.baseline.length : undefined} />
          <p className="chart-note">
            {detail.detections.length === 0
              ? "The detector stayed quiet on this recording."
              : "Click any alarm to read its diagnostic summary."}{" "}
            The published recordings carry no engineering units, so the vertical axis displays raw normalized values as released.
          </p>

          {selected && (
            <div className="detail">
              <div className="detail-head">
                <h3>{PATTERN[selected.signature] ?? selected.title}</h3>
                <p className="where">
                  Readings <span className="num">{fmtInt.format(selected.start)}</span> to{" "}
                  <span className="num">{fmtInt.format(selected.end)}</span> out of{" "}
                  <span className="num">{fmtInt.format(detail.n)}</span>, so{" "}
                  <span className="num">{fmtInt.format(selected.length)}</span> readings long.{" "}
                  {URGENCY[selected.severity] ?? "The detector did not rate it"}.{" "}
                  {selected.hit ? "A real fault sits under it." : "Nothing was there."}
                </p>
                <p className="fine">
                  Urgency ratings follow deterministic rules inside the detector based on excursion magnitude, modeled after flight controller checklists.
                </p>
              </div>

              {selected.brief ? (
                <>
                  <p className="source-note">
                    The following diagnostic summary was generated locally by IBM Granite, producing one brief per alarm across all {briefs} detections. A transient spike denotes an abrupt departure that quickly returns to baseline. One sigma represents standard signal variation: a reading multiple sigma away indicates extreme deviation. Robust sigma estimates this baseline variance using median absolute deviation, preventing extreme outliers from distorting the threshold.
                  </p>
                  <div className="brief">
                    <div>
                      <h4>What happened</h4>
                      <p>{selected.brief.happened}</p>
                    </div>
                    <div>
                      <h4>Why it matters</h4>
                      <p>{selected.brief.matters}</p>
                    </div>
                    <div>
                      <h4>What to do next</h4>
                      <p>{selected.brief.next}</p>
                    </div>
                  </div>
                </>
              ) : (
                <p className="empty">This alarm has no write-up.</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
