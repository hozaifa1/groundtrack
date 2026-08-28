# Groundtrack — Master Blueprint

**AI Builders Challenge with IBM Bob · August Challenge (Advance Space Exploration with AI)**

> This document replaces the previous "AetherOps" blueprint, which was discarded after adversarial review. Every fact below was verified against a primary source or by running a command on this machine. Claims that could not be verified are marked UNVERIFIED. Nothing here is aspirational unless labelled as such.

---

## 1. What we are building

**IBM Bob runs headless, inside a scored keep/discard loop, as the sole author of a spacecraft anomaly-detection engine — validated against real labelled NASA telemetry. IBM Granite turns each detection into a plain-language operations brief.**

Delete Bob's commits and there is no engine. That claim is falsifiable by any judge in under a minute with `git log --author`, and the repo is built so that it stays true.

- **Track**: Advance Space Exploration with AI (August theme)
- **Deadline**: Aug 31 2026, 11:59pm ET (Sep 1, 09:59 Asia/Dhaka)
- **Primary target**: Grand Prize ($5,000), then 1st Place ($2,250), Best Technical Use of IBM Bob ($750)

### Why this concept

Four concepts were built by independent agents and scored blind by three adversarial critics (an IBM engineer persona, a delivery-focused engineering manager, and a hostile domain expert). Groundtrack was the only concept no critic ranked poorly.

| Concept | IBM judge | Feasibility | Hostile expert | Mean |
|---|---|---|---|---|
| **Groundtrack** | 16 | **17** | 15 | **16.0** |
| ScopeGuard (spec-drift CI bot) | 16 | 16 | 13 | 15.0 |
| TOI Copilot (TESS vetting) | 13 | 15 | 13 | 13.7 |
| GigSathi (Dhaka gig riders) | 12 | 15 | 14 | 13.7 |

---

## 2. The actual judging rubric

From the official rules. Each judge scores each criterion 1–5. **Maximum 20 points.**

| Criterion | Wording |
|---|---|
| Technical Execution | "Effective use of IBM Bob and additional technologies, with a functional and well-structured solution" |
| Innovation | "Creativity, originality, and unique application of AI" |
| Challenge Fit | "Relevance to the challenge and ability to address real-world problems" |
| Implementation & Feasibility | "Practicality, scalability, and potential for real-world use" |

There is no "wow factor" criterion. Feasibility is a full quarter of the score. The previous blueprint's 99/100 matrix was invented.

---

## 3. Verified environment facts

### IBM Bob — WORKS HEADLESS (proven on this machine)

Authentication is via API key, not the interactive login (which hangs on "restoring session…", a known auth-state bug).

```bash
export BOBSHELL_API_KEY=$(python -c "import json;print(json.load(open('competition.json'))['apikey'])")
```

Proven invocation and its real result:

```
bob run --format json --max-cost 1 --max-turns 1 --trust --accept-license \
        --log-level error --disable-mcp --disable-subagents "Reply with exactly: OK"

{"type":"result","status":"success","stats":{"task_id":"1999be3fab0b5f9980185f3ebff4defc",
 "duration_ms":38463,"session_costs":0.264168,"max_cost":1,"tool_calls":0},"last_message":"OK"}
```

**Budget reality — measured on Day 2, not estimated:**

| Call | Tool calls | Duration | Cost | Produced |
|---|---|---|---|---|
| Day 1 smoke test | 0 | 38s | 0.264 | `OK` |
| Iteration 0, attempt 1 (`--max-cost 1`) | 4 | 37s | **1.092** | **nothing — hit the cap** |
| Iteration 0, attempt 2 (`--max-cost 5`) | 3 | 128s | **1.381** | `detect.py` + `runbook.py`, holdout F1 0.266 |

Three things this measurement changed:

1. **`--max-cost 1` is actively harmful.** Attempt 1 spent a full coin on orientation reads and a directory listing, hit the cap, and wrote no code. A capped call still costs full price, so a cap set below the true cost of an iteration converts coins into nothing.
2. **Prompt design dominates cost.** Attempt 1 told Bob to go read `AGENTS.md` and the skill file and orient itself. Attempt 2 inlined every fact it needed and explicitly forbade exploratory reads — and finished the whole baseline in *fewer* tool calls for a comparable price. The forge loop must inject the failure report inline, never point Bob at files to fetch.
3. **The 16–20 iteration plan does not fit.** At a realistic 2–3 coins for an iteration that reads a report, edits, and re-scores, 16–20 iterations is 32–60 coins against a 40-coin balance with 2.47 already spent.

**Realistic ceiling: 12 loop iterations at `--max-cost 3`, plus reserve.** Wall clock matters too — each call is 40–130s and each scoring pass reads 81 parquet files in 30–60s.

Verified `bob run` flags in use: `--format json`, `--mode <custom-slug>`, `--max-cost`, `--max-turns`, `--trust`, `--accept-license`, `--disable-mcp`, `--disable-subagents`, `--team-id`, `--workspace`.

### IBM Granite — local Ollama is the only ungated path

| Path | Verdict |
|---|---|
| HF serverless Inference API | Not deployed for Granite |
| HF **Docker** Space + Ollama | **Requires PRO — not free** |
| HF **ZeroGPU Gradio** Space | Free but: max 2, account must be >30 days old, Gradio-only, owner 5 min GPU/day, **unauthenticated visitors 2 min/day**, 60s function cap |
| OpenRouter | Granite is paid-only |
| watsonx.ai Lite | Credit card required for identity verification |
| **Ollama local** | **Unconditionally free.** `granite4:350m` = 708MB/32K ctx · `granite4:3b` (micro) = 2.1GB/128K ctx |

**Mandated design:** Granite briefs are **pre-generated offline with local Ollama**, committed, and served statically from Vercel.

This is not a compromise — it is strictly better for judging:
- Granite genuinely does the work, and it is reproducible (the generation script ships; `make briefs` regenerates).
- The judged experience has **zero live dependencies**. No cold start, no quota, no card, no account gate. It cannot fail on camera.
- The README states plainly that briefs are pre-generated. We never imply live inference that isn't happening.

A ZeroGPU "try it live" button is an optional bonus only, and only if the HF account clears the 30-day age gate.

### Machine constraints

Windows 11 · Python 3.12.10 · Node v24.19.0 · **no NVIDIA GPU** · **no Docker** · zero budget · Vercel available.

The bundled `autoresearch/` clone requires an NVIDIA GPU and **cannot run here**. Our loop is built from scratch.

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

**Runtime (no Bob, ever):** operator picks a telemetry replay window → `engine/detect.py` flags anomalies → matching pre-generated Granite brief is displayed with its cited runbook entry.

### The integrity rule that makes the headline claim true

The previous draft of this concept planned for the human to hand-write a baseline detector on Day 2. That silently destroyed the "delete Bob and there is no engine" claim, because under the concept's own failure mode what shipped would have been substantially human-authored.

**Corrected split:**

- The human writes **only `tools/score.py`** — the metric, the data split, the harness. The ruler.
- **Bob writes 100% of `engine/`**, including the very first baseline, as iteration 0.
- Therefore `git log --author -- engine/` shows only Bob-authored commits, and the claim holds under every outcome.

If the loop plateaus, the claim degrades honestly to "Bob authored and validated this engine" — still true, still git-provable — never to a fabricated improvement curve.

---

## 5. Data

**Telemanom / NASA SMAP + MSL labelled telemetry anomalies** — real spacecraft telemetry from the Soil Moisture Active Passive satellite and Mars Science Laboratory (Curiosity), expert-labelled. 82 channels, 105 labelled anomaly sequences (62 point, 43 contextual), ~496,444 values. Apache-2.0.

- Repo: https://github.com/khundman/telemanom
- Paper: Hundman et al., "Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding," KDD 2018

Runbook text is templated from Telemanom's own public channel/class metadata and phrased in generic flight-rule style. The README states in one sentence that this is **illustrative operator-facing text, not certified NASA operational doctrine** — stated plainly to pre-empt an authenticity challenge rather than waiting to be caught.

---

## 6. The autonomous iteration loop

```bash
python tools/forge_loop.py --iterations 8 --max-cost-per-call 1 --max-turns 12
```

Each iteration:
1. `score.py` computes current F1 and the list of failing anomaly sequences.
2. `bob run --mode anomaly-forge-engineer --format json --max-cost 1 --max-turns 12 --disable-mcp --disable-subagents --trust --accept-license` with the failure list injected.
3. Bob edits `engine/detect.py` and/or `engine/runbook.py`.
4. `score.py` re-runs on the same held-out split.
5. Improved → `git commit` (Bob as author). Not improved → `git checkout -- engine/`.
6. Append `{task_id, cost, turns, f1_before, f1_after, kept}` to `results/ledger.jsonl`.

`progress.png` is plotted directly from `ledger.jsonl` by a committed script. Anyone can regenerate it from the ledger without spending a single Bobcoin.

**Bobcoin allocation (of 40):**

Revised on Day 2 against measured cost. Coins, not calls, because calls are not a fixed price.

| Purpose | Coins | Status |
|---|---|---|
| Iteration 0 — Bob authors the baseline engine | 2.47 | **spent** (2 calls, one wasted on the cost cap) |
| Day 3 — four live loop iterations, all reverted | 4.48 | **spent** (1.14 of it on a harness bug, not on Bob) |
| Day 3 — one attempt killed from outside, cost unknown | ≤3.00 | **assumed spent** at its cap |
| Forge loop main iterations (12 at ~1.14 measured) | ~14 | budgeted |
| Demo capture and debugging reserve | ~6 | budgeted |
| **Hard floor — stop here** | **5 remaining** | |

**Revised again on Day 3 against four measured iterations.** A real iteration — read the
failure report, edit the engine, re-score, report — costs **1.10 to 1.14 coins**, not the
2–3 the Day 2 estimate assumed. The prompt is fully self-contained, so Bob makes exactly
three tool calls every time and never explores. Twelve iterations is roughly 14 coins,
not 24.

The binding constraint is therefore not price, it is waste. Of the 4.48 coins spent on
Day 3, 1.14 bought nothing because the harness misjudged its own working tree, and a
further attempt was lost entirely because a shell timeout killed the run from outside
before any ledger line was written. Both failure modes are now fixed in the harness and
both are recorded in `results/ledger.jsonl` rather than tidied away.

Iterations run in batches of four with the ledger re-read between batches. Twelve queued unattended is how thirty coins disappear with nothing kept.

**Budget kill condition:** if balance drops below 5 coins before 3 kept iterations have landed, stop the loop, ship the ledger as-is, and drop any improvement claim.

---

## 7. Nine-day plan

Granite work starts Day 2 in parallel, not Day 5 — the feasibility critic flagged it as under-budgeted devops squeezed behind three days of loop work.

| Day | Deliverable at end of day |
|---|---|
| **1 (Aug 22)** | Repo scaffold; Telemanom data cached; `tools/score.py` written and tested; `.bob/skills/anomaly-forge-engineer/SKILL.md` drafted; **public GitHub repo created and pushed** |
| **2 (Aug 23)** | Bob authors iteration-0 baseline engine (first real `bob run` calls); baseline F1 committed. **In parallel:** Ollama installed, `granite4:3b` pulled, first brief generated locally |
| **3 (Aug 24)** | ✅ Forge loop wired end-to-end; four live calls verified JSON parsing, cost caps, the guardrail, and the revert gate. All four reverted — holdout F1 unchanged at 0.266. Outreach **drafted, not sent** (`docs/outreach/`) |
| **4 (Aug 25)** | Bulk of Forge iterations run; `ledger.jsonl` + `progress.png` committed |
| **5 (Aug 26)** | `make_briefs.py` generates the full committed brief set; brief quality reviewed by hand |
| **6 (Aug 27)** | ✅ Console built: channel index, telemetry plate with labelled/engine alignment rails, deviation plate with the 6-sigma cut-off, Granite brief pane, iteration-0 comparison, and the ledger view. Stack is **Vite + React**, not Next.js as this blueprint originally said; a static SPA needs no framework server and the line above is corrected rather than left to imply otherwise. Not yet deployed |
| **7 (Aug 28)** | Integration + the falsifiability pass (§8). Fresh-clone test: can a judge reproduce the score with zero Bobcoins? **Outreach follow-up** |
| **8 (Aug 29)** | README (problem / approach / impact / Bob usage); 3-minute video recorded |
| **9 (Aug 30–31)** | Buffer; BeMyApp submission well before 11:59pm ET |

---

## 8. Falsifiability pass — how a skeptical judge verifies us in 60 seconds

Every claim we make must be checkable. The README carries a section titled "Verify this yourself" containing exactly this:

```bash
git log --format='%an' -- 'engine/*.py' | sort -u   # names IBM Bob, nothing else
cat results/ledger.jsonl                       # every iteration, cost, and outcome
python tools/score.py                          # reproduce the metric, no Bobcoins needed
python tools/make_briefs.py --check            # regenerate a Granite brief and diff it

# Note: `engine/README.md` is human-written documentation and does show up under
# `git log -- engine/`. The claim is about engine/*.py, and it is stated that way
# in engine/README.md itself rather than left for a judge to catch.
```

Plus a Bobcoin budget table with real `task_id`s. This packaging was the element the IBM judge said to steal from the strongest concept — we ship it deliberately.

---

## 9. Known weaknesses, stated plainly

We state these ourselves rather than letting a judge find them.

1. **The user is not yet real.** The named beneficiary — small university CubeSat and NewSpace ops teams — is plausible but unvalidated. This is the single biggest gap versus a Grand Prize winner, and cold outreach (§10) is the mitigation.
2. **Runbook text is illustrative**, not certified operational doctrine.
3. **The dataset is small** (105 labelled sequences), inviting a fair generalisation challenge.
4. **The Bob-loop pattern is not unique.** Three of four independently generated concepts converged on "agent edits code → metric gate → commit/revert." We are the best-executed instance of a house style, so we need one demo beat nobody else has (§11).

---

## 10. Cold outreach plan (real-user validation)

No existing contacts in space. All three channels attempted in parallel, starting Day 3.

- University satellite/CubeSat teams and ground-station clubs
- SPARRSO (Bangladesh Space Research and Remote Sensing Organization); BRAC Onnesha CubeSat alumni
- IEEE network and EEE faculty for an introduction into aerospace / remote sensing

**Ask:** 15 minutes to look at a screen recording and answer one question — "would this have saved you time?" A single named person on record is worth a full rubric point on Implementation & Feasibility. Anything less, and we drop all claims implying operator validation.

---

## 11. Open item — the differentiating demo beat

**Day 3 update: the evidence now points at the first candidate, and it arrived unstaged.**
Iteration 1 raised the engine's minimum window length. Dev F1 went *up* (0.235 → 0.258),
holdout F1 went *down* (0.266 → 0.250), and the gate reverted it — the held-out split
catching a change that looked like an improvement on the only data the agent could see.
Bob diagnosed it correctly in its own report without being prompted to. That is ten
seconds of footage no entrant showing a rising curve can match, and it is already in
`results/ledger.jsonl`. Lead with it unless Day 4 produces something stronger, and do not
re-shoot it.

Needed: one thing in the 3-minute video no other entrant will have. Candidates to test on Day 5–6, decided by evidence, not preference:

- Show Bob **failing** an iteration and the harness reverting it — honesty as the differentiator; nobody shows their agent losing.
- Show the same anomaly before and after the loop, with the Granite brief changing accordingly.
- Let the judge scrub a live telemetry replay and watch detections appear against ground-truth labels.

---

## 12. Submission checklist

- [x] IBM SkillsBuild learning activity
- [ ] IBM Bob as core component — evidenced, not asserted
- [ ] Public GitHub repo with clean architecture and `.gitignore`
- [ ] README: problem / AI approach / why it matters / IBM Bob usage
- [ ] Functioning prototype (web console + CLI)
- [ ] Video, max 3 minutes
- [ ] BeMyApp submission before Aug 31, 11:59pm ET

**Security note:** `competition.json` holds a live IBM API key and is now gitignored. It must never be committed. Verify with `git check-ignore -v competition.json` before every push.
