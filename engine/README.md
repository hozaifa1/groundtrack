# engine/ — authored entirely by IBM Bob

This directory is deliberately empty of hand-written code.

Every `.py` file that appears here is written by IBM Bob running headlessly via
`bob run`, inside the scored keep/discard loop in `tools/forge_loop.py`. No human
writes or edits detector logic in this directory — including the initial baseline,
which Bob produces as iteration 0.

That constraint is what makes this project's central claim checkable rather than
asserted:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u    # -> IBM Bob, and nothing else
```

If that command names only Bob, then removing Bob removes the engine. If a human had
bootstrapped a baseline here "just to get started", the claim would be quietly false —
so we don't.

Note the exact scope of the claim, because we would rather state it than be caught on
it: **this file** — `engine/README.md` — is human-written documentation, and it shows up
under `git log -- engine/`. Every `.py` file in this directory is Bob's, which is why the
command above filters to `engine/*.py`. Prose about the engine is ours; the engine is not.

## The interface Bob implements

```python
# engine/detect.py
def detect(df) -> list[tuple[int, int]]:
    """Flag anomalous index ranges in a single telemetry channel.

    df columns: timestep, value, cmd_0 .. cmd_N
      value  - the telemetry signal being monitored
      cmd_*  - one-hot encoded spacecraft command context

    Returns inclusive (start, end) index ranges, in ascending order.
    """
```

```python
# engine/runbook.py
def match(df, window: tuple[int, int]) -> dict:
    """Map a detected anomaly to an operator-facing runbook entry."""
```

## Rules Bob operates under

Defined in `.bob/skills/anomaly-forge-engineer/SKILL.md`:

- may edit only `engine/detect.py` and `engine/runbook.py`
- may never edit `tools/score.py` — the ruler sits outside the agent's reach
- may never read `data/telemanom/labeled_anomalies.csv` — detection runs on telemetry
  alone; only the scorer sees ground truth
- no per-channel hardcoding, no new dependencies, deterministic output

The held-out split (26 of 82 channels, decided by a hash of the channel id) is what
gates whether an iteration is kept, so improvements have to generalise rather than
memorise the channels Bob was shown.
