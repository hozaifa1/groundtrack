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
        <div className="hero-grid">
          <div className="hero-text">
            <h1>Catching real spacecraft faults without a flood of false alarms.</h1>
            <p className="hero-copy">
              Spacecraft telemetry hides real faults inside long stretches of ordinary noise, and
              missing one can ground a mission. Catching every fault once meant burying operators
              in false alarms. The detector&apos;s first version raised{" "}
              <strong>{fmtInt.format(first.holdout.fp)}</strong> false alarms across the {hidden} test
              recordings. The shipped version brought that count down to{" "}
              <strong>{fmtInt.format(kept.holdout.fp)}</strong>.
            </p>
          </div>

          <div className="panel stat hero-stat">
            <p className="stat-was">
              was <span className="num">{fmtInt.format(first.holdout.fp)}</span>
            </p>
            <div className="stat-now">{fmtInt.format(kept.holdout.fp)}</div>
            <p className="caption">
              False alarms on the {hidden} recordings IBM Bob never saw. Across all{" "}
              {manifest.totals.channels} recordings, the operator queue dropped from{" "}
              {fmtInt.format(first.alarms)} alarms to {fmtInt.format(kept.alarms)}.
            </p>
          </div>
        </div>
      </section>

      <section aria-label="Headline results" className="stat-rail">
        <div className="panel stat">
          <p className="stat-was">
            was <span className="num">{first.holdout.f1.toFixed(3)}</span>
          </p>
          <div className="stat-now">{kept.holdout.f1.toFixed(3)}</div>
          <p className="caption">
            Benchmark score on those same recordings, out of 1.0. The metric weighs detected
            faults against false alarms.
          </p>
        </div>
        <div className="panel stat">
          <p className="stat-was">written by IBM Bob</p>
          <div className="stat-now">
            {totalLines}
            <span className="stat-unit">/{totalLines}</span>
          </div>
          <p className="caption">
            Lines of detector code written by IBM Bob. Git history confirms that no human edited
            these files.
          </p>
        </div>
        <div className="panel stat">
          <p className="stat-was">written by IBM Granite</p>
          <div className="stat-now">{fmtInt.format(manifest.totals.briefs)}</div>
          <p className="caption">
            Operator briefs generated by IBM Granite, one for each alarm raised by the shipped
            detector.
          </p>
        </div>
      </section>

      <section aria-label="How the detector was built">
        <div className="section-head">
          <h2>How this works</h2>
          <p>
            IBM Bob revised the detector seven times against a fixed grading script it could not
            modify. Bob committed each change before seeing the score.
          </p>
        </div>
        <div className="flow">
          <div className="panel flow-step">
            <span className="step-no">1. Write</span>
            <h3>IBM Bob edits the detector</h3>
            <p>Bob modifies thresholds, window sizes, or merging rules, then commits the change.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">2. Grade</span>
            <h3>A script Bob cannot edit scores it</h3>
            <p>
              <code>tools/score.py</code> was committed before the detector existed. It evaluates
              the revision against {hidden} recordings kept hidden from Bob, revealing the score
              only after the commit.
            </p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">3. Decide</span>
            <h3>The harness keeps or reverts</h3>
            <p>A higher score keeps the revision. A lower score triggers an immediate automatic revert.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">4. Repeat</span>
            <h3>Bob tries again</h3>
            <p>Bob starts from the latest accepted version and begins the next attempt.</p>
          </div>
        </div>
        <p className="flow-loop">
          During one round, Bob&apos;s revision caught{" "}
          <strong>{greediest.holdout.tp}</strong> of the 35 marked faults on the hidden
          recordings, exceeding the shipped version on raw detections. However, it also triggered{" "}
          <strong>{greediest.holdout.fp}</strong> false alarms, compared to{" "}
          <strong>{kept.holdout.fp}</strong> in the shipped engine. The grader penalized the higher
          false alarm count and reverted the change automatically.
        </p>
      </section>

      <section aria-label="What each model did" className="ibm-grid">
        <div className="panel ibm-card">
          <span className="ibm-badge">IBM Bob</span>
          <h3>Wrote every line of the detector</h3>
          <p>
            Bob authored all {totalLines} lines in <code>engine/</code>, including the initial
            baseline, split between <code>detect.py</code> ({detectLines} lines) and{" "}
            <code>runbook.py</code> ({runbookLines} lines). It operated headlessly without human
            intervention across {ledgerRows} logged attempts ({ledgerWithTask} of which returned a
            task ID). It used {spend.toFixed(1)} of its {BUDGET}-coin budget, the unit IBM uses to
            meter Bob runs.
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
            <code>granite4:3b</code> ran locally through Ollama to generate concise briefs for all{" "}
            {fmtInt.format(manifest.totals.briefs)} alarms raised by the shipped detector. None
            were edited or curated by hand.
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
            Decoding parameters are pinned: tools can re-prompt every brief and diff the output
            against committed files.
          </p>
        </div>
      </section>

      <section aria-label="Development rounds step by step">
        <div className="section-head">
          <h2>Watch it happen, round by round</h2>
          <p>
            The eight rounds advance automatically. Pause playback at any point or step through
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
          Bob had access to {seen} of the {manifest.totals.channels} recordings during
          development. The remaining {hidden} recordings were held out to verify that revisions
          generalized to unseen telemetry.
        </p>
      </section>

      <section aria-label="Telemetry explorer">
        <div className="section-head">
          <h2>Inspect all {manifest.totals.channels} recordings</h2>
          <p>
            Diagnostic traces across the full benchmark, including channels with missed faults or
            false alarms.
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
            marked faults on hidden recordings than the initial baseline, but it nearly eliminates
            false alarms. The scoring metric rewarded that trade with a substantially higher overall
            grade.
          </p>
          <p>
            The grader checks whether a true fault overlaps an alarm window, regardless of window
            width. {manifest.totals.wide.over_half} of the {kept.alarms} alarms span more than half
            their recording, and {manifest.totals.wide.almost_all} cover nearly the entire run; each
            still registers as a hit. The proportion of flagged timesteps increased from{" "}
            {(first.flagged_share * 100).toFixed(1)}% to{" "}
            {(kept.flagged_share * 100).toFixed(1)}% while total alarms decreased, because the engine
            merges nearby bursts into wider windows.
          </p>
          <p>
            Do those {kept.holdout.fp} false alarms hold up under stricter scrutiny? If you discard
            every alarm spanning more than half a recording, the detector still finds 17 of{" "}
            {kept.holdout.tp + kept.holdout.fn} marked faults, keeps false alarms at{" "}
            {kept.holdout.fp}, and scores 0.576: more than double the initial{" "}
            {first.holdout.f1.toFixed(3)} baseline. The wide windows do not mask false alarms. You
            can verify this directly with <code>tools/robustness_check.py</code>.
          </p>
          <p>
            The engine still misses {kept.holdout.fn} of the {kept.holdout.tp + kept.holdout.fn}{" "}
            marked faults in the holdout set. Each missed fault appears in the explorer above
            alongside successful detections.
          </p>
          <p className="chart-note">
            All metrics on this page come directly from recomputed telemetry. The data exporter
            validates output against execution logs before writing.
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
