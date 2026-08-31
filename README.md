# Groundtrack

A spacecraft in orbit sends home a steady stream of sensor readings: temperatures,
voltages, valve positions, battery levels. That stream is called **telemetry**, and buried
in it are the early signs of things going wrong. Finding those signs is a real job that
small mission teams do badly, because there is a lot of telemetry and not many people.

I gave that job to **IBM Bob**, an AI coding agent that reads a prompt and writes and edits
code on its own. Bob wrote the fault detector. Then I set the project up so that neither
Bob nor I could be the one who decides whether the result was any good.

Here is how that works. The day before Bob wrote its first line of code, I committed a
grading script and locked it. Of the 81 real NASA telemetry recordings in the benchmark,
26 were set aside for that script alone. Bob never saw those 26 recordings, and Bob was
never allowed to read the grading script. Each time Bob revised the detector, the grader
scored the new version against the recordings Bob had never seen, and the revision was
kept or thrown away on that number alone. Eight rounds ran. The grader kept one of them.

You do not have to take any of that on faith. The whole point of the setup is that a
stranger with a laptop can check it in about a minute, and [the commands are
below](#verify-this-yourself).

Built for the [AI Builders Challenge with IBM
Bob](https://aibuilderschallenge-bobhub.bemyapp.com/), August theme: *Advance Space
Exploration with AI*.

**Live console: [groundtrack-console.vercel.app](https://groundtrack-console.vercel.app)**
There is nothing to sign into and nothing running on a server. The page is a set of
pre-computed files, and every figure on it can be traced back to the telemetry it came
from.

### Contents

- [The problem this is meant to solve](#the-problem-this-is-meant-to-solve)
- [How the experiment is set up](#how-the-experiment-is-set-up)
- [What the numbers say](#what-the-numbers-say)
- [How IBM Bob is used, and what it cost](#how-ibm-bob-is-used-and-what-it-cost)
- [What the loop did, round by round](#what-the-loop-did-round-by-round)
- [The benchmark](#the-benchmark)
- [Quick start](#quick-start)
- [The console](#the-console)
- [Verify this yourself](#verify-this-yourself)
- [Honest limitations](#honest-limitations)

---

## The problem this is meant to solve

Picture a small mission-operations team: a university CubeSat program, or an early
NewSpace startup where "ops" means three or four rotating grad students. At commissioning,
somebody wrote a runbook, a document mapping telemetry signatures to corrective actions.
If this sensor does that, do this.

Almost nobody ever revalidates that runbook against real flight data as new fault modes
turn up. Doing it properly means replaying months of telemetry against the current rules,
finding what the rules miss, and patching the logic. That is unglamorous maintenance work,
and a four-person team juggling theses and a semester will keep putting it off.

Then something goes wrong on orbit, and the person sitting at the console needs an answer
that is immediate, traceable to actual data, and *already validated*. Asking a chatbot at
that moment is not an answer, because nothing has checked whether the chatbot is right.

## How the experiment is set up

Two halves, kept apart on purpose.

**The grader is written outside the loop. The detector is Bob's.**

**The grader.** [`tools/score.py`](tools/score.py) holds the scoring metric, the split
between the data Bob may learn from and the data it may not, and the failure report Bob
gets to read. I wrote it and committed it before the detector existed, and Bob cannot
touch it. The one rule the whole project rests on is that the agent being tested cannot
reach its own grader.

**The detector.** IBM Bob authors 100% of [`engine/`](engine/), including the very first
baseline version. It runs headlessly through `bob run` inside a loop: Bob proposes one
small edit, the grader re-runs, and the harness either commits the change or reverts it.

**Two terms to know before the numbers.** The score is an **F1**, a single value from 0 to
1 that combines two things: how many of the real faults the detector catches (*recall*) and
how many of its alarms turn out to be real (*precision*). Raising one usually costs you the
other, which is why a single combined number is useful. The **held-out split** is the 26
recordings the grader keeps to itself. A detector can always be tuned to look good on data
it has already seen, so the held-out split is what tells you whether it learned anything
that transfers.

**Who found what, stated plainly.** Bob proposed and wrote iterations 1 through 5 with no
help from me, and none of them survived. Three were reverted on score, one was killed
mid-call before it produced anything, and one was discarded unscored because of a bug in
my harness (recorded and corrected in the ledger). The iteration that did survive
implemented two constants that came out of an offline search I ran on my own machine
against the visible split. Bob wrote the code and the reasoning, the search picked the
numbers, and the held-out grader made the call. That division of labour is written into
[`engine/detect.py`](engine/detect.py) itself, in a provenance comment Bob wrote without
being asked, and the full account is in
[`docs/parameter-search.md`](docs/parameter-search.md).

**The plain-English briefs.** A detection on its own is a pair of row numbers. **IBM
Granite** (`granite4:3b`, running locally on this laptop's CPU through Ollama) turns each
one into a short operations brief a tired engineer can act on. All 78 of them were
generated offline and committed, one per detection, with nothing curated or hand-edited.
[`tools/audit_briefs.py`](tools/audit_briefs.py) then traces every number in every brief
back to the telemetry it claims to describe.

Because the grader sits outside the agent's reach, the central claim can be checked in one
command:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u
```

That prints `IBM Bob`, and nothing else. Take Bob out and there is no detector left.

(`engine/README.md` is documentation I wrote, and it does show up under `git log --
engine/`. The claim is about the detector code, so the command is scoped to `engine/*.py`,
which [`engine/README.md`](engine/README.md) says itself.)

### Why bother

Research literature has no shortage of spacecraft anomaly detectors. What a four-person
team lacks is one they can *own*: small enough to read in an afternoon and practical to
re-tune when a new fault mode shows up. A model published in 2018 and never touched again
cannot be re-tuned by the people flying the spacecraft in 2026.

## What the numbers say

Measured on the 26 recordings Bob never saw:

| | Bob's first detector | What ships | |
|---|---|---|---|
| F1 (the gate metric) | 0.266 | **0.623** | higher is better |
| False alarms | 128 | **7** | against 35 real faults to find |
| Alarms that were real | about 1 in 6 | about **3 in 4** | precision 0.163 to 0.731 |
| Real faults caught | 25 of 35 | 19 of 35 | recall 0.714 to 0.543 |

Read the bottom two rows together, because that is the actual trade: six real faults given
up in exchange for 121 fewer false alarms. For a team triaging alerts by hand, that is the
difference between a queue somebody reads and a queue somebody ignores. It is a choice, and
[Honest limitations](#honest-limitations) says so again at the end.

Some other things that are true of the shipped version:

- It runs all 81 recordings without crashing.
- Eight rounds ran: the baseline plus seven revisions. The grader kept exactly one. It
  reverted four on score, and two never reached it at all.
- Tuning stopped on evidence rather than on budget. Across the search space, the score on
  the data Bob could see turned out to be uncorrelated with the score on the data it could
  not, so more tuning had nothing left to buy
  ([`docs/generalisation.md`](docs/generalisation.md)). Roughly 28 of my 40 credits went
  unspent.
- IBM Granite wrote an operator brief for every one of the 78 detections, and every number
  in every brief is checked back against the telemetry.

The [console](#the-console) reads all of this back, and every figure on the page comes out
of the same exported data.

## How IBM Bob is used, and what it cost

Bob is a **development-time** tool here. It never runs when a user loads the page, and the
project exposes no runtime API to it.

| Where | What Bob does |
|---|---|
| [`.bob/skills/anomaly-forge-engineer/`](.bob/skills/anomaly-forge-engineer/SKILL.md) | A real, reusable Bob skill defining the engineer role, its guardrails, and its JSON report format |
| `tools/forge_loop.py` | Invokes `bob run --format json --max-cost 3 --max-turns 12` per iteration, parses the result, and gates it on the held-out metric |
| `engine/` | Every file, authored and re-authored by Bob |
| `results/ledger.jsonl` | Every iteration recorded: `task_id`, cost, turns, score before/after, kept or reverted |

IBM meters Bob in credits called **Bobcoins**, and the trial account came with 40. Spending
is capped per call and tracked per iteration. 12.2 of those 40 coins produced the shipped
engine. The ledger records every run, including the ones that cost money and returned
nothing.

### Where the coins went

Every row below is one `bob run`. The `task_id` is IBM's, shortened to eight characters
here and carried in full in `results/ledger.jsonl`; the cost is what IBM billed; and the
transcript is committed, so each line can be audited against Bob's raw output.

| # | task_id | Coins | What came back | Transcript |
|---|---|---|---|---|
| 0a | `e83ea8ef` | 1.0925 | **Nothing.** Spent the whole 1-coin cap orienting itself before writing any code | `iter0_attempt1.json` |
| 0b | `c7d91d62` | 1.3813 | The baseline detector, from a self-contained prompt. **Kept** | `iter0_attempt2.json` |
| 1 | `206d55d1` | 1.1027 | Minimum window length 5 → 12, reverted | `iter1.json` |
| 2 | `f060abb7` | 1.1033 | Threshold 4.0σ → 4.5σ, reverted | `iter2.json` |
| 3 | *(none returned)* | ≤ 3.0000 | Killed from outside the harness mid-call; no transcript, no task id | none |
| 4 | `c6660c1c` | 1.1373 | An engine edit the harness discarded unscored, wrongly (see below) | `iter4.json` |
| 5 | `f585bfa2` | 1.1367 | Global MAD → rolling local MAD, reverted | `iter5.json` |
| 6 | `e1b96ece` | 1.1144 | Threshold 6.0σ **and** merge gap 150. **Kept, and it is what ships** | `iter6.json` |
| 7 | `9584e6a7` | 1.1555 | Peak test → area test, reverted | `iter7.json` |
| | **billed and known** | **9.2237** | | |
| | **charged against budget** | **12.2237** | iteration 3 counted at its full 3-coin cap | |

The single largest charge is the one with the least to show for it. Iteration 3 returned
no transcript and no task id, and nothing in IBM's local task database matches the call,
so it may never have been billed at all. It is charged here at its full 3-coin cap
anyway, because a budget that guesses in its own favour is not a budget. Iteration 0a is
the same lesson at smaller scale: a whole coin spent reading the repository before writing
a line of code.

The engine that ships cost 1.1144 coins. Everything else was the search that found it, and
roughly 28 of the 40 coins were never spent, for the reason given in
[`docs/generalisation.md`](docs/generalisation.md): further tuning had stopped buying any
held-out score.

Audit any row against IBM's own numbers:

```bash
grep -o '"session_costs":[0-9.]*' results/bob_runs/iter6.json   # 1.114388, matching the ledger
```

## What the loop did, round by round

Seven live iterations ran after the baseline. The gate kept one, reverted four, discarded
one unscored and lost one to an abort. Every round is in the ledger, including the two that
cost coins and produced no code. A rejected round is a hypothesis eliminated at a known
price, and it is recorded as such.

In the table, **dev** is the 56 recordings Bob was allowed to learn from and **holdout** is
the 26 it never saw. Only the holdout column decides anything.

| # | Bob's change | dev F1 | holdout F1 | Verdict |
|---|---|---|---|---|
| 1 | minimum window length 5 → 12 | 0.235 → **0.258** | 0.266 → 0.250 | reverted |
| 2 | detection threshold 4.0σ → 4.5σ | 0.235 → 0.250 | 0.266 → 0.255 | reverted |
| 4 | *(never scored, see below)* | - | - | discarded |
| 5 | global MAD → rolling local MAD | 0.235 → 0.148 | 0.266 → 0.249 | reverted |
| 6 | threshold → 6.0σ **and** merge gap → 150 | 0.235 → 0.608 | 0.266 → **0.623** | **kept** |
| 7 | peak test → **area** test (Σ excursion above 4σ ≥ 40) | 0.608 → **0.702** | 0.623 → 0.615 | reverted |

Iteration 1 shows the whole dynamic in one line. Bob's edit **improved the score on the
data Bob could see** and hurt the score on the data it could not, which is the exact
failure the split exists to catch. Bob diagnosed it correctly and without prompting:
*"recall fell too much on holdout channels whose true positives happen to be short windows
not visible in the dev failure report."*

Iterations 1 and 2 come apart the same way, trading recall for precision roughly one for
one. Iteration 5 comes apart in reverse: a locally estimated scale collapses in flat
stretches, so recall rose on both splits while false alarms more than doubled.

Iteration 6 explains why the earlier attempts could not have worked. The two constants
**interact**, and changing one at a time never finds the pair. Setting 6σ alone loses
recall, because a real anomaly crosses the threshold in several short bursts rather than
one continuous stretch, and a 150-sample merge gap stitches those bursts back into the
single event they physically are. Together they take holdout precision from 0.163 to 0.731,
which is 128 false positives down to 7. The result is fewer windows, each of which
consolidates bursts that the old merge gap left scattered.

The clearest effect of that iteration shows up in the operator's inbox. Run the committed
engine over all 81 channels and it emits **78 windows on 48 channels**. Run the iteration-0
baseline over the same 81 channels and it emits **506 windows on 60 channels**, so the
triage queue is one sixth the size. On the 26 held-out channels, a separate population from
that count, precision went from 0.163 to 0.731 over the same change. That is also the
entire brief set: 78 detections, 78 Granite briefs, nothing curated. At 506, briefing all of
them would have been impossible, and picking a subset would have meant deciding which
detections a reader ever sees.

The change did not reduce the total amount of flagged telemetry. Averaged over all 81
channels, the flagged share went **up**, 13.2% → 15.8%. Windows became longer (mean 120 →
968 samples, median 26 → 134), because a 150-sample merge gap joins bursts that a 50-sample
gap left separate. The engine gained consolidation and precision while flagging slightly
more total volume.

(The console states the same fact as 11.9% → 14.8%. Both are correct and neither is
rounded. The figure here is the mean of the 81 per-channel shares; the console's is every
flagged reading over all 509,555 readings pooled together. Long recordings carry more
weight in the pooled figure, which is why it sits lower.)

That consolidation has a drawback. **9 of the 78 windows cover more than half their
channel, seven of them upwards of 99%**, against 4 of 506 at the baseline. A window
spanning an entire recording tells an operator very little, and it still scores as a true
positive whenever a labelled anomaly happens to fall inside it. This is the metric loophole
documented in [`docs/parameter-search.md`](docs/parameter-search.md), turning up in the
committed engine. It is smaller than the degenerate configurations the search rejected, and
it is above zero.

The obvious question is whether the headline result leans on that loophole, and it does
not. Re-score the held-out channels with every window covering more than half its channel
deleted, and the engine finds **17 of 35** labelled faults instead of 19, at **7 false
positives either way**, for a holdout F1 of **0.576** against 0.623 with them kept. So the
wide windows are not concealing false positives, and the trimmed score still sits well
above the 0.266 baseline. Reproduce it with
[`tools/robustness_check.py`](tools/robustness_check.py), which reads the same exported
detections the console draws and reproduces the committed score exactly when nothing is
dropped.

The parameter pair itself came out of an offline search on the visible split, documented in
[`docs/parameter-search.md`](docs/parameter-search.md). That write-up includes how the
sweep's first result scored **dev F1 0.807** by the cheap trick of emitting a single
1668-sample window per channel covering 39% of the telemetry. The metric is gameable, the
scorer is fixed and cannot be adjusted to close the hole, and the design notes reject that
shortcut explicitly.

Iteration 7 ended the search. Steered by the best of 1440 offline configurations, Bob
replaced the detector's peak test (*did any single sample cross 6σ*) with an area test that
integrates the excursion across the whole window, so a three-sample glitch fails and a
sustained 4.5σ drift passes. It moved dev F1 **0.608 → 0.702**, the largest dev gain of any
iteration the gate reverted, while holdout dropped from 0.623 to 0.615. (Iteration 6 had
moved dev further, 0.235 → 0.608, and was kept.) Bob implemented it faithfully: the ledger's
dev figure matches the offline prediction to six decimal places.

Across all 432 admissible configurations of that sweep, **dev F1 and held-out F1 are
uncorrelated: Pearson +0.007, Spearman -0.001.** 382 of them beat the committed engine on
dev and only 58 beat it on holdout. Filtering by a dev win shifts the odds of a held-out win
from 13.4% to 14.7%, and the configuration that scores highest on dev gets **0.597** on the
held-out channels against 0.623 for what ships. Tuning stopped there, under a rule I had set
in advance, leaving roughly 28 of 40 Bobcoins unspent. The analysis behind it, the
one-window error bar the search harness surfaced, and what all of it implies for this
benchmark are in [`docs/generalisation.md`](docs/generalisation.md).

I also read eight years of follow-up literature for refinements people have proposed since
the original paper, including EWMA residual smoothing, trimmed scale estimation, and
hysteresis thresholding. Tested across the search space, they did almost nothing: the best
candidate improved holdout F1 by **+0.0086**, less than the weight of a single window among
the 35 held-out targets. That negative result, and the published analysis that explains why
it happens, are in [`docs/literature-review.md`](docs/literature-review.md).

Two failures of mine, on the record. During iteration 4 my harness compared the working
tree only *after* the call, mistook files I had saved during execution for Bob's work,
reverted an engine edit that had cost 1.14 coins, and deleted my files along the way. The
ledger carries an appended `correction` entry, the harness now snapshots the tree before
every call, and the spent coins stay logged. Separately, an `aborted` entry with a **null**
cost marks a run killed from outside the harness; IBM bills for calls that were initiated
whether or not a transcript comes back, so that one is charged against the budget at its
full cap.

The cost cap sits at 3 Bobcoins because Day 2 measurements showed that runs hitting
`--max-cost` are billed in full. A cap set below the real cost of an iteration aborts the
run without reducing the charge.

## The benchmark

**Telemanom** is real labelled spacecraft telemetry released by NASA, from the Soil
Moisture Active Passive satellite (SMAP) and the Mars Science Laboratory rover (MSL,
Curiosity). Mission engineers labelled the faults by hand. Apache-2.0.

- 81 channels · 105 expert-labelled anomaly sequences · 62 point, 43 contextual
  (`labeled_anomalies.csv` has 82 rows, but `P-2` is listed twice with identical spacecraft
  and length, so 81 distinct channels have telemetry)
- Split deterministically by channel-id hash into **56 dev / 26 holdout** channels (**70 /
  35** labelled windows), which is what `tools/score.py --json` reports. Both `P-2` rows
  land in `dev`, so the split covers **55 distinct dev recordings**, and that is the figure
  the console shows.
- Bob sees failures from `dev` only. `holdout` decides whether an iteration is kept.

Source: [khundman/telemanom](https://github.com/khundman/telemanom) · Hundman et al.,
*Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding*, KDD
2018.

The metric is window-overlap F1: a labelled anomaly counts as caught if any prediction
overlaps it anywhere.

The original paper reports **F₀.₅ 0.71** (precision 87.5%, recall 80.0%). That is a
different evaluation, and the numbers are not directly comparable: it trains an LSTM per
channel, weights precision higher with an F₀.₅ metric, and scores only inside a window
around each labelled anomaly rather than across the full series. A detailed comparison is
in [`docs/telemanom-paper-comparison.md`](docs/telemanom-paper-comparison.md). This engine
reaches comparable **recall** (0.714 against 0.80) with no per-channel model training at
all, and precision accounts for the rest of the gap.

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
virtualenv and the system Python has none, so a bare `python tools/score.py` dies on the
import, and that is the most common way a first run goes wrong. Running
`tools/fetch_data.py` without `--check` re-downloads the benchmark if `data/` ever goes
missing: about 9 MB, no API key, no account.

## The console

**Deployed and open to anyone:
[groundtrack-console.vercel.app](https://groundtrack-console.vercel.app)**

The console is a web page for looking at what the detector found. Everything on it was
computed once by [`tools/export_console.py`](tools/export_console.py) and written to
`web/public/data/` as JSON files. The deployed page runs no Python, calls no model, and
talks to no backend, so there is nothing that can fail during a demo and nothing to pay for
hosting.

```bash
python tools/export_console.py    # freeze engine output, labels and briefs to JSON
npm --prefix web ci
npm --prefix web run dev          # http://localhost:5273
```

What is on the page:

- **The walkthrough**: eight steps in the middle of the page, running from the first
  detector Bob wrote to the version that shipped. Each step explains in one sentence
  what changed, redraws channel T-1 with that version's alarms, updates the summary bar
  across all 81 channels, updates the counters, and shows whether the gate kept or
  discarded the change. You can play it, pause it, or step through by hand, and autoplay
  stops at the final step.
- **Every version of the detector, re-run**: Four of the seven rounds were reverted upon
  scoring, so their code is no longer in the repository.
  [`tools/variants.py`](tools/variants.py) rebuilds each version from the ledger records.
  The export script writes output only if every rebuilt detector matches the recorded
  precision, recall, and F1 to six decimal places. The rebuilt iteration 0 must also emit
  the exact windows Bob's original file produced in git, and iteration 6 must match the
  current working tree, channel by channel. All of them do.
- **Baseline comparison**: The final walkthrough step places iteration 0 directly under the
  shipped engine on a single axis: one alarm covering both labelled anomalies on T-1, above
  the 88 marks raised by the initial version. That step also notes that the single alarm
  covers 99% of the recording while still counting as correct.
- **Any of the 81 recordings**: Below the walkthrough, selecting a recording shows its
  labelled anomalies and engine alarms drawn on the trace. Clicking an alarm opens its
  Granite brief. Detections on a labelled anomaly are green, false positives are red with
  hatching, and anomalies the engine missed keep their amber column with a dashed red
  border, so the misses stay visible next to the hits.
- **What the numbers leave out**: Three paragraphs on the edge cases: the nine windows
  covering more than half their channel, the total flagged duration rising while alarm
  counts fell, and the shipped engine catching 19 of 35 held-out anomalies against 26
  caught by an earlier rejected round.

All data and in-sentence figures load straight from the exported JSON, so nothing on the
page can drift away from the underlying measurements.

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

The obvious follow-up question, *whether a human quietly tidied the engine afterwards*,
has its own two commands:

```bash
git log --format='%h %an | %cn' -- 'engine/*.py'   # two commits, IBM Bob as both author and committer
git diff 9cc792e -- 'engine/*.py'                  # empty: the shipped engine is byte-for-byte Bob's
```

`9cc792e` is iteration 6, the last time any engine code changed. Nothing has been edited
into it since, by anyone.

And the claim the whole project rests on, that the grader was fixed before the engine
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
repository when it is a missing dependency. The paths are Windows; on macOS or Linux the
same commands read `.venv/bin/python`.

`tools/test_forge_loop.py` covers the gate mechanics. It verifies that edits to
`tools/score.py` register as violations, that reverts restore `engine/` and clean untracked
files left by Bob, that the prompt inlines the engine source while withholding held-out
failures, and that kept iterations list **IBM Bob** as the git author read by the command
above. The suite runs 45 checks and costs zero Bobcoins.

`tools/make_briefs.py --check` takes about a minute. It warms the model, runs the engine,
asks Granite for the first brief again, and diffs the output against the committed file. It
prints `OK ... reproduces exactly` when they match, and the diff itself when they do not.
`--limit N` widens the sample to the first N briefs, in the order they were originally
written, at roughly 50 seconds each.

`tools/audit_briefs.py` checks the briefs against the flight data. It re-derives all 78
detections from the engine and verifies that every number in every brief traces back to
source telemetry, that procedure and subsystem IDs exist in the metadata, and that all
sections are intact. It takes about a minute and needs no Ollama instance running. Treat it
as a linter for data consistency: a human still has to judge whether the sentences
interpret those numbers sensibly.

Raw `bob run` transcripts are committed under `results/bob_runs/`, so each `task_id` and
coin cost in the ledger can be audited against Bob's raw output. Every cost in the table
above matches the `session_costs` field IBM returned in the corresponding transcript, to
six decimal places.

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
command against the same files gives a different answer each time. Local CPU inference does
not produce bit-identical logits from one process to the next, and a single flipped token
rewrites the rest of a paragraph. The diffs are whole sentences reordered and rephrased,
carrying the same telemetry figures with no drift in them.

The third run was the attempted fix, and it failed. `--check` originally walked the briefs
alphabetically while they had been written in engine order, and the two sequences diverge at
the sixth brief; since Ollama reuses cached prefix state between calls, replaying the
original order looked like the explanation. The walk was corrected, which is the right order
to check in anyway, and 2 of 8 reproduced where 1 had before. The ordering was not the
cause.

So `--check` demonstrates exactly one thing: the committed text came out of this model, with
these settings, from this prompt. It says nothing about the other 77 briefs. The check that
does cover all 78 is `tools/audit_briefs.py`, which verifies every number in every brief
against the telemetry instead of against the model, and which is deterministic because it
never calls Granite at all.

### Reproduced from a clean clone

All of that works on the machine it was written on, which proves very little. So on **30
August 2026** the repository was cloned fresh from GitHub into an empty directory, given a
new virtualenv, and put through every command above. Nothing was carried over from the
development machine.

| Command | Result |
|---|---|
| `git clone` + `python -m venv .venv` + `pip install -r requirements.txt` | clean, no build steps, no compiler |
| `git log --format='%an' -- 'engine/*.py' \| sort -u` | `IBM Bob` |
| `git log --format='%h %an \| %cn' -- 'engine/*.py'` | two commits, `IBM Bob` as author and committer of both |
| `git diff 9cc792e -- 'engine/*.py'` | empty |
| `git log --date=short -- tools/score.py` | one commit, `ae0ff42`, 2026-08-22, a day before the engine |
| `tools/fetch_data.py --check` | 164/164 telemetry files, 9.0 MB, `OK - benchmark complete` |
| `tools/test_score.py` | `ruler OK - all metric tests passed` |
| `tools/score.py` | holdout F1 **0.622951**, tp 19 / fp 7 / fn 16, the headline number to six decimals |
| `tools/test_forge_loop.py` | `45 passed, 0 failed` |
| `tools/sweep.py --selftest` | `MATCH`, the search harness reproduces the ruler exactly |
| `tools/variants.py` | all six reconstructions match the ledger |
| `tools/robustness_check.py` | 0.623 as shipped, 0.576 with wide windows deleted, 7 false alarms either way |
| `tools/audit_briefs.py` | 78 briefs, 0 ungrounded numbers |
| `tools/audit_console_numbers.py` | every number on the page traces to the data |
| `tools/export_console.py --check` | console data matches the current engine |
| `tools/make_briefs.py --check` | `A-5_2762-2806.md reproduces exactly from Granite` |
| `npm --prefix web ci && npm --prefix web run build` | 0 vulnerabilities, built in 3.7s |

After all of it, `git status` in that clone was still clean. `plot_progress.py` rewrites
`results/progress.png` and `export_console.py --check` re-derives the console's JSON, and
both come back byte-identical to what is committed, which is the check behind the check.

Two things a fresh clone does **not** need: the benchmark (all 164 telemetry files are
committed, so there is no download step and no network dependency) and an IBM API key
(nothing in the verification path calls Bob, and none of it spends coins). Ollama with
`granite4:3b` is the one external prerequisite, and only for the brief check.

Pip resolved current releases during that run (`pandas` 3.0.5, `numpy` 2.5.2, `pyarrow`
25.0.1) over the versions the engine was written against, and the score came out identical.

## Honest limitations

- **The runbook text is illustrative.** Descriptions are templated from Telemanom's public
  channel metadata and do not constitute certified NASA flight doctrine.
- **The held-out split is small.** It holds 35 labelled windows. F1 scores over a sample
  that size move around easily, so treat large score shifts between iterations with
  suspicion.
- **Granite briefs are pre-generated offline.** Local Ollama inference writes them ahead of
  time. The repository includes the generation script, and `tools/make_briefs.py --check`
  re-prompts the model and diffs the result against the committed file.
- **Regeneration is only reliable for the first brief.** Pinned decoding and a warmed runner
  make the first generation after warm-up reproduce exactly, in every run measured,
  including from a clean clone. Beyond that it is unreliable: three runs of `--check --limit
  8` across two hours reproduced 7 of 8, then 1 of 8, then 2 of 8. Local CPU inference is
  not bit-reproducible across processes, and one flipped token rewrites a paragraph. The
  telemetry figures inside the briefs are stable; the prose around them is not.
  `tools/audit_briefs.py` is the check that covers all 78, and it never calls the model.
- **Every detection gets a brief because the volume is low.** The current engine emits 78
  windows, so all 78 get a brief and nothing has to be curated out. The iteration-0 baseline
  emits 506 windows (corrected from 466 reported in an early draft), the large majority of
  them false alarms, and a brief on each would have meant choosing which ones a reader ever
  sees. Generation is also slow: measured at roughly 50 seconds a brief on this machine, 78
  take about an hour and 506 would take about seven. (An earlier draft of this section said
  25 hours, extrapolated instead of measured. The measurement is above.)
- **Operational user demand is unvalidated.** Small satellite operations teams are a
  plausible audience for this, and nobody from one has looked at it. No external mission
  controller has field-validated any of it.
- **Window-overlap F1 contains a documented metric loophole.** Overlap-based scoring rewards
  emitting broad windows across entire channels. Because `tools/score.py` is immutable, the
  offline parameter search applies an explicit constraint to reject degenerate broad
  windows. The analysis is in [`docs/parameter-search.md`](docs/parameter-search.md).
- **The final engine retains several wide windows.** Nine of its 78 detected windows cover
  more than half of their respective channels, and seven cover over 99%. They count as true
  positives under the metric while telling an operator almost nothing about where the fault
  sits. For comparison, the baseline had 4 wide windows out of 506. Briefs for these wide
  detections stay committed in the repository so all the output remains visible.
- **Recall declined on the holdout split.** Holdout recall dropped from 0.714 to 0.543, and
  the whole F1 improvement comes from higher precision. Operators who would sooner chase
  false alarms than miss anomalies can move the two constants with the included search
  tools.

## License

Apache-2.0, matching the underlying benchmark.
