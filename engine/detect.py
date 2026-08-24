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
