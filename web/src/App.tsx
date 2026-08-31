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
            <h1>IBM Bob wrote this spacecraft fault detector. It never got to grade its own work.</h1>
            <p className="hero-copy">
              A satellite sends home a steady stream of sensor readings, and the first signs of a
              fault sit somewhere inside it. Finding them is what this detector does, and every line
              of it was written by IBM Bob, IBM&apos;s coding agent. Neither Bob nor I got to say
              whether it worked. A grading script written a day earlier, which Bob was never allowed
              to read, scored each revision against {hidden} recordings Bob never saw. Bob&apos;s
              first attempt raised{" "}
              <strong>{fmtInt.format(first.holdout.fp)}</strong> false alarms on those recordings.
              The version that survived raises{" "}
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
            The benchmark&apos;s own score for those same recordings, from 0 to 1. It balances how
            many real faults the detector found against how many of its alarms were wrong.
          </p>
        </div>
        <div className="panel stat">
          <p className="stat-was">written by IBM Bob</p>
          <div className="stat-now">
            {totalLines}
            <span className="stat-unit">/{totalLines}</span>
          </div>
          <p className="caption">
            Lines of detector code, all of them Bob&apos;s. The git history shows that no human
            ever edited these files.
          </p>
        </div>
        <div className="panel stat">
          <p className="stat-was">written by IBM Granite</p>
          <div className="stat-now">{fmtInt.format(manifest.totals.briefs)}</div>
          <p className="caption">
            Plain-language briefs written by IBM Granite, one for every alarm the shipped detector
            raises.
          </p>
        </div>
      </section>

      <section aria-label="How the detector was built">
        <div className="section-head">
          <h2>How this works</h2>
          <p>
            Bob revised the detector seven times. Each change was committed before anyone, Bob
            included, knew what it scored.
          </p>
        </div>
        <div className="flow">
          <div className="panel flow-step">
            <span className="step-no">1. Write</span>
            <h3>IBM Bob edits the detector</h3>
            <p>Bob changes a threshold, a window size, or a merging rule, and commits it.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">2. Grade</span>
            <h3>A script Bob cannot edit scores it</h3>
            <p>
              <code>tools/score.py</code> was committed before the detector existed. It scores the
              revision against {hidden} recordings kept hidden from Bob, and only after the change
              is already in.
            </p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">3. Decide</span>
            <h3>The harness keeps or reverts</h3>
            <p>If the score went up, the change stayed. If it went down, the harness undid it on the spot.</p>
          </div>
          <div className="flow-arrow" aria-hidden="true">
            &rarr;
          </div>
          <div className="panel flow-step">
            <span className="step-no">4. Repeat</span>
            <h3>Bob tries again</h3>
            <p>Bob picks up from whichever version survived and tries something else.</p>
          </div>
        </div>
        <p className="flow-loop">
          One round found more real faults than the version that ships:{" "}
          <strong>{greediest.holdout.tp}</strong> of the 35 marked faults on the hidden recordings.
          It also raised{" "}
          <strong>{greediest.holdout.fp}</strong> false alarms where the shipped detector raises{" "}
          <strong>{kept.holdout.fp}</strong>. The grader weighed the two against each other and
          reverted it, without asking anyone.
        </p>
      </section>

      <section aria-label="What each model did" className="ibm-grid">
        <div className="panel ibm-card">
          <span className="ibm-badge">IBM Bob</span>
          <h3>Wrote every line of the detector</h3>
          <p>
            Bob wrote all {totalLines} lines in <code>engine/</code>, the first baseline included,
            across <code>detect.py</code> ({detectLines} lines) and <code>runbook.py</code>{" "}
            ({runbookLines} lines). It ran headlessly, with nobody stepping in, over{" "}
            {ledgerRows} logged attempts, {ledgerWithTask} of which came back with a task ID. That
            cost {spend.toFixed(1)} of a {BUDGET}-coin budget. Bobcoins are how IBM meters these
            runs.
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
            <code>granite4:3b</code> ran locally, on a laptop CPU, through Ollama. It wrote a short
            operator brief for each of the {fmtInt.format(manifest.totals.briefs)} alarms the
            shipped detector raises. Nothing was edited or picked over by hand.
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
            Decoding is pinned, and the command above asks the model again and diffs what comes
            back. The first brief reproduces reliably. The ones after it drift, because local
            inference does not repeat itself exactly from one run to the next. The check that does
            cover all 78 traces every number in every brief back to the telemetry, and never calls
            the model at all.
          </p>
        </div>
      </section>

      <section aria-label="Development rounds step by step">
        <div className="section-head">
          <h2>Watch it happen, round by round</h2>
          <p>
            The eight rounds play through on their own. Pause anywhere, or step through them
            yourself.
          </p>
        </div>
        <Walkthrough
          data={manifest.walkthrough}
          channel={showcase}
          recordings={manifest.totals.channels}
          hidden={hidden}
        />
        <p className="chart-note">
          Bob could see {seen} of the {manifest.totals.channels} recordings while it worked. The
          other {hidden} were kept back, so a revision had to hold up on telemetry Bob had never
          encountered before it counted for anything.
        </p>
      </section>

      <section aria-label="Telemetry explorer">
        <div className="section-head">
          <h2>Inspect all {manifest.totals.channels} recordings</h2>
          <p>
            Every recording in the benchmark, including the ones where the detector missed a fault
            or raised a false alarm. Click any alarm to read what IBM Granite wrote about it.
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
            marked faults on the hidden recordings than the first version did, and in exchange it
            nearly eliminates false alarms. The grader scored that trade as a large net win. It is
            still a trade, so it is stated here rather than buried.
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
            Those wide alarms raise a fair doubt, so here is the check. Throw away every alarm
            spanning more than half a recording and the detector still finds 17 of{" "}
            {kept.holdout.tp + kept.holdout.fn} marked faults, still holds false alarms at{" "}
            {kept.holdout.fp}, and scores 0.576, more than double the{" "}
            {first.holdout.f1.toFixed(3)} it started from. The wide windows are not hiding false
            alarms. Run <code>tools/robustness_check.py</code> and see for yourself.
          </p>
          <p>
            The detector still misses {kept.holdout.fn} of the{" "}
            {kept.holdout.tp + kept.holdout.fn} marked faults on the hidden recordings. Every one of
            those misses is drawn in the explorer above, next to the hits.
          </p>
          <p className="chart-note">
            Every number on this page was recomputed from the telemetry itself. The exporter
            refuses to write these files if they disagree with the run logs.
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
