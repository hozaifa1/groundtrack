"""
runbook.py — anomaly classification and flight-rule guidance

Why a separate runbook module: the detector (detect.py) answers WHEN; the runbook
answers WHAT and HOW URGENT.  Keeping them separate lets mission ops update response
procedures without touching detection logic, and lets the detector be tested in
isolation from the classification rules.
"""

import numpy as np
import pandas as pd

# ── classification thresholds ─────────────────────────────────────────────────

# Fraction of samples inside the window that must be flagged as "shifted" for
# the window to be called a level shift rather than a transient spike.
# A level shift is a persistent displacement; if the value returns toward baseline
# in the back half of the window it is more likely a spike or noise burst.
LEVEL_SHIFT_PERSISTENCE: float = 0.6

# Ratio of in-window variance to baseline variance that separates a noise burst
# from a level shift.  A noise burst has high variance without a large mean offset.
NOISE_BURST_VAR_RATIO: float = 3.0

# Severity boundaries in robust-sigma units (same scale as detect.py z-scores).
# "low"    < LOW_SEV_THRESHOLD  → within watch limits, log only
# "medium" < HIGH_SEV_THRESHOLD → requires annotation, possible commanding hold
# "high"   >= HIGH_SEV_THRESHOLD → immediate operator review
LOW_SEV_THRESHOLD: float = 5.0
HIGH_SEV_THRESHOLD: float = 10.0

# Baseline estimation window used *only* inside this module for computing the
# channel's pre-anomaly statistics.  Intentionally longer than the detector's
# rolling window to represent the "quiet" regime, not just the recent history.
BASELINE_WINDOW: int = 200


def match(df: pd.DataFrame, window: tuple[int, int]) -> dict:
    """
    Classify an anomaly window and return flight-rule guidance.

    Parameters
    ----------
    df     : DataFrame for the full channel, same schema as passed to detect().
    window : (start, end) inclusive index pair as returned by detect().

    Returns
    -------
    dict with keys:
        signature  — machine-readable anomaly class
        title      — human-readable one-liner
        severity   — "low" | "medium" | "high"
        action     — one or two sentences of generic flight-rule guidance

    Why we look only at data *inside* the window:
    The runbook must not access ground-truth labels, and it must not look outside
    the window at future data (that would not be available in real-time ops).
    We are allowed to use pre-window baseline data as a reference.
    """
    start, end = window
    values: pd.Series = df["value"].reset_index(drop=True)

    # ── pre-anomaly baseline ──────────────────────────────────────────────────
    # Take the BASELINE_WINDOW samples immediately before the window.  If the
    # window starts near the beginning of the channel, use whatever is available.
    baseline_start = max(0, start - BASELINE_WINDOW)
    baseline_vals = values.iloc[baseline_start:start]

    if len(baseline_vals) < 2:
        # Channel is too short to compute a meaningful baseline; use the whole
        # channel excluding the window itself.
        baseline_vals = pd.concat([
            values.iloc[:start],
            values.iloc[end + 1:]
        ])

    # Robust baseline statistics.
    if len(baseline_vals) >= 2:
        baseline_median = float(baseline_vals.median())
        baseline_std = float(baseline_vals.std())
        if baseline_std < 1e-10:
            baseline_std = 1e-10   # guard against zero-variance reference
    else:
        # Absolute fall-back when no usable reference exists.
        baseline_median = float(values.median())
        baseline_std = max(float(values.std()), 1e-10)

    # ── window statistics ─────────────────────────────────────────────────────
    window_vals = values.iloc[start:end + 1]
    window_mean = float(window_vals.mean())
    window_std = float(window_vals.std()) if len(window_vals) > 1 else 0.0

    # Mean displacement from baseline, normalised to baseline spread.
    mean_shift_sigma = abs(window_mean - baseline_median) / baseline_std

    # Variance ratio: how much noisier is the window than the baseline?
    var_ratio = (window_std / baseline_std) if baseline_std > 1e-10 else 0.0

    # Persistence: fraction of window samples that remain displaced from baseline.
    # We define "displaced" as more than 1 baseline-sigma away from baseline median.
    displaced = (window_vals - baseline_median).abs() > baseline_std
    persistence = float(displaced.mean())  # 0..1

    # ── classify ──────────────────────────────────────────────────────────────
    signature, title = _classify(mean_shift_sigma, var_ratio, persistence, window_vals, baseline_median)

    # ── severity ──────────────────────────────────────────────────────────────
    severity = _severity(mean_shift_sigma)

    # ── action ────────────────────────────────────────────────────────────────
    action = _action(signature, severity)

    return {
        "signature": signature,
        "title": title,
        "severity": severity,
        "action": action,
    }


# ── classification logic ──────────────────────────────────────────────────────

def _classify(
    mean_shift_sigma: float,
    var_ratio: float,
    persistence: float,
    window_vals: pd.Series,
    baseline_median: float,
) -> tuple[str, str]:
    """
    Map window statistics to an anomaly signature.

    Rules (in priority order):

    1. noise_burst — variance is much higher than baseline but there is no large
       sustained mean offset.  Typical of RF interference, actuator chatter, or
       a noisy sensor mode switch.

    2. level_shift — large mean offset that persists through most of the window.
       Typical of a stuck valve, latch relay stuck, or commanded state change that
       was not expected.

    3. transient_spike — large instantaneous excursion that does not persist.
       Typical of a single-event upset, a brief thruster firing, or an EMC hit.

    4. unclassified — none of the above patterns fit.
    """
    high_variance = var_ratio >= NOISE_BURST_VAR_RATIO
    large_shift = mean_shift_sigma >= 2.0
    persistent = persistence >= LEVEL_SHIFT_PERSISTENCE

    # Check whether the signal returns toward baseline in the second half.
    n = len(window_vals)
    if n >= 4:
        first_half = window_vals.iloc[: n // 2]
        second_half = window_vals.iloc[n // 2 :]
        first_dev = float((first_half - baseline_median).abs().mean())
        second_dev = float((second_half - baseline_median).abs().mean())
        returns_to_baseline = second_dev < 0.5 * first_dev
    else:
        returns_to_baseline = False

    if high_variance and not large_shift:
        return "noise_burst", "Noise burst: elevated variance without mean offset"

    if large_shift and persistent and not returns_to_baseline:
        return "level_shift", "Level shift: sustained displacement from baseline"

    if large_shift and (not persistent or returns_to_baseline):
        return "transient_spike", "Transient spike: brief excursion returning to baseline"

    if high_variance:
        # High variance but also some mean shift — most likely noise with a bias.
        return "noise_burst", "Noise burst: elevated variance with partial mean offset"

    return "unclassified", "Unclassified anomaly: pattern does not match standard signatures"


# ── severity logic ────────────────────────────────────────────────────────────

def _severity(mean_shift_sigma: float) -> str:
    """
    Map normalised displacement to a severity tier.

    Why sigma-based thresholds rather than absolute values:
    Different channels have vastly different engineering ranges.  Expressing
    severity in terms of how many baseline-standard-deviations the window
    departs ensures that a 0.001 V anomaly on a precision gyro and a 100 V
    anomaly on a power bus are each judged relative to their own quiet-time
    variability.
    """
    if mean_shift_sigma >= HIGH_SEV_THRESHOLD:
        return "high"
    if mean_shift_sigma >= LOW_SEV_THRESHOLD:
        return "medium"
    return "low"


# ── action text ───────────────────────────────────────────────────────────────

_ACTION_MATRIX: dict[tuple[str, str], str] = {
    ("level_shift", "low"): (
        "Log anomaly and monitor for 30 minutes. "
        "If displacement persists, compare against last commanded state."
    ),
    ("level_shift", "medium"): (
        "Place commanding on hold and notify the subsystem engineer. "
        "Verify last command sequence against expected telemetry response."
    ),
    ("level_shift", "high"): (
        "Immediately notify Flight Director and subsystem engineer. "
        "Do not issue further commands to this subsystem until root cause is identified."
    ),
    ("transient_spike", "low"): (
        "Log anomaly. "
        "A single brief excursion at low amplitude is likely sensor noise; watch for recurrence."
    ),
    ("transient_spike", "medium"): (
        "Log anomaly and flag for engineering review at next pass. "
        "Check for correlated events on power, thermal, or command channels."
    ),
    ("transient_spike", "high"): (
        "Notify subsystem engineer immediately. "
        "Correlate with command history and check for single-event upset indicators."
    ),
    ("noise_burst", "low"): (
        "Log anomaly. "
        "Elevated noise at low amplitude is often transient EMC interference; continue monitoring."
    ),
    ("noise_burst", "medium"): (
        "Annotate telemetry and monitor for recurrence. "
        "Check for concurrent RF transmissions or actuator activity that may be coupling noise."
    ),
    ("noise_burst", "high"): (
        "Notify subsystem engineer; elevated broadband noise at this amplitude may indicate "
        "sensor degradation or a loose electrical connection."
    ),
    ("unclassified", "low"): (
        "Log anomaly for post-pass review. "
        "Pattern does not match standard signatures; compare against historical trend data."
    ),
    ("unclassified", "medium"): (
        "Flag for engineering review. "
        "Unclassified anomaly at medium severity warrants manual inspection of raw telemetry."
    ),
    ("unclassified", "high"): (
        "Escalate to Flight Director. "
        "High-severity unclassified anomaly requires immediate human review before further operations."
    ),
}


def _action(signature: str, severity: str) -> str:
    """
    Look up the appropriate flight-rule action text.

    A default is provided so unknown future signatures degrade gracefully rather
    than raising a KeyError in an on-console tool.
    """
    return _ACTION_MATRIX.get(
        (signature, severity),
        (
            "Log anomaly and notify the subsystem engineer for review. "
            "Consult the applicable subsystem anomaly response procedure."
        ),
    )
