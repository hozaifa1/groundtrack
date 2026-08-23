Write the initial baseline for a spacecraft anomaly detector. `engine/` has no code
yet; you are its sole author. Everything you need is below — do not read other files,
do not list directories, do not explore. Write the two files, verify once, report.

## 1. `engine/detect.py`

```python
def detect(df) -> list[tuple[int, int]]:
```

`df` is a pandas DataFrame for ONE telemetry channel, 1000-9000 rows, columns:
`timestep` (int), `value` (float, the monitored signal), and `cmd_0`..`cmd_N`
(one-hot command context, N varies). Return inclusive `(start, end)` index ranges,
ascending and non-overlapping.

Baseline algorithm — implement exactly this, nothing fancier:

1. Robust baseline: rolling median of `value` over a window of ~100 samples,
   `min_periods=1`, centered=False.
2. Residual: `value - rolling median`.
3. Robust scale: median absolute deviation of the residual times 1.4826. If it is
   ~0 (constant channel), fall back to the standard deviation; if that is also ~0,
   return `[]`.
4. Flag samples where `|residual| / scale` exceeds ~4.
5. Merge flagged samples separated by fewer than ~50 samples into one window.
6. Drop windows shorter than ~5 samples as noise.

Put the constants in named module-level variables so later iterations can tune them.

## 2. `engine/runbook.py`

```python
def match(df, window: tuple[int, int]) -> dict:
```

Return `{"signature": str, "title": str, "severity": str, "action": str}`.
Classify from telemetry inside the window only, using a few explicit rules —
e.g. a sustained mean shift is `"level_shift"`, a brief excursion that returns is
`"transient_spike"`, a jump in local variance is `"noise_burst"`, otherwise
`"unclassified"`. Severity from how far the window sits from the channel baseline.
`action` is one or two sentences of generic flight-rule guidance.

## Hard rules

- stdlib, `numpy`, `pandas` only. No new imports beyond those.
- Never read `data/telemanom/labeled_anomalies.csv`. Telemetry only.
- No per-channel hardcoding. Never mention a channel id.
- Deterministic. No randomness.
- Never touch `tools/`, `data/`, or `results/`.
- Must not crash on short, constant, or zero-variance channels.
- Docstrings explain *why* a rule exists. A mission-ops engineer reads this to see
  why it fired.

## Verify (once)

```bash
.venv/Scripts/python.exe tools/score.py
```

Takes 30-60s — that is normal, not a hang. It must print a `GATE METRIC` line. If it
errors, fix it and re-run once.

## Report

End with only this JSON:

```json
{"target_failure":"no engine existed","hypothesis":"...","change":"...",
 "files_touched":["engine/detect.py","engine/runbook.py"],
 "f1_before":0.0,"f1_after":<the GATE METRIC actually printed>,
 "generalises":"dev F1 ... / holdout F1 ..."}
```

Report the number the scorer printed. Never invent one.
