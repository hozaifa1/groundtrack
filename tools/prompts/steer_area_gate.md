## Where to aim this iteration

The engine currently asks one question of every candidate window: **did any single
sample cross 6σ?** That is a peak test, and it is why recall has stalled. On the dev
split the detector now finds 38 of 70 labelled windows — precision 0.691, recall 0.543,
F1 0.608. The 32 it misses are not quiet. They are windows that deviate moderately for
a long time and never spike hard enough to trip a peak test.

A dev-split search run offline (no Bobcoins, held-out channels never a selection input)
replaced the peak test with an **area test** and measured, on dev:

    precision 0.909   recall 0.571   F1 0.7018   (tp 40 / fp 4 / fn 30)

The peak branch was then ablated to check which half was doing the work. Removing the
peak test changed the result **not at all** — F1 0.7018 either way. Removing the area
test dropped it to 0.6476. The area test is the entire mechanism. Ship it as that, not
as a two-threshold rule.

## The change

    DETECTION_THRESHOLD   6.0 -> 4.0     (now a CANDIDATE threshold, not a verdict)
    MERGE_GAP             150 -> 200
    MIN_WINDOW_AREA       new, 40.0
    MIN_WINDOW_LEN        5   (unchanged)
    ROLLING_WINDOW        100 (unchanged)

The detection procedure becomes, in this order:

1. `z = |value - rolling_median| / (MAD * 1.4826)` — unchanged.
2. Flag samples where `z > DETECTION_THRESHOLD` (4.0). This is back to the value the
   engine started with, and it is deliberate: 4σ is a good *candidate* generator and
   was only ever a bad *verdict*.
3. Merge flagged runs separated by `<= MERGE_GAP` (200) samples — unchanged in kind.
4. Drop merged windows shorter than `MIN_WINDOW_LEN` (5) — unchanged.
5. **New, and this is the iteration:** for each surviving window compute

       area = sum over samples i in the window of max(z_i - DETECTION_THRESHOLD, 0)

   and keep the window only if `area >= MIN_WINDOW_AREA` (40.0). Note the sum runs over
   the *whole merged window*; samples inside it that sit below the threshold contribute
   zero, which is what the `max(..., 0)` is for.

## Why area is the right question

A peak test asks how *extreme* the worst sample was. An area test asks how much total
excursion the window accumulated — depth integrated over duration. Those come apart
exactly where this engine has been losing:

- A single 7σ spike lasting three samples has a large peak and a small area. It is
  usually a sensor glitch. The area test drops it.
- A 4.5σ deviation sustained for two hundred samples never approaches 6σ, so the peak
  test discards it entirely. Its area is large. It is also what a degrading component,
  a thermal runaway or a slow leak actually looks like in telemetry, and the benchmark
  labels this class of event as `contextual` rather than `point`.

That second case is where the 32 dev misses live, and recovering some of them is the
whole point: at 4 false positives the detector has precision to spare and has been
spending recall to buy more of it.

## A constraint you must not violate

This metric can be gamed. Window-overlap F1 is maximised by emitting one enormous
window per channel: it overlaps whatever anomaly is present and can only ever cost a
single false positive. A configuration doing that scored dev F1 0.807 while flagging
39% of every channel with a median window of 1668 samples — an alarm that tells an
operator nothing. It was rejected, and `tools/score.py` is fixed and is not to be
touched.

The configuration above was measured at **median window 139 samples and 18.8% of a
channel flagged**, against the current engine's 134 samples and 16.5%. It emits *fewer*
windows than the engine it replaces (43 against 53), not larger ones.

**Do not raise MERGE_GAP beyond 200, and do not lower MIN_WINDOW_AREA below 40.** Both
of those loosen the rule in the direction of the degenerate regime. If you find
yourself making detections bigger, you are optimising the hole in the metric rather
than the detector.

## What to do

1. Make exactly the change above in `engine/detect.py`.
2. Rewrite the constant docstrings. The existing comment on `DETECTION_THRESHOLD`
   argues at length for 6.0 and for why it must move together with `MERGE_GAP`; that
   reasoning describes a peak test and will be actively wrong once the verdict is an
   area test. Explain the new rule the way the old one was explained — depth times
   duration, why a glitch fails it and a drift passes it, and why the threshold going
   back down to 4.0 is not a reversion to the old behaviour.
3. Change nothing else. No pruning, no EWMA smoothing, no local or trimmed scale
   estimate, no multi-scale baseline. All four were implemented and measured offline;
   pruning and the two scale variants hurt, and multi-scale bought one extra dev true
   positive for a second mechanism this iteration does not need.
