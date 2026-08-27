"""Local parameter search over detector configurations, on the dev split only.

Why this exists: four forge iterations have been reverted and the engine is still at
its iteration-0 baseline. Bob gets one shot per ~1.1 coins and cannot try fifty
configurations. This can, for free, and its job is to find out *which mechanisms are
worth an iteration* before one is bought.

Two rules this file obeys, and they are not decoration:

* **Dev only.** `--verify-holdout` exists and is the only thing that ever touches the
  held-out split. It reports; it never selects. Choosing a configuration by its holdout
  score would overfit 35 labelled windows and make every number downstream meaningless,
  including the ones in the ledger.
* **It does not write `engine/`.** The detector here is a throwaway reimplementation
  used for search. Whatever it finds goes to Bob as a direction to implement, and the
  forge loop's gate still decides.

The pruning step is from Hundman et al., KDD 2018 (arXiv:1802.04431) §3.3 — the
component whose ablation in their Table 2 moves precision from 48.9% to 87.5% for 4.8
points of recall.

    .venv/Scripts/python.exe tools/sweep.py --stage baseline
    .venv/Scripts/python.exe tools/sweep.py --stage prune
    .venv/Scripts/python.exe tools/sweep.py --verify-holdout '{"prune_p": 0.13}'
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import score  # the fixed ruler; imported for its metric, never modified


# --------------------------------------------------------------------------
# the parameterised detector
# --------------------------------------------------------------------------


def z_scores_v2(
    values: np.ndarray,
    rolling_window: int,
    ewma_span: int = 0,
    trim_quantile: float = 1.0,
) -> np.ndarray:
    """Residual from a rolling median, with two literature-backed refinements.

    `ewma_span` — smooth the absolute residual with an exponentially-weighted mean
    before thresholding. Both Hundman et al. §3.2 and the more recent LSTD-Detect
    pipeline place a smoothing stage between the residual and the threshold, on the
    grounds that abrupt single-sample spikes in the residual are usually measurement
    noise rather than fault signatures. The committed engine thresholds the raw
    residual and has no such stage.

    `trim_quantile` — estimate the MAD from residuals *below* this quantile, so the
    scale is not inflated by the anomalies it is supposed to find. This is the failure
    mode LSTD-Detect names directly: fixed statistical thresholds "are inflated by
    anomalous segments, catastrophically suppressing recall on the contextual anomalies
    prevalent in spacecraft operations". Our recall fell from 0.714 to 0.543 when the
    threshold rose, which is that effect exactly.

    Note this is *not* iteration 5's rolling local scale, which collapsed towards zero
    in flat stretches and doubled the false alarms. The scale here stays global per
    channel; only the sample set it is estimated from changes.
    """
    n = len(values)
    if n == 0:
        return np.zeros(0)

    baseline = _rolling_median(values, rolling_window)
    residual = np.abs(values - baseline)

    if ewma_span and ewma_span > 1:
        residual = _ewma(residual, ewma_span)

    pool = residual
    if trim_quantile < 1.0:
        cut = float(np.quantile(residual, trim_quantile))
        trimmed = residual[residual <= cut]
        if len(trimmed) >= 10:
            pool = trimmed

    mad = float(np.median(pool)) * 1.4826
    if mad < 1e-10:
        std = float(pool.std())
        if std < 1e-10:
            return np.zeros(n)
        scale = std
    else:
        scale = mad
    return residual / scale


def _ewma(values: np.ndarray, span: int) -> np.ndarray:
    """Exponentially-weighted moving average, trailing, seeded at the first sample."""
    alpha = 2.0 / (span + 1.0)
    out = np.empty_like(values)
    acc = values[0]
    for i, v in enumerate(values):
        acc = alpha * v + (1.0 - alpha) * acc
        out[i] = acc
    return out


def hysteresis_windows(
    z: np.ndarray,
    seed_threshold: float,
    grow_threshold: float,
    merge_gap: int,
    min_len: int,
) -> list[tuple[int, int]]:
    """Two thresholds: a high one to *start* a detection, a low one to *extend* it.

    The problem this attacks is the one measured on the current engine. At 6 sigma
    precision is 0.731 but recall is only 0.543, because a real anomaly crosses 6 sigma
    only at its most extreme moments and the rest of the event sits below the bar. A
    single threshold has to choose between admitting the whole event and admitting
    every noise excursion.

    Hysteresis does not choose. A contiguous run above the low threshold is kept only
    if it contains at least one sample above the high threshold — so the *body* of a
    real anomaly is recovered at 3 sigma while a 3-sigma noise wobble with no strong
    core is still discarded. Recent work reaches the same structure by combining a
    global and a local adaptive threshold; this is the cheap deterministic version of
    that idea, and it needs no model.
    """
    if grow_threshold >= seed_threshold:
        return windows_from_z(z, seed_threshold, merge_gap, min_len)

    low = z > grow_threshold
    if not low.any():
        return []
    high = z > seed_threshold

    padded = np.concatenate(([False], low, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0] - 1

    kept = [(int(s), int(e)) for s, e in zip(starts, ends) if high[s : e + 1].any()]
    if not kept:
        return []

    merged = [kept[0]]
    for start, end in kept[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end - 1 <= merge_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return [(s, e) for s, e in merged if (e - s + 1) >= min_len]


def z_scores(values: np.ndarray, rolling_window: int) -> np.ndarray:
    """Residual from a rolling median, in robust-sigma units.

    Same shape as the committed baseline: rolling median, MAD scale, dimensionless
    ratio. Kept identical on purpose so a sweep result is attributable to the knob
    being swept and not to an incidental rewrite.
    """
    n = len(values)
    if n == 0:
        return np.zeros(0)

    series = _rolling_median(values, rolling_window)
    residual = np.abs(values - series)
    mad = float(np.median(residual)) * 1.4826
    if mad < 1e-10:
        std = float(residual.std())
        if std < 1e-10:
            return np.zeros(n)
        scale = std
    else:
        scale = mad
    return residual / scale


def _rolling_median(values: np.ndarray, window: int) -> np.ndarray:
    """Trailing rolling median with min_periods=1, as a numpy sliding window.

    pandas would do this in one call, but the sweep evaluates the same channel under
    many parameter sets and this is the inner loop.
    """
    n = len(values)
    if window <= 1:
        return values.copy()
    out = np.empty(n, dtype=float)
    # Warm-up region: expanding median.
    warm = min(window, n)
    for i in range(warm):
        out[i] = np.median(values[: i + 1])
    if n > window:
        strided = np.lib.stride_tricks.sliding_window_view(values, window)
        out[window - 1:] = np.median(strided, axis=1)
    return out


def windows_from_z(
    z: np.ndarray,
    threshold: float,
    merge_gap: int,
    min_len: int,
) -> list[tuple[int, int]]:
    flagged = z > threshold
    if not flagged.any():
        return []
    padded = np.concatenate(([False], flagged, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0] - 1
    segments = list(zip(starts.tolist(), ends.tolist()))

    merged = [segments[0]]
    for start, end in segments[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end - 1 <= merge_gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return [(s, e) for s, e in merged if (e - s + 1) >= min_len]


def prune(
    z: np.ndarray,
    windows: list[tuple[int, int]],
    p: float,
) -> list[tuple[int, int]]:
    """Hundman et al. §3.3 anomaly pruning, applied to residual magnitudes.

    Reduce each candidate window to one number — the largest z inside it — sort those
    descending, and append the largest z that was *not* inside any window. Walk the
    sorted list computing the percent drop to the next value. Every time a drop exceeds
    `p`, everything seen so far is confirmed and the pending removal list resets; what
    remains pending at the end is reclassified as nominal.

    The idea: a channel's real anomalies stand clearly above its own background. A long
    tail of candidates that shades smoothly into the noise floor *is* the noise floor.

    The paper prunes LSTM prediction errors and this engine has none, so the input here
    is |residual| / scale instead. Whether that substitution holds is the open question
    the sweep is answering.
    """
    if not windows or p <= 0:
        return windows

    maxima = [float(z[s : e + 1].max()) for s, e in windows]
    order = sorted(range(len(windows)), key=lambda i: -maxima[i])
    ranked = [maxima[i] for i in order]

    mask = np.zeros(len(z), dtype=bool)
    for s, e in windows:
        mask[s : e + 1] = True
    background = float(z[~mask].max()) if (~mask).any() else 0.0
    ranked.append(background)

    pending: list[int] = []
    for i in range(len(ranked) - 1):
        current = ranked[i]
        if current <= 0:
            pending.append(i + 1)
            continue
        drop = (current - ranked[i + 1]) / current
        if drop > p:
            pending = []
        else:
            pending.append(i + 1)

    drop_ranks = {r for r in pending if r < len(order)}
    return [windows[order[r]] for r in range(len(order)) if r not in drop_ranks]


def detect_with(z: np.ndarray, cfg: dict) -> list[tuple[int, int]]:
    grow = cfg.get("grow_threshold", 0.0)
    if grow:
        windows = hysteresis_windows(
            z,
            seed_threshold=cfg.get("threshold", 4.0),
            grow_threshold=grow,
            merge_gap=cfg.get("merge_gap", 50),
            min_len=cfg.get("min_len", 5),
        )
    else:
        windows = windows_from_z(
            z,
            threshold=cfg.get("threshold", 4.0),
            merge_gap=cfg.get("merge_gap", 50),
            min_len=cfg.get("min_len", 5),
        )
    return prune(z, windows, cfg.get("prune_p", 0.0))


# --------------------------------------------------------------------------
# data, loaded once
# --------------------------------------------------------------------------


class Bench:
    """Channels and labels for one split, held in memory across the whole sweep.

    A scoring pass through `tools/score.py` re-reads 81 parquet files and costs 30-60
    seconds. A sweep of a few hundred configurations cannot pay that each time, so the
    telemetry is read once and the rolling-median transform is cached per window size.
    """

    def __init__(self, split: str) -> None:
        self.split = split
        # Iterate ROWS, not unique channel ids. `labeled_anomalies.csv` can carry more
        # than one row for the same channel, and `tools/score.py` scores each row
        # separately — so keying anything by channel id silently drops a row and makes
        # the sweep disagree with the ruler. It did, by one channel and one window,
        # until this was fixed.
        self.rows = [r for r in score.load_labels() if score.split_of(r["chan_id"]) == split]
        self.values: dict[str, np.ndarray] = {}
        self.truth: list[tuple[str, list[tuple[int, int]]]] = []
        for row in self.rows:
            chan = row["chan_id"]
            if chan not in self.values:
                df = score.load_channel(chan)
                self.values[chan] = df["value"].to_numpy(dtype=float)
            arr = self.values[chan]
            self.truth.append((chan, score._clamp(row["windows"], len(arr))))
        self._z_cache: dict[tuple[str, int], np.ndarray] = {}
        self._pred_cache: dict[tuple, list[tuple[int, int]]] = {}

    def z(self, chan: str, rolling_window: int, ewma_span: int = 0,
          trim_quantile: float = 1.0) -> np.ndarray:
        key = (chan, rolling_window, ewma_span, trim_quantile)
        if key not in self._z_cache:
            self._z_cache[key] = z_scores_v2(
                self.values[chan], rolling_window, ewma_span, trim_quantile)
        return self._z_cache[key]

    def _z_for(self, chan: str, cfg: dict) -> np.ndarray:
        return self.z(chan, cfg.get("rolling_window", 100),
                      cfg.get("ewma_span", 0), cfg.get("trim_quantile", 1.0))

    def evaluate(self, cfg: dict) -> dict:
        """Score a configuration, and measure whether its output is worth having.

        F1 alone is not enough here, and finding that out cost nothing but is the most
        important result of the whole sweep. Window-overlap F1 is maximised by emitting
        ONE enormous window per channel: it overlaps whatever anomaly is present, and it
        can only ever be a single false positive. A search told to maximise F1 walks
        straight to that degenerate corner — the first wide sweep put every one of its
        top eighteen results there, at F1 0.81, emitting 0.9 windows per channel with a
        median length of 1668 samples covering 39% of the data.

        That detector is useless on console. "Something is wrong somewhere in this
        40% of your telemetry" is not an anomaly detection. So coverage and localisation
        are measured alongside the metric, and `--max-coverage` / `--max-median-len`
        exist to keep the search inside the region where a detection means something.
        """
        tp = fp = fn = 0
        cache: dict[str, list[tuple[int, int]]] = {}
        lengths: list[int] = []
        coverage: list[float] = []
        for chan, truth in self.truth:
            if chan not in cache:
                z = self._z_for(chan, cfg)
                cache[chan] = score._clamp(detect_with(z, cfg), len(self.values[chan]))
            a, b, c = score.score_channel(truth, cache[chan])
            tp += a
            fp += b
            fn += c
        for chan, windows in cache.items():
            lengths.extend(e - s + 1 for s, e in windows)
            coverage.append(sum(e - s + 1 for s, e in windows) / len(self.values[chan]))
        precision, recall, f1 = score.prf(tp, fp, fn)
        return {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "n_windows": sum(len(w) for w in cache.values()),
            "median_len": int(np.median(lengths)) if lengths else 0,
            "mean_coverage": float(np.mean(coverage)) if coverage else 0.0,
        }

    def n_windows(self) -> int:
        return sum(len(w) for _, w in self.truth)


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------


def grid(stage: str) -> list[dict]:
    if stage == "baseline":
        # Re-walks the scalar knobs the forge loop already lost on, so "the constants
        # are exhausted" is measured over a grid rather than inferred from two samples.
        # merge_gap runs far past the committed 50: the first pass put every top result
        # at the grid's edge, which means the edge was in the wrong place.
        return [
            {"rolling_window": rw, "threshold": t, "merge_gap": mg, "min_len": ml}
            for rw, t, mg, ml in itertools.product(
                [50, 100, 200, 400],
                [3.0, 4.0, 5.0, 6.0, 8.0, 10.0],
                [50, 100, 200, 400, 800],
                [5, 20, 50],
            )
        ]
    if stage == "prune":
        # merge_gap stays inside the operationally sane range found above. The question
        # this stage answers is whether the paper's pruning buys precision *without*
        # buying it the degenerate way, by inflating windows until one covers everything.
        return [
            {"rolling_window": rw, "threshold": t, "merge_gap": mg, "min_len": ml,
             "prune_p": p}
            for rw, t, mg, ml, p in itertools.product(
                [50, 100, 200],
                [3.0, 4.0, 5.0, 6.0, 8.0],
                [50, 100, 150, 200],
                [5, 20],
                [0.0, 0.05, 0.09, 0.13, 0.18, 0.25, 0.35, 0.50],
            )
        ]
    raise SystemExit("unknown stage: " + stage)


def main() -> int:
    ap = argparse.ArgumentParser(description="Dev-split parameter search.")
    ap.add_argument("--stage", choices=["baseline", "prune"], default="prune")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--verify-holdout", metavar="JSON",
                    help="score ONE named config on holdout and report it. Never used "
                         "to choose a config - see the module docstring.")
    ap.add_argument("--out", default=None, help="write full results as JSON")
    ap.add_argument("--max-coverage", type=float, default=0.20,
                    help="reject configs flagging more than this fraction of a channel")
    ap.add_argument("--max-median-len", type=int, default=300,
                    help="reject configs whose median window is longer than this")
    ap.add_argument("--selftest", action="store_true",
                    help="score the committed engine's exact configuration and check it "
                         "against the number tools/score.py reports for it")
    args = ap.parse_args()

    if args.selftest:
        # The whole sweep is worthless if its reimplementation is not the committed
        # engine. This asserts the two agree before any result is believed.
        print("loading dev...")
        dev = Bench("dev")
        baseline = {"rolling_window": 100, "threshold": 4.0, "merge_gap": 50, "min_len": 5}
        got = dev.evaluate(baseline)
        expected = {"tp": 45, "fp": 268, "fn": 25, "f1": 0.234987}
        print("  channels={0} rows={1} windows={2}".format(
            len(dev.values), len(dev.truth), dev.n_windows()))
        print("  sweep   : tp={tp} fp={fp} fn={fn} F1={f1:.6f}".format(**got))
        print("  score.py: tp={tp} fp={fp} fn={fn} F1={f1:.6f}".format(**expected))
        ok = (got["tp"], got["fp"], got["fn"]) == (expected["tp"], expected["fp"], expected["fn"])
        print("  MATCH" if ok else "  MISMATCH - do not trust any sweep result")
        return 0 if ok else 1

    if args.verify_holdout:
        cfg = json.loads(args.verify_holdout)
        print("loading holdout...")
        bench = Bench("holdout")
        result = bench.evaluate(cfg)
        print(json.dumps({"config": cfg, "holdout": result}, indent=2))
        return 0

    print("loading dev channels...")
    started = time.time()
    bench = Bench("dev")
    print("  {0} channels, {1} rows, {2} labelled windows, {3:.1f}s".format(
        len(bench.values), len(bench.truth), bench.n_windows(), time.time() - started))

    configs = grid(args.stage)
    print("evaluating {0} configurations...".format(len(configs)))
    results = []
    for i, cfg in enumerate(configs, 1):
        results.append({"config": cfg, "dev": bench.evaluate(cfg)})
        if i % 25 == 0:
            print("  {0}/{1}".format(i, len(configs)))

    admissible = [
        r for r in results
        if r["dev"]["mean_coverage"] <= args.max_coverage
        and r["dev"]["median_len"] <= args.max_median_len
    ]
    rejected = len(results) - len(admissible)
    results = admissible
    results.sort(key=lambda r: -r["dev"]["f1"])

    print("\n{0} of {1} configurations rejected as degenerate "
          "(coverage > {2:.0%} or median window > {3} samples)".format(
              rejected, rejected + len(results), args.max_coverage, args.max_median_len))
    print("\ntop {0} by DEV F1, among operationally usable configurations:".format(args.top))
    print("  {0:>4} {1:>5} {2:>4} {3:>4} {4:>6}   {5:>5} {6:>5} {7:>6}   "
          "{8:>10}  {9:>5} {10:>6}".format(
              "win", "thr", "gap", "len", "p", "P", "R", "F1",
              "tp/fp/fn", "medln", "cover"))
    for r in results[: args.top]:
        c, d = r["config"], r["dev"]
        print("  {0:>4} {1:>5} {2:>4} {3:>4} {4:>6}   {5:.3f} {6:.3f} {7:.4f}   "
              "{8:>3}/{9:>3}/{10:>3}  {11:>5} {12:>5.1%}".format(
                  c.get("rolling_window"), c.get("threshold"), c.get("merge_gap"),
                  c.get("min_len"), c.get("prune_p", 0.0),
                  d["precision"], d["recall"], d["f1"], d["tp"], d["fp"], d["fn"],
                  d["median_len"], d["mean_coverage"]))

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print("\nfull results -> " + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
