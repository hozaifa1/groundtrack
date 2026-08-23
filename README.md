# Groundtrack

**IBM Bob writes the spacecraft anomaly detector. A fixed benchmark decides whether it was any good.**

Built for the [AI Builders Challenge with IBM Bob](https://aibuilderschallenge-bobhub.bemyapp.com/) — August theme, *Advance Space Exploration with AI*.

> **Status: in active development (Day 2 of 9).** Bob has authored the iteration-0 baseline engine. It scores **holdout F1 0.266** (precision 0.163, recall 0.714) across 26 held-out channels, and crashes on none of the 82. Precision is the weak half and is what the forge loop will attack. The improvement loop itself is not wired up yet.

---

## The problem

A small mission-operations team — a university CubeSat program, or an early NewSpace startup where "ops" is three or four rotating grad students — inherits an anomaly-response runbook written once at commissioning. It maps telemetry signatures to corrective actions.

It is almost never revalidated against real flight data as new fault modes appear, because doing that means sitting down, replaying months of telemetry against the current rules, finding the misses, and patching the logic. That is unglamorous maintenance work, and a four-person team with theses and a semester will keep deferring it.

Then an anomaly hits, and the person on console needs an answer that is instant, cited, and *already validated* — not a chatbot improvising over numbers it has never been checked against.

## The approach

Groundtrack splits the problem in two, and the split is the point.

**The ruler is written outside the loop. The engine is Bob's.**

- [`tools/score.py`](tools/score.py) — the metric, the data split, the failure reporting — is authored outside the forge loop, committed before the engine exists, and Bob may never touch it. What matters is not who typed it but that the agent under test cannot reach its own grader.
- **IBM Bob authors 100% of [`engine/`](engine/)** — including the initial baseline — running headlessly through `bob run` inside a scored keep/discard loop. Bob proposes one minimal edit, the scorer re-runs, and the harness commits the change or reverts it.
- **IBM Granite** turns each detection into a plain-language operations brief, generated offline via Ollama and committed to the repo.

Because the thing that grades the agent sits outside the agent's reach, the central claim is checkable rather than asserted:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u
```

That names `IBM Bob`, and nothing else. Remove Bob, and there is no detector.

(`engine/README.md` is human-written documentation and does appear under `git log -- engine/`. The claim is about the engine, so the command is scoped to `engine/*.py` — [`engine/README.md`](engine/README.md) says so itself rather than leaving it for a reader to catch.)

## Why it matters

Anomaly detectors for spacecraft telemetry are not scarce — the research literature is full of them. What is scarce is a detector a four-person team can *own*: one small enough to read, cheap enough to re-tune when a new fault mode appears, and honest enough to show its working.

Groundtrack is an argument that an agentic SDLC tool can maintain that kind of artifact continuously, against a real metric, with every decision written down — instead of a model that was accurate once, in a paper, in 2018.

## IBM Bob usage

Bob is a **development-time** tool here and is never in a runtime request path — it has no runtime API, and pretending otherwise would be architecturally false.

| Where | What Bob does |
|---|---|
| [`.bob/skills/anomaly-forge-engineer/`](.bob/skills/anomaly-forge-engineer/SKILL.md) | A real, reusable Bob skill defining the engineer role, its guardrails, and its JSON report format |
| `tools/forge_loop.py` | Invokes `bob run --format json --max-cost 3 --max-turns 12` per iteration, parses the result, and gates it on the held-out metric |
| `engine/` | Every file, authored and re-authored by Bob |
| `results/ledger.jsonl` | Every iteration recorded: `task_id`, cost, turns, score before/after, kept or reverted |

Bobcoin spend is capped per call and tracked per iteration. Failed experiments are logged as failures, never quietly dropped — the very first ledger entry is a run that hit its cost cap and produced no code at all.

The cap is 3 rather than 1 because of something measured on Day 2: a run that hits `--max-cost` is still billed in full. A cap set below the real cost of an iteration does not save coins, it converts them into nothing.

## The benchmark

**Telemanom** — real labelled spacecraft telemetry from NASA's Soil Moisture Active Passive satellite (SMAP) and the Mars Science Laboratory rover (MSL). Apache-2.0.

- 82 channels · 105 expert-labelled anomaly sequences · 62 point, 43 contextual
- Split deterministically by channel-id hash into **56 dev / 26 holdout** channels (**70 / 35** labelled windows)
- Bob sees failures from `dev` only. `holdout` decides whether an iteration is kept.

Source: [khundman/telemanom](https://github.com/khundman/telemanom) · Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD 2018.

The metric is window-overlap F1: a labelled anomaly counts as caught if any prediction overlaps it. Operators care whether the event was caught, not whether every sample inside it was flagged.

## Quick start

```bash
python -m venv .venv && ./.venv/Scripts/activate    # Windows
pip install -r requirements.txt

python tools/fetch_data.py        # ~9 MB, no API key, no account
python tools/test_score.py        # validate the ruler
python tools/score.py             # grade the current engine
```

`pandas` must come from the virtualenv. If `python` on your PATH is the system
interpreter, call the venv one explicitly — `.venv/Scripts/python.exe tools/score.py`
on Windows — or the scorer will fail on a missing import rather than on the metric.

## Verify this yourself

Every claim here is meant to be checked, not believed. None of these commands spend Bobcoins.

```bash
git log --format='%an' -- 'engine/*.py' | sort -u   # names IBM Bob, nothing else
cat results/ledger.jsonl                            # every iteration, cost, outcome
python tools/score.py                               # reproduce the headline metric
python tools/fetch_data.py --check                  # confirm the benchmark is intact
python tools/make_briefs.py --check                 # regenerate a Granite brief, diff it
```

Raw `bob run` transcripts are committed under `results/bob_runs/`, so the `task_id`
and coin cost in the ledger can be checked against Bob's own output rather than taken
on trust.

## Honest limitations

Stated here rather than left for a reader to find:

- **The runbook text is illustrative**, templated from Telemanom's public channel metadata. It is not certified NASA operational doctrine.
- **The held-out split is small** — 35 labelled windows. F1 on that many events is noisy, and a large swing between iterations should be read with suspicion.
- **Granite briefs are pre-generated offline**, not produced live per request. The generation script ships, so anyone with Ollama can regenerate and diff them.
- **The beneficiary is not yet validated.** Small-team mission ops is a plausible user, not a confirmed one. Outreach is in progress and this line will be updated honestly either way.

## License

Apache-2.0 — matching the benchmark it is built on.
