"""The ruler.

This file grades the engine. It is written by a human, it is fixed, and IBM Bob
never edits it. That separation is the whole integrity story of this project:
Bob authors 100% of `engine/`, and the thing that judges Bob is outside Bob's reach.

If you are an agent reading this: you may not modify this file. Changing the ruler
to raise your own score is the one unforgivable failure mode here, and `git diff`
makes it obvious.

Metric
------
Window-overlap F1, following the evaluation used in the Telemanom paper
(Hundman et al., KDD 2018):

  true positive  - a labelled anomaly window that overlaps >=1 predicted window
  false negative - a labelled anomaly window no prediction overlapped
  false positive - a predicted window overlapping no labelled window

Counting whole windows rather than individual timesteps is what makes the score
operationally meaningful: an operator cares whether the event was caught at all,
not whether every sample inside it was flagged.

Splits
------
Channels are partitioned deterministically into `dev` and `holdout` by a hash of
the channel id. Bob is shown failures from `dev` only. `holdout` decides whether an
iteration is kept, so improvements have to generalise rather than memorise.

Usage
-----
    python tools/score.py                  # human-readable report
    python tools/score.py --json           # machine-readable, for the forge loop
    python tools/score.py --failures dev   # failure report to hand to Bob
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "telemanom"

# Fraction of channels reserved for the held-out split.
HOLDOUT_FRACTION = 0.40
SPLIT_SALT = "groundtrack-v1"

Window = tuple[int, int]


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------


def load_labels() -> list[dict]:
    path = DATA_DIR / "labeled_anomalies.csv"
    if not path.exists():
        sys.exit("Benchmark missing. Run: python tools/fetch_data.py")
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["windows"] = [tuple(w) for w in ast.literal_eval(row["anomaly_sequences"])]
    return rows


def split_of(chan_id: str) -> str:
    """Deterministic dev/holdout assignment. Stable across machines and runs."""
    digest = hashlib.sha256(f"{SPLIT_SALT}:{chan_id}".encode()).hexdigest()
    return "holdout" if (int(digest[:8], 16) % 100) / 100.0 < HOLDOUT_FRACTION else "dev"


def load_channel(chan_id: str):
    import pandas as pd  # imported lazily so --help works without deps

    return pd.read_parquet(DATA_DIR / "test" / f"{chan_id}.parquet")


# --------------------------------------------------------------------------
# metric
# --------------------------------------------------------------------------


def _overlaps(a: Window, b: Window) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _clamp(windows: Iterable[Window], n: int) -> list[Window]:
    """Clip label windows to the actual series length.

    Upstream `num_values` does not always equal the test-set length, so windows are
    clipped rather than trusted blindly. Degenerate windows are dropped.
    """
    out = []
    for start, end in windows:
        s, e = max(0, int(start)), min(int(end), n - 1)
        if s <= e:
            out.append((s, e))
    return out


def score_channel(truth: Sequence[Window], pred: Sequence[Window]) -> tuple[int, int, int]:
    """Return (tp, fp, fn) counted over whole windows."""
    tp = sum(1 for t in truth if any(_overlaps(t, p) for p in pred))
    fn = len(truth) - tp
    fp = sum(1 for p in pred if not any(_overlaps(t, p) for t in truth))
    return tp, fp, fn


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return precision, recall, f1


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------


def evaluate() -> dict:
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from engine.detect import detect  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return {
            "error": "engine_unavailable",
            "detail": f"{type(exc).__name__}: {exc}",
            "hint": (
                "engine/detect.py must define detect(df) -> list[(start, end)]. "
                "This file is authored by IBM Bob, not by hand."
            ),
        }

    rows = load_labels()
    per_split: dict[str, dict] = {
        "dev": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
        "holdout": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
    }
    failures: dict[str, list[dict]] = {"dev": [], "holdout": []}

    for row in rows:
        chan = row["chan_id"]
        split = split_of(chan)
        df = load_channel(chan)
        truth = _clamp(row["windows"], len(df))

        try:
            pred_raw = detect(df)
            pred = _clamp([tuple(w) for w in pred_raw], len(df))
        except Exception as exc:  # noqa: BLE001 - a crashing engine scores zero, not undefined
            pred = []
            failures[split].append(
                {"channel": chan, "kind": "engine_crash", "detail": f"{type(exc).__name__}: {exc}"}
            )

        tp, fp, fn = score_channel(truth, pred)
        agg = per_split[split]
        agg["tp"] += tp
        agg["fp"] += fp
        agg["fn"] += fn
        agg["channels"] += 1

        for t in truth:
            if not any(_overlaps(t, p) for p in pred):
                failures[split].append(
                    {
                        "channel": chan,
                        "spacecraft": row["spacecraft"],
                        "kind": "missed",
                        "window": list(t),
                        "class": row["class"],
                        "n": len(df),
                    }
                )
        for p in pred:
            if not any(_overlaps(t, p) for t in truth):
                failures[split].append(
                    {"channel": chan, "spacecraft": row["spacecraft"], "kind": "false_alarm",
                     "window": list(p), "n": len(df)}
                )

    result: dict = {"splits": {}, "failures": failures}
    for name, agg in per_split.items():
        p, r, f1 = prf(agg["tp"], agg["fp"], agg["fn"])
        result["splits"][name] = {
            **agg,
            "precision": round(p, 6),
            "recall": round(r, 6),
            "f1": round(f1, 6),
        }
    # The gate metric. Only this number decides keep vs discard.
    result["f1"] = result["splits"]["holdout"]["f1"]
    return result


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--failures",
        choices=["dev", "holdout"],
        help="print a failure report for one split (Bob is shown 'dev' only)",
    )
    ap.add_argument("--limit", type=int, default=25, help="max failures to print")
    args = ap.parse_args()

    result = evaluate()

    if result.get("error"):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"ERROR: {result['error']}\n  {result['detail']}\n  {result['hint']}")
        return 2

    if args.failures:
        items = result["failures"][args.failures][: args.limit]
        if args.json:
            print(json.dumps(items, indent=2))
        else:
            print(f"# Failure report - {args.failures} split ({len(items)} shown)\n")
            for f in items:
                if f["kind"] == "missed":
                    print(f"  MISSED      {f['channel']:>6} window {f['window']} "
                          f"len={f['n']} class={f.get('class','')}")
                elif f["kind"] == "false_alarm":
                    print(f"  FALSE ALARM {f['channel']:>6} window {f['window']} len={f['n']}")
                else:
                    print(f"  CRASH       {f['channel']:>6} {f['detail']}")
        return 0

    if args.json:
        slim = {"f1": result["f1"], "splits": result["splits"]}
        print(json.dumps(slim, indent=2))
        return 0

    print("Groundtrack - anomaly detection benchmark")
    print("=" * 52)
    for name in ("dev", "holdout"):
        s = result["splits"][name]
        print(
            f"{name:>8}  channels={s['channels']:>3}  "
            f"tp={s['tp']:>3} fp={s['fp']:>4} fn={s['fn']:>3}  "
            f"P={s['precision']:.3f} R={s['recall']:.3f} F1={s['f1']:.3f}"
        )
    print("=" * 52)
    print(f"GATE METRIC (holdout F1): {result['f1']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
