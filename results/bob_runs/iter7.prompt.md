You are the sole author of `engine/` in a spacecraft anomaly-detection repository.
Everything you need is inlined below, including the current source of the file you
are editing. Do NOT read files. Do NOT list directories. Do NOT search the repo.
Exploration is billed and produces nothing: a previous run spent its entire budget
on orientation reads and wrote no code at all.

Make ONE minimal, explainable edit. Verify once. Report.

## Where the engine stands

           precision  recall      F1      tp     fp     fn
  dev         0.691      0.543   0.608     38     17     32
  holdout     0.731      0.543   0.623     19      7     16   <- THE GATE

The gate is holdout F1: 0.622951. Your edit is committed only if that number rises.
The held-out channels are hidden from you by design, so a change that works only by
memorising dev will be reverted. Aim for a rule that is true of telemetry in general.

## Where to aim this iteration

The engine currently asks one question of every candidate window: **did any single
sample cross 6σ?** That is a peak test, and it is why recall has stalled. On the dev
split the detector now finds 38 of 70 labelled windows — precision 0.691, recall 0.543,
F1 0.608. The 32 it misses are not quiet. They are windows that deviate moderately for
a long time and never spike hard enough to trip a peak test.

A dev-split search run offline (no Bobcoins, held-out channels never a selection input)
replaced the peak test with an **area test** and measured, on dev:

    precision 0.909   recall 0.571   F1 0.7018   (tp 40 / fp 4 / fn 30)

The peak branch was then ablated to check which half was doing the work. Removing the
peak test changed the result **not at all** — F1 0.7018 either way. Removing the area
test dropped it to 0.6476. The area test is the entire mechanism. Ship it as that, not
as a two-threshold rule.

## The change

    DETECTION_THRESHOLD   6.0 -> 4.0     (now a CANDIDATE threshold, not a verdict)
    MERGE_GAP             150 -> 200
    MIN_WINDOW_AREA       new, 40.0
    MIN_WINDOW_LEN        5   (unchanged)
    ROLLING_WINDOW        100 (unchanged)

The detection procedure becomes, in this order:

1. `z = |value - rolling_median| / (MAD * 1.4826)` — unchanged.
2. Flag samples where `z > DETECTION_THRESHOLD` (4.0). This is back to the value the
   engine started with, and it is deliberate: 4σ is a good *candidate* generator and
   was only ever a bad *verdict*.
3. Merge flagged runs separated by `<= MERGE_GAP` (200) samples — unchanged in kind.
4. Drop merged windows shorter than `MIN_WINDOW_LEN` (5) — unchanged.
5. **New, and this is the iteration:** for each surviving window compute

       area = sum over samples i in the window of max(z_i - DETECTION_THRESHOLD, 0)

   and keep the window only if `area >= MIN_WINDOW_AREA` (40.0). Note the sum runs over
   the *whole merged window*; samples inside it that sit below the threshold contribute
   zero, which is what the `max(..., 0)` is for.

## Why area is the right question

A peak test asks how *extreme* the worst sample was. An area test asks how much total
excursion the window accumulated — depth integrated over duration. Those come apart
exactly where this engine has been losing:

- A single 7σ spike lasting three samples has a large peak and a small area. It is
  usually a sensor glitch. The area test drops it.
- A 4.5σ deviation sustained for two hundred samples never approaches 6σ, so the peak
  test discards it entirely. Its area is large. It is also what a degrading component,
  a thermal runaway or a slow leak actually looks like in telemetry, and the benchmark
  labels this class of event as `contextual` rather than `point`.

That second case is where the 32 dev misses live, and recovering some of them is the
whole point: at 4 false positives the detector has precision to spare and has been
spending recall to buy more of it.

## A constraint you must not violate

This metric can be gamed. Window-overlap F1 is maximised by emitting one enormous
window per channel: it overlaps whatever anomaly is present and can only ever cost a
single false positive. A configuration doing that scored dev F1 0.807 while flagging
39% of every channel with a median window of 1668 samples — an alarm that tells an
operator nothing. It was rejected, and `tools/score.py` is fixed and is not to be
touched.

The configuration above was measured at **median window 139 samples and 18.8% of a
channel flagged**, against the current engine's 134 samples and 16.5%. It emits *fewer*
windows than the engine it replaces (43 against 53), not larger ones.

**Do not raise MERGE_GAP beyond 200, and do not lower MIN_WINDOW_AREA below 40.** Both
of those loosen the rule in the direction of the degenerate regime. If you find
yourself making detections bigger, you are optimising the hole in the metric rather
than the detector.

## What to do

1. Make exactly the change above in `engine/detect.py`.
2. Rewrite the constant docstrings. The existing comment on `DETECTION_THRESHOLD`
   argues at length for 6.0 and for why it must move together with `MERGE_GAP`; that
   reasoning describes a peak test and will be actively wrong once the verdict is an
   area test. Explain the new rule the way the old one was explained — depth times
   duration, why a glitch fails it and a drift passes it, and why the threshold going
   back down to 4.0 is not a reversion to the old behaviour.
3. Change nothing else. No pruning, no EWMA smoothing, no local or trimmed scale
   estimate, no multi-scale baseline. All four were implemented and measured offline;
   pruning and the two scale variants hurt, and multi-scale bought one extra dev true
   positive for a second mechanism this iteration does not need.

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
  [KEPT] DETECTION_THRESHOLD 4.0â†’6.0, MERGE_GAP 50â†’150, with comments explaining the interaction and the cap against gameable large-gap regimes
      holdout F1 0.265957 -> 0.622951

## Dev-split failure report

This is the only failure information you are allowed to see.

FALSE ALARMS - 17 on dev, across 7 channels.
  Worst offenders (top 7 of 7 channels):
    G-7      9 false alarms
    P-2      2 false alarms
    P-15     2 false alarms
    E-2      1 false alarms
    D-5      1 false alarms
    D-6      1 false alarms
    M-4      1 false alarms
  Window lengths: min=9 p10=33 median=135 p90=201 max=202
  1 of 17 false alarms are <= 10 samples long (6%).

MISSED - 32 labelled anomalies on dev that no prediction overlapped.
    E-1    window [5000, 5030] len=31    class=[contextual, contextual] channel_len=8516
    E-1    window [5610, 6086] len=477   class=[contextual, contextual] channel_len=8516
    E-4    window [5450, 8261] len=2812  class=[point]     channel_len=8354
    E-5    window [5600, 5920] len=321   class=[point]     channel_len=8294
    E-8    window [5400, 6022] len=623   class=[point]     channel_len=8532
    E-9    window [5550, 5900] len=351   class=[point]     channel_len=8302
    E-10   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8505
    E-10   window [5601, 5871] len=271   class=[contextual, contextual] channel_len=8505
    E-11   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8514
    E-11   window [5614, 5857] len=244   class=[contextual, contextual] channel_len=8514
    E-12   window [5610, 6141] len=532   class=[contextual, contextual] channel_len=8512
    E-12   window [5000, 5050] len=51    class=[contextual, contextual] channel_len=8512
    A-1    window [4690, 4774] len=85    class=[point]     channel_len=8640
    A-2    window [4450, 4560] len=111   class=[contextual] channel_len=7914
    ... and 18 more

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
# At 4 σ the detector fires on ordinary variation, generating hundreds of false
# alarms (268 on dev) against a small number of true positives (45).  Raising
# the threshold to 6 σ eliminates most of those false alarms, but a real anomaly
# is often only briefly extreme: several short bursts cross 6 σ with quieter
# intervals between them.  Moving the threshold alone therefore loses recall
# nearly one-for-one with precision — the fragments are each too short to survive
# MIN_WINDOW_LEN and they are not yet merged because they are separated by more
# than the old MERGE_GAP.  DETECTION_THRESHOLD and MERGE_GAP must be changed
# together; see the companion note on MERGE_GAP below.
# Values selected by an offline grid search over 960 configurations on the dev
# split (tools/sweep.py); held-out channels were not a selection input.
DETECTION_THRESHOLD: float = 6.0

# Maximum gap (samples) allowed between two flagged regions before they are
# merged into one window.
#
# Why 150, not 50: at 6 σ a genuine anomaly produces several separated bursts
# above the threshold with quiet intervals that can span ~100 samples.  A merge
# gap of 50 discards each fragment as an isolated short window; 150 reconstitutes
# the separated bursts into the single event they physically are.  The two
# constants are one change: 6 σ + 150-sample merge is the pair the offline search
# validated; neither value is effective alone.
#
# Why not higher: merging across very long gaps collapses every channel into one
# enormous window that trivially overlaps any labelled anomaly while flagging
# ~40 % of the channel — an alarm that tells an operator nothing.  150 is
# deliberately well below that regime; median flagged window length stays in the
# low hundreds of samples and total flagged coverage stays near 14 % of a channel.
MERGE_GAP: int = 150

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
  "f1_before":0.622951,"f1_after":<the GATE METRIC actually printed>,
  "generalises":"dev F1 ... / holdout F1 ..."}
```

Report the number the scorer printed. If it went down, say so - the harness will
revert the edit and record the attempt, and a logged failed experiment is a useful
result. A fabricated one poisons the ledger and the project's central claim with it.
