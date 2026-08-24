## Where to aim this iteration

Read the "Already tried" list above. Four iterations have been reverted, and the two
that moved a single constant each traded recall for precision at roughly one for one.
That was the right *class* of change made in the wrong *combination*: the constants
interact, and moving one at a time cannot find the pair that works.

A dev-split search over 960 configurations has now been run offline
(`tools/sweep.py`, committed, reproducible, no Bobcoins). It selected a configuration
**on the dev split only** — the held-out channels were never a selection input — and
that configuration is:

    ROLLING_WINDOW      100   (unchanged)
    DETECTION_THRESHOLD 4.0 -> 6.0
    MERGE_GAP            50 -> 150
    MIN_WINDOW_LEN        5   (unchanged)

Measured on dev: precision 0.691, recall 0.543, F1 0.608, against the current 0.235.

**Your task is to make that change to `engine/detect.py`, and to write the reasoning
into the code so a mission-ops engineer reads it and understands why.** This is the one
iteration where the values are given to you rather than proposed by you; the search that
produced them is in `tools/sweep.py` and its findings are in `docs/parameter-search.md`.
Do not go read those files — everything you need is here.

### Why these two constants move together

At 4σ the detector fires on ordinary variation, producing a spray of short windows —
268 false alarms on dev against 45 true positives. Raising the threshold to 6σ alone
removes false alarms *and* true positives together, because a real anomaly is often only
briefly extreme and the rest of it falls back under the bar; that is what a previous
iteration measured when it moved the threshold alone and lost recall one-for-one.

Widening the merge gap to 150 samples is what makes the higher threshold survivable. A
genuine anomaly produces several separated bursts above 6σ, and merging across a longer
quiet interval reconstitutes them into the single event they actually are, instead of
discarding each fragment as too short. The two changes are one change.

### A constraint you must not violate

The search found that this metric can be gamed. Merging across very long gaps collapses
each channel into roughly one enormous window, which overlaps whatever anomaly exists
and can only cost one false positive. That scores dev F1 0.807 while flagging 39% of
every channel with a median window of 1668 samples — an alarm that tells an operator
nothing.

`MERGE_GAP = 150` is deliberately well short of that. **Do not raise it further, and do
not add any change whose effect is to emit fewer, larger windows.** The detector must
still localise: median window length should stay in the low hundreds of samples and
total flagged coverage near 14% of a channel, which is where the baseline already sits.

## What to do

1. Change the two constants in `engine/detect.py`.
2. Rewrite their docstring comments to explain the interaction above — why 6σ needs a
   wider merge gap to be viable, and why the merge gap is capped well below the point
   where the metric becomes gameable. The existing comments justify 4.0 and 50 and will
   be actively wrong once you change the values.
3. Change nothing else. No new mechanism, no pruning, no local scale estimation. Those
   were tried and measured; see the "Already tried" list.
