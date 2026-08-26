# What a dev-split gain is actually worth

Day 4 bought one forge iteration with the best configuration a 1440-point offline search
could find. It raised dev F1 from 0.608 to 0.702 — the largest dev gain of the project —
and the held-out gate reverted it. Chasing that result produced a more useful finding
than the configuration would have been.

**In the region this project has been searching, dev F1 and held-out F1 are
uncorrelated. Pearson +0.007. Spearman −0.001, across 432 admissible configurations.**

## The iteration that produced the question

The literature review concluded that the remaining headroom was recall — 0.543 on
holdout, 16 of 35 windows missed, against a precision of 0.731 with room to spare — and
that on this benchmark the scoring stage matters more than the model. So the search left
the residual alone and replaced the question the detector asks of a candidate window.

The engine asked a **peak** question: did any single sample cross 6σ. The replacement was
an **area** question — depth integrated over duration:

    area = Σ max(z_i − 4.0, 0)  over the merged window,  keep if area ≥ 40

The two come apart exactly where the engine was losing. A 7σ spike lasting three samples
has a large peak and a small area; it is usually a sensor glitch. A 4.5σ deviation
sustained for two hundred samples never approaches 6σ and a peak test discards it
entirely, but its area is large — and that is what a degrading component or a slow leak
looks like in telemetry. The benchmark labels that class `contextual` rather than `point`.

The peak branch was ablated rather than assumed. Removing the peak test changed the dev
result by nothing at all, 0.7018 either way; removing the area test dropped it to 0.6476.
So the rule shipped to Bob as what it measurably was — an area rule — rather than as a
two-threshold rule whose second threshold does no work.

Selection was on dev only, and two guards were applied before holdout was read: the
sweep's self-test reproduced `tools/score.py` exactly with both levers off, and each
configuration was scored by the mean dev F1 of its grid neighbours so a lone spike could
not be selected. The chosen configuration sat on a plateau — neighbour mean 0.7044, worst
neighbour 0.6897.

**Iteration 7: dev 0.608 → 0.702, holdout 0.623 → 0.615. Reverted. 1.1555 Bobcoins.**

Bob implemented the specification faithfully; the ledger's dev figure, 0.701754, is the
sweep's number to six decimal places.

## A one-window error bar, found by disagreeing with the engine

The sweep predicted holdout 0.6364 for that configuration. The engine measured 0.6154.
Dev had agreed exactly, so this was worth running down.

The sweep computes its rolling median with a numpy sliding window, for speed — it
evaluates the same channel hundreds of times and pandas is too slow in that inner loop.
The engine uses `pandas.rolling(100, min_periods=1).median()`. Reimplementing the area
rule with pandas and scoring it through the ruler's own data path reproduces the engine
exactly: dev 40/4/30, holdout 20/10/15.

So the two rolling medians differ by enough to flip **one** held-out window — 21 true
positives against 20. On dev, with 70 labelled windows, they had agreed exactly; the
baseline self-test agrees exactly too, across 335 emitted windows. It is a rare edge, and
it happened to be the entire apparent gain.

The consequence is not that the sweep is wrong. It is that **sweep holdout figures carry
a ±1-window error bar**, which on 35 windows is roughly ±0.02 F1. That retroactively
settles an open question from Day 3: the hysteresis mechanism's +0.0086 was already
dismissed as smaller than one window, and it is now clear that it was also smaller than
the measurement's own resolution.

## The measurement that ended the search

Seven of the eight top dev configurations, walked in dev order and scored with the
engine's own arithmetic, came in **below** the committed engine on holdout. That is
either bad luck or the dev signal in this region carries no information, so it was
measured over the whole admissible set:

| | |
|---|---|
| admissible configurations | 432 |
| dev F1 range | 0.5736 – 0.7130 |
| held-out F1 range | 0.4762 – 0.6885 |
| **Pearson r(dev, holdout)** | **+0.007** |
| **Spearman r(dev, holdout)** | **−0.001** |
| beat the committed engine on dev | 382 of 432 |
| beat it on holdout | 58 of 432 |
| beat it on both | 56 of 432 |
| **P(wins on holdout \| wins on dev)** | **14.7%** |
| dev argmax | dev 0.7130 → **holdout 0.5970** |

Read the last row first. The configuration a dev search is *designed* to return is worse
on held-out channels than the engine already committed. And a dev win predicts a held-out
win 14.7% of the time — against a 13.4% base rate for picking a configuration at random.
The dev split, in this region, is not a weak signal. It is not a signal.

Both columns here use the sweep's numpy arithmetic, which is one window optimistic on
holdout. That is irrelevant to a rank correlation over 432 points, and is stated so the
figures are not read as more precise than they are.

## What follows from it

**Stop spending Bobcoins on the metric.** This was written into the plan in advance as a
stopping rule — if a wide dev sweep finds nothing above ~0.63 that generalises, stop —
and it has now fired with better evidence than the rule asked for. Buying another
iteration in this region purchases a 14.7% chance of an improvement, and the search's own
best answer is a regression.

This is not a claim that the detector cannot be improved. It is a claim about what
*this* search can tell us, and there are two honest reasons for it:

* **35 held-out windows is a small ruler.** One window is 0.02 F1. Differences of the
  size the sweep was chasing are not resolvable against it, in either direction — which
  also means the one configuration above that beat the committed engine by +0.022 is not
  evidence of anything, and it was not shipped.
* **The benchmark is contested.** Wu and Keogh's examination of the popular anomaly
  benchmarks, NASA's included, found triviality, unrealistic anomaly density, mislabeled
  ground truth and run-to-failure bias, and concluded that much of the field's apparent
  progress "may be illusionary" [5 in [`literature-review.md`](literature-review.md)].
  A dev/holdout correlation of zero over 432 configurations is what that looks like from
  the inside.

The engine stays where the gate left it: **holdout F1 0.622951**, iteration 6, authored
by IBM Bob.

## Reproducing this

The search harness is local development scaffolding and is not in the repository — see
[`parameter-search.md`](parameter-search.md) for why. What ships is checkable:

```bash
.venv/Scripts/python.exe tools/score.py          # reproduces holdout F1 0.622951
.venv/Scripts/python.exe tools/plot_progress.py  # redraws results/progress.png from the ledger
cat results/ledger.jsonl                         # iteration 7, reverted, with its cost and task id
```
