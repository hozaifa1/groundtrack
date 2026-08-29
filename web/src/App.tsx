import { useEffect, useState } from "react";
import type { ChannelDetail, Manifest } from "./types";
import { Walkthrough } from "./components/Walkthrough";
import { Explorer } from "./components/Explorer";
import { fmtInt } from "./lib/plot";

export default function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [showcase, setShowcase] = useState<ChannelDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    fetch("data/manifest.json")
      .then((r) => r.json())
      .then((m: Manifest) => {
        if (!live) return;
        setManifest(m);
        return fetch(`data/channel/${m.walkthrough.showcase.channel}.json`)
          .then((r) => r.json())
          .then((c: ChannelDetail) => live && setShowcase(c));
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  if (failed) {
    return (
      <main className="shell">
        <p className="loading">The data files did not load. Reloading the page usually fixes it.</p>
      </main>
    );
  }

  if (!manifest || !showcase) {
    return (
      <main className="shell">
        <p className="loading">Loading the recordings.</p>
      </main>
    );
  }

  const kept = manifest.walkthrough.steps.find((s) => s.key === "round6")!;
  const first = manifest.walkthrough.steps.find((s) => s.key === "start")!;
  // The round that found the most real faults on the hidden recordings, used
  // below to say what finding more of them actually cost.
  const greediest = manifest.walkthrough.steps.reduce((best, s) =>
    s.holdout.tp > best.holdout.tp ? s : best,
  );
  const hidden = manifest.splits.holdout.channels;
  const seen = manifest.splits.dev.channels;

  return (
    <main className="shell">
      <header className="masthead">
        <span className="wordmark">Groundtrack</span>
        <p>Fault detection for spacecraft telemetry, written by an AI agent</p>
      </header>

      <section className="lede">
        <h1>An AI agent wrote a fault detector, then attempted seven revisions.</h1>
        <p>
          The detector monitors telemetry from two NASA missions and flags anomalies. An AI
          agent named Bob wrote the baseline, then attempted seven revisions. A fixed grading
          script evaluated each attempt against engineer-verified faults, reverting any regression.
          Only one attempt survived. It lowered total alarms from{" "}
          <strong>{fmtInt.format(first.alarms)}</strong> to{" "}
          <strong>{fmtInt.format(kept.alarms)}</strong>, though it catches fewer verified faults
          than the initial baseline.
        </p>
      </section>

      <section aria-label="Development rounds step by step">
        <p className="cue">
          The eight rounds below advance automatically. Pause at any time or step through manually.
        </p>
        <Walkthrough
          data={manifest.walkthrough}
          channel={showcase}
          recordings={manifest.totals.channels}
          hidden={hidden}
        />
        <p className="chart-note">
          {seen} of the {manifest.totals.channels} recordings were available during development.
          The remaining {hidden} were held out to evaluate whether each revision improved overall
          detection. The benchmark score balances fault recall and alarm precision, with 1.0
          representing a perfect run.
        </p>
      </section>

      <section aria-label="Telemetry explorer">
        <div className="section-head">
          <h2>Inspect all {manifest.totals.channels} recordings</h2>
          <p>
            Diagnostic traces across the full benchmark, including channels where the detector
            missed a fault or triggered a false alarm.
          </p>
        </div>
        <Explorer channels={manifest.channels} initial={showcase} briefs={manifest.totals.briefs} />
      </section>

      <section aria-label="Benchmark limitations and context">
        <div className="section-head">
          <h2>What the numbers leave out</h2>
        </div>
        <div className="notes">
          <div className="panel note">
            <h3>Some alarms are far too wide</h3>
            <p>
              {manifest.totals.wide.over_half} of the {kept.alarms} alarms span more than half of
              their recording, and {manifest.totals.wide.almost_all} cover nearly all of it.
              The benchmark grades them as correct because a real fault falls inside the window,
              even though an operator would still need to search the entire time series.
            </p>
          </div>
          <div className="panel note">
            <h3>Fewer alarms, larger flagged windows</h3>
            <p>
              The surviving revision merged scattered alarm bursts into single continuous blocks.
              Because of this grouping, the total share of readings flagged as anomalous increased
              from {(first.flagged_share * 100).toFixed(1)}% to{" "}
              {(kept.flagged_share * 100).toFixed(1)}%.
            </p>
          </div>
          <div className="panel note">
            <h3>Half the faults remain undetected</h3>
            <p>
              On the held-out channels, the detector catches {kept.holdout.tp} of the{" "}
              {kept.holdout.tp + kept.holdout.fn} marked faults. The round with the highest recall
              caught {greediest.holdout.tp} faults, but raised {greediest.holdout.fp} false alarms
              compared to {kept.holdout.fp} in the final version, leading the scorer to reject it.
            </p>
          </div>
        </div>
        <p className="chart-note" style={{ marginTop: 18 }}>
          Every figure on this page is recomputed directly from the telemetry. The visualizer reruns
          each detector version across the dataset, and the build fails if any score deviates from
          the recorded benchmark results.
        </p>
      </section>

      <footer className="foot">
        <span>
          Telemetry from two NASA missions with ground-truth anomalies labeled by mission engineers:
          SMAP (Soil Moisture Active Passive satellite) and MSL (Curiosity rover).
        </span>
        <span className="num">
          {manifest.totals.channels} recordings, with diagnostic summaries for all{" "}
          {manifest.totals.briefs} alarms
        </span>
      </footer>
    </main>
  );
}
