## Where to aim this iteration

Read the "Already tried" list above first. Three iterations have been reverted and the
shape of their failure is the whole briefing:

- Two moved a single scalar constant (minimum window length, then the sigma threshold)
  and each traded recall away for precision at roughly one for one, so F1 fell both
  times. **The constants are exhausted. Do not propose another value for one.**
- One replaced the global MAD with a rolling local MAD. Recall went *up* on both splits
  (dev 0.643 -> 0.771) while false alarms more than doubled, because a local scale
  collapses towards zero in a temporarily flat stretch. **A naive local scale is not the
  answer either.**

### What the literature says about exactly this gap

This benchmark comes from Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs
and Nonparametric Dynamic Thresholding*, KDD 2018 (arXiv:1802.04431). Their Table 2
reports the same detector with and without one post-processing component:

    without pruning    precision 48.9%   recall 84.8%
    with pruning       precision 87.5%   recall 80.0%

Precision up 38.6 points for 4.8 points of recall. That is the opposite of the
one-for-one trade every iteration here has made so far, and it is the single largest
effect in their results table.

Their pruning step (paper §3.3), stated as a mechanism rather than as code:

1. Every candidate anomalous sequence is reduced to **one number**: the maximum error
   inside it.
2. Those maxima are sorted in descending order, and the largest error from the
   *non-flagged* part of the signal is appended to the end of that list.
3. Walk the sorted list computing the percent decrease from each value to the next:
   `d_i = (e_{i-1} - e_i) / e_{i-1}`.
4. At the first step where `d_i` exceeds a minimum percentage `p`, everything ranked
   above that step stays an anomaly. Everything from that step onward — including all
   subsequent sequences — is reclassified as nominal.
5. The paper used `p = 0.13` and reports `0.05 < p < 0.20` as the workable range.

The idea underneath it: a channel's genuine anomalies stand clearly above its own
background, and if a long tail of candidates shades smoothly into the noise floor with
no clear break, that tail is the noise floor. It is a **per-sequence** decision made
after the per-sample threshold has already fired, which is precisely the layer none of
the three reverted iterations touched.

### What you have to work out yourself

The paper prunes *LSTM prediction errors*. This engine has no model and no prediction
errors — it has residual magnitudes from a rolling median. Whether the same ranking
logic works on `|residual| / scale` is not something the paper answers, and the value of
`p` that suits this engine is not necessarily theirs. Their evaluation also differs from
this one: they score only a window around each labelled anomaly, while `tools/score.py`
scores the entire series and charges you for every false alarm anywhere in it.

So: adapt the mechanism, choose the parameter, and let the gate decide. Precision is
still the weak half, and the last iteration showed that recall is available if the false
alarms can be controlled.
