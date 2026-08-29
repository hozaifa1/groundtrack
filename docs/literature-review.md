# Eight years after the benchmark: what the follow-up literature says

The benchmark for this project comes from a 2018 paper. A review of literature from
2021 to 2026 examined what the field has learned since, and whether newer methods
improve the held-out score.

**The main takeaway: the literature formally documents the exact metric weakness this
project encountered, and refinements published since 2018 did not improve our
held-out score.**

## 1. The metric hole is a known, named problem

While searching the parameter space, this project found that window-overlap F1 can reach
0.807 on dev by emitting **one enormous window per channel**: it overlaps any anomaly
present and incurs only a single false positive. That configuration flags 39% of every
channel with a median window of 1668 samples. It was rejected. See the note on the
metric in the README.

The literature documents this exact result:

- Kim et al. showed that the **point adjustment** protocol, near-universal in this
  field, "has a great possibility of overestimating the detection performance; even a
  random anomaly score can easily turn into a state-of-the-art TAD method" [1].
- Garg et al. found that existing metrics "either do not take events into account or
  **cannot distinguish between a good detector and trivial detectors, such as a random
  or an all-positive detector**", and proposed a composite F-score to fix it [2]. That
  matches the failure measured here.
- Sehili et al. put it bluntly: the point-adjust protocol is "so flawed ... that a
  random guess can be shown to systematically outperform all algorithms developed so
  far" [3].
- A 2026 adversarial stress-test of the *replacement* metrics found they hold up under
  a single honest run, but ROC-based and affiliation metrics inflate sharply under
  best-of-N seed shopping, while **PR-based metrics stay flat**. Its recommendation is
  to report single-run scores or disclose N [4].

Window-overlap F1, used by Hundman et al. and computed by `tools/score.py`, belongs to
this family. While distinct from point adjustment, it shares the core weakness: scoring
whether an event was touched rewards oversized detections and ignores precision.

**This project's response:** the scorer remains fixed without modification to keep the
benchmark objective. Instead, the parameter search enforces operational constraints
(flagged coverage per channel and median window length) and rejects degenerate
configurations outright. One search stage eliminated 301 of 960 configurations on this
basis. The single-run recommendation in [4] is also followed: every number in
`results/ledger.jsonl` is one run without best-of-N selection.

## 2. The benchmark itself is contested

Wu and Keogh examined common benchmarks (Yahoo, Numenta, **NASA**, OMNI) and concluded
that most individual exemplars suffer from at least one of four flaws: **triviality,
unrealistic anomaly density, mislabeled ground truth, and run-to-failure bias**. Their
conclusion is that "much of the apparent progress in recent years may be
illusionary" [5].

SMAP and MSL are the NASA datasets in question. The telemetry remains real labelled
spacecraft data from the original paper. Given the benchmark flaws, an F1 score on
SMAP/MSL indicates sensible detector behavior on recorded traces, not literal
operational accuracy in orbit.

## 3. Simple methods match sophisticated ones on these datasets

This finding supports the detector design used here: a compact, readable algorithm.

- Sehili et al. propose "a simple, yet challenging, baseline based on Principal
  Components Analysis that **surprisingly outperforms many recent Deep Learning based
  approaches** on popular benchmark datasets" [3].
- A 2026 study shows a **closed-form linear autoregressive** anomaly score from ordinary
  least squares "consistently matches or outperforms state-of-the-art deep detectors",
  at orders of magnitude lower cost, and argues future work must always include strong
  linear baselines [6].
- Garg et al. found that a **simple channel-wise fully-connected autoencoder** with a
  dynamic Gaussian scoring function beat state-of-the-art algorithms, noting that "the choice
  of scoring functions often matters more than the choice of the underlying model" [2].
- A re-examination of OmniAnomaly under identical thresholding and 100 runs per machine
  found PCA "can achieve performance comparable to OmniAnomaly, and even outperform it
  when point-adjustment is not applied" [7].

The engine here uses a rolling median and MAD. Published evidence supports this choice,
and the scoring stage, which the literature identifies as more critical than the model,
is where this project achieved its improvement.

## 4. What was implemented from this literature, and what it did

Three mechanisms recommended by post-2018 work were implemented and searched on the dev
split:

| Mechanism | Source | Result on dev |
|---|---|---|
| **EWMA smoothing of the residual** before thresholding | Hundman §3.2; LSTD-Detect [8] | Hurt. Absent from every top configuration. |
| **Trimmed scale estimate**: MAD from residuals below a quantile, so anomalies do not inflate the threshold that must find them | LSTD-Detect, which names "fixed statistical thresholds inflated by anomalous segments, catastrophically suppressing recall" [8] | Hurt. Absent from every top configuration. |
| **Hysteresis thresholding**: a high threshold to seed a detection, a low one to extend it | The global + local adaptive threshold combination in [9]; adaptive-threshold framings in [10] | Best on dev: F1 0.654 vs 0.608 |

The hysteresis configuration was then scored once on holdout:

| | dev F1 | holdout F1 | precision | recall |
|---|---|---|---|---|
| current engine | 0.608 | **0.6230** | 0.731 | 0.543 |
| hysteresis (dev-selected) | 0.654 | **0.6316** | 0.818 | 0.514 |

**+0.0086 on holdout (smaller than a single one of the 35 held-out windows).** Precision
rises meaningfully (0.731 → 0.818) and recall falls (0.543 → 0.514), while F1 stays
within noise.

That is a negative result, reported as one. Three mechanisms from the follow-up
literature, implemented faithfully and searched systematically, produced no held-out gain over
two well-chosen constants.

This outcome aligns with the critical literature. When domain evaluations show that
simple baselines match deep models [3][6][7], that common metrics fail to separate a good
detector from a trivial one [1][2][3], and that benchmarks contain structural flaws [5],
a sophisticated addition is unlikely to outperform a simple detector, as observed here.

## 5. What this changes about the plan

- **Do not chase mechanism complexity for score.** It was tried, from the literature,
  and measured. Remaining headroom is in recall (0.514 to 0.543; 16 of 35 held-out windows
  still missed), and no reviewed technique addressed it without giving back precision.
- **Report single-run numbers only** [4]. Already the case.
- **Keep the operational constraint on any search.** The metric rewards large windows
  and the field knows it.
- **The "small readable detector" choice is now evidence-backed**, and the README
  documents this with citations.

## References

1. [Towards a Rigorous Evaluation of Time-series Anomaly Detection](https://consensus.app/papers/details/205b131dc31158e981941e596f68de40/?utm_source=claude_desktop). Siwon Kim et al., 2021, 249 citations
2. [An Evaluation of Anomaly Detection and Diagnosis in Multivariate Time Series](https://consensus.app/papers/details/e6f62a5e92065cdca4ab474429b8662f/?utm_source=claude_desktop). Astha Garg et al., 2021, IEEE TNNLS, 346 citations
3. [Multivariate Time Series Anomaly Detection: Fancy Algorithms and Flawed Evaluation Methodology](https://consensus.app/papers/details/210f6351a8545a829c21359350e3f72d/?utm_source=claude_desktop). M. A. Sehili et al., 2023, ArXiv
4. [Did We Actually Fix It? An Independent Adversarial Stress-Test of Post-Point-Adjustment Evaluation Metrics](https://consensus.app/papers/details/1f8c3fa3f596509ea3057d5a9b02f52a/?utm_source=claude_desktop). Zongye Lyu, 2026, ArXiv
5. [Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress](https://consensus.app/papers/details/680875e66c5753a7bdb8d7c809a9b29b/?utm_source=claude_desktop). R. Wu et al., 2022, IEEE ICDE
6. [Strong Linear Baselines Strike Back: Closed-Form Linear Models as Gaussian Process Conditional Density Estimators for TSAD](https://consensus.app/papers/details/242e6c111ac654b5b6206b9eb2ab043a/?utm_source=claude_desktop). Aleksandr Yugay et al., 2026, ArXiv
7. [Revisiting OmniAnomaly for Anomaly Detection: performance metrics and comparison with PCA-based models](https://consensus.app/papers/details/9e60017dde705f359b856b3de91dd20c/?utm_source=claude_desktop). Bruna Alves et al., 2026, ArXiv
8. [LSTD-Detect: LSTM-Based Telemetry Anomaly Detection with Non-Parametric Dynamic Thresholding for Spacecraft Health Monitoring](https://consensus.app/papers/details/d7d5adf1b1a35931828153e85384db45/?utm_source=claude_desktop). Gao Deng, 2026, ISEAE
9. [Anomaly Detection in Telemetry Data Using Attention-Based LSTM-VAE and Multi-Scale Residual Analysis](https://consensus.app/papers/details/d90e6c1dd2995512addb1c0d04be1458/?utm_source=claude_desktop). A. K. Pandey et al., 2025, BuildSEC
10. [Segmented Confidence Sequences and Multi-Scale Adaptive Confidence Segments for Anomaly Detection in Nonstationary Time Series](https://consensus.app/papers/details/c6c0eb4eea035617a7e908d6ae7c12cb/?utm_source=claude_desktop). Muyang Li et al., 2025
