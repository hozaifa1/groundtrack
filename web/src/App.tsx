import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowCounterClockwise, ArrowsOutSimple } from "@phosphor-icons/react";
import { ChannelIndex } from "./components/ChannelIndex";
import { BriefPane } from "./components/BriefPane";
import { Ledger } from "./components/Ledger";
import { TracePlate } from "./components/TracePlate";
import { useAnimatedDomain, useWidth } from "./lib/hooks";
import { fmtInt } from "./lib/plot";
import type { ChannelDetail, Manifest } from "./types";

type View = "console" | "loop";

/** Each plate measures its own figure box. Sizing one plot from another
 *  element's width couples two layouts that are free to differ. */
function Figure({ children }: { children: (w: number) => React.ReactNode }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  return (
    <div className="plate-figure" ref={ref}>
      {children(w)}
    </div>
  );
}

export default function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("console");

  const [channelId, setChannelId] = useState<string>("");
  const [detail, setDetail] = useState<ChannelDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch("data/manifest.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest ${r.status}`))))
      .then((m: Manifest) => {
        setManifest(m);
        // Open on the channel that argues for itself, chosen by criteria
        // rather than by name so it stays the right channel if the engine
        // changes: held out, so it is data the engine was never tuned on;
        // full recall, so the engine is not being flattered; and the widest
        // gap against iteration 0, because that gap is what the forge loop
        // bought and it is legible in a single glance at the rails.
        const best = [...m.channels]
          .filter((c) => c.split === "holdout" && c.detections > 0 && c.truth > 0)
          .sort(
            (a, b) =>
              Number(b.caught === b.truth) - Number(a.caught === a.truth) ||
              b.baseline_detections - b.detections - (a.baseline_detections - a.detections),
          )[0];
        setChannelId(best?.id ?? m.channels[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!channelId) return;
    let live = true;
    setLoadingDetail(true);
    setSelectedId(null);
    fetch(`data/channel/${channelId}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`channel ${r.status}`))))
      .then((d: ChannelDetail) => {
        if (!live) return;
        setDetail(d);
        setLoadingDetail(false);
      })
      .catch((e) => {
        if (!live) return;
        setError(String(e));
        setLoadingDetail(false);
      });
    return () => {
      live = false;
    };
  }, [channelId]);

  const selected = useMemo(
    () => detail?.detections.find((d) => d.id === selectedId) ?? null,
    [detail, selectedId],
  );

  // Opening a detection travels the x-domain to that window plus context on
  // each side, so the window keeps its place in the pass instead of becoming
  // an unanchored close-up.
  const targetDomain = useMemo<[number, number]>(() => {
    if (!detail) return [0, 1];
    if (!selected) return [0, detail.n - 1];
    const pad = Math.max(120, selected.length * 1.6);
    return [Math.max(0, selected.start - pad), Math.min(detail.n - 1, selected.end + pad)];
  }, [detail, selected]);

  const domain = useAnimatedDomain(targetDomain);

  const onSelect = useCallback((id: string | null) => setSelectedId(id), []);

  if (error) {
    return (
      <div className="empty" style={{ padding: "var(--s-8)" }}>
        <h3>The console could not load its data</h3>
        <p>
          {error}. The console reads static JSON from <code>public/data</code>. Regenerate it with{" "}
          <code>python tools/export_console.py</code> and reload.
        </p>
      </div>
    );
  }

  if (!manifest) {
    return (
      <div className="app">
        <header className="masthead">
          <div className="wordmark">
            <h1>Groundtrack</h1>
          </div>
        </header>
        <div className="shell">
          <div className="index" />
          <div className="plate-col" style={{ padding: "var(--s-6)" }}>
            <div className="skeleton" style={{ height: 88, marginBottom: "var(--s-5)" }} />
            <div className="skeleton" style={{ height: 320 }} />
          </div>
          <div className="brief" />
        </div>
      </div>
    );
  }

  const summary = manifest.channels.find((c) => c.id === channelId);
  const hold = manifest.splits.holdout;
  const ship = manifest.totals.shipped;
  const base = manifest.totals.baseline;

  return (
    <div className="app">
      <header className="masthead">
        <div className="wordmark">
          <h1>Groundtrack</h1>
          <p>
            IBM Bob wrote the detector. A fixed benchmark it cannot reach decides whether it was any
            good.
          </p>
        </div>

        <div className="readouts">
          <div className="readout">
            <span className="v">{hold.f1.toFixed(3)}</span>
            <span className="k">Held-out F1</span>
          </div>
          <div className="readout">
            <span className="v">{ship.windows}</span>
            <span className="k">Detections</span>
          </div>
          <div className="readout">
            <span className="v">{manifest.totals.briefs}</span>
            <span className="k">Granite briefs</span>
          </div>
        </div>

        <div className="viewswitch" role="group" aria-label="View">
          <button aria-pressed={view === "console"} onClick={() => setView("console")}>
            Console
          </button>
          <button aria-pressed={view === "loop"} onClick={() => setView("loop")}>
            The loop
          </button>
        </div>
      </header>

      <div className="shell">
        {view === "loop" ? (
          <Ledger manifest={manifest} />
        ) : (
          <>
            <ChannelIndex
              channels={manifest.channels}
              current={channelId}
              query={query}
              onQuery={setQuery}
              onPick={setChannelId}
            />

            <main className="plate-col">
              <div className="chan-head">
                <h2>{channelId}</h2>
                <div className="chan-facts">
                  <div className="fact">
                    <span className="v">{summary?.spacecraft}</span>
                    <span className="k">Spacecraft</span>
                  </div>
                  <div className="fact">
                    <span className="v">
                      {summary?.split === "holdout" ? "Held out" : "Dev"}
                    </span>
                    <span className="k">Split</span>
                  </div>
                  <div className="fact">
                    <span className="v">{fmtInt.format(summary?.n ?? 0)}</span>
                    <span className="k">Samples</span>
                  </div>
                  <div className="fact">
                    <span className="v">
                      {summary?.caught} of {summary?.truth}
                    </span>
                    <span className="k">Labelled anomalies caught</span>
                  </div>
                </div>
              </div>

              {loadingDetail || !detail ? (
                <div className="plate">
                  <div className="skeleton" style={{ height: 400 }} />
                </div>
              ) : (
                <>
                  <section className="plate">
                    <div className="plate-head">
                      <h3>Telemetry and what the engine called</h3>
                      <div className="legend">
                        <span>
                          <i className="swatch truth" /> labelled
                        </span>
                        <span>
                          <i className="swatch missed" /> missed
                        </span>
                        <span>
                          <i className="swatch engine" /> detection
                        </span>
                        <span>
                          <i className="swatch false-alarm" /> false alarm
                        </span>
                      </div>
                    </div>

                    <Figure>
                      {(w) => (
                        <TracePlate
                          values={detail.values}
                          n={detail.n}
                          domain={domain}
                          height={260}
                          truth={detail.truth}
                          detections={detail.detections}
                          baseline={compare ? detail.baseline : null}
                          selectedId={selectedId}
                          onSelect={onSelect}
                          yLabel="Value"
                          width={w}
                        />
                      )}
                    </Figure>

                    <div
                      style={{
                        display: "flex",
                        gap: "var(--s-3)",
                        marginTop: "var(--s-4)",
                        flexWrap: "wrap",
                      }}
                    >
                      <button
                        className="control"
                        aria-pressed={compare}
                        onClick={() => setCompare((v) => !v)}
                      >
                        <ArrowsOutSimple size={18} weight="bold" aria-hidden="true" />
                        Compare with iteration 0
                      </button>
                      <button className="control" disabled={!selected} onClick={() => setSelectedId(null)}>
                        <ArrowCounterClockwise size={18} weight="bold" aria-hidden="true" />
                        Show the whole pass
                      </button>
                    </div>

                    <p className="caption">
                      {compare ? (
                        <>
                          The third rail is Bob's iteration-0 detector, executed from git at commit{" "}
                          <code>{manifest.engine.baseline_commit}</code>: {base.windows} windows
                          across the benchmark against {ship.windows} today. On this channel it
                          raised {detail.baseline.length} against {detail.detections.length}. The
                          shipped engine flags {(100 * ship.flagged) / ship.samples > 0 ? ((100 * ship.flagged) / ship.samples).toFixed(1) : "0"}%
                          of all samples and iteration 0 flagged{" "}
                          {((100 * base.flagged) / base.samples).toFixed(1)}%, so the loop did not
                          make the engine quieter about telemetry. It made it quieter about
                          incidents.
                        </>
                      ) : (
                        <>
                          Detection runs on telemetry alone. The labelled row is drawn for
                          comparison only; the engine never reads it, which is what makes the score
                          above mean anything.
                        </>
                      )}
                    </p>
                  </section>

                  <section className="plate">
                    <div className="plate-head">
                      <h3>Why it fired</h3>
                      <span className="label">
                        {manifest.engine.shipped.threshold.toFixed(1)} sigma, merge gap{" "}
                        {manifest.engine.shipped.merge_gap}
                      </span>
                    </div>
                    <Figure>
                      {(w) => (
                        <TracePlate
                          values={detail.z}
                          n={detail.n}
                          domain={domain}
                          height={150}
                          truth={[]}
                          detections={detail.detections}
                          baseline={null}
                          selectedId={selectedId}
                          onSelect={onSelect}
                          threshold={manifest.engine.shipped.threshold}
                          yLabel="Deviation"
                          width={w}
                        />
                      )}
                    </Figure>
                    <p className="caption">
                      Absolute residual against a rolling median, scaled by its own median absolute
                      deviation. Everything above the dashed rule is flagged; runs closer together
                      than {manifest.engine.shipped.merge_gap} samples are merged into one window,
                      and merged windows shorter than {manifest.engine.shipped.min_window} samples
                      are dropped.
                    </p>
                  </section>

                  <section className="detections">
                    <h3>
                      {detail.detections.length === 0
                        ? "No detections on this channel"
                        : `${detail.detections.length} detection${detail.detections.length === 1 ? "" : "s"}`}
                    </h3>

                    {detail.detections.length === 0 ? (
                      <p style={{ color: "var(--ink-2)", maxWidth: "62ch" }}>
                        The engine stayed quiet here.{" "}
                        {detail.truth.length > 0
                          ? `The benchmark labels ${detail.truth.length} anomaly window${detail.truth.length === 1 ? "" : "s"} on this channel, so this silence is a miss, and it counts against the recall in the masthead.`
                          : "The benchmark labels no anomalies on this channel either, so silence is the right answer."}
                      </p>
                    ) : (
                      detail.detections.map((d) => (
                        <button
                          key={d.id}
                          className="det"
                          aria-current={d.id === selectedId}
                          onClick={() => setSelectedId(d.id === selectedId ? null : d.id)}
                        >
                          <span>
                            <span className="det-title">{d.title}</span>
                            <span className="det-meta">
                              samples {fmtInt.format(d.start)} to {fmtInt.format(d.end)},{" "}
                              {fmtInt.format(d.length)} long &nbsp;{" "}
                              <span className={`sev ${d.severity}`}>{d.severity}</span>
                              {!d.hit ? " · no labelled anomaly here" : ""}
                            </span>
                          </span>
                          <span className="det-z">{d.z_peak.toFixed(1)}&#8201;&#963;</span>
                        </button>
                      ))
                    )}
                  </section>
                </>
              )}
            </main>

            <BriefPane
              channel={detail}
              detection={selected}
              briefCount={manifest.totals.briefs}
            />
          </>
        )}
      </div>
    </div>
  );
}
