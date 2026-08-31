# Groundtrack: Master Blueprint

**AI Builders Challenge with IBM Bob · August Challenge (Advance Space Exploration with AI)**

> This document replaces the previous "AetherOps" blueprint, which was discarded after adversarial review. Every fact below was verified against a primary source or by running a command on this machine. Claims that could not be verified are marked UNVERIFIED. Nothing here is aspirational unless labelled as such.

---

## 1. What we are building

**IBM Bob runs headless inside a scored keep-or-discard loop as the sole author of a spacecraft anomaly-detection engine, validated against real labelled NASA telemetry. IBM Granite turns each detection into a plain-language operations brief.**

Deleting Bob's commits removes the engine. Any reviewer can falsify that in under a minute with `git log --author`, and the repository is laid out to keep it true for the whole build.

- **Track**: Advance Space Exploration with AI (August theme)
- **Deadline**: Aug 31 2026, 11:59pm ET (Sep 1, 09:59 Asia/Dhaka)
- **Primary target**: Grand Prize ($5,000), then 1st Place ($2,250), Best Technical Use of IBM Bob ($750)

### Why this concept

Independent agents built four concepts, and three adversarial critics scored them blind: an IBM engineer persona, a delivery-focused engineering manager, and a domain expert. Groundtrack scored consistently across all three.

| Concept | IBM judge | Feasibility | Hostile expert | Mean |
|---|---|---|---|---|
| **Groundtrack** | 16 | **17** | 15 | **16.0** |
| ScopeGuard (spec-drift CI bot) | 16 | 16 | 13 | 15.0 |
| TOI Copilot (TESS vetting) | 13 | 15 | 13 | 13.7 |
| GigSathi (Dhaka gig riders) | 12 | 15 | 14 | 13.7 |

---

## 2. The actual judging rubric

From the official rules. Each judge scores each criterion 1 to 5. **Maximum 20 points.**

| Criterion | Wording |
|---|---|
| Technical Execution | "Effective use of IBM Bob and additional technologies, with a functional and well-structured solution" |
| Innovation | "Creativity, originality, and unique application of AI" |
| Challenge Fit | "Relevance to the challenge and ability to address real-world problems" |
| Implementation & Feasibility | "Practicality, scalability, and potential for real-world use" |

There is no "wow factor" criterion. Feasibility accounts for a full quarter of the total score.

---

## 3. Verified environment facts

### IBM Bob works headless (proven on this machine)

Authentication uses an API key because interactive login hangs on "restoring session...", a known auth-state bug.

```bash
export BOBSHELL_API_KEY=$(python -c "import json;print(json.load(open('competition.json'))['apikey'])")
```

Proven invocation and result:

```
bob run --format json --max-cost 1 --max-turns 1 --trust --accept-license \
        --log-level error --disable-mcp --disable-subagents "Reply with exactly: OK"

{"type":"result","status":"success","stats":{"task_id":"1999be3fab0b5f9980185f3ebff4defc",
 "duration_ms":38463,"session_costs":0.264168,"max_cost":1,"tool_calls":0},"last_message":"OK"}
```

**Measured budget reality from Day 2:**

| Call | Tool calls | Duration | Cost | Produced |
|---|---|---|---|---|
| Day 1 smoke test | 0 | 38s | 0.264 | `OK` |
| Iteration 0, attempt 1 (`--max-cost 1`) | 4 | 37s | **1.092** | **nothing (hit the cost cap)** |
| Iteration 0, attempt 2 (`--max-cost 5`) | 3 | 128s | **1.381** | `detect.py` + `runbook.py`, holdout F1 0.266 |

What this measurement changed:

1. **`--max-cost 1` is counterproductive.** Attempt 1 spent a full coin on orientation reads and directory listings, hit the cap, and produced no code. A capped call is still billed in full, so a cap set below the real iteration cost buys nothing.
2. **Prompt design determines cost efficiency.** Attempt 1 told Bob to read `AGENTS.md` and the skill file to orient itself. Attempt 2 inlined every piece of context it needed and forbade exploratory reads, and it finished the baseline in fewer tool calls at about the same cost. The forge loop now injects the failure report inline so Bob spends its turns editing code.
3. **The 16-20 iteration plan exceeds the budget.** With iterations costing 1.10 to 1.14 coins, planning for 16 to 20 iterations requires 18 to 23 coins plus reserves.

**Realistic ceiling: 12 loop iterations at `--max-cost 3`, plus reserve.** Execution time is also a factor: each call takes 40-130s and each scoring pass reads 81 parquet files in 30-60s.

Verified `bob run` flags in use: `--format json`, `--mode <custom-slug>`, `--max-cost`, `--max-turns`, `--trust`, `--accept-license`, `--disable-mcp`, `--disable-subagents`, `--team-id`, `--workspace`.

### IBM Granite: local Ollama is the only ungated path

| Path | Verdict |
|---|---|
| HF serverless Inference API | Not deployed for Granite |
| HF **Docker** Space + Ollama | **Requires paid PRO** |
| HF **ZeroGPU Gradio** Space | Free constraints: max 2, account age >30 days, Gradio-only, owner 5 min GPU/day, unauthenticated visitors 2 min/day, 60s function cap |
| OpenRouter | Granite is paid-only |
| watsonx.ai Lite | Credit card required for identity verification |
| **Ollama local** | **Free and unmetered.** `granite4:350m` = 708MB/32K ctx · `granite4:3b` (micro) = 2.1GB/128K ctx |

**Mandated design:** Granite briefs are pre-generated offline with local Ollama, committed, and served statically from Vercel.

That buys three things at judging time. Granite still does the generation work and anyone can repeat it, since the generation script ships and `make briefs` rewrites every file. The deployed app has no live dependency, so no cold start, quota, billing card or account gate can break it during a demo. And the README says plainly that the briefs are pre-generated, so nobody has to guess where they came from.

If the Hugging Face account clears the 30-day age requirement, a ZeroGPU live inference button is an optional bonus.

### Machine constraints

Windows 11 · Python 3.12.10 · Node v24.19.0 · **no NVIDIA GPU** · **no Docker** · zero budget · Vercel available.

The bundled `autoresearch/` clone requires an NVIDIA GPU and cannot run on this machine. The iteration loop is built from scratch.

---

## 4. Architecture

```
repo/
  engine/                          <-- 100% BOB-AUTHORED. Never hand-edited.
    detect.py                        rolling z-score / EWMA drift detection
    runbook.py                       maps anomaly signature -> runbook entry
  tools/
    score.py                       <-- HUMAN-WRITTEN. The ruler. Bob never touches it.
    forge_loop.py                    harness: calls bob run, parses JSON, keep/discard gate
    make_briefs.py                   offline Granite brief generation via local Ollama
  .bob/
    skills/anomaly-forge-engineer/SKILL.md    shipped, reusable Bob skill
  data/telemanom/                  labelled NASA SMAP+MSL telemetry
  results/
    ledger.jsonl                   every iteration: task_id, cost, turns, score, keep/discard
    progress.png                   generated FROM ledger.jsonl, never hand-drawn
    briefs/                        Granite-generated ops briefs, committed
  web/                             Vite + React console on Vercel, serves cached data only
    public/data/                   static JSON written by tools/export_console.py; the
                                   deployed page never runs Python, Bob, or Granite
```

**Dev-time loop (Bob):** `forge_loop.py` → `bob run --mode anomaly-forge-engineer -f json` → Bob edits `engine/*.py` → `score.py` runs → improved? commit : revert → append to ledger.

**Runtime (no Bob):** operator selects a telemetry replay window → `engine/detect.py` flags anomalies → matching pre-generated Granite brief displays with its cited runbook entry.

### Integrity rules for authorship

The repository split is what makes attribution checkable:

- The human writes only `tools/score.py`: the metric calculation, the data split definitions, and the test harness.
- Bob writes 100% of `engine/`, including the initial baseline engine in iteration 0.
- `git log --author -- engine/` shows that only Bob authored the detection code.

If engine improvements plateau, the outcome is still checkable, because Bob authored and validated the detection engine on every iteration.

---

## 5. Data

**Telemanom / NASA SMAP + MSL labelled telemetry anomalies**: real spacecraft telemetry from the Soil Moisture Active Passive satellite and Mars Science Laboratory (Curiosity), with expert anomaly labels. Contains 82 channels, 105 labelled anomaly sequences (62 point, 43 contextual), and approximately 496,444 values under Apache-2.0.

- Repo: https://github.com/khundman/telemanom
- Paper: Hundman et al., "Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding," KDD 2018

Runbook text is templated from Telemanom public channel and class metadata in generic flight-rule style. The README says outright that it is illustrative operator-facing guidance and carries no certification.

---

## 6. The autonomous iteration loop

```bash
python tools/forge_loop.py --iterations 8 --max-cost-per-call 1 --max-turns 12
```

Each iteration:
1. `score.py` computes current F1 and lists failing anomaly sequences.
2. `bob run --mode anomaly-forge-engineer --format json --max-cost 1 --max-turns 12 --disable-mcp --disable-subagents --trust --accept-license` executes with injected failure data.
3. Bob edits `engine/detect.py` and `engine/runbook.py`.
4. `score.py` re-evaluates performance on the held-out split.
5. Improved performance leads to `git commit` (Bob author); otherwise `git checkout -- engine/` reverts changes.
6. Record `{task_id, cost, turns, f1_before, f1_after, kept}` in `results/ledger.jsonl`.

A committed script plots `progress.png` straight from `ledger.jsonl`, so anyone can regenerate it without spending a Bobcoin.

**Bobcoin allocation (of 40 total):**

Budgeted by coin totals based on measured execution costs:

| Purpose | Coins | Status |
|---|---|---|
| Iteration 0: Bob authors baseline engine | 2.47 | spent (2 calls, one consumed by cost cap) |
| Day 3: four live loop iterations, all reverted | 4.48 | spent (1.14 spent on harness issue) |
| Day 3: one attempt killed externally, cost unknown | ≤3.00 | assumed spent at cap limit |
| Forge loop main iterations (12 at ~1.14 measured) | ~14 | budgeted |
| Demo capture and debugging reserve | ~6 | budgeted |
| **Hard floor: stop here** | **5 remaining** | |

**Iteration cost parameters:** A standard iteration (read the failure report, edit engine code, re-score, report) costs 1.10 to 1.14 coins, which sharpens the earlier 2-3 coin estimate. The prompt is fully self-contained, so Bob settles at three tool calls and skips exploratory reads. Twelve iterations come to roughly 14 coins.

The main operational risk is harness waste. Of the 4.48 coins spent on Day 3, 1.14 bought no code because the harness verified the working tree at the wrong moment, and a shell timeout killed another run before it wrote a ledger record. Both failure modes are fixed, and both are written down in `results/ledger.jsonl`.

Iterations run in batches of four, and the ledger gets read between batches.

**Budget termination condition:** if the balance drops below 5 coins before 3 kept iterations succeed, stop the loop, commit the current ledger, and proceed with existing results.

---

## 7. Nine-day schedule

Granite integration begins in parallel on Day 2 to avoid scheduling bottlenecks during final testing.

| Day | Deliverable at end of day |
|---|---|
| **1 (Aug 22)** | Repo scaffold; Telemanom data cached; `tools/score.py` written and tested; `.bob/skills/anomaly-forge-engineer/SKILL.md` drafted; **public GitHub repo created and pushed** |
| **2 (Aug 23)** | Bob authors iteration-0 baseline engine (first real `bob run` calls); baseline F1 committed. **In parallel:** Ollama installed, `granite4:3b` pulled, first brief generated locally |
| **3 (Aug 24)** | Done. Forge loop wired end-to-end; four live calls verified JSON parsing, cost caps, guardrails, and revert mechanics. All four reverted; holdout F1 remained at 0.266 |
| **4 (Aug 25)** | Bulk of Forge iterations run; `ledger.jsonl` and `progress.png` committed |
| **5 (Aug 26)** | `make_briefs.py` generates the complete brief set; brief quality reviewed |
| **6 (Aug 27)** | Done. Console built: channel index, telemetry plate with alignment rails, deviation plate with 6-sigma cut-off, Granite brief pane, iteration-0 comparison, and ledger view. Implemented with Vite + React as a static single-page application. Not yet deployed |
| **7 (Aug 28)** | Integration and falsifiability pass (§8). Fresh-clone test: verify that a reviewer can reproduce the score with zero Bobcoins |
| **8 (Aug 29)** | README (problem, approach, impact, Bob usage); 3-minute video recorded |
| **9 (Aug 30-31)** | Buffer; BeMyApp submission ahead of 11:59pm ET deadline |

---

## 8. Falsifiability pass: verification in 60 seconds

Every claim can be checked directly. The README carries a "Verify this yourself" section:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u          # names IBM Bob, nothing else
cat results/ledger.jsonl                                   # every iteration, cost, and outcome
.venv/Scripts/python.exe tools/score.py                    # reproduce the metric, no Bobcoins needed
.venv/Scripts/python.exe tools/make_briefs.py --check      # regenerate a Granite brief and diff it

# Note: `engine/README.md` is human-written documentation and does show up under
# `git log -- engine/`. The claim is about engine/*.py, and it is stated that way
# in engine/README.md itself for full transparency.
```

The interpreter is named by path because `pandas` lives in the virtualenv and the system
Python has none. A bare `python` is the most common way a first run fails for the wrong
reason. The README carries a Bobcoin budget table with the recorded task IDs, and the
whole block was re-run against a clean clone on 30 August 2026.

---

## 9. Known weaknesses, stated plainly

1. **Operational user context is unvalidated.** The target user base, small university CubeSat and NewSpace ops teams, is plausible, and nobody in one has tried the thing.
2. **Runbook text is illustrative** flight-rule material with no certification behind it.
3. **The dataset is small.** 105 labelled sequences is a normal generalisation constraint for this benchmark.
4. **The agent iteration loop pattern is shared across entrants.** What separates Groundtrack is execution rigor and how openly it handles its failures (§10).

---

## 10. Open item: differentiating demo presentation

**Day 3 update: experimental evidence supports leading with real failure handling.**
Iteration 1 raised the engine's minimum window length. Dev F1 went up (0.235 to 0.258) while holdout F1 went down (0.266 to 0.250), so the gate reverted it. The held-out split caught a change that only looked good on the development split, and Bob diagnosed it correctly in its own report. That is real footage of the validation working, and `results/ledger.jsonl` has the record.

Demo options to weigh on Day 5-6:

- Show Bob running an unproductive iteration and the harness reverting it on its own.
- Show detection before and after the loop, with the Granite briefs updating alongside.
- Let the viewer scrub the telemetry with detection overlays drawn against the ground-truth labels.

---

## 11. Submission checklist

- [x] IBM SkillsBuild learning activity
- [ ] IBM Bob as core component (verified in git history)
- [ ] Public GitHub repo with clean structure and `.gitignore`
- [ ] README covering problem, AI approach, impact, and IBM Bob usage
- [ ] Functioning prototype (web console + CLI)
- [ ] Video (maximum 3 minutes)
- [ ] BeMyApp submission before Aug 31, 11:59pm ET

**Security note:** `competition.json` holds a live IBM API key and is gitignored. It must never be committed. Verify with `git check-ignore -v competition.json` before every push.
