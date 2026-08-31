# The dev-split parameter search

Four forge iterations were reverted, leaving the engine at its iteration-0 baseline of holdout F1 0.266. Bob evaluates one configuration per ~1.1 Bobcoins and cannot test thousands. An offline search on this machine can run exhaustive sweeps for free; here is what it found.

The search harness was written as local development scaffolding instead of a shipped artifact. It is committed here as [`tools/sweep.py`](../tools/sweep.py) so the method can be inspected and re-run. Its resulting configuration, method, and benchmark findings (including negative outcomes) are recorded below.

Result: holdout F1 0.266 to 0.623, from changing two constants.

## Method

- The search harness is [`tools/sweep.py`](../tools/sweep.py), matching the path named in Bob's provenance comment in `engine/detect.py`. It was written for and executed from that path. An over-broad `local/` gitignore rule initially excluded it from the first push, causing the comment to reference an inaccessible file. It is committed here unmodified. `.venv/Scripts/python.exe tools/sweep.py --selftest` prints `MATCH`.
- The sweep reimplements the committed detector and self-tests against the ruler before any result is accepted. The search self-test runs the committed configuration and verifies it reproduces `tools/score.py` exactly (tp=45, fp=268, fn=25, F1 0.234987).
- Configurations are chosen exclusively on `dev`. Holdout is scored once per finalist for reporting and is never used as a selection input. Tuning against the 35 held-out windows would overfit and collapse under external re-evaluation.
- The search space covers the existing named constants plus the pruning step from Hundman et al. §3.3.

## Metric gaming and degenerate solutions

The initial wide sweep placed every one of its top eighteen results at the grid edge (`merge_gap = 800`), reporting dev F1 up to 0.807 (more than triple the baseline).

This apparent breakthrough was an artifact of the metric. Window-overlap F1 is maximized by emitting one enormous window per channel: it overlaps any anomaly present and counts as at most a single false positive. Measured at that setting:

| | windows/channel | median window | channel covered |
|---|---|---|---|
| committed baseline | 6.1 | 26 samples | 14.3% |
| sweep "winner" (gap 800) | 0.9 | 1668 samples | 39.2% |

A detector that flags 40% of telemetry in a single 1668-sample span provides no operational value on console despite a high benchmark score.

To prevent this, the search carries operational constraints alongside the metric: `--max-coverage` (default 20% of a channel) and `--max-median-len` (default 300 samples). 301 of 960 configurations in the pruning sweep were rejected as degenerate. The numbers below are all from the admissible region.

The scorer is fixed and cannot be modified to close this loophole. Surfacing metric flaws directly ensures valid results without exploiting evaluation artifacts.

## What was selected

Chosen as the best `dev` F1 among configurations that change only the existing constants:

```
ROLLING_WINDOW      100   (unchanged)
DETECTION_THRESHOLD 4.0 -> 6.0
MERGE_GAP            50 -> 150
MIN_WINDOW_LEN        5   (unchanged)
```

| | dev F1 | holdout F1 | precision | recall | median window | coverage |
|---|---|---|---|---|---|---|
| iteration-0 baseline | 0.235 | 0.266 | 0.163 | 0.714 | 26 | 14.3% |
| selected | 0.608 | 0.623 | 0.731 | 0.543 | 138 | 14.3% |

Dev 0.608 to holdout 0.623 shows almost no generalisation gap on a configuration selected without inspecting holdout data. Coverage remains unchanged from the baseline at 14.3%: the detector flags fewer, better-consolidated windows, producing 7 false positives on holdout compared to 128 for the baseline.

Precision reached 0.731 against the paper's 0.875 on an evaluation that scores the whole series instead of a window around each anomaly. See [`telemanom-paper-comparison.md`](telemanom-paper-comparison.md).

## What did not work: the paper's pruning

Hundman et al. report that pruning improved precision from 48.9% to 87.5% for 4.8 points of recall, the largest single effect in their results table. It did not transfer here.

On dev, the best pruning configuration (`p = 0.5`, threshold 4.0, merge gap 100) scored dev F1 0.672, topping the selected constant-only config on dev, but dropped to holdout F1 0.571. A tighter, higher-precision pruning variant reached dev 0.624 and collapsed to holdout 0.407.

The likely reason relates to what is being ranked. Pruning ranks *LSTM prediction errors*, which encode how surprising a value is given learned temporal context. This engine has no model and ranks `|residual| / MAD`, which measures only distance from a rolling median. The ranking heuristic that separates true anomalies from the noise floor in model residuals does not appear to separate them in median deviations. The best-performing values of `p` also fell between 0.35 and 0.50, well outside the paper's 0.05 to 0.20 range, indicating that the mechanism was being pushed beyond its intended use.

This provides an empirical negative result on the paper's headline component.

## Verifying this

The search ran off-repo, but the conclusion is checkable directly from the repository:

```bash
.venv/Scripts/python.exe tools/score.py     # reproduces holdout F1 0.622951
cat results/ledger.jsonl                    # iteration 6, kept, with its cost and task id
git show 9cc792e                            # the change itself, authored by IBM Bob
```

The constants live in [`engine/detect.py`](../engine/detect.py) with Bob's own comment recording where they came from.

## What was tried afterwards and did not work

Three mechanisms from the post-2018 literature (EWMA residual smoothing, a trimmed scale estimate, and hysteresis thresholding) were implemented and searched the same way. The best candidate gained +0.0086 holdout F1, which is less than a single window on the 35-window split. See [`literature-review.md`](literature-review.md).

## Day 4: the same method pushed until it broke

The search above chose two constants and they held up: dev 0.608, holdout 0.623, with a generalisation gap near zero. Day 4 ran the same method against the scoring stage (replacing the detector's peak test with an area test) and reached dev 0.702. While this was the largest dev gain of any candidate, the gate reverted it at holdout 0.615.

Analyzing that discrepancy produced a clear statistical result. Across all 432 admissible configurations in that sweep, dev F1 and held-out F1 are uncorrelated (Pearson +0.007, Spearman -0.001). 382 configurations beat the committed engine on dev, while only 58 beat it on holdout. A dev win moves the chance of a holdout win from 13.4% to 14.7%.

This analysis also established an error bar on every holdout metric: the sweep's numpy rolling median and the engine's pandas rolling median differ by enough to flip one held-out window, which represents ±0.02 F1 on a 35-window split.

Both findings, and the decision to conclude score tuning before depleting the project budget, are documented in [`generalisation.md`](generalisation.md).
