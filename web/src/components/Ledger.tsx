import type { LedgerRow, Manifest } from "../types";

/** Every iteration the forge loop ran, including the ones that cost coins and
 *  produced nothing. Showing only the kept iteration would make the curve look
 *  like a straight line up, which is not what happened.
 *
 *  Several fields in the ledger are genuinely null, and they are rendered as
 *  "not recorded" rather than coerced to zero. One attempt was killed from
 *  outside by a shell timeout before any cost came back; printing 0.00 for it
 *  would be a made-up number sitting in the middle of the honesty argument. */
export function Ledger({ manifest }: { manifest: Manifest }) {
  const rows = manifest.ledger;
  const kept = rows.filter((r) => r.kept).length;
  const known = rows.filter((r) => typeof r.cost === "number");
  const spend = known.reduce((a, r) => a + (r.cost as number), 0);
  const unknown = rows.length - known.length;

  return (
    <div className="ledger">
      <div className="ledger-inner">
        <h2 className="display" style={{ fontSize: "var(--t-3xl)", marginBottom: "var(--s-5)" }}>
          The forge loop
        </h2>
        <p className="ledger-lede">
          IBM Bob proposes one minimal edit to the engine. The scorer re-runs against a held-out
          split Bob never sees. The harness commits the change or reverts it. Across{" "}
          <strong>{rows.length} recorded attempts</strong>, <strong>{kept} were kept</strong>, for a
          measured spend of <strong>{spend.toFixed(2)} Bobcoins</strong>
          {unknown > 0 ? (
            <>
              {" "}
              plus {unknown} attempt{unknown === 1 ? "" : "s"} whose cost was never recorded, because
              it was killed from outside before the harness could write a line
            </>
          ) : null}
          . The failures are here for the same reason the successes are: a ledger that quietly drops
          them is not evidence of anything.
        </p>

        {rows.map((r, i) => (
          <Row key={`${r.iteration}-${r.attempt ?? 0}-${i}`} row={r} />
        ))}
      </div>
    </div>
  );
}

const OUTCOME_LABEL: Record<string, string> = {
  cost_cap_hit: "cost cap hit",
  baseline_authored: "kept",
  reverted: "reverted",
  aborted: "aborted",
  guardrail_violation: "guardrail stop",
  correction: "ledger correction",
  kept: "kept",
};

function num(v: number | null | undefined, digits: number): string {
  return typeof v === "number" ? v.toFixed(digits) : "not recorded";
}

function Row({ row }: { row: LedgerRow }) {
  const verdict = row.kept ? "kept" : row.outcome === "reverted" ? "reverted" : "none";
  const rep = row.bob_report;

  const delta =
    typeof row.f1_before === "number" && typeof row.f1_after === "number"
      ? row.f1_after - row.f1_before
      : null;

  return (
    <article className="iter">
      <div>
        <div className="iter-n">
          {row.iteration}
          {typeof row.attempt === "number" && row.attempt > 1 ? `.${row.attempt}` : ""}
        </div>
        <div className={`iter-verdict ${verdict}`}>
          {OUTCOME_LABEL[row.outcome] ?? row.outcome.replace(/_/g, " ")}
        </div>
      </div>

      <div>
        <h4>{rep?.change ?? row.note ?? "No change reached the engine."}</h4>
        {rep?.generalises ? (
          <blockquote>{rep.generalises}</blockquote>
        ) : row.note && rep?.change ? (
          <blockquote>{row.note}</blockquote>
        ) : null}
      </div>

      <div className="iter-scores">
        <div className="score-row">
          <span className="k">Dev F1</span>
          <span className="num">{num(row.dev_f1, 3)}</span>
        </div>
        <div className="score-row">
          <span className="k">Holdout F1</span>
          <span className="num">{num(row.holdout_f1, 3)}</span>
        </div>
        <div className="score-row">
          <span className="k">Change</span>
          <span className={`num delta ${delta == null ? "" : delta > 0 ? "up" : "down"}`}>
            {delta == null ? "not scored" : `${delta > 0 ? "+" : ""}${delta.toFixed(3)}`}
          </span>
        </div>
        <div className="score-row">
          <span className="k">Cost</span>
          <span className="num">{num(row.cost, 2)}</span>
        </div>
      </div>
    </article>
  );
}
