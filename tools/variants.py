"""Every version of the detector the loop ever ran, so the console can draw them.

The console's walkthrough steps from the first detector Bob wrote to the last
one, redrawing the chart at each step. That needs the *output* of six different
detectors, and only two of them still exist as code: the version that shipped is
in `engine/detect.py`, and the first version is recoverable from git. The four in
between were reverted by the gate the moment they scored, exactly as the rules
require, so nothing was ever committed.

What survives them is `results/ledger.jsonl`, which records for each round the one
change that was made and the precision, recall and F1 it earned. This module
rebuilds each of those detectors from the recorded change, and then refuses to
hand any of them to the console until the rebuilt detector reproduces the
recorded precision, recall and F1 to six decimal places on the held-out channels.
A reconstruction that scores differently is a different detector, and `check()`
fails loudly rather than letting the console draw a picture of something that
never ran.

That check is not a formality. All five reconstructions match the ledger exactly,
including round 5, whose change was a mechanism rather than a constant.

Nothing here is imported by `engine/`. This file reads the labels in order to
score, and the engine is never allowed to see them.
"""

from __future__ import annotations

import ast
import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = REPO_ROOT / "data" / "telemanom"

from tools.score import _clamp, prf, score_channel, split_of  # noqa: E402

# The MAD-to-sigma consistency factor is the one constant no round ever touched.
MAD_CONSISTENCY_FACTOR = 1.4826
ROLLING_WINDOW = 100


# --------------------------------------------------------------------------
# the pieces every round shares
# --------------------------------------------------------------------------


def _residual(values: np.ndarray):
    """Absolute distance from a rolling median, and the channel's noise level.

    Every round in the loop kept this front end. What changed between them was
    what happened to the number that comes out of it.
    """
    rolling = pd.Series(values).rolling(window=ROLLING_WINDOW, min_periods=1).median().to_numpy()
    residual = values - rolling
    absolute = np.abs(residual)
    mad = float(np.median(absolute)) * MAD_CONSISTENCY_FACTOR
    if mad < 1e-10:
        std = float(pd.Series(residual).std())
        if std < 1e-10:
            return None, None
        return absolute, std
    return absolute, mad


def _runs(mask: np.ndarray) -> list:
    if not mask.any():
        return []
    padded = np.concatenate(([False], mask, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0] - 1
    return list(zip(starts.tolist(), ends.tolist()))


def _merge(segments: list, max_gap: int) -> list:
    if not segments:
        return []
    merged = [segments[0]]
    for start, end in segments[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end - 1 <= max_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


# --------------------------------------------------------------------------
# the rounds
# --------------------------------------------------------------------------


def _scalar(threshold: float, merge_gap: int, min_len: int):
    """Rounds 0, 1, 2 and 6: the same machinery, different numbers."""

    def detect(df: pd.DataFrame) -> list:
        absolute, scale = _residual(df["value"].to_numpy(dtype=float))
        if absolute is None:
            return []
        z = absolute / scale
        segments = _merge(_runs(z > threshold), merge_gap)
        return [(s, e) for s, e in segments if e - s + 1 >= min_len]

    return detect


def _local_scale(df: pd.DataFrame) -> list:
    """Round 5: measure the noise level in a moving window instead of once.

    From the ledger: a rolling median absolute deviation over 300 samples,
    floored at a tenth of the whole-channel figure so a temporarily flat stretch
    cannot drive the scale to zero.
    """
    absolute, global_scale = _residual(df["value"].to_numpy(dtype=float))
    if absolute is None:
        return []
    local = (
        pd.Series(absolute).rolling(window=300, min_periods=1).median().to_numpy()
        * MAD_CONSISTENCY_FACTOR
    )
    scale = np.maximum(local, 0.1 * global_scale)
    scale = np.where(scale < 1e-10, global_scale, scale)
    z = absolute / scale
    return [(s, e) for s, e in _merge(_runs(z > 4.0), 50) if e - s + 1 >= 5]


def _area(df: pd.DataFrame) -> list:
    """Round 7: judge a window by how far it strays in total, not by its peak.

    From the ledger: 4.0 becomes a floor for candidate samples rather than the
    verdict, the merge gap widens to 200, and a window survives only if the
    excursion above the floor, summed over the window, reaches 40.
    """
    absolute, scale = _residual(df["value"].to_numpy(dtype=float))
    if absolute is None:
        return []
    z = absolute / scale
    segments = _merge(_runs(z > 4.0), 200)
    segments = [(s, e) for s, e in segments if e - s + 1 >= 5]
    return [
        (s, e)
        for s, e in segments
        if float(np.sum(np.maximum(z[s : e + 1] - 4.0, 0.0))) >= 40.0
    ]


@dataclass(frozen=True)
class Round:
    """One version of the detector, with what the harness recorded about it."""

    key: str
    iteration: int
    detect: Callable[[pd.DataFrame], list] = field(repr=False)
    ledger_f1: float = None
    ledger_precision: float = None
    ledger_recall: float = None


ROUNDS = [
    Round("start", 0, _scalar(4.0, 50, 5), 0.265957, 0.163399, 0.714286),
    Round("round1", 1, _scalar(4.0, 50, 12), 0.250000, 0.160000, 0.571429),
    Round("round2", 2, _scalar(4.5, 50, 5), 0.254545, 0.161538, 0.600000),
    Round("round5", 5, _local_scale, 0.248804, 0.149425, 0.742857),
    Round("round6", 6, _scalar(6.0, 150, 5), 0.622951, 0.730769, 0.542857),
    Round("round7", 7, _area, 0.615385, 0.666667, 0.571429),
]


# --------------------------------------------------------------------------
# scoring one reconstruction
# --------------------------------------------------------------------------


def _label_rows() -> list:
    with (DATA_DIR / "labeled_anomalies.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["windows"] = [tuple(w) for w in ast.literal_eval(row["anomaly_sequences"])]
    return rows


def run(detect: Callable[[pd.DataFrame], list], frames: dict) -> dict:
    """Score one detector the way tools/score.py scores the shipped one.

    The label file carries one channel twice, with two slightly different
    labelled windows, and the scorer walks the file row by row. Following it row
    by row here is what makes the F1 comparable; the alarm and channel counts
    below deliberately count each channel once instead.
    """
    rows = _label_rows()
    per_split = {
        "dev": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
        "holdout": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
    }
    windows_by_channel: dict = {}

    for row in rows:
        chan = row["chan_id"]
        df = frames.get(chan)
        if df is None:
            continue
        n = len(df)
        if chan not in windows_by_channel:
            windows_by_channel[chan] = _clamp([tuple(map(int, w)) for w in detect(df)], n)
        pred = windows_by_channel[chan]
        truth = _clamp(row["windows"], n)
        tp, fp, fn = score_channel(truth, pred)
        agg = per_split[split_of(chan)]
        agg["tp"] += tp
        agg["fp"] += fp
        agg["fn"] += fn
        agg["channels"] += 1

    splits = {}
    for name, agg in per_split.items():
        p, r, f1 = prf(agg["tp"], agg["fp"], agg["fn"])
        splits[name] = {**agg, "precision": round(p, 6), "recall": round(r, 6), "f1": round(f1, 6)}

    alarms = sum(len(w) for w in windows_by_channel.values())
    firing = sum(1 for w in windows_by_channel.values() if w)
    flagged = sum(e - s + 1 for w in windows_by_channel.values() for s, e in w)
    samples = sum(len(frames[c]) for c in windows_by_channel)

    return {
        "splits": splits,
        "alarms": alarms,
        "channels_firing": firing,
        "flagged": flagged,
        "samples": samples,
        "windows": windows_by_channel,
    }


def check(frames: dict) -> list:
    """Return one line per reconstruction that disagrees with the ledger."""
    problems = []
    for rnd in ROUNDS:
        if rnd.ledger_f1 is None:
            continue
        got = run(rnd.detect, frames)["splits"]["holdout"]
        for label, recorded in (
            ("f1", rnd.ledger_f1),
            ("precision", rnd.ledger_precision),
            ("recall", rnd.ledger_recall),
        ):
            if recorded is not None and abs(got[label] - recorded) > 1e-6:
                problems.append(
                    f"{rnd.key}: held-out {label} {got[label]:.6f} "
                    f"does not match the recorded {recorded:.6f}"
                )
    return problems


def load_frames() -> dict:
    frames = {}
    for row in _label_rows():
        chan = row["chan_id"]
        if chan in frames:
            continue
        path = DATA_DIR / "test" / f"{chan}.parquet"
        if path.exists():
            frames[chan] = pd.read_parquet(path)
    return frames


if __name__ == "__main__":
    all_frames = load_frames()
    found = check(all_frames)
    for r in ROUNDS:
        outcome = run(r.detect, all_frames)
        holdout = outcome["splits"]["holdout"]
        recorded = f"   recorded {r.ledger_f1:.6f}" if r.ledger_f1 is not None else ""
        print(
            f"{r.key:8s} alarms {outcome['alarms']:4d} on "
            f"{outcome['channels_firing']:3d} channels   "
            f"held-out F1 {holdout['f1']:.6f}{recorded}"
        )
    if found:
        print("\nMISMATCH")
        for line in found:
            print("  " + line)
        raise SystemExit(1)
    print("\nEvery reconstruction reproduces the recorded held-out score.")
