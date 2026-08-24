You are the sole author of `engine/` in a spacecraft anomaly-detection repository.
Everything you need is inlined below, including the current source of the file you
are editing. Do NOT read files. Do NOT list directories. Do NOT search the repo.
Exploration is billed and produces nothing: a previous run spent its entire budget
on orientation reads and wrote no code at all.

Make ONE minimal, explainable edit. Verify once. Report.

## Where the engine stands

           precision  recall      F1      tp     fp     fn
  dev         0.144      0.643   0.235     45    268     25
  holdout     0.163      0.714   0.266     25    128     10   <- THE GATE

The gate is holdout F1: 0.265957. Your edit is committed only if that number rises.
The held-out channels are hidden from you by design, so a change that works only by
memorising dev will be reverted. Aim for a rule that is true of telemetry in general.

## Where to aim this iteration

Read the "Already tried" list above. Four iterations have been reverted, and the two
that moved a single constant each traded recall for precision at roughly one for one.
That was the right *class* of change made in the wrong *combination*: the constants
interact, and moving one at a time cannot find the pair that works.

A dev-split search over 960 configurations has now been run offline
(`tools/sweep.py`, committed, reproducible, no Bobcoins). It selected a configuration
**on the dev split only** — the held-out channels were never a selection input — and
that configuration is:

    ROLLING_WINDOW      100   (unchanged)
    DETECTION_THRESHOLD 4.0 -> 6.0
    MERGE_GAP            50 -> 150
    MIN_WINDOW_LEN        5   (unchanged)

Measured on dev: precision 0.691, recall 0.543, F1 0.608, against the current 0.235.

**Your task is to make that change to `engine/detect.py`, and to write the reasoning
into the code so a mission-ops engineer reads it and understands why.** This is the one
iteration where the values are given to you rather than proposed by you; the search that
produced them is in `tools/sweep.py` and its findings are in `docs/parameter-search.md`.
Do not go read those files — everything you need is here.

### Why these two constants move together

At 4σ the detector fires on ordinary variation, producing a spray of short windows —
268 false alarms on dev against 45 true positives. Raising the threshold to 6σ alone
removes false alarms *and* true positives together, because a real anomaly is often only
briefly extreme and the rest of it falls back under the bar; that is what a previous
iteration measured when it moved the threshold alone and lost recall one-for-one.

Widening the merge gap to 150 samples is what makes the higher threshold survivable. A
genuine anomaly produces several separated bursts above 6σ, and merging across a longer
quiet interval reconstitutes them into the single event they actually are, instead of
discarding each fragment as too short. The two changes are one change.

### A constraint you must not violate

The search found that this metric can be gamed. Merging across very long gaps collapses
each channel into roughly one enormous window, which overlaps whatever anomaly exists
and can only cost one false positive. That scores dev F1 0.807 while flagging 39% of
every channel with a median window of 1668 samples — an alarm that tells an operator
nothing.

`MERGE_GAP = 150` is deliberately well short of that. **Do not raise it further, and do
not add any change whose effect is to emit fewer, larger windows.** The detector must
still localise: median window length should stay in the low hundreds of samples and
total flagged coverage near 14% of a channel, which is where the baseline already sits.

## What to do

1. Change the two constants in `engine/detect.py`.
2. Rewrite their docstring comments to explain the interaction above — why 6σ needs a
   wider merge gap to be viable, and why the merge gap is capped well below the point
   where the metric becomes gameable. The existing comments justify 4.0 and 50 and will
   be actively wrong once you change the values.
3. Change nothing else. No new mechanism, no pruning, no local scale estimation. Those
   were tried and measured; see the "Already tried" list.

## Already tried

You have no memory of previous iterations, so here they are. A REVERTED line
is a lever already known not to generalise - do not propose it again, and do
not propose a near-identical variant of it. Pick a different mechanism.

  [REVERTED] MIN_WINDOW_LEN raised from 5 to 12 in engine/detect.py
      holdout F1 0.265957 -> 0.25
  [REVERTED] DETECTION_THRESHOLD raised from 4.0 to 4.5 in engine/detect.py
      holdout F1 0.265957 -> 0.254545
  [REVERTED] Replaced single global MAD scale with a rolling MAD over LOCAL_SCALE_WINDOW=300 samples, floored at LOCAL_SCALE_FLOOR_FRACTION=0.1 of the global scale
      holdout F1 0.265957 -> 0.248804

## Dev-split failure report

This is the only failure information you are allowed to see.

FALSE ALARMS - 268 on dev, across 15 channels.
  Worst offenders (top 12 of 15 channels):
    T-2     69 false alarms
    E-13    54 false alarms
    E-2     48 false alarms
    P-2     48 false alarms
    F-7     12 false alarms
    E-4      8 false alarms
    D-15     7 false alarms
    P-15     6 false alarms
    D-6      5 false alarms
    M-4      4 false alarms
    D-5      2 false alarms
    F-8      2 false alarms
  Window lengths: min=5 p10=10 median=26 p90=144 max=945
  35 of 268 false alarms are <= 10 samples long (13%).

MISSED - 25 labelled anomalies on dev that no prediction overlapped.
    E-1    window [5000, 5030] len=31    class=[contextual, contextual] channel_len=8516
    E-1    window [5610, 6086] len=477   class=[contextual, contextual] channel_len=8516
    E-5    window [5600, 5920] len=321   class=[point]     channel_len=8294
    E-9    window [5550, 5900] len=351   class=[point]     channel_len=8302
    E-10   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8505
    E-10   window [5601, 5871] len=271   class=[contextual, contextual] channel_len=8505
    E-11   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8514
    E-11   window [5614, 5857] len=244   class=[contextual, contextual] channel_len=8514
    E-12   window [5610, 6141] len=532   class=[contextual, contextual] channel_len=8512
    E-12   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8512
    A-1    window [4690, 4774] len=85    class=[point]     channel_len=8640
    A-2    window [4450, 4560] len=111   class=[contextual] channel_len=7914
    G-1    window [4770, 4890] len=121   class=[contextual] channel_len=8469
    D-5    window [4800, 4850] len=51    class=[point]     channel_len=7628
    ... and 11 more

## Current `engine/detect.py` - verbatim, do not open the file

```python
"""
detect.py — spacecraft telemetry anomaly detector (baseline)

Why this approach: mission telemetry channels spend most of their time in a slowly
drifting nominal regime.  A rolling median tracks that regime robustly (outliers
cannot drag it far), leaving a residual that is near-zero when the channel is healthy
and large when something unexpected happens.  Scaling by the MAD (median absolute
deviation) makes the threshold channel-agnostic — a sensor with a 0.001 V range and
one with a 1000 V range use the same dimensionless cut-off.
"""

import numpy as np
import pandas as pd

# ── tunable constants ─────────────────────────────────────────────────────────

# Rolling window for the nominal baseline estimate.
# ~100 samples corresponds to roughly one orbit pass worth of data at typical
# SMAP/MSL downlink cadences; short enough to track slow trends, long enough to
# be insensitive to a single spike.
ROLLING_WINDOW: int = 100

# Consistency factor that converts MAD to an equivalent Gaussian σ.
# For a normal distribution  MAD ≈ 0.6745 σ, so 1/0.6745 ≈ 1.4826.
# We use this so the threshold below is expressed in "sigma-equivalent" units.
MAD_CONSISTENCY_FACTOR: float = 1.4826

# Detection threshold in robust-sigma units.
# 4 σ keeps the false-alarm rate low on channels that stay near-Gaussian while
# still catching genuine level shifts and spikes.
DETECTION_THRESHOLD: float = 4.0

# Maximum gap (samples) allowed between two flagged regions before they are
# merged into one window.  50 samples bridges short un-flagged notches that are
# artefacts of the rolling baseline rather than true anomaly boundaries.
MERGE_GAP: int = 50

# Minimum window length (samples) that is reported as a real anomaly.
# Windows shorter than 5 are almost certainly single-sample noise or sensor
# glitches that the scoring rubric does not consider true anomalies.
MIN_WINDOW_LEN: int = 5


# ── main entry point ──────────────────────────────────────────────────────────

def detect(df: pd.DataFrame) -> list[tuple[int, int]]:
    """
    Detect anomaly windows in a single telemetry channel.

    Parameters
    ----------
    df : DataFrame with columns ``timestep`` (int), ``value`` (float), and
         zero or more ``cmd_*`` one-hot command columns.

    Returns
    -------
    List of (start, end) index pairs, inclusive, ascending, non-overlapping.
    An empty list means the channel looks nominal or is constant/zero-variance.

    Why we use integer positions, not timestep values:
    The scorer matches on positional indices that align with the ground-truth
    label ranges stored in ``labeled_anomalies.csv``, so we track row positions
    throughout and only convert back at the very end.
    """
    values: pd.Series = df["value"].reset_index(drop=True)
    n = len(values)

    if n == 0:
        return []

    # ── 1. Rolling median baseline ────────────────────────────────────────────
    # min_periods=1 avoids NaN at the start of the series (important for short
    # channels and for channels whose anomaly starts in the first few rows).
    rolling_median: pd.Series = values.rolling(
        window=ROLLING_WINDOW, min_periods=1, center=False
    ).median()

    # ── 2. Residual from baseline ─────────────────────────────────────────────
    residual: pd.Series = values - rolling_median

    # ── 3. Robust scale via MAD ───────────────────────────────────────────────
    # np.median of the absolute residual is the MAD.  Multiplying by the
    # consistency factor converts it to an equivalent Gaussian standard deviation
    # so our threshold is directly comparable to "N-sigma" limits in flight rules.
    abs_residual = residual.abs()
    mad = float(np.median(abs_residual.values)) * MAD_CONSISTENCY_FACTOR

    if mad < 1e-10:
        # Channel is near-constant; MAD is essentially zero.  Fall back to std
        # so we can still flag the rare case where a constant channel suddenly
        # jumps.  If std is also zero the channel is truly inert — return empty.
        std = float(residual.std())
        if std < 1e-10:
            return []
        scale = std
    else:
        scale = mad

    # ── 4. Flag anomalous samples ─────────────────────────────────────────────
    z_score: np.ndarray = abs_residual.values / scale
    flagged: np.ndarray = z_score > DETECTION_THRESHOLD  # boolean array, length n

    if not flagged.any():
        return []

    # ── 5. Merge nearby flagged runs ──────────────────────────────────────────
    # Convert the boolean mask to (start, end) run-length segments, then merge
    # pairs whose gap is small enough to be an artefact of the sliding window.
    segments = _runs_from_mask(flagged)
    segments = _merge_segments(segments, MERGE_GAP)

    # ── 6. Drop short windows ─────────────────────────────────────────────────
    segments = [(s, e) for s, e in segments if (e - s + 1) >= MIN_WINDOW_LEN]

    return segments


# ── helpers ───────────────────────────────────────────────────────────────────

def _runs_from_mask(mask: np.ndarray) -> list[tuple[int, int]]:
    """
    Convert a boolean array into a list of (start, end) inclusive index ranges
    where the value is True.

    Why not itertools.groupby: a tight numpy diff is faster and avoids object
    iteration on potentially 9000-element arrays.
    """
    if not mask.any():
        return []
    # Pad with False on both ends so diff catches leading and trailing runs.
    padded = np.concatenate(([False], mask, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]   # rising edges
    ends = np.where(diff == -1)[0] - 1  # falling edges (adjust for padding)
    return list(zip(starts.tolist(), ends.tolist()))


def _merge_segments(
    segments: list[tuple[int, int]], max_gap: int
) -> list[tuple[int, int]]:
    """
    Merge consecutive segments whose inter-segment gap is <= max_gap samples.

    Why merge: the rolling baseline deliberately lags behind a sudden shift.
    During the lag interval a few non-flagged samples appear between two flagged
    bursts; merging them prevents one real anomaly from being reported as two
    separate windows with poor overlap against the ground-truth label.
    """
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
```

`engine/runbook.py` also exists. It turns a detected window into an operator runbook
entry and does not affect the score. Leave it alone unless your change genuinely
requires it.

## What to do

1. Name ONE failure mode from the report above. One, not five.
2. Make the smallest edit to `engine/detect.py` that plausibly fixes it. Prefer
   retuning a named constant, or adding one explicit, well-commented rule, over
   rewriting the module. A small change the next iteration can build on is worth
   more here than a large one that scores the same.
3. Explain in a comment or docstring *why* the rule exists. A mission-ops engineer
   has to read this file and see why it fired.

## Hard rules

- Edit ONLY `engine/detect.py` and, if truly necessary, `engine/runbook.py`.
- NEVER edit `tools/score.py`. It is the ruler that grades you. Editing it to raise
  your own score is the one unforgivable failure in this repo; the harness diffs the
  working tree after you finish and discards the entire iteration if you touched it.
- Never read `data/telemanom/labeled_anomalies.csv`. Detection runs on telemetry
  alone. Only the scorer sees ground truth.
- Standard library, `numpy`, `pandas` only. Do not add a dependency.
- No per-channel hardcoding. Never name a channel id in code.
- Deterministic: same input, same output. No unseeded randomness.
- Must not crash on short, constant, or zero-variance channels. A crash scores zero.

## Verify - exactly once

```bash
.venv/Scripts/python.exe tools/score.py
```

It reads 81 telemetry files and takes 30-60 seconds. That is normal, not a hang.
It prints a line beginning `GATE METRIC`. Read the number off that line.

## Report

The last thing you output must be this JSON object, with nothing after it:

```json
{"target_failure":"...","hypothesis":"...","change":"...",
  "files_touched":["engine/detect.py"],
  "f1_before":0.265957,"f1_after":<the GATE METRIC actually printed>,
  "generalises":"dev F1 ... / holdout F1 ..."}
```

Report the number the scorer printed. If it went down, say so - the harness will
revert the edit and record the attempt, and a logged failed experiment is a useful
result. A fabricated one poisons the ledger and the project's central claim with it.
