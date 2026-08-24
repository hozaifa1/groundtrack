## Where to aim this iteration

Two iterations have now moved a single scalar knob - the minimum window length,
then the sigma threshold - and both traded recall away for precision at almost
exactly one for one, so F1 fell both times. Treat the constants as exhausted. The
baseline sits at a local optimum for scalar tuning, and another value of another
constant will not move the gate.

What has not been tried is the mechanism. The residual scale is estimated ONCE per
channel, from the entire channel, so a channel with one noisy stretch carries that
noise into its threshold everywhere, and a quiet channel flags its own ordinary
variation. Four channels produce 219 of the 268 dev false alarms; that concentration
is a property of how the scale is estimated, not of where the threshold sits.

Change how the engine decides, not what number it compares against. Precision is
still the weak half, and recall is what you must not spend to get it.
