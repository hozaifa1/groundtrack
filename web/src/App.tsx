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
        <p>Fault detection for spacecraft sensor data, written by an AI agent</p>
      </header>

      <section className="lede">
        <h1>An agent wrote a fault detector, then tried seven times to improve it.</h1>
        <p>
          The detector reads sensor recordings from two NASA missions and raises an alarm when
          something looks wrong. An AI agent called Bob wrote it, then tried seven times to make it
          better. Engineers had already marked the real faults in those recordings, and a grading
          script Bob was never allowed to edit used them to check each attempt. Anything that did
          not score better was undone straight away. One attempt out of the seven survived. It took
          the number of alarms from <strong>{fmtInt.format(first.alarms)}</strong> down to{" "}
          <strong>{fmtInt.format(kept.alarms)}</strong>, and it also finds fewer of the real faults
          than the first version did. Here is every round, in order.
        </p>
      </section>

      <section aria-label="The seven rounds, step by step">
        <p className="cue">
          The eight steps below play by themselves, one after another. Pause at any point, or step
          back and forward yourself.
        </p>
        <Walkthrough
          data={manifest.walkthrough}
          channel={showcase}
          recordings={manifest.totals.channels}
          hidden={hidden}
        />
        <p className="chart-note">
          {seen} of the {manifest.totals.channels} recordings were open to the agent. The other{" "}
          {hidden} were kept hidden, and those are the ones that decided whether a change survived.
          The score balances two things: how many of the real faults were found, and how many of
          the alarms were real. One would be perfect.
        </p>
      </section>

      <section aria-label="Look at any recording">
        <div className="section-head">
          <h2>Look at any of the {manifest.totals.channels} recordings</h2>
          <p>
            The same picture for every recording in the benchmark, including the ones where the
            detector missed a fault or raised an alarm over nothing.
          </p>
        </div>
        <Explorer channels={manifest.channels} initial={showcase} briefs={manifest.totals.briefs} />
      </section>

      <section aria-label="What this does not show">
        <div className="section-head">
          <h2>What the numbers leave out</h2>
        </div>
        <div className="notes">
          <div className="panel note">
            <h3>Some alarms are far too wide</h3>
            <p>
              {manifest.totals.wide.over_half} of the {kept.alarms} alarms cover more than half of
              their recording, and {manifest.totals.wide.almost_all} of those cover almost all of
              it. The grading counts them as correct, because a real fault
              falls somewhere inside. An operator reading one would still have to search the whole
              recording.
            </p>
          </div>
          <div className="panel note">
            <h3>Fewer alarms, more data under suspicion</h3>
            <p>
              The change that survived did not narrow what the detector is suspicious of. It joined
              scattered bursts into single events, so the share of readings sitting inside an alarm
              went up, from{" "}
              {(first.flagged_share * 100).toFixed(1)}% to {(kept.flagged_share * 100).toFixed(1)}%.
            </p>
          </div>
          <div className="panel note">
            <h3>Half the faults are still missed</h3>
            <p>
              On the hidden recordings the detector finds {kept.holdout.tp} of the{" "}
              {kept.holdout.tp + kept.holdout.fn} marked faults. The round that found the most,{" "}
              {greediest.holdout.tp}, raised {greediest.holdout.fp} alarms over nothing on those
              same recordings against the {kept.holdout.fp} this one raises. That is why the
              grading turned it down.
            </p>
          </div>
        </div>
        <p className="chart-note" style={{ marginTop: 18 }}>
          Every figure on this page is recomputed. The pictures of the earlier versions are not
          drawings of what was written down at the time: each one is that version of the detector
          run again over the recordings, and the page will not build unless it scores exactly what
          the record says it scored.
        </p>
      </section>

      <footer className="foot">
        <span>
          Recordings from two NASA missions, with the faults marked by the engineers who published
          them: SMAP, a satellite that measures soil moisture from orbit, and MSL, the Curiosity
          rover on Mars.
        </span>
        <span className="num">
          {manifest.totals.channels} recordings, one write-up for each of the{" "}
          {manifest.totals.briefs} alarms
        </span>
      </footer>
    </main>
  );
}
