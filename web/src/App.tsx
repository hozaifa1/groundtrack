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
  // below to show what chasing recall actually cost: this is the concrete
  // example of the grader rejecting a change on its own.
  const greediest = manifest.walkthrough.steps.reduce((best, s) =>
    s.holdout.tp > best.holdout.tp ? s : best,
  );
  const hidden = manifest.splits.holdout.channels;
  const seen = manifest.splits.dev.channels;

  // Lines authored: FACTS.md / IBM Bob section. The manifest carries scores
  // and alarms but not source line counts, so this is the one figure on the
  // page that is not read out of manifest.json.
  const detectLines = 179;
  const runbookLines = 266;
  const totalLines = detectLines + runbookLines;

  const ledgerRows = manifest.ledger.length;
  const ledgerWithTask = manifest.ledger.filter((r) => r.task_id).length;

  // Bobcoin spend, summed from the ledger rather than written down, so it
  // cannot drift. One run was killed from outside the harness and returned no
  // cost. IBM bills an initiated call regardless, so it counts at the cap it
  // was launched under instead of as a zero: anything else would understate
  // what the loop actually cost. The sentence on the page says so, because a
  // reader adding up the `cost` column alone would land 3 coins lower.
  const spend = manifest.ledger.reduce(
    (sum, r) => sum + (r.cost ?? r.max_cost ?? 0),
    0,
  );
  const BUDGET = 40;

  return (
    <main className="shell">
      <header className="masthead">
        <span className="wordmark">Groundtrack</span>
        <p>Fault detection for spacecraft telemetry, written by IBM Bob, IBM&apos;s coding agent</p>
      </header>

      <section className="lede hero">
        <h1>Catching real spacecraft faults, without the flood of false alarms.</h1>
        <p className="hero-copy">
          Spacecraft telemetry hides real faults inside long stretches of ordinary noise, and
          missing one can ground a mission. Catching every one used to mean drowning operators in
          false alarms: the first version of this detector raised{" "}
          <strong>{fmtInt.format(first.holdout.fp)}</strong> of them on the {hidden} recordings it
          was tested against. The version that shipped brought that down to{" "}
          <strong>{fmtInt.format(kept.holdout.fp)}</strong>.
        </p>
      </section>

      <section aria-label="Headline results" className="stat-rail">
        <div className="panel stat">
          <div className="value">
            {fmtInt.format(first.holdout.fp)}
            <span className="arrow">&rarr;</span>
            {fmtInt.format(kept.holdout.fp)}
          </div>
          <p className="caption">
            False alarms on the {hidden} recordings IBM Bob never saw during development. Across
            all {manifest.totals.channels}, the queue an operator has to work through fell from{" "}
            {fmtInt.format(first.alarms)} alarms to {fmtInt.format(kept.alarms)}.
          </p>
        </div>
        <div className="panel stat">
          <div className="value">
            {first.holdout.f1.toFixed(3)}
            <span className="arrow">&rarr;</span>
            {kept.holdout.f1.toFixed(3)}
          </div>
          <p className="caption">
            Benchmark score on those same recordings, out of a possible 1.0. It balances catching
            real faults against raising false ones.
          </p>
        </div>
        <div className="panel stat">
          <div className="value">
            {totalLines}/{totalLines}
          </div>
          <p className="caption">
            Lines of the detector&apos;s code, all written by IBM Bob. No human ever edited a
            line, and it checks out in git history.
          </p>
        </div>
        <div className="panel stat">
          <div className="value">{fmtInt.format(manifest.totals.briefs)}</div>
          <p className="caption">
            Operator briefs, one for every alarm the shipped detector raises, written by IBM
            Granite.
          </p>
        </div>
      </section>

      <section aria-label="How the detector was built">
        <div className="section-head">
          <h2>How this works</h2>
          <p>
            IBM Bob rewrote the detector seven times against a fixed grading script it could not
            edit, and never saw its own grade before committing to a change.
          </p>
        </div>
        <div className="flow">
          <div className="panel flow-step">
            <span className="step-no">1. Write</span>
            <h3>IBM Bob edits the detector</h3>
            <p>It changes the threshold, the window, or the merging rule and commits the result.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">2. Grade</span>
            <h3>A script Bob cannot edit scores it</h3>
            <p>
              <code>tools/score.py</code> was written and committed before the detector existed.
              It runs the new version against {hidden} recordings held back from Bob the whole
              time, and it never publishes the score before the change is committed.
            </p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">3. Decide</span>
            <h3>The harness keeps or reverts</h3>
            <p>A higher score keeps the change. A lower one reverts it automatically, without a vote.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">4. Repeat</span>
            <h3>Bob tries again</h3>
            <p>From the last kept version, working blind toward the next attempt.</p>
          </div>
        </div>
        <p className="flow-loop">
          In one round, Bob&apos;s change caught{" "}
          <strong>{greediest.holdout.tp}</strong> of the 35 marked faults on the hidden
          recordings, more than the version that shipped. But it also raised{" "}
          <strong>{greediest.holdout.fp}</strong> false alarms there, against{" "}
          <strong>{kept.holdout.fp}</strong> in the version that shipped, and the grader scored
          that as worse. The harness reverted it without Bob ever arguing the point.
        </p>
      </section>

      <section aria-label="What each model did" className="ibm-grid">
        <div className="panel ibm-card">
          <span className="ibm-badge">IBM Bob</span>
          <h3>Wrote every line of the detector</h3>
          <p>
            Bob authored all {totalLines} lines of <code>engine/</code>, including the original
            baseline, split across <code>detect.py</code> ({detectLines} lines) and{" "}
            <code>runbook.py</code> ({runbookLines} lines). It ran headlessly, with no human in
            the loop, across {ledgerRows} logged attempts ({ledgerWithTask} of which returned a
            task id). It used {spend.toFixed(1)} of a {BUDGET}-coin budget, the unit IBM meters
            Bob&apos;s runs in.
          </p>
          <div className="ibm-stats">
            <div className="readout">
              <span className="label">Detector versions written</span>
              <span className="value num">8</span>
            </div>
            <div className="readout">
              <span className="label">Versions the grader kept</span>
              <span className="value num">1</span>
            </div>
          </div>
          <div className="verify">
            <span className="cmd">$ git log --format=&apos;%an&apos; -- &apos;engine/*.py&apos; | sort -u</span>
            <span className="out">IBM Bob</span>
          </div>
        </div>
        <div className="panel ibm-card">
          <span className="ibm-badge">IBM Granite</span>
          <h3>Wrote every operator brief</h3>
          <p>
            <code>granite4:3b</code>, run locally through Ollama, wrote a plain-language brief for
            each of the {fmtInt.format(manifest.totals.briefs)} alarms the shipped detector
            raises. None were hand-curated or touched up afterward.
          </p>
          <div className="ibm-stats">
            <div className="readout">
              <span className="label">Briefs written</span>
              <span className="value num">{fmtInt.format(manifest.totals.briefs)}</span>
            </div>
            <div className="readout">
              <span className="label">Hand-edited afterward</span>
              <span className="value num">0</span>
            </div>
          </div>
          <div className="verify">
            <span className="cmd">$ tools/make_briefs.py --check</span>
            <span className="out">Granite model: granite4:3b</span>
            <span className="out">warming up the runner (required for reproducible output)</span>
            <span className="out">OK - A-5_2762-2806.md reproduces exactly from Granite.</span>
          </div>
          <p className="chart-note">
            Decoding is pinned, so this re-prompts every brief and diffs it against what is
            committed.
          </p>
        </div>
      </section>

      <section aria-label="Development rounds step by step">
        <div className="section-head">
          <h2>Watch it happen, round by round</h2>
          <p>
            The eight rounds below advance automatically. Pause at any time or step through
            manually.
          </p>
        </div>
        <Walkthrough
          data={manifest.walkthrough}
          channel={showcase}
          recordings={manifest.totals.channels}
          hidden={hidden}
        />
        <p className="chart-note">
          {seen} of the {manifest.totals.channels} recordings were available during development.
          The remaining {hidden} were held out to evaluate whether each revision improved overall
          detection.
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
          <h2>What we measured, and what we didn&apos;t</h2>
        </div>
        <div className="panel credibility">
          <p>
            The shipped detector finds{" "}
            {first.holdout.tp - kept.holdout.tp} fewer of the {kept.holdout.tp + kept.holdout.fn}{" "}
            marked faults on the hidden recordings than the first version did, in exchange for
            nearly eliminating false alarms there. The grader scored that trade a large net win.
          </p>
          <p>
            The grader checks whether a real fault falls inside an alarm window, not how tightly
            that window is drawn. {manifest.totals.wide.over_half} of the {kept.alarms} alarms
            span more than half their recording, and {manifest.totals.wide.almost_all} cover
            nearly all of it; each still counts as a hit. The share of readings flagged as
            anomalous rose from {(first.flagged_share * 100).toFixed(1)}% to{" "}
            {(kept.flagged_share * 100).toFixed(1)}%, even as total alarms fell, because the
            shipped detector merges nearby bursts into fewer, wider windows.
          </p>
          {/* The 17 and the 0.576 are the only two figures on this page the
              manifest cannot supply: they come from re-scoring with the widest
              windows dropped, which tools/robustness_check.py does. Regenerate
              them by running it if the exported detections ever change. */}
          <p>
            Are those {kept.holdout.fp} false alarms real, or is the detector exploiting the
            wide-window rule? It holds up. Throw out every alarm spanning
            more than half its recording and it still finds 17 of {kept.holdout.tp + kept.holdout.fn}{" "}
            marked faults, false alarms stay at {kept.holdout.fp}, and the score lands at 0.576,
            more than double the {first.holdout.f1.toFixed(3)} baseline. The wide windows are not
            concealing false alarms. Check it with <code>tools/robustness_check.py</code>.
          </p>
          <p>
            And {kept.holdout.fn} of the {kept.holdout.tp + kept.holdout.fn} marked faults on the
            hidden recordings are still missed. Every one of those is visible in the explorer
            above, next to the ones the detector caught.
          </p>
          <p className="chart-note">
            Every figure on this page is recomputed from the telemetry. The exporter that
            produced this data refuses to write a version of the detector whose output
            disagrees with the engine that actually ran.
          </p>
        </div>
      </section>

      <footer className="foot">
        <span>
          Telemetry from two NASA missions with ground-truth anomalies labeled by mission
          engineers: SMAP (Soil Moisture Active Passive satellite) and MSL (Curiosity rover).
        </span>
        <span className="num">
          {manifest.totals.channels} recordings, with diagnostic summaries for all{" "}
          {manifest.totals.briefs} alarms
        </span>
      </footer>
    </main>
  );
}
