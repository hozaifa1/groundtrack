# Groundtrack

**IBM Bob writes the spacecraft anomaly detector. A fixed benchmark decides whether it was any good.**

Built for the [AI Builders Challenge with IBM Bob](https://aibuilderschallenge-bobhub.bemyapp.com/) — August theme, *Advance Space Exploration with AI*.

> **Status: in active development (Day 4 of 9).** Bob has authored every line of the engine. It scores **holdout F1 0.623** (precision 0.731, recall 0.543) across 26 held-out channels, up from an iteration-0 baseline of 0.266, and crashes on none of the 82. Seven forge iterations have run; one was kept and the gate reverted or discarded the rest. Score work has now been **stopped on evidence** — in the region being searched, dev F1 and held-out F1 turn out to be uncorrelated ([`docs/generalisation.md`](docs/generalisation.md)). IBM Granite runs locally and writes operator briefs that regenerate byte-for-byte.

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
- **Where the direction comes from is stated, not implied.** Bob proposed and wrote iterations 1–5 unaided; all five were reverted by the gate. The kept iteration implemented two constants found by an offline dev-split search run on the developer's machine. Bob wrote the code and the reasoning; the search chose the numbers; the held-out gate decided. That division of labour is recorded in [`engine/detect.py`](engine/detect.py) itself — Bob wrote the provenance comment above the constants unprompted — and worked through in [`docs/parameter-search.md`](docs/parameter-search.md).
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

Seven live iterations after the baseline. One kept, four reverted by the gate, one discarded unscored, one aborted — and the ledger carries all of them, including the two that cost coins and produced nothing:

| # | Bob's change | dev F1 | holdout F1 | Verdict |
|---|---|---|---|---|
| 1 | minimum window length 5 → 12 | 0.235 → **0.258** | 0.266 → 0.250 | reverted |
| 2 | detection threshold 4.0σ → 4.5σ | 0.235 → 0.250 | 0.266 → 0.255 | reverted |
| 4 | *(never scored — see below)* | — | — | discarded |
| 5 | global MAD → rolling local MAD | 0.235 → 0.148 | 0.266 → 0.249 | reverted |
| 6 | threshold → 6.0σ **and** merge gap → 150 | 0.235 → 0.608 | 0.266 → **0.623** | **kept** |
| 7 | peak test → **area** test (Σ excursion above 4σ ≥ 40) | 0.608 → **0.702** | 0.623 → 0.615 | reverted |

Iteration 1 is still the one worth looking at. Bob's edit **improved the score on the data
Bob could see** and hurt the held-out score — exactly the failure the split exists to
catch — and Bob reported it accurately without being asked to: *"recall fell too much on
holdout channels whose true positives happen to be short windows not visible in the dev
failure report."*

Iterations 1 and 2 fail the same way, trading recall for precision roughly one for one.
Iteration 5 fails the opposite way: a locally-estimated scale collapses in flat stretches,
so recall rose on both splits while false alarms more than doubled.

Iteration 6 is why they failed. The two constants **interact**, and one-at-a-time search
cannot find the pair: 6σ alone loses recall because a real anomaly crosses the threshold
in several short bursts, and a 150-sample merge gap is what reconstitutes those bursts
into the single event they physically are. Together they take holdout precision from
0.163 to 0.731 — 128 false positives down to 7 — while flagging the same 14% of each
channel as before. Fewer, better-consolidated windows, not bigger ones.

That pair was found by an offline dev-split search, not by Bob, and
[`docs/parameter-search.md`](docs/parameter-search.md) says so at length — including the
part where the search first found a way to score **dev F1 0.807** by emitting one
1668-sample window per channel covering 39% of the telemetry. The metric is gameable, the
scorer is fixed and cannot be patched to close it, and walking through that hole was
declined in writing rather than quietly taken.

Iteration 7 is the one that ended the search, and it is worth more than the
configuration would have been. Steered by the best of 1440 offline configurations, Bob
replaced the detector's peak test — *did any sample cross 6σ* — with an area test that
integrates excursion over the whole window, so a three-sample glitch fails and a
sustained 4.5σ drift passes. It produced the largest dev gain of the project, **0.608 →
0.702**, and lost on holdout. Bob implemented it faithfully: the ledger's dev figure
matches the offline prediction to six decimal places.

So the region was measured rather than argued about. Across all 432 admissible
configurations of that sweep, **dev F1 and held-out F1 are uncorrelated — Pearson +0.007,
Spearman −0.001.** 382 of them beat the committed engine on dev; 58 beat it on holdout.
Filtering by a dev win moves your odds of a held-out win from 13.4% to 14.7%, and the
configuration the dev search was designed to return scores **0.597** on held-out channels
against the committed engine's 0.623. Score work stopped there, on a rule written down
in advance and with roughly 28 of 40 Bobcoins still unspent. The reasoning, the
one-window error bar found in the search harness along the way, and what it says about
this benchmark are in [`docs/generalisation.md`](docs/generalisation.md).

Eight years of follow-up literature was then read and its recommended refinements — EWMA
residual smoothing, trimmed scale estimation, hysteresis thresholding — were implemented
and searched. The best of them moved holdout F1 by **+0.0086**, less than one of the 35
held-out windows. That negative result, and the published work explaining why it was the
expected one, are in [`docs/literature-review.md`](docs/literature-review.md).

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
.venv/Scripts/python.exe tools/plot_progress.py      # redraws results/progress.png from that ledger
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
- **Bob did not find the winning configuration; an offline search did.** Bob proposed and wrote iterations 1–5 unaided and the gate reverted all five. The kept iteration implemented two numbers chosen by an offline dev-split search. Bob wrote every line of the engine and the reasoning in it, and the held-out gate still decided — but "the agent improved its own score by itself" is not a claim this project makes.
- **The metric has a hole in it, and it is documented.** Window-overlap F1 rewards emitting one enormous window per channel. `tools/score.py` is fixed and is not being patched to close it, so the search carries an operational constraint instead and rejects degenerate configurations. See [`docs/parameter-search.md`](docs/parameter-search.md).
- **Recall went down.** 0.714 → 0.543 on holdout. The F1 gain is entirely precision. A mission-ops team that would rather chase false alarms than miss an event should tune this differently, and the search harness ships so they can.

## License

Apache-2.0 — matching the benchmark it is built on.
