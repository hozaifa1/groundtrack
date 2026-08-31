# Groundtrack

**IBM Bob writes the spacecraft anomaly detector. A grader it cannot reach decides whether the work was any good.**

Built for the [AI Builders Challenge with IBM Bob](https://aibuilderschallenge-bobhub.bemyapp.com/) (August theme: *Advance Space Exploration with AI*).

**Live console → [groundtrack-console.vercel.app](https://groundtrack-console.vercel.app)** · no sign-in, no backend, every figure on the page traced back to the telemetry it came from.

> **Result.** IBM Bob wrote every line of the detector. Measured on 26 recordings Bob never saw, it takes the benchmark score from **0.266 to 0.623** and cuts false alarms from **128 to 7**, so roughly three in four alarms are now real where before it was one in six. It runs all 81 recordings without crashing. Eight rounds ran: the baseline plus seven revisions, of which the fixed grader kept exactly one — four it reverted on score, and two never reached it at all. That is the guardrail doing its job. Optimisation was then **stopped on evidence**: across the search space, the score on data Bob could see turns out to be uncorrelated with the score on data it could not ([`docs/generalisation.md`](docs/generalisation.md)). IBM Granite runs locally and has written an operator brief for **every one of the 78 detections**, and every number in every one of them is checked back against the telemetry it came from. A static [console](#the-console) reads all of it back.

---

## The problem

A small mission-operations team, like a university CubeSat program or an early NewSpace startup where "ops" is three or four rotating grad students, inherits an anomaly-response runbook written once at commissioning. It maps telemetry signatures to corrective actions.

It is almost never revalidated against real flight data as new fault modes appear. Doing that requires replaying months of telemetry against current rules, finding misses, and patching the logic. That is unglamorous maintenance work, and a four-person team with theses and a semester will keep deferring it.

Then an anomaly hits, and the person on console needs an answer that is instant, cited, and *already validated*, without relying on an unverified chatbot.

## The approach

Groundtrack splits the problem in two, and the split is the point.

**The ruler is written outside the loop. The engine is Bob's.**

- [`tools/score.py`](tools/score.py) (the metric, data split, and failure reporting) is authored outside the forge loop and committed before the engine exists. Bob cannot touch it. The core requirement is that the agent under test cannot reach its own grader.
- **IBM Bob authors 100% of [`engine/`](engine/)** (including the initial baseline), running headlessly through `bob run` inside a scored keep/discard loop. Bob proposes one minimal edit, the scorer re-runs, and the harness commits the change or reverts it.
- **Provenance is stated directly.** Bob proposed and wrote iterations 1 to 5 unaided, and none of them survived: three were reverted on score, one was killed mid-call before it produced anything, and one was discarded unscored by a harness bug (recorded and corrected in the ledger). The kept iteration implemented two constants found by an offline dev-split search run on the developer's machine. Bob wrote the code and the reasoning; the search chose the numbers; the held-out gate decided. That division of labour is recorded in [`engine/detect.py`](engine/detect.py) itself (Bob wrote the provenance comment above the constants unprompted) and detailed in [`docs/parameter-search.md`](docs/parameter-search.md).
- **IBM Granite** (`granite4:3b`, run locally through Ollama) turns a detection into a plain-language operations brief, generated offline and committed to the repo: all **78** of them, one per detection, without manual curation. Decoding is pinned and `tools/make_briefs.py --check` re-prompts Granite and diffs the result, which holds for the first brief and does not hold reliably beyond it — [measured, and written up below](#about-that-byte-for-byte-claim). What does cover all 78 is [`tools/audit_briefs.py`](tools/audit_briefs.py), which traces every number in every brief back to the telemetry.

Because the grader sits outside the agent's reach, the central claim is directly verifiable:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u
```

That names `IBM Bob`, and nothing else. Remove Bob, and there is no detector.

(`engine/README.md` is human-written documentation and appears under `git log -- engine/`. The claim concerns the engine, so the command is scoped to `engine/*.py`, as [`engine/README.md`](engine/README.md) explicitly states.)

## Why it matters

Anomaly detectors for spacecraft telemetry are abundant in research literature. What is missing is a detector a four-person team can *own*: one small enough to read, practical to re-tune when a new fault mode appears, and transparent about its reasoning.

Groundtrack demonstrates that an agentic SDLC tool can maintain this kind of detector continuously against a fixed benchmark, recording every decision, rather than relying on a static model published in 2018.

## IBM Bob usage

Bob operates as a **development-time** tool and never runs in a runtime request path. It provides no runtime API.

| Where | What Bob does |
|---|---|
| [`.bob/skills/anomaly-forge-engineer/`](.bob/skills/anomaly-forge-engineer/SKILL.md) | A real, reusable Bob skill defining the engineer role, its guardrails, and its JSON report format |
| `tools/forge_loop.py` | Invokes `bob run --format json --max-cost 3 --max-turns 12` per iteration, parses the result, and gates it on the held-out metric |
| `engine/` | Every file, authored and re-authored by Bob |
| `results/ledger.jsonl` | Every iteration recorded: `task_id`, cost, turns, score before/after, kept or reverted |

Bobcoin spend is capped per call and tracked per iteration, and **12.2 of the 40 available coins** produced the shipped engine. The ledger records every run, including the ones that cost money and returned nothing.

### Where the coins went

Every row below is one `bob run`. The `task_id` is IBM's, shortened to eight characters
here and carried in full in `results/ledger.jsonl`; the cost is what IBM billed; and the
transcript is committed, so each line can be audited against Bob's raw output rather than
taken on trust.

| # | task_id | Coins | What came back | Transcript |
|---|---|---|---|---|
| 0a | `e83ea8ef` | 1.0925 | **Nothing.** Spent the whole 1-coin cap orienting itself before writing any code | `iter0_attempt1.json` |
| 0b | `c7d91d62` | 1.3813 | The baseline detector, from a self-contained prompt — **kept** | `iter0_attempt2.json` |
| 1 | `206d55d1` | 1.1027 | Minimum window length 5 → 12 — reverted | `iter1.json` |
| 2 | `f060abb7` | 1.1033 | Threshold 4.0σ → 4.5σ — reverted | `iter2.json` |
| 3 | *(none returned)* | ≤ 3.0000 | Killed from outside the harness mid-call; no transcript, no task id | — |
| 4 | `c6660c1c` | 1.1373 | An engine edit the harness discarded unscored, wrongly (see below) | `iter4.json` |
| 5 | `f585bfa2` | 1.1367 | Global MAD → rolling local MAD — reverted | `iter5.json` |
| 6 | `e1b96ece` | 1.1144 | Threshold 6.0σ **and** merge gap 150 — **kept, and it is what ships** | `iter6.json` |
| 7 | `9584e6a7` | 1.1555 | Peak test → area test — reverted | `iter7.json` |
| | **billed and known** | **9.2237** | | |
| | **charged against budget** | **12.2237** | iteration 3 counted at its full 3-coin cap rather than guessed at zero | |

The single largest charge is the one with the least to show for it. Iteration 3 returned
no transcript and no task id, and nothing in IBM's local task database matches the call,
so it may never have been billed at all — it is charged here at its full 3-coin cap
anyway, because a budget that guesses in its own favour is not a budget. Iteration 0a is
the same lesson at smaller scale: a whole coin spent reading the repository before writing
a line of code.

The engine that ships cost 1.1144 coins. Everything else was the search that found it, and
roughly 28 of the 40 coins were never spent, for the reason given in
[`docs/generalisation.md`](docs/generalisation.md): further optimisation had stopped buying
held-out score.

Audit any row against IBM's own numbers:

```bash
grep -o '"session_costs":[0-9.]*' results/bob_runs/iter6.json   # 1.114388, matching the ledger
```

## What the loop did, round by round

Seven live iterations ran after the baseline. The gate kept one, reverted four, discarded one unscored and lost one to an abort. Every round is in the ledger, including the two that cost coins and produced no code. A rejected round is a hypothesis eliminated at a known price, and it is recorded as such:

| # | Bob's change | dev F1 | holdout F1 | Verdict |
|---|---|---|---|---|
| 1 | minimum window length 5 → 12 | 0.235 → **0.258** | 0.266 → 0.250 | reverted |
| 2 | detection threshold 4.0σ → 4.5σ | 0.235 → 0.250 | 0.266 → 0.255 | reverted |
| 4 | *(never scored, see below)* | - | - | discarded |
| 5 | global MAD → rolling local MAD | 0.235 → 0.148 | 0.266 → 0.249 | reverted |
| 6 | threshold → 6.0σ **and** merge gap → 150 | 0.235 → 0.608 | 0.266 → **0.623** | **kept** |
| 7 | peak test → **area** test (Σ excursion above 4σ ≥ 40) | 0.608 → **0.702** | 0.623 → 0.615 | reverted |

Iteration 1 shows the dynamic clearly. Bob's edit **improved the score on the data Bob could see** and hurt the held-out score (the exact failure the split exists to catch). Bob reported it accurately without prompting: *"recall fell too much on holdout channels whose true positives happen to be short windows not visible in the dev failure report."*

Iterations 1 and 2 come apart the same way, trading recall for precision roughly one for one. Iteration 5 comes apart in reverse: a locally estimated scale collapses in flat stretches, so recall rose on both splits while false alarms more than doubled.

Iteration 6 explains why the earlier attempts could not have worked. The two constants **interact**, and one-at-a-time search cannot find the pair. Setting 6σ alone loses recall because a real anomaly crosses the threshold in several short bursts, and a 150-sample merge gap reconstitutes those bursts into the single event they physically represent. Together they take holdout precision from 0.163 to 0.731 (128 false positives down to 7). Fewer windows result, each consolidating bursts the old merge gap left scattered.

The clearest effect of that iteration shows up in the operator's inbox. Run the committed engine over all 81 channels and it emits **78 windows on 48 channels**. Run the iteration-0 baseline over the same 81 channels and it emits **506 windows on 60 channels**: one sixth as many items to triage. On the 26 held-out channels (a separate population from that count), precision went from 0.163 to 0.731 over the same change. That is the entire brief set: 78 detections, 78 Granite briefs, without curation. At 506, showing all of them would be impossible, and selecting a subset would decide which detections the reader sees.

The change did not reduce total flagged telemetry. Averaged over all 81 channels, the flagged share went **up**, 13.2% → 15.8%. Windows became longer (mean 120 → 968 samples, median 26 → 134), as a 150-sample merge gap joins bursts that a 50-sample gap left separate. The engine gained consolidation and precision while flagging slightly more total volume.

(The console states the same fact as 11.9% → 14.8%. Both are correct and neither is rounded: this figure is the mean of the 81 per-channel shares, the console's is every flagged reading over all 509,555 readings pooled. Long recordings carry more weight in the pooled figure, which is why it sits lower.)

This consolidation has a drawback: **9 of the 78 windows cover more than half their channel, seven of them upwards of 99%**, compared to 4 of 506 at the baseline. A window spanning an entire channel tells an operator very little, yet still scores as a true positive whenever a labelled anomaly falls inside it. This is the metric loophole documented in [`docs/parameter-search.md`](docs/parameter-search.md) appearing in the committed engine. It is smaller than the degenerate configurations rejected during the search, but remains non-zero.

The obvious question is whether the headline result leans on that loophole, and it does not. Re-score the held-out channels with every window covering more than half its channel deleted and the engine finds **17 of 35** labelled faults instead of 19, at **7 false positives either way**, for holdout F1 **0.576** against 0.623 with them kept. The wide windows are not hiding false positives, and the trimmed score still sits well above the 0.266 baseline. Reproduce it with [`tools/robustness_check.py`](tools/robustness_check.py), which reads the same exported detections the console draws and reproduces the committed score exactly when nothing is dropped.

An offline dev-split search found that parameter pair, as documented in [`docs/parameter-search.md`](docs/parameter-search.md), including how the sweep first scored **dev F1 0.807** by emitting a single 1668-sample window per channel covering 39% of the telemetry. The metric is gameable, the scorer is fixed, and that shortcut was explicitly rejected in the design notes.

Iteration 7 ended the search. Steered by the best of 1440 offline configurations, Bob replaced the detector's peak test (*did any sample cross 6σ*) with an area test that integrates excursion over the whole window, so a three-sample glitch fails and a sustained 4.5σ drift passes. It moved dev F1 **0.608 → 0.702** (the largest dev gain of any iteration the gate reverted) while holdout dropped from 0.623 to 0.615. (Iteration 6 had moved dev further, 0.235 → 0.608, and was kept.) Bob implemented it faithfully: the ledger's dev figure matches the offline prediction to six decimal places.

Across all 432 admissible configurations of that sweep, **dev F1 and held-out F1 are uncorrelated: Pearson +0.007, Spearman -0.001.** While 382 of them beat the committed engine on dev, only 58 beat it on holdout. Filtering by a dev win shifts the odds of a held-out win from 13.4% to 14.7%, and the dev argmax configuration scores **0.597** on held-out channels compared to 0.623 for the committed engine. Optimization stopped there under a rule set in advance, leaving roughly 28 of 40 Bobcoins unspent. The underlying analysis, the one-window error bar identified in the search harness, and the implications for this benchmark are in [`docs/generalisation.md`](docs/generalisation.md).

A review of eight years of follow-up literature identified common proposed refinements, including EWMA residual smoothing, trimmed scale estimation, and hysteresis thresholding. Testing these across the search space showed little effect: the best candidate improved holdout F1 by **+0.0086**, which is smaller than the weight of a single window among the 35 held-out targets. That negative result and the published analysis explaining why it occurred are documented in [`docs/literature-review.md`](docs/literature-review.md).

During Iteration 4, a harness issue caused a lost update. The harness compared the working tree only *after* the call, mistook operator files saved during execution for Bob's work, reverted an engine edit that had cost 1.14 coins, and deleted the operator's files. The ledger records this with an appended `correction` entry, and the harness now snapshots the tree before every call. The spent coins remain logged.

An `aborted` entry with a **null** cost reflects a run terminated from outside the harness. Because IBM bills for initiated calls regardless of transcript return, this run is charged against the budget at its full cap.

The cost cap was set to 3 Bobcoins after Day 2 measurements showed that runs hitting `--max-cost` are billed in full. Setting the cap lower than the actual cost of an iteration risks aborting runs without reducing charges.

## The benchmark

**Telemanom**: real labelled spacecraft telemetry from NASA's Soil Moisture Active Passive satellite (SMAP) and the Mars Science Laboratory rover (MSL). Apache-2.0.

- 81 channels · 105 expert-labelled anomaly sequences · 62 point, 43 contextual
  (`labeled_anomalies.csv` has 82 rows, but `P-2` is listed twice with identical spacecraft and length, so 81 distinct channels have telemetry)
- Split deterministically by channel-id hash into **56 dev / 26 holdout** channels (**70 / 35** labelled windows), which is what `tools/score.py --json` reports. Both `P-2` rows land in `dev`, so the split covers **55 distinct dev recordings**, and that is the figure the console shows.
- Bob sees failures from `dev` only. `holdout` decides whether an iteration is kept.

Source: [khundman/telemanom](https://github.com/khundman/telemanom) · Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD 2018.

The metric is window-overlap F1: a labelled anomaly counts as caught if any prediction overlaps it.

The paper reports **F₀.₅ 0.71** (precision 87.5%, recall 80.0%). That evaluation uses a different setup: an LSTM trained per channel, an F₀.₅ metric weighting precision higher, and scoring restricted to a window around each labelled anomaly instead of evaluating across the full series. A detailed comparison is in [`docs/telemanom-paper-comparison.md`](docs/telemanom-paper-comparison.md). Our engine achieves comparable **recall** (0.714 vs 0.80) without training a channel-specific model, while precision accounts for the remaining gap.

## Quick start

The benchmark is committed to the repository, so a clone needs nothing but Python 3.10+
and a virtualenv. These are the exact commands a fresh clone was verified against:

```bash
git clone https://github.com/hozaifa1/groundtrack.git
cd groundtrack

python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt    # Windows
# .venv/bin/python -m pip install -r requirements.txt          # macOS / Linux

.venv/Scripts/python.exe tools/fetch_data.py --check    # 164 telemetry files, intact
.venv/Scripts/python.exe tools/test_score.py            # validate the ruler
.venv/Scripts/python.exe tools/score.py                 # grade the current engine
```

Call the virtualenv interpreter by path instead of activating it. `pandas` lives in the
virtualenv and not in the system Python, so a bare `python tools/score.py` fails on the
import, and that is the most common way a first run goes wrong. Running
`tools/fetch_data.py` without `--check` re-downloads the benchmark if `data/` ever goes
missing: ~9 MB, no API key, no account.

## The console

**Deployed and open to anyone: [groundtrack-console.vercel.app](https://groundtrack-console.vercel.app)**

The web console is a static interface for reviewing detector output. Everything
it displays was computed once by [`tools/export_console.py`](tools/export_console.py)
and written to `web/public/data/` as JSON. The deployed page runs no Python, calls
no model, and has no backend, so it cannot fail during a demo and costs nothing to host.

```bash
python tools/export_console.py    # freeze engine output, labels and briefs to JSON
npm --prefix web ci
npm --prefix web run dev          # http://localhost:5273
```

The interface includes:

- **The walkthrough**: Positioned at the center of the page, eight steps advance
  from the first detector Bob wrote to the version that shipped. Each step explains
  in one sentence what changed, redraws channel T-1 with that version's alarms,
  updates the summary bar across all 81 channels, updates the counters, and shows
  whether the gate kept or discarded the change. Controls allow playing, pausing,
  and stepping manually; autoplay stops at the final step.
- **Every version of the detector, re-run**: Four of the seven rounds were
  reverted upon scoring, so their code is no longer in the repository.
  [`tools/variants.py`](tools/variants.py) rebuilds each version from the ledger
  records. The export script writes output only if every rebuilt detector matches
  the recorded precision, recall, and F1 to six decimal places. The rebuilt
  iteration 0 must also emit the exact windows Bob's original file produced in
  git, and iteration 6 must match the current working tree, channel by channel.
  All of them do.
- **Baseline comparison**: The final walkthrough step places iteration 0 directly
  under the shipped engine on a single axis: one alarm covering both labelled
  anomalies on T-1, above the 88 marks raised by the initial version. That step
  notes that the single alarm covers 99% of the recording while still counting
  as correct.
- **Any of the 81 recordings**: Below the walkthrough, selecting a recording shows
  its labelled anomalies and engine alarms drawn on the trace. Clicking an alarm
  opens its Granite brief. Detections on a labelled anomaly are green, false
  positives are red with hatching, and uncaught anomalies keep their amber column
  with a dashed red border. Uncaught anomalies remain visible alongside hits.
- **What the numbers leave out**: Three paragraphs document edge cases: the nine
  windows covering more than half their channel, the total flagged duration rising
  while alarm counts fell, and the shipped engine catching 19 of 35 held-out
  anomalies compared to 26 caught by an earlier rejected round.

All data and in-sentence figures load directly from the exported JSON, so numbers
on the page cannot drift from underlying measurements.

Design notes are in [`web/DESIGN.md`](web/DESIGN.md).

## Verify this yourself

Every claim in this repository can be checked directly. None of these commands spend
Bobcoins, and every one of them was run against a clean clone on 30 August 2026 (see
[Reproduced from a clean clone](#reproduced-from-a-clean-clone) below for the outputs).

The four that matter most, in the order a sceptic would want them:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u        # names IBM Bob, nothing else
cat results/ledger.jsonl                                 # every iteration, cost, outcome
.venv/Scripts/python.exe tools/score.py                  # reproduce the headline metric
.venv/Scripts/python.exe tools/make_briefs.py --check    # regenerate a Granite brief, diff it
```

The obvious follow-up question — *whether a human quietly tidied the engine afterwards* —
has its own two commands:

```bash
git log --format='%h %an | %cn' -- 'engine/*.py'   # two commits, IBM Bob as both author and committer
git diff 9cc792e -- 'engine/*.py'                  # empty: the shipped engine is byte-for-byte Bob's
```

`9cc792e` is iteration 6, the last time any engine code changed. Nothing has been edited
into it since, by anyone.

And the claim the whole project rests on — that the ruler was fixed before the engine
existed and never moved:

```bash
git log --format='%h %ad %an' --date=short -- tools/score.py
```

One commit, `ae0ff42`, dated **2026-08-22**, the day before Bob's first engine commit on
**2026-08-23**. The metric has not been touched since, in any direction, by Bob or by
anyone else.

And the rest of the audit trail:

```bash
.venv/Scripts/python.exe tools/test_score.py             # validate the ruler itself
.venv/Scripts/python.exe tools/test_forge_loop.py        # validate the harness that keeps/reverts
.venv/Scripts/python.exe tools/fetch_data.py --check     # confirm the benchmark is intact
.venv/Scripts/python.exe tools/sweep.py --selftest       # the search harness reproduces the ruler
.venv/Scripts/python.exe tools/variants.py               # re-run every version of the detector, check each against the ledger
.venv/Scripts/python.exe tools/robustness_check.py       # re-score with the widest windows deleted
.venv/Scripts/python.exe tools/audit_briefs.py           # check all 78 briefs against the telemetry
.venv/Scripts/python.exe tools/audit_console_numbers.py  # check every number the console prints
.venv/Scripts/python.exe tools/export_console.py --check # confirm the console shows the current engine
.venv/Scripts/python.exe tools/plot_progress.py          # redraw results/progress.png from the ledger
```

Every line names the virtualenv interpreter on purpose. A bare `python` on this machine,
and on a fresh clone, has no `pandas`, and the resulting `ImportError` looks like a broken
repository rather than a missing dependency. The paths are Windows; on macOS or Linux the
same commands read `.venv/bin/python`.

`tools/test_forge_loop.py` covers the gate mechanics. It verifies that edits to `tools/score.py` register as violations, that reverts restore `engine/` and clean untracked files left by Bob, that the prompt inlines the engine source while withholding held-out failures, and that kept iterations list **IBM Bob** as the git author read by the command above. The suite runs 45 checks and costs zero Bobcoins.

`tools/make_briefs.py --check` takes about a minute. It warms the model, runs the engine, asks Granite for the first brief again, and diffs the output against the committed file. It prints `OK ... reproduces exactly` when they match, and the diff itself when they do not. `--limit N` widens the sample to the first N briefs, in the order they were originally written, at roughly 50 seconds each.

`tools/audit_briefs.py` validates brief contents against flight data. The audit re-derives all 78 detections from the engine, verifying that every number in every brief traces to source telemetry, that procedure and subsystem IDs exist in metadata, and that all sections remain intact. Running the script takes about a minute and requires no Ollama instance. This check functions as a linter for data consistency; human reviewers still evaluate whether the written sentences interpret the numbers accurately.

Raw `bob run` transcripts are committed under `results/bob_runs/`, so each `task_id` and coin cost recorded in the ledger can be audited directly against Bob's raw output. Every cost in the table above matches the `session_costs` field IBM returned in the corresponding transcript, to six decimal places.

### About that byte-for-byte claim

Earlier drafts of this README said the briefs regenerate byte-for-byte. The Day 7
falsifiability pass measured it, and that claim was too strong. What the measurements
actually show:

| Run | Result |
|---|---|
| `--check` (one brief), five separate runs including one from a clean clone | reproduced exactly, every time |
| `--check --limit 2` | 2 of 2 reproduced |
| `--check --limit 8`, three runs across two hours | 7 of 8, then 1 of 8, then 2 of 8 |

Decoding is pinned and the runner is warmed before the first call, and that is enough to
make the **first** generation after warm-up reproduce reliably. It is not enough for the
ones after it, and the spread across those three runs is the whole finding: the same
command against the same files gives a different answer each time. Local CPU inference
does not produce bit-identical logits from one process to the next, and a single flipped
token rewrites the rest of a paragraph — the diffs are whole sentences reordered and
rephrased, carrying the same telemetry figures, not drifting numbers.

The third run was the attempted fix, and it failed. `--check` originally walked the briefs
alphabetically while they had been written in engine order, and the two sequences diverge
at the sixth brief; since Ollama reuses cached prefix state between calls, replaying the
original order looked like the explanation. The walk was corrected — it is worth doing
anyway — and 2 of 8 reproduced instead of 1. The ordering was not the cause.

So `--check` demonstrates exactly one thing: the committed text came out of this model,
with these settings, from this prompt. It is not evidence about the other 77 briefs.
The check that does cover all 78 is `tools/audit_briefs.py`, which verifies every number
in every brief against the telemetry rather than against the model, and which is
deterministic because it never calls Granite at all.

### Reproduced from a clean clone

All of that works on the machine it was written on, which proves very little. So on
**30 August 2026** the repository was cloned fresh from GitHub into an empty directory,
given a new virtualenv, and put through every command above. Nothing was carried over from
the development machine.

| Command | Result |
|---|---|
| `git clone` + `python -m venv .venv` + `pip install -r requirements.txt` | clean, no build steps, no compiler |
| `git log --format='%an' -- 'engine/*.py' \| sort -u` | `IBM Bob` |
| `git log --format='%h %an \| %cn' -- 'engine/*.py'` | two commits, `IBM Bob` as author and committer of both |
| `git diff 9cc792e -- 'engine/*.py'` | empty |
| `git log --date=short -- tools/score.py` | one commit, `ae0ff42`, 2026-08-22 — a day before the engine |
| `tools/fetch_data.py --check` | 164/164 telemetry files, 9.0 MB, `OK - benchmark complete` |
| `tools/test_score.py` | `ruler OK - all metric tests passed` |
| `tools/score.py` | holdout F1 **0.622951**, tp 19 / fp 7 / fn 16 — the headline number, to six decimals |
| `tools/test_forge_loop.py` | `45 passed, 0 failed` |
| `tools/sweep.py --selftest` | `MATCH` — the search harness reproduces the ruler exactly |
| `tools/variants.py` | all six reconstructions match the ledger |
| `tools/robustness_check.py` | 0.623 as shipped, 0.576 with wide windows deleted, 7 false alarms either way |
| `tools/audit_briefs.py` | 78 briefs, 0 ungrounded numbers |
| `tools/audit_console_numbers.py` | every number on the page traces to the data |
| `tools/export_console.py --check` | console data matches the current engine |
| `tools/make_briefs.py --check` | `A-5_2762-2806.md reproduces exactly from Granite` |
| `npm --prefix web ci && npm --prefix web run build` | 0 vulnerabilities, built in 3.7s |

After all of it, `git status` in that clone was still clean. `plot_progress.py` rewrites
`results/progress.png` and `export_console.py --check` re-derives the console's JSON, and
both come back byte-identical to what is committed — which is the check behind the check.

Two things a fresh clone does **not** need: the benchmark (all 164 telemetry files are
committed, so there is no download step and no network dependency) and an IBM API key
(nothing in the verification path calls Bob, and none of it spends coins). Ollama with
`granite4:3b` is the one external prerequisite, and only for the brief check.

Pip resolved current releases during that run — `pandas` 3.0.5, `numpy` 2.5.2,
`pyarrow` 25.0.1 — rather than the versions the engine was written against, and the score
came out identical.

## Honest limitations

Documented caveats and project boundaries:

- **The runbook text is illustrative.** Descriptions are templated from Telemanom's public channel metadata and do not constitute certified NASA flight doctrine.
- **The held-out split is small.** The set contains 35 labelled windows. F1 scores over a sample of this size fluctuate easily, so large score shifts between iterations warrant skepticism.
- **Granite briefs are pre-generated offline.** Briefs are created ahead of time using local Ollama inference. The repository includes the generation script, and `tools/make_briefs.py --check` re-prompts the model and diffs the result against the committed file.
- **Regeneration is only reliable for the first brief.** Pinned decoding and a warmed runner make the first generation after warm-up reproduce exactly, in every run measured, including from a clean clone. Beyond that it is unreliable: three runs of `--check --limit 8` across two hours reproduced 7 of 8, then 1 of 8, then 2 of 8. Local CPU inference is not bit-reproducible across processes, and one flipped token rewrites a paragraph. The telemetry figures inside the briefs are stable; the prose around them is not. `tools/audit_briefs.py` is the check that covers all 78, and it never calls the model.
- **Every detection receives a brief because volume is low.** The current engine emits 78 windows, allowing all 78 to be briefed without selective curation. The iteration-0 baseline emits 506 windows (corrected from 466 reported in an early draft), the large majority of them false alarms, and a brief on each would have meant choosing which ones a reader ever sees. Generation is also slow: measured at roughly 50 seconds a brief on this machine, 78 take about an hour and 506 would take about seven. (An earlier draft of this section said 25 hours, extrapolated rather than measured. The measurement is above.)
- **Operational user demand is unvalidated.** Small satellite operations teams represent a plausible target audience, but direct field validation with external mission controllers has not been conducted.
- **An offline search found the winning configuration.** Bob proposed and implemented iterations 1 to 5 autonomously, and none of them shipped: the gate reverted three on score, one run was killed mid-call, and one was discarded unscored by a harness bug. The single accepted iteration implemented two threshold values identified by an offline search on the development split. While Bob authored the code and internal reasoning, the project makes no claim that the model found the winning configuration autonomously.
- **Window-overlap F1 contains a documented metric loophole.** Overlap-based scoring inherently rewards emitting broad windows across entire channels. Because `tools/score.py` is immutable, the offline parameter search applies an explicit constraint to reject degenerate broad windows. Detailed analysis is in [`docs/parameter-search.md`](docs/parameter-search.md).
- **The final engine retains several wide windows.** Nine of its 78 detected windows cover more than half of their respective channels, and seven cover over 99%. These detections count as true positives under the metric while providing minimal localization detail for operators. For comparison, the baseline had 4 wide windows out of 506. Briefs for these wide detections remain committed in the repository so all outputs stay visible.
- **Recall declined on the holdout split.** Holdout recall dropped from 0.714 to 0.543, with overall F1 improvement driven entirely by higher precision. Operators who prefer investigating false alarms over risking missed anomalies can adjust these parameters using the included search tools.

## License

Apache-2.0, matching the underlying benchmark.
