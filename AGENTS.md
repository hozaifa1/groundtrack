# AGENTS.md — Groundtrack

Project context for IBM Bob. Read this before touching anything.

## What this project is

IBM Bob authors a spacecraft anomaly-detection engine. A fixed, human-written scorer
grades it against real labelled NASA telemetry. A harness keeps improvements and
reverts regressions.

Built for the AI Builders Challenge with IBM Bob, August theme: *Advance Space
Exploration with AI*. Deadline **31 August 2026, 11:59pm ET**.

## The one rule that matters

**You author `engine/`. You never touch `tools/score.py`.**

`tools/score.py` is the ruler. It decides whether your work is kept. Editing the ruler
to raise your own score is the single unforgivable failure mode in this repo, and a
`git diff` makes it obvious. If the metric seems wrong, say so in your report — do not
change it.

## Ownership map

| Path | Owner | Notes |
|---|---|---|
| `engine/detect.py`, `engine/runbook.py` | **Bob** | Including the initial baseline. No human edits, ever. |
| `tools/score.py` | Outside the loop | Fixed before the engine existed. Read it to understand the metric; never modify. |
| `tools/test_score.py` | Outside the loop | Tests for the ruler. |
| `tools/fetch_data.py` | Outside the loop | Benchmark download. |
| `tools/forge_loop.py` | Outside the loop | The harness that invokes you. |
| `data/` | Nobody | Immutable benchmark. Never edit or regenerate. |
| `results/` | Harness | Append-only ledger. Never hand-edit. |

## Constraints

- **Dependencies**: standard library, `numpy`, `pandas` only. Do not add packages.
- **No label peeking**: `engine/` must never read `data/telemanom/labeled_anomalies.csv`.
  Detection runs on telemetry alone. Only the scorer sees ground truth.
- **No per-channel hardcoding**: never special-case a channel id. The held-out split
  exists to catch exactly that.
- **Deterministic**: no unseeded randomness. Same input, same output, or the
  keep/discard gate is meaningless.
- **CPU only**: no GPU on this machine, no Docker, no paid services.
- **Small edits**: one targeted change per iteration, explained. A large rewrite that
  scores better is worth less than a small change the next iteration can build on.

## Style

- Readable over clever. A mission-ops engineer must be able to read `detect.py` and see
  why it fired.
- Docstrings explain *why*, not *what*. The code already says what.
- Prefer an explicit rule over a dense one-liner.

## Honesty

Report results accurately, including regressions. A logged failed experiment is a
useful result. A misreported one poisons the ledger and the project's central claim
along with it. Never fabricate a number, and never claim an improvement the scorer did
not produce.

## Security

`competition.json` holds a live IBM API key. It is gitignored and must never be
committed, printed, or echoed into logs, reports, or commit messages.
