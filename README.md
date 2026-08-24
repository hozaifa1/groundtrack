# Groundtrack

**IBM Bob writes the spacecraft anomaly detector. A fixed benchmark decides whether it was any good.**

Built for the [AI Builders Challenge with IBM Bob](https://aibuilderschallenge-bobhub.bemyapp.com/) — August theme, *Advance Space Exploration with AI*.

> **Status: in active development (Day 3 of 9).** Bob has authored the iteration-0 baseline engine. It scores **holdout F1 0.266** (precision 0.163, recall 0.714) across 26 held-out channels, and crashes on none of the 82. The forge loop is now wired end-to-end and has run four live iterations. **All four were reverted** — the held-out metric has not moved off the baseline yet. IBM Granite runs locally and writes operator briefs that regenerate byte-for-byte.

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
- **IBM Granite** (`granite4:3b`, run locally through Ollama) turns a detection into a plain-language operations brief, generated offline and committed to the repo. Decoding is pinned so the briefs regenerate byte-for-byte — `tools/make_briefs.py --check` re-asks Granite and diffs the answer against what is committed.

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

## What the loop has actually done

Four live iterations, four reverts. The gate has never yet said yes, and the ledger says so:

| # | Bob's change | dev F1 | holdout F1 | Verdict |
|---|---|---|---|---|
| 1 | minimum window length 5 → 12 | 0.235 → **0.258** | 0.266 → 0.250 | reverted |
| 2 | detection threshold 4.0σ → 4.5σ | 0.235 → 0.250 | 0.266 → 0.255 | reverted |
| 4 | *(never scored — see below)* | — | — | discarded |
| 5 | global MAD → rolling local MAD | 0.235 → 0.148 | 0.266 → 0.249 | reverted |

Iteration 1 is the one worth looking at. Bob's edit **improved the score on the data Bob
could see** and hurt the held-out score, which is exactly the failure the split exists to
catch — and Bob reported it accurately without being asked to: *"recall fell too much on
holdout channels whose true positives happen to be short windows not visible in the dev
failure report."*

Iterations 1 and 2 fail the same way, trading recall for precision roughly one for one.
Iteration 5 fails the opposite way: a locally-estimated scale collapses in flat stretches,
so recall rose on both splits while false alarms more than doubled. Between them they
bracket the problem, and each iteration's prompt now carries the previous verdicts so the
loop does not pay to walk in a circle.

Iteration 4 was not Bob's failure. The harness compared the working tree only *after* the
call, mistook files the operator had saved during it for Bob's work, reverted an engine
edit it had already paid 1.14 coins for, and deleted the operator's files. The ledger
carries a `correction` line saying so — appended, not edited over — and the harness now
snapshots the tree before each call. The wasted coins stay on the books.

There is also an `aborted` line with a **null** cost: a run killed from outside the harness,
which IBM bills whether or not a transcript comes back. It is counted against the budget at
its cap rather than guessed at zero.

The cap is 3 rather than 1 because of something measured on Day 2: a run that hits `--max-cost` is still billed in full. A cap set below the real cost of an iteration does not save coins, it converts them into nothing.

## The benchmark

**Telemanom** — real labelled spacecraft telemetry from NASA's Soil Moisture Active Passive satellite (SMAP) and the Mars Science Laboratory rover (MSL). Apache-2.0.

- 82 channels · 105 expert-labelled anomaly sequences · 62 point, 43 contextual
- Split deterministically by channel-id hash into **56 dev / 26 holdout** channels (**70 / 35** labelled windows)
- Bob sees failures from `dev` only. `holdout` decides whether an iteration is kept.

Source: [khundman/telemanom](https://github.com/khundman/telemanom) · Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD 2018.

The metric is window-overlap F1: a labelled anomaly counts as caught if any prediction overlaps it. Operators care whether the event was caught, not whether every sample inside it was flagged.

The paper's own headline is **F₀.₅ 0.71** (precision 87.5%, recall 80.0%). That is a better result than ours, and it is also not the same measurement — different statistic, an LSTM trained per channel, and an evaluation restricted to a window around each labelled anomaly rather than the whole series. [`docs/telemanom-paper-comparison.md`](docs/telemanom-paper-comparison.md) works the comparison through in full, including the parts that do not flatter us. The short version: our **recall is already in their range** (0.714 vs 0.80) with no model and no training, and precision is the entire gap.

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
python tools/test_score.py                          # validate the ruler itself
python tools/test_forge_loop.py                     # validate the harness that keeps/reverts
python tools/fetch_data.py --check                  # confirm the benchmark is intact
python tools/make_briefs.py --check                 # regenerate a Granite brief, diff it
```

`tools/test_forge_loop.py` is the one to read if you doubt the gate. It asserts that an
edit to `tools/score.py` is classified as a violation, that a revert restores `engine/`
and deletes anything untracked Bob left behind, that the prompt inlines the engine source
while withholding held-out failures, and that a kept iteration is committed with **IBM
Bob** as the git *author* — the field the headline command above reads. 45 checks, no
Bobcoins.

`--check` takes about three minutes: it warms the model, re-runs the engine, asks
Granite for the brief again, and diffs it against the committed file. It is meant to
print `OK ... reproduces exactly`. If it prints a diff, something really did change.

Raw `bob run` transcripts are committed under `results/bob_runs/`, so the `task_id`
and coin cost in the ledger can be checked against Bob's own output rather than taken
on trust.

## Honest limitations

Stated here rather than left for a reader to find:

- **The runbook text is illustrative**, templated from Telemanom's public channel metadata. It is not certified NASA operational doctrine.
- **The held-out split is small** — 35 labelled windows. F1 on that many events is noisy, and a large swing between iterations should be read with suspicion.
- **Granite briefs are pre-generated offline**, not produced live per request. The generation script ships, so anyone with Ollama can regenerate and diff them — `--check` does exactly that and is expected to reproduce the committed text exactly.
- **Only some detections are briefed.** The baseline emits 466 windows and most are false alarms; briefing all of them is hours of CPU inference for output nobody would read. The README will state the final count and the basis for it.
- **The beneficiary is not yet validated.** Small-team mission ops is a plausible user, not a confirmed one. Outreach is drafted in [`docs/outreach/`](docs/outreach/) and not yet sent; that directory also states in advance what may be claimed if nobody replies, which is nothing.
- **The loop has not yet improved anything.** Four iterations, four reverts, holdout F1 still at the baseline 0.266. If it stays there, this ships as "Bob authored and validated this engine, and the gate rejected every change it proposed" — which is still true and still git-provable — rather than as an improvement curve that did not happen.

## License

Apache-2.0 — matching the benchmark it is built on.
