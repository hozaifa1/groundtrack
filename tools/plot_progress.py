"""Render results/progress.png from results/ledger.jsonl.

The plot is generated from the ledger, never drawn by hand. That matters more than it
sounds: the ledger is the only record of what the forge loop actually did, including
the attempts that cost money and produced nothing, and a hand-drawn "progress" chart
would quietly lose exactly those. Everything here is read from the file.

Two panels:

* **Held-out F1.** The step line is the *engine's* score — it moves only when the gate
  kept an iteration. The markers are what each attempt actually measured, so a reverted
  attempt appears below the line it failed to beat rather than vanishing.
* **Bobcoin spent.** Two lines, because the true figure is not known. One aborted run
  returned no cost: it may never have been billed, and it cannot be proven either way,
  so `known` counts it as zero and `conservative` counts it at its 3-coin cap. The gap
  between the lines is the uncertainty, drawn rather than argued about.

Usage:
    .venv/Scripts/python.exe tools/plot_progress.py
    .venv/Scripts/python.exe tools/plot_progress.py --out results/progress.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "results" / "ledger.jsonl"

# Outcomes that never produced a scored engine. They still cost money and still belong
# on the chart; they just have no F1 to plot.
UNSCORED = {"cost_cap_hit", "aborted", "guardrail_violation", "correction"}


def load_ledger(path: Path) -> list[dict]:
    """Read the ledger defensively.

    Every field here is optional on purpose. Real entries in this file are missing
    `cost`, `f1_after`, `task_id` and `attempt` in various combinations, and a plotting
    script that assumes otherwise breaks the moment the loop has a bad day - which is
    precisely when the chart is worth having.
    """
    if not path.exists():
        sys.exit(f"No ledger at {path}. Nothing to plot.")
    entries = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"  skipping malformed ledger line {lineno}: {exc}", file=sys.stderr)
    return entries


def as_float(value) -> float | None:
    """None, missing, or a non-number all mean 'no measurement', not zero."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def label_of(entry: dict, index: int) -> str:
    it = entry.get("iteration")
    attempt = entry.get("attempt")
    if it is None:
        return str(index)
    return f"{it}.{attempt}" if attempt not in (None, 1) else str(it)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--out", default=str(REPO_ROOT / "results" / "progress.png"))
    args = ap.parse_args()

    try:
        import matplotlib
        matplotlib.use("Agg")  # headless: this machine has no display and CI would not either
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit(
            "matplotlib is not installed in this interpreter.\n"
            "  .venv/Scripts/python.exe -m pip install -r requirements.txt\n"
            "It is listed in requirements.txt for exactly this script."
        )

    entries = load_ledger(Path(args.ledger))
    if not entries:
        sys.exit("Ledger is empty. Nothing to plot.")

    xs = list(range(len(entries)))
    labels = [label_of(e, i) for i, e in enumerate(entries)]

    # Engine state: the committed holdout F1, which only moves on a keep.
    engine_f1: list[float] = []
    current = 0.0
    for e in entries:
        after = as_float(e.get("f1_after"))
        if e.get("kept") and after is not None:
            current = after
        engine_f1.append(current)

    kept_x, kept_y, rev_x, rev_y, none_x = [], [], [], [], []
    for i, e in enumerate(entries):
        after = as_float(e.get("f1_after"))
        outcome = e.get("outcome")
        if after is None or outcome in UNSCORED:
            none_x.append(i)
            continue
        (kept_x if e.get("kept") else rev_x).append(i)
        (kept_y if e.get("kept") else rev_y).append(after)

    known, conservative = [], []
    k = c = 0.0
    for e in entries:
        cost = as_float(e.get("cost"))
        cap = as_float(e.get("max_cost")) or 0.0
        # A missing cost is not a free run. It is an unknown one: zero in the lower
        # bound, its own cap in the upper.
        k += cost if cost is not None else 0.0
        c += cost if cost is not None else cap
        known.append(k)
        conservative.append(c)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 7.5), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.12})

    ax1.step(xs, engine_f1, where="post", color="#2563EB", lw=2,
             label="engine (gate-kept holdout F1)")
    ax1.scatter(kept_x, kept_y, s=90, color="#16A34A", zorder=5, label="kept")
    ax1.scatter(rev_x, rev_y, s=70, color="#DC2626", marker="v", zorder=5,
                label="reverted (measured, then discarded)")
    for i in none_x:
        ax1.axvline(i, color="#9CA3AF", ls=":", lw=1)
    if none_x:
        ax1.scatter(none_x, [0.0] * len(none_x), s=55, marker="x", color="#6B7280",
                    zorder=5, label="no scored engine (capped / aborted / corrected)")

    for x, y in zip(kept_x, kept_y):
        ax1.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(0, 10),
                     ha="center", fontsize=9, color="#166534")

    ax1.set_ylabel("held-out F1")
    ax1.set_ylim(-0.03, max(0.7, max(engine_f1 + kept_y + rev_y + [0]) + 0.1))
    ax1.set_title("Groundtrack — IBM Bob forge loop, held-out F1 per iteration\n"
                  "every point read from results/ledger.jsonl", fontsize=12)
    ax1.grid(alpha=0.25)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.95)

    ax2.plot(xs, conservative, color="#B45309", lw=2, ls="--",
             label=f"conservative ({conservative[-1]:.2f})")
    ax2.plot(xs, known, color="#0F766E", lw=2, label=f"known spend ({known[-1]:.2f})")
    ax2.fill_between(xs, known, conservative, color="#F59E0B", alpha=0.18)
    ax2.set_ylabel("Bobcoins, cumulative")
    ax2.set_xlabel("ledger entry (iteration.attempt)")
    ax2.set_xticks(xs)
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.grid(alpha=0.25)
    ax2.legend(loc="upper left", fontsize=9, framealpha=0.95)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"wrote {out}")
    print(f"  entries={len(entries)}  kept={len(kept_x)}  reverted={len(rev_x)}  "
          f"unscored={len(none_x)}")
    print(f"  engine holdout F1 now {engine_f1[-1]:.6f}")
    print(f"  Bobcoins: known {known[-1]:.4f}, conservative {conservative[-1]:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
