# How our score compares to the Telemanom paper

Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic
Thresholding*, KDD 2018 ([arXiv:1802.04431](https://arxiv.org/abs/1802.04431)) — the
paper that produced the benchmark this project is scored on.

Anyone comparing our number to theirs deserves the comparison done honestly, including
the parts that flatter us and the parts that do not.

## Their headline result (Table 2)

| Approach | Precision | Recall | F₀.₅ |
|---|---|---|---|
| Non-parametric **with** pruning (p = 0.13) | 87.5% | 80.0% | **0.71** |
| Non-parametric **without** pruning (p = 0) | 48.9% | 84.8% | 0.47 |
| Gaussian tail (ε_norm = 0.0001) | 87.5% | 66.7% | 0.66 |

## Ours, at iteration 0

| Split | Precision | Recall | F₁ |
|---|---|---|---|
| dev | 0.144 | 0.643 | 0.235 |
| holdout | 0.163 | 0.714 | 0.266 |

## What is genuinely comparable

**The true/false positive definition is identical.** The paper's §4.1 counts a true
positive when any portion of a predicted sequence falls inside a labelled one, records
only one true positive per labelled sequence however many predictions overlap it, and
counts every non-overlapping prediction as a false positive. That is exactly what
[`tools/score.py`](../tools/score.py) does. The ruler was written before the paper's
evaluation section was consulted, and it happens to match.

**Our recall is already in the same range as theirs.** 0.714 against their 0.80, from a
rolling median and a MAD, with no model and no training. That is the surprising half of
the comparison and it is worth saying out loud.

## What is not comparable, and why our number looks worse than it is

**They report F₀.₅, we report F₁.** F₀.₅ weights precision above recall. The paper says
plainly that precision "is weighted more heavily when tuning parameters." Their 0.71 and
our 0.266 are not the same statistic.

**They evaluate a window around each anomaly; we evaluate the whole series.** §4.1: for
each stream they evaluate telemetry "from t_s = t_a − 3d to t_f = t_a + 2d where d is
days" around the anomaly. Every timestep outside that window — where a detector can only
produce false positives, never true ones — is excluded from their count and included in
ours. The paper acknowledges the consequence directly: *"The experiment also does not
include processing for all streams not exhibiting anomalous behavior for a given time
window, which would further increase the number of false positives."*

We do not adjust the ruler to match. `tools/score.py` was fixed before the engine
existed and is not edited to make a number look better — that is the whole integrity
premise here. The honest statement is that our evaluation is **harsher on precision than
the paper's**, and that the gap is therefore smaller than the raw figures suggest, not
that we have matched them.

**They train an LSTM per channel.** Two hidden layers, 80 units, 35 epochs, on a
separate training split, achieving 5.9% average prediction error. Our engine has no
training phase at all and sees only the test series.

## The actionable finding

Precision is the entire gap. Recall is not.

And the paper says what closes it, in a component that has nothing to do with the LSTM:
**pruning**. Table 2's two non-parametric rows are the same detector with and without it.
Turning pruning on moved precision from 48.9% to 87.5% — 38.6 points — while costing
4.8 points of recall.

The mechanism (§3.3) is a per-sequence evidence test rather than a per-sample threshold.
Take the maximum error of every candidate anomalous sequence, sort them descending,
append the largest error that was *not* flagged, then walk the sorted list computing the
percent drop from each value to the next. Sequences above the first drop that exceeds a
minimum percentage *p* stay anomalies; everything from that point on is reclassified as
nominal. The paper used p = 0.13 and reports 0.05 < p < 0.20 as the workable range.

This is public prior art, and it is the direction the forge loop's steer now points Bob
at. Bob has to do the actual work of adapting it: our engine has no prediction errors to
prune, only residual magnitudes, and whether that substitution survives the held-out gate
is not something the paper can answer.

## Sources

- Hundman, Constantinou, Laporte, Colwell, Soderstrom. *Detecting Spacecraft Anomalies
  Using LSTMs and Nonparametric Dynamic Thresholding.* KDD 2018.
  <https://arxiv.org/abs/1802.04431>
- Benchmark data and reference implementation: <https://github.com/khundman/telemanom>
