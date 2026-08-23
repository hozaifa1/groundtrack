You are the sole author of the anomaly-detection engine in this repository. Read
`AGENTS.md` and `.bob/skills/anomaly-forge-engineer/SKILL.md` first — they define the
rules you operate under.

`engine/` currently contains no code at all. Your job this run is **iteration 0**:
create the initial baseline engine from scratch. No human has written, or will ever
write, any detector code here.

## Create exactly two files

### `engine/detect.py`

```python
def detect(df) -> list[tuple[int, int]]:
    """Flag anomalous index ranges in a single telemetry channel."""
```

`df` is a pandas DataFrame for ONE channel with columns:
  `timestep` (int), `value` (float, the monitored signal), `cmd_0 .. cmd_N`
  (one-hot spacecraft command context; N varies by channel).

Return inclusive `(start, end)` index ranges in ascending order, non-overlapping.
Returning `[]` is legal and scores zero.

### `engine/runbook.py`

```python
def match(df, window: tuple[int, int]) -> dict:
    """Map a detected anomaly to an operator-facing runbook entry."""
```

Return a dict with at least: `signature` (short slug, e.g. `"level_shift"`),
`title`, `severity`, and `action` (what a mission-ops engineer should do next).
Classify from the telemetry inside the window only. Keep the text generic
flight-rule style; it is illustrative operator guidance, not certified doctrine.

## What the baseline should be

Something simple, explicit, and defensible — a rolling-statistics detector is the
expected starting point. Smooth the signal, measure how far each sample sits from its
local expectation in robust units, threshold it, and merge nearby exceedances into
windows. Do not attempt anything sophisticated. This is the floor that later
iterations improve on, and a small readable baseline is worth far more here than a
clever one that nobody can build on.

Write real docstrings explaining *why* a rule exists. A mission-ops engineer must be
able to read `detect.py` and see why it fired.

## Hard rules

- Standard library, `numpy`, `pandas` only. No new dependencies.
- Never read `data/telemanom/labeled_anomalies.csv`. Detection runs on telemetry alone.
- No per-channel hardcoding. Never reference a channel id.
- Deterministic. No unseeded randomness.
- Never modify `tools/score.py`, `data/`, or `results/`.
- The engine must not crash on any channel. Guard against short series, constant
  signals, and zero variance.

## Verify before you finish

```bash
.venv/Scripts/python.exe tools/score.py
```

That takes 30-60 seconds and reads all 81 channels — this is normal. It must print a
GATE METRIC line, not an error. If it errors, fix `engine/detect.py` and re-run once.

## Report

Finish with a JSON object on its own:

```json
{
  "target_failure": "no engine existed",
  "hypothesis": "<the detection idea in one sentence>",
  "change": "<what you created>",
  "files_touched": ["engine/detect.py", "engine/runbook.py"],
  "f1_before": 0.0,
  "f1_after": <the GATE METRIC the scorer actually printed>,
  "generalises": "<dev vs holdout F1 as reported by the scorer>"
}
```

Report the number the scorer actually printed. Never invent one.
