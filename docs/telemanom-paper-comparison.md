# How our score compares to the Telemanom paper

Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD 2018 ([arXiv:1802.04431](https://arxiv.org/abs/1802.04431)), defines the benchmark for scoring this project.

## Their headline result (Table 2)

| Approach | Precision | Recall | F₀.₅ |
|---|---|---|---|
| Non-parametric with pruning (p = 0.13) | 87.5% | 80.0% | 0.71 |
| Non-parametric without pruning (p = 0) | 48.9% | 84.8% | 0.47 |
| Gaussian tail (ε_norm = 0.0001) | 87.5% | 66.7% | 0.66 |

## Ours, at iteration 0

| Split | Precision | Recall | F₁ |
|---|---|---|---|
| dev | 0.144 | 0.643 | 0.235 |
| holdout | 0.163 | 0.714 | 0.266 |

## Comparable metrics

The true and false positive definitions are identical. Section 4.1 in the paper counts a true positive when any portion of a predicted sequence falls inside a labelled anomaly. It records only one true positive per labelled sequence regardless of how many predictions overlap it, and counts every non-overlapping prediction as a false positive. [`tools/score.py`](../tools/score.py) implements this evaluation logic.

Our holdout recall reaches 0.714 compared to their 0.80, computed from a rolling median and median absolute deviation (MAD) without a trained model.

## Differences in evaluation setup

The paper reports F₀.₅, weighting precision higher than recall during parameter tuning. We report standard F₁. The 0.71 and 0.266 summary values cannot be compared directly since the two statistics weigh precision differently.

The paper evaluates a restricted window around each anomaly. In §4.1, the authors evaluate telemetry from `t_s = t_a - 3d` to `t_f = t_a + 2d` around the event, where `d` represents days. Timesteps outside that window are excluded from their evaluation. The paper notes: *"The experiment also does not include processing for all streams not exhibiting anomalous behavior for a given time window, which would further increase the number of false positives."* Our benchmark evaluates the entire telemetry series continuously.

We keep `tools/score.py` fixed. Because our evaluation measures false alarms across full time series, the precision metric is stricter than the paper's windowed setup.

The paper trains an LSTM for each channel with two hidden layers of 80 units over 35 epochs on a dedicated training split, reaching an average prediction error of 5.9%. Our detector runs directly on the test series without prior training.

## Pruning mechanism and next steps

The performance difference between the systems lies mostly in precision.

Pruning provides the main precision gain in the paper's non-parametric pipeline. In Table 2, adding pruning raised precision from 48.9% to 87.5% (a 38.6 point gain) with a 4.8 point loss in recall.

The pruning algorithm (§3.3) operates per candidate sequence. It takes the maximum error of each candidate anomalous sequence, sorts them in descending order, appends the largest unflagged error, and computes the percentage drop between consecutive values. Sequences occurring before the first drop exceeding threshold *p* remain classified as anomalies. The remaining sequences are marked nominal. The paper uses p = 0.13, citing an effective range between 0.05 and 0.20.

We can apply sequence-level pruning to residual magnitudes to reduce false positives.

## Sources

- Hundman, Constantinou, Laporte, Colwell, Soderstrom. *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding.* KDD 2018. <https://arxiv.org/abs/1802.04431>
- Benchmark data and reference implementation: <https://github.com/khundman/telemanom>
