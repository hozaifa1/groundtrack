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
  level_shift: "The reading moved to a new level and stayed there",
  transient_spike: "The reading jumped and came back",
  noise_burst: "The reading got much noisier without shifting its average",
  unclassified: "The shape of this one does not match any of the patterns",
};

const URGENCY: Record<string, string> = {
  high: "Rated urgent",
  medium: "Rated worth a look",
  low: "Rated minor",
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
          Show what the first version flagged here
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
              {detail.split === "holdout" ? "kept hidden from Bob" : "one Bob could study"}
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
              : "Click any alarm to read what the write-up says about it."}{" "}
            The published recordings carry no unit for the reading, so the up and down scale is
            just the numbers as they were released.
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
                  {URGENCY[selected.severity] ?? "Not rated"}.{" "}
                  {selected.hit ? "A real fault sits under it." : "Nothing was there."}
                </p>
                <p className="fine">
                  The urgency rating comes from a short set of rules inside the detector, based on
                  how far the readings moved. It is written to sound like a flight controller's
                  checklist and is not anyone's real procedure.
                </p>
              </div>

              {selected.brief ? (
                <>
                  <p className="source-note">
                    What follows is the write-up exactly as a small language model produced it on
                    the computer that built this page, one for each of the {briefs} alarms. It
                    says transient spike when a reading jumps and comes back. Where it says sigma,
                    one sigma is the sensor's usual amount of wobble, so 24 sigma is far outside it.
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
