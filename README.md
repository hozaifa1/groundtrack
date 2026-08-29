# Groundtrack

**IBM Bob writes the spacecraft anomaly detector. A fixed benchmark decides whether it was any good.**

Built for the [AI Builders Challenge with IBM Bob](https://aibuilderschallenge-bobhub.bemyapp.com/) (August theme: *Advance Space Exploration with AI*).

> **Status: in active development (Day 6 of 9).** Bob has authored every line of the engine. It scores **holdout F1 0.623** (precision 0.731, recall 0.543) across 26 held-out channels, up from an iteration-0 baseline of 0.266, and crashes on none of the 81. Seven forge iterations have run: one was kept and the gate reverted or discarded the rest. Score work has now been **stopped on evidence**: in the search space, dev F1 and held-out F1 turn out to be uncorrelated ([`docs/generalisation.md`](docs/generalisation.md)). IBM Granite runs locally and has written an operator brief for **every one of the 78 detections** the engine emits; they regenerate byte-for-byte. A static [console](#the-console) reads all of it back: the telemetry, the labelled anomalies, the engine's calls, the briefs, the ledger, and iteration 0 re-executed out of git for comparison.

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
- **Provenance is stated directly.** Bob proposed and wrote iterations 1-5 unaided; all five were reverted by the gate. The kept iteration implemented two constants found by an offline dev-split search run on the developer's machine. Bob wrote the code and the reasoning; the search chose the numbers; the held-out gate decided. That division of labour is recorded in [`engine/detect.py`](engine/detect.py) itself (Bob wrote the provenance comment above the constants unprompted) and detailed in [`docs/parameter-search.md`](docs/parameter-search.md).
- **IBM Granite** (`granite4:3b`, run locally through Ollama) turns a detection into a plain-language operations brief, generated offline and committed to the repo: all **78** of them, one per detection, without manual curation. Decoding is pinned so the briefs regenerate byte-for-byte; `tools/make_briefs.py --check` re-prompts Granite and diffs the output against what is committed.

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

Bobcoin spend is capped per call and tracked per iteration. The ledger logs failed experiments as failures without dropping runs. For instance, the very first ledger entry records a run that hit its cost cap and produced no code.

## What the loop has actually done

Seven live iterations ran after the baseline: one was kept, four were reverted by the gate, one was discarded unscored, and one was aborted. The ledger records all of them, including the two that cost coins and produced no code:

| # | Bob's change | dev F1 | holdout F1 | Verdict |
|---|---|---|---|---|
| 1 | minimum window length 5 → 12 | 0.235 → **0.258** | 0.266 → 0.250 | reverted |
| 2 | detection threshold 4.0σ → 4.5σ | 0.235 → 0.250 | 0.266 → 0.255 | reverted |
| 4 | *(never scored, see below)* | - | - | discarded |
| 5 | global MAD → rolling local MAD | 0.235 → 0.148 | 0.266 → 0.249 | reverted |
| 6 | threshold → 6.0σ **and** merge gap → 150 | 0.235 → 0.608 | 0.266 → **0.623** | **kept** |
| 7 | peak test → **area** test (Σ excursion above 4σ ≥ 40) | 0.608 → **0.702** | 0.623 → 0.615 | reverted |

Iteration 1 shows the dynamic clearly. Bob's edit **improved the score on the data Bob could see** and hurt the held-out score (the exact failure the split exists to catch). Bob reported it accurately without prompting: *"recall fell too much on holdout channels whose true positives happen to be short windows not visible in the dev failure report."*

Iterations 1 and 2 fail the same way, trading recall for precision roughly one for one. Iteration 5 fails in reverse: a locally estimated scale collapses in flat stretches, so recall rose on both splits while false alarms more than doubled.

Iteration 6 explains why earlier attempts failed. The two constants **interact**, and one-at-a-time search cannot find the pair. Setting 6σ alone loses recall because a real anomaly crosses the threshold in several short bursts, and a 150-sample merge gap reconstitutes those bursts into the single event they physically represent. Together they take holdout precision from 0.163 to 0.731 (128 false positives down to 7). Fewer windows result, each consolidating bursts the old merge gap left scattered.

The clearest effect of that iteration shows up in the operator's inbox. Run the committed engine over all 81 channels and it emits **78 windows on 48 channels**. Run the iteration-0 baseline over the same 81 channels and it emits **506 windows on 60 channels**: one sixth as many items to triage. On the 26 held-out channels (a separate population from that count), precision went from 0.163 to 0.731 over the same change. That is the entire brief set: 78 detections, 78 Granite briefs, without curation. At 506, showing all of them would be impossible, and selecting a subset would decide which failures the reader sees.

The change did not reduce total flagged telemetry. Averaged over all 81 channels, the flagged share went **up**, 13.2% → 15.8%. Windows became longer (mean 120 → 968 samples, median 26 → 134), as a 150-sample merge gap joins bursts that a 50-sample gap left separate. The engine gained consolidation and precision while flagging slightly more total volume.

This consolidation has a drawback: **9 of the 78 windows cover more than half their channel, seven of them upwards of 99%**, compared to 4 of 506 at the baseline. A window spanning an entire channel tells an operator very little, yet still scores as a true positive whenever a labelled anomaly falls inside it. This is the metric loophole documented in [`docs/parameter-search.md`](docs/parameter-search.md) appearing in the committed engine. It is smaller than the degenerate configurations rejected during the search, but remains non-zero.

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
- Split deterministically by channel-id hash into **56 dev / 26 holdout** channels (**70 / 35** labelled windows)
- Bob sees failures from `dev` only. `holdout` decides whether an iteration is kept.

Source: [khundman/telemanom](https://github.com/khundman/telemanom) · Hundman et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD 2018.

The metric is window-overlap F1: a labelled anomaly counts as caught if any prediction overlaps it.

The paper reports **F₀.₅ 0.71** (precision 87.5%, recall 80.0%). That evaluation uses a different setup: an LSTM trained per channel, an F₀.₅ metric weighting precision higher, and scoring restricted to a window around each labelled anomaly instead of evaluating across the full series. A detailed comparison is in [`docs/telemanom-paper-comparison.md`](docs/telemanom-paper-comparison.md). Our engine achieves comparable **recall** (0.714 vs 0.80) without training a channel-specific model, while precision accounts for the remaining gap.

## Quick start

```bash
python -m venv .venv && ./.venv/Scripts/activate    # Windows
pip install -r requirements.txt

python tools/fetch_data.py        # ~9 MB, no API key, no account
python tools/test_score.py        # validate the ruler
python tools/score.py             # grade the current engine
```

`pandas` must come from the virtualenv. If `python` on your PATH points to the
system interpreter, run the venv binary directly (`.venv/Scripts/python.exe tools/score.py`
on Windows) so the scorer does not fail on a missing import.

## The console

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

Every claim in this repository can be checked directly. None of these commands spend Bobcoins.

```bash
git log --format='%an' -- 'engine/*.py' | sort -u   # names IBM Bob, nothing else
cat results/ledger.jsonl                            # every iteration, cost, outcome
.venv/Scripts/python.exe tools/plot_progress.py      # redraws results/progress.png from that ledger
python tools/score.py                               # reproduce the headline metric
python tools/test_score.py                          # validate the ruler itself
python tools/test_forge_loop.py                     # validate the harness that keeps/reverts
python tools/fetch_data.py --check                  # confirm the benchmark is intact
python tools/make_briefs.py --check                 # regenerate a Granite brief, diff it
.venv/Scripts/python.exe tools/audit_briefs.py      # check all 78 briefs against the telemetry
.venv/Scripts/python.exe tools/variants.py          # re-run every version of the detector, check each against the ledger
python tools/export_console.py --check              # confirm the console shows the current engine
```

`tools/test_forge_loop.py` covers the gate mechanics. It verifies that edits to `tools/score.py` register as violations, that reverts restore `engine/` and clean untracked files left by Bob, that the prompt inlines the engine source while withholding held-out failures, and that kept iterations list **IBM Bob** as the git author read by the command above. The suite runs 45 checks and costs zero Bobcoins.

Running `python tools/make_briefs.py --check` takes about three minutes. It warms the model, runs the engine, requests the brief from Granite again, and diffs the output against the committed file. The run prints `OK ... reproduces exactly` when outputs match. A diff indicates that generated text changed.

`tools/audit_briefs.py` validates brief contents against flight data. The audit re-derives all 78 detections from the engine, verifying that every number in every brief traces to source telemetry, that procedure and subsystem IDs exist in metadata, and that all sections remain intact. Running the script takes about a minute and requires no Ollama instance. This check functions as a linter for data consistency; human reviewers still evaluate whether the written sentences interpret the numbers accurately.

Raw `bob run` transcripts are committed under `results/bob_runs/`, so each `task_id` and coin cost recorded in the ledger can be audited directly against Bob's raw output.

## Honest limitations

Documented caveats and project boundaries:

- **The runbook text is illustrative.** Descriptions are templated from Telemanom's public channel metadata and do not constitute certified NASA flight doctrine.
- **The held-out split is small.** The set contains 35 labelled windows. F1 scores over a sample of this size fluctuate easily, so large score shifts between iterations warrant skepticism.
- **Granite briefs are pre-generated offline.** Briefs are created ahead of time using local Ollama inference. The repository includes the generation script, and running `python tools/make_briefs.py --check` regenerates the files to verify that they match committed text.
- **Every detection receives a brief because volume is low.** The current engine emits 78 windows, allowing all 78 to be briefed without selective curation. The iteration-0 baseline emits 506 windows (corrected from 466 reported in an early draft). Briefing 506 detections would have required roughly 25 hours of single-threaded CPU inference, mostly processing false alarms, which would have forced manual filtering.
- **Operational user demand is unvalidated.** Small satellite operations teams represent a plausible target audience, but direct field validation with external mission controllers has not been conducted.
- **An offline search found the winning configuration.** Bob proposed and implemented iterations 1 to 5 autonomously, but the automated gate reverted all five. The single accepted iteration implemented two threshold values identified by an offline search on the development split. While Bob authored the code and internal reasoning, the project makes no claim that the model found the winning configuration autonomously.
- **Window-overlap F1 contains a documented metric loophole.** Overlap-based scoring inherently rewards emitting broad windows across entire channels. Because `tools/score.py` is immutable, the offline parameter search applies an explicit constraint to reject degenerate broad windows. Detailed analysis is in [`docs/parameter-search.md`](docs/parameter-search.md).
- **The final engine retains several wide windows.** Nine of its 78 detected windows cover more than half of their respective channels, and seven cover over 99%. These detections count as true positives under the metric while providing minimal localization detail for operators. For comparison, the baseline had 4 wide windows out of 506. Briefs for these wide detections remain committed in the repository so all outputs stay visible.
- **Recall declined on the holdout split.** Holdout recall dropped from 0.714 to 0.543, with overall F1 improvement driven entirely by higher precision. Operators who prefer investigating false alarms over risking missed anomalies can adjust these parameters using the included search tools.

## License

Apache-2.0, matching the underlying benchmark.
