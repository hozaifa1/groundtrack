"""Tests for the ruler.

The scorer decides which of Bob's edits are kept and which are reverted. If the
metric is wrong, every downstream decision in the ledger is wrong too, silently.
So the metric gets tested directly, against hand-checked cases.

    python tools/test_score.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from score import _clamp, _overlaps, prf, score_channel, split_of  # noqa: E402

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        FAILURES.append(f"{name}: got {got!r}, want {want!r}")


def approx(name: str, got: float, want: float, tol: float = 1e-6) -> None:
    if abs(got - want) > tol:
        FAILURES.append(f"{name}: got {got!r}, want ~{want!r}")


# -- overlap ---------------------------------------------------------------
check("touching at a point overlaps", _overlaps((10, 20), (20, 30)), True)
check("adjacent does not overlap", _overlaps((10, 19), (20, 30)), False)
check("contained overlaps", _overlaps((10, 50), (20, 30)), True)
check("disjoint does not overlap", _overlaps((0, 5), (100, 200)), False)

# -- clamping --------------------------------------------------------------
# Upstream num_values disagrees with test length on some channels, so windows
# past the end must be clipped rather than trusted.
check("clips window past end", _clamp([(10, 999)], 100), [(10, 99)])
check("drops fully out-of-range window", _clamp([(500, 600)], 100), [])
check("clamps negative start", _clamp([(-5, 10)], 100), [(0, 10)])
check("keeps in-range window", _clamp([(10, 20)], 100), [(10, 20)])

# -- window counting -------------------------------------------------------
# One prediction spanning two labelled windows catches BOTH: an operator alerted
# once to a compound event has not missed the second half of it.
check("one pred spanning two truths", score_channel([(10, 20), (30, 40)], [(5, 45)]), (2, 0, 0))
check("perfect single match", score_channel([(10, 20)], [(10, 20)]), (1, 0, 0))
check("total miss", score_channel([(10, 20)], []), (0, 0, 1))
check("pure false alarm", score_channel([], [(10, 20)]), (0, 1, 0))
check("partial overlap counts", score_channel([(10, 20)], [(18, 25)]), (1, 0, 0))
check("two preds one truth = 1tp 1fp", score_channel([(10, 20)], [(10, 12), (90, 95)]), (1, 1, 0))
check("nothing at all", score_channel([], []), (0, 0, 0))

# -- precision / recall / f1 ----------------------------------------------
approx("f1 of perfect", prf(10, 0, 0)[2], 1.0)
approx("f1 of nothing detected", prf(0, 0, 10)[2], 0.0)
approx("f1 balanced", prf(5, 5, 5)[2], 0.5)
check("empty is zero not nan", prf(0, 0, 0), (0.0, 0.0, 0.0))

# -- split determinism -----------------------------------------------------
check("split is stable", split_of("P-1"), split_of("P-1"))
check("split is a valid label", split_of("A-1") in {"dev", "holdout"}, True)

# A detector that flags the entire series must NOT score well. It catches every
# window (perfect recall) but this is the degenerate cheat the metric has to punish
# on precision across a corpus.
tp, fp, fn = score_channel([(10, 20)], [(0, 8639)])
check("flag-everything gets tp but is caught by fp elsewhere", (tp, fn), (1, 0))
_, _, f1_cheat = prf(tp=1, fp=81, fn=0)  # 1 real window, 81 other channels false-alarmed
if f1_cheat > 0.10:
    FAILURES.append(f"flag-everything scores too well: f1={f1_cheat}")

if FAILURES:
    print(f"FAILED ({len(FAILURES)}):")
    for f in FAILURES:
        print("  -", f)
    raise SystemExit(1)

print("ruler OK - all metric tests passed")
