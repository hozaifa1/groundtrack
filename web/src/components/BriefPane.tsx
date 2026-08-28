import type { ChannelDetail, Detection } from "../types";
import { fmtInt } from "../lib/plot";

interface Props {
  channel: ChannelDetail | null;
  detection: Detection | null;
  briefCount: number;
}

const SIGNATURE_COPY: Record<string, string> = {
  level_shift: "sustained displacement from baseline",
  transient_spike: "brief excursion returning to baseline",
  noise_burst: "elevated variance without a mean offset",
  unclassified: "no standard signature matched",
};

export function BriefPane({ channel, detection, briefCount }: Props) {
  if (!detection) {
    return (
      <aside className="brief" aria-label="Operator brief">
        <div className="brief-head">
          <h3>Operator brief</h3>
        </div>
        <div className="empty">
          <p>
            {channel && channel.detections.length > 0
              ? "Open a detection to read the brief IBM Granite wrote for it."
              : "The engine raised nothing on this channel, so there is no brief. Channels with a detection count in the index have one brief each."}
          </p>
        </div>
        <Provenance count={briefCount} />
      </aside>
    );
  }

  const b = detection.brief;

  return (
    <aside className="brief" aria-label="Operator brief">
      <div className="brief-head">
        <h3>{detection.title}</h3>
        <span className={`sev ${detection.severity}`}>{detection.severity} severity</span>
      </div>

      <div className="brief-body">
        {b ? (
          <>
            <section className="brief-section lead">
              <h4>What happened</h4>
              <p>{b.happened}</p>
            </section>
            <section className="brief-section">
              <h4>Why it matters</h4>
              <p>{b.matters}</p>
            </section>
            <section className="brief-section">
              <h4>What to do next</h4>
              <p>{b.next}</p>
            </section>
          </>
        ) : (
          <section className="brief-section">
            <h4>No committed brief</h4>
            <p>
              This window has no brief in <code>results/briefs/</code>. That means the engine
              changed after the brief set was generated, and the two are out of step. Regenerate
              with <code>tools/make_briefs.py</code>.
            </p>
          </section>
        )}

        <div className="brief-stats">
          <div>
            <div className="v">{fmtInt.format(detection.start)}</div>
            <div className="k">First sample</div>
          </div>
          <div>
            <div className="v">{fmtInt.format(detection.end)}</div>
            <div className="k">Last sample</div>
          </div>
          <div>
            <div className="v">{fmtInt.format(detection.length)}</div>
            <div className="k">Window length</div>
          </div>
          <div>
            <div className="v">{detection.z_peak.toFixed(1)}</div>
            <div className="k">Peak deviation, sigma</div>
          </div>
          <div>
            <div className="v">{detection.w_mean.toFixed(3)}</div>
            <div className="k">Mean inside</div>
          </div>
          <div>
            <div className="v">{detection.b_mean.toFixed(3)}</div>
            <div className="k">Mean outside</div>
          </div>
        </div>

        <section className="brief-section">
          <h4>Runbook</h4>
          <p>{detection.action}</p>
          <p style={{ marginTop: "var(--s-3)", color: "var(--ink-2)", fontSize: "var(--t-sm)" }}>
            Classified <strong>{detection.signature.replace(/_/g, " ")}</strong>:{" "}
            {SIGNATURE_COPY[detection.signature] ?? "pattern outside the standard set"}.
            {detection.cmds.length > 0
              ? ` Commands active in this window: ${detection.cmds.join(", ")}.`
              : " No commands were active in this window."}
          </p>
        </section>
      </div>

      <Provenance count={briefCount} file={b?.file} />
    </aside>
  );
}

function Provenance({ count, file }: { count: number; file?: string }) {
  return (
    <div className="provenance">
      All {count} briefs were written by IBM Granite (<code>granite4:3b</code>) running locally
      through Ollama, generated offline and committed to the repository. Nothing on this page calls
      a model. Decoding is pinned, so <code>tools/make_briefs.py --check</code> re-asks Granite and
      diffs the answer against what is committed.
      {file ? (
        <>
          {" "}
          This one is <code>{file}</code>.
        </>
      ) : null}
      <br />
      <br />
      Runbook wording is illustrative operator-facing text in generic flight-rule style. It is not
      certified NASA operational doctrine.
    </div>
  );
}
