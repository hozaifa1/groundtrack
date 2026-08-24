## Where to aim this iteration

Three iterations have been reverted and each one is worth reading before you propose
a fourth.

Two of them moved a single scalar constant - the minimum window length, then the sigma
threshold - and each traded recall away for precision at almost exactly one for one, so
F1 fell both times. The constants are exhausted. Do not propose another value for one.

The third replaced the single global MAD with a rolling local MAD over 300 samples,
floored at a fraction of the global scale. That was the right kind of idea and it failed
in an instructive direction: recall went **up** on both splits (dev 0.643 -> 0.771,
holdout 0.714 -> 0.743) while false positives more than doubled. A local scale collapses
towards zero in a temporarily flat stretch, so ordinary quantisation steps in a quiet
region start clearing the threshold. The floor was too permissive to stop it.

So the picture is: a global scale is too blunt, and a naive local scale is too fragile
in flat regions. What has *not* been tried is making the engine decide **per candidate
window** rather than per sample - some evidence test a window has to pass before it is
emitted at all, so that a burst of samples clearing the threshold in a flat, quiet
stretch is not the same thing as a burst clearing it against a genuinely varying signal.

Precision is still the weak half. Recall is what you must not spend to get it, and the
last iteration proved recall is available if the false alarms can be controlled.
