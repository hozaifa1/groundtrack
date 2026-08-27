# The dev-split parameter search

Four forge iterations were reverted and the engine sat at its iteration-0 baseline of
holdout F1 0.266. Bob gets one configuration per ~1.1 Bobcoins and cannot try a
thousand. An offline search on this machine can, for free, and this is what it found.

The search harness itself is local development scaffolding and is not part of this
repository. What it produced — the configuration, the method, and the results below,
including the negative ones — is.

**Result: holdout F1 0.266 → 0.623**, from changing two constants.

## Method

- The search harness is [`tools/sweep.py`](../tools/sweep.py) — the path Bob's own
  provenance comment in `engine/detect.py` names. It was written for that path and run
  from it; an over-broad `local/` gitignore rule kept it out of the first push, so the
  comment pointed at a file a reader could not open. Committed here unmodified.
  `.venv/Scripts/python.exe tools/sweep.py --selftest` prints `MATCH`.
- The sweep reimplements the committed detector and **self-tests against the ruler**
  before any result is believed: the search's self-test runs the committed
  configuration and checks it reproduces `tools/score.py` exactly (tp=45, fp=268, fn=25,
  F1 0.234987). It does.
- **Configurations are chosen on `dev` and only on `dev`.** Holdout is scored once per
  finalist, for reporting. It is never a selection input. Tuning against 35 held-out
  windows would overfit them and produce a number that collapses the moment anyone
  re-runs it.
- The search space is the existing named constants plus the pruning step from Hundman
  et al. §3.3.

## The most important finding is a trap, not a number

The first wide sweep put **every one of its top eighteen results at the grid's edge**,
`merge_gap = 800`, reporting dev F1 up to 0.807 — more than triple the baseline.

It was worthless. Window-overlap F1 is maximised by emitting **one enormous window per
channel**: it overlaps whatever anomaly is present, and it can only ever count as a
single false positive. Measured at that setting:

| | windows/channel | median window | channel covered |
|---|---|---|---|
| committed baseline | 6.1 | 26 samples | 14.3% |
| sweep "winner" (gap 800) | **0.9** | **1668 samples** | **39.2%** |

A detector that says *"something is wrong somewhere in this 1668-sample stretch, which
is 40% of your telemetry"* is not an anomaly detector. It scores well and is useless on
console.

So the search carries an operational constraint alongside the metric — `--max-coverage`
(default 20% of a channel) and `--max-median-len` (default 300 samples). **301 of 960
configurations in the pruning sweep were rejected as degenerate.** The numbers below are
all from the admissible region.

This is worth stating plainly because the scorer is fixed and cannot be changed to close
the loophole, and because the honest response to finding a hole in your own metric is to
say so rather than to walk through it.

## What was selected

Chosen as the best `dev` F1 among configurations that change only the existing
constants:

```
ROLLING_WINDOW      100   (unchanged)
DETECTION_THRESHOLD 4.0 -> 6.0
MERGE_GAP            50 -> 150
MIN_WINDOW_LEN        5   (unchanged)
```

| | dev F1 | **holdout F1** | precision | recall | median window | coverage |
|---|---|---|---|---|---|---|
| iteration-0 baseline | 0.235 | **0.266** | 0.163 | 0.714 | 26 | 14.3% |
| selected | 0.608 | **0.623** | 0.731 | 0.543 | 138 | 14.3% |

Dev 0.608 → holdout 0.623. A generalisation gap of roughly zero, on a configuration
picked without ever looking at holdout. Coverage is unchanged from the baseline: the
detector is not flagging more of the channel, it is flagging **fewer, better-consolidated
windows** — 7 false positives on holdout against the baseline's 128.

Precision 0.731 against the paper's 0.875, on an evaluation that scores the whole series
rather than a window around each anomaly. See
[`telemanom-paper-comparison.md`](telemanom-paper-comparison.md).

## What did not work: the paper's pruning

Hundman et al. report pruning moving precision from 48.9% to 87.5% for 4.8 points of
recall — the largest single effect in their results table. **It did not transfer here.**

The best pruning configuration on dev (`p = 0.5`, threshold 4.0, merge gap 100) scored
dev F1 0.672 — better than the selected config on dev — and **holdout F1 0.571**, worse.
A tighter, higher-precision pruning variant scored dev 0.624 and holdout 0.407, a
collapse.

The likely reason is stated in the paper without being about our case: pruning ranks
*LSTM prediction errors*, which encode how surprising a value is given learned context.
This engine has no model and ranks `|residual| / MAD` instead, which encodes only how
far a value sits from a rolling median. The ranking that separates real anomalies from
the noise floor in the first quantity does not appear to separate them in the second.
The best-performing values of `p` were also 0.35–0.50, far outside the paper's stated
0.05–0.20 range — a sign the mechanism was being pushed to do something other than what
it was designed for.

A negative result on the paper's own headline component, measured rather than assumed.

## Verifying this

The search ran off-repo, but its *conclusion* is fully checkable from what ships here,
which is the part that matters:

```bash
.venv/Scripts/python.exe tools/score.py     # reproduces holdout F1 0.622951
cat results/ledger.jsonl                    # iteration 6, kept, with its cost and task id
git show 9cc792e                            # the change itself, authored by IBM Bob
```

The constants live in [`engine/detect.py`](../engine/detect.py) with Bob's own comment
recording where they came from.

## What was tried afterwards and did not work

Three mechanisms from the post-2018 literature — EWMA residual smoothing, a trimmed
scale estimate, and hysteresis thresholding — were implemented and searched the same
way. The best of them gained **+0.0086 holdout F1**, less than a single one of the 35
held-out windows. See [`literature-review.md`](literature-review.md).

## Day 4: the same method, pushed until it broke

The search above chose two constants and they held up: dev 0.608, holdout 0.623, a
generalisation gap of roughly zero. Day 4 ran the same method against the *scoring*
stage — replacing the detector's peak test with an area test — found dev 0.702 — the
largest dev gain of any reverted iteration — and the gate reverted it at holdout 0.615.

Chasing that produced the more useful result. Across the 432 admissible configurations
of that sweep, **dev F1 and held-out F1 are uncorrelated: Pearson +0.007, Spearman
−0.001.** 382 of them beat the committed engine on dev; 58 beat it on holdout. A dev win
raises the chance of a held-out win from 13.4% to 14.7%.

The same work also put an error bar on every holdout figure this search harness has ever
reported: the sweep's numpy rolling median and the engine's pandas rolling median differ
by enough to flip one held-out window, which is ±0.02 F1 on a 35-window split.

Both findings, and what they mean for the plan, are in
[`generalisation.md`](generalisation.md). The short version is that score work stopped
here, deliberately and in advance of the budget running out.
