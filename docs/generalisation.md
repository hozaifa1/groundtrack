# What a dev-split gain tells us

Day 4 bought one forge iteration with the best configuration a 1440-point offline search
could find. It raised dev F1 from 0.608 to 0.702, the largest dev gain of any reverted
iteration, but the held-out gate reverted it. (Iteration 6 moved dev further still,
0.235 → 0.608, and was kept.) Investigating that failure uncovered something more useful
than the configuration itself.

**In the region this project has been searching, dev F1 and held-out F1 are
uncorrelated. Pearson +0.007. Spearman -0.001, across 432 admissible configurations.**

## The iteration that produced the question

The literature review concluded that the remaining headroom was recall (0.543 on
holdout, 16 of 35 windows missed, against a precision of 0.731 with room to spare) and
that on this benchmark the scoring stage matters more than the model. The search therefore
left the residual alone and changed how the detector scores a candidate window.

The engine originally asked a peak question: did any single sample cross 6σ. The replacement
tested area, integrating depth over duration:

    area = Σ max(z_i - 4.0, 0)  over the merged window,  keep if area ≥ 40

The two approaches diverge where the engine was losing. A 7σ spike lasting three samples
has a large peak and a small area, which is usually a sensor glitch. A 4.5σ deviation
sustained for two hundred samples never approaches 6σ, so a peak test discards it
entirely. Its area is large, matching how degrading components or slow leaks appear in
telemetry (labelled contextual in the benchmark).

Ablation testing confirmed the peak branch was unnecessary. Removing the peak test left
the dev score unchanged at 0.7018, whereas removing the area test dropped it to 0.6476.
Bob received a pure area rule, eliminating the inactive second threshold.

Selection used dev only, protected by two guards before checking holdout: the sweep
self-test reproduced `tools/score.py` with both levers off, and each configuration was
scored by the mean dev F1 of its grid neighbours to avoid isolated spikes. The chosen
configuration sat on a plateau with a neighbour mean of 0.7044 and a worst neighbour
of 0.6897.

**Iteration 7: dev 0.608 → 0.702, holdout 0.623 → 0.615. Reverted. 1.1555 Bobcoins.**

Bob implemented the specification faithfully; the ledger's dev figure, 0.701754, is the
sweep's number to six decimal places.

## A one-window error bar, found by disagreeing with the engine

The sweep predicted holdout 0.6364 for that configuration, while the engine measured 0.6154.
Because dev had agreed exactly, tracking down the discrepancy became necessary.

The sweep computes its rolling median with a numpy sliding window for speed, evaluating
the same channel hundreds of times where pandas is too slow in the inner loop. The engine
uses `pandas.rolling(100, min_periods=1).median()`. Reimplementing the area rule with
pandas and scoring it through the ruler's data path reproduces the engine exactly:
dev 40/4/30, holdout 20/10/15.

The two rolling medians differ by enough to flip one held-out window (21 true positives
versus 20). On dev, with 70 labelled windows, they agreed exactly; the baseline self-test
also agrees across 335 emitted windows. This rare edge case accounted for the entire
apparent gain.

In practice, sweep holdout figures carry a ±1-window error bar, which on 35 windows is
roughly ±0.02 F1. That settles an open question from Day 3: the hysteresis mechanism's
+0.0086 gain was already dismissed as smaller than one window, and it fell well below
the measurement resolution.

## The measurement that ended the search

Seven of the eight top dev configurations, evaluated in dev order with the engine's own arithmetic, came in below the committed engine on holdout. Either that outcome was bad luck or the dev signal in this region carries no information, so the correlation was evaluated across the whole admissible set:

| | |
|---|---|
| admissible configurations | 432 |
| dev F1 range | 0.5736 to 0.7130 |
| held-out F1 range | 0.4762 to 0.6885 |
| **Pearson r(dev, holdout)** | **+0.007** |
| **Spearman r(dev, holdout)** | **-0.001** |
| beat the committed engine on dev | 382 of 432 |
| beat it on holdout | 58 of 432 |
| beat it on both | 56 of 432 |
| **P(wins on holdout \| wins on dev)** | **14.7%** |
| dev argmax | dev 0.7130 → **holdout 0.5970** |

The configuration a dev search is designed to return performs worse on held-out channels than the committed baseline. A dev win predicts a held-out win 14.7% of the time, barely above the 13.4% base rate for picking a configuration at random. In this parameter region, the dev split carries no predictive signal.

Both columns use the sweep's numpy arithmetic, which runs one window optimistic on holdout. That offset does not affect a rank correlation across 432 points; it is noted here to clarify the precision of the numbers.

## What follows from it

**Stop spending Bobcoins on the metric.** The plan defined a stopping rule in advance: if a wide dev sweep finds nothing above ~0.63 that generalises, stop. That rule has now triggered, leaving 28 of 40 Bobcoins unspent. Buying another iteration in this region offers only a 14.7% chance of improvement, while the search's own top candidate is a regression.

This is not a claim that the detector cannot be improved, but a conclusion about what this search can resolve. Two reasons explain why:

* **35 held-out windows is a small ruler.** One window represents roughly 0.02 F1. Differences of the size the sweep chased cannot be resolved against it in either direction. The single configuration that beat the committed engine by +0.022 was therefore treated as noise and left uncommitted.
* **The benchmark is contested.** Wu and Keogh's evaluation of common anomaly benchmarks, including NASA's telemetry, identified trivial cases, unrealistic anomaly densities, mislabeled ground truth, and run-to-failure bias. They concluded that much of the field's apparent progress "may be illusionary" [5 in [`literature-review.md`](literature-review.md)]. A dev/holdout correlation of zero across 432 configurations reflects those structural flaws.

The engine stays where the gate left it: **holdout F1 0.622951**, iteration 6, authored by IBM Bob.

## Reproducing this

The shipped results are directly verifiable:

```bash
.venv/Scripts/python.exe tools/score.py          # reproduces holdout F1 0.622951
.venv/Scripts/python.exe tools/plot_progress.py  # redraws results/progress.png from the ledger
cat results/ledger.jsonl                         # iteration 7, reverted, with its cost and task id
```

So is the search harness, which is committed as [`tools/sweep.py`](../tools/sweep.py):

```bash
.venv/Scripts/python.exe tools/sweep.py --selftest                  # prints MATCH against the ruler
.venv/Scripts/python.exe tools/sweep.py --stage prune --out out.json # re-runs the dev sweep
.venv/Scripts/python.exe tools/sweep.py --verify-holdout '{...}'     # scores one configuration on holdout
```

What that covers, and what it does not. The sweep regenerates the dev column and
will score any single configuration on holdout, so every number in the table above can be
re-derived from it. The loop that walked all 432 configurations through `--verify-holdout`
and computed the two correlation coefficients was a throwaway local script and is not
committed; re-deriving the correlation means writing that loop again around the commands
above.
