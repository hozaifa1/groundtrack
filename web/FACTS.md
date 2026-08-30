# Verified facts for console copy — DO NOT INVENT ANYTHING NOT ON THIS LIST

Every number below is derived from `web/public/data/manifest.json` or
`results/ledger.jsonl` and was recomputed on 2026-08-29. If a number is not on
this list, it does not go on the page.

## The headline result (holdout = 26 recordings IBM Bob never saw)

| Measure | First detector | Shipped detector |
|---|---|---|
| Benchmark score (F1) | 0.266 | 0.623  (2.3x) |
| False alarms | 128 | 7  (94.5% fewer) |
| Real faults found | 25 of 35 | 19 of 35 |
| Share of alarms that were real | 0.163 (~1 in 6) | 0.731 (~3 in 4) |

Across all 81 recordings: alarms 506 -> 78.
Dev-split score (55 recordings): 0.235 -> 0.608.

**The trade, stated honestly:** the shipped detector finds 6 fewer of the 35
marked faults, and in exchange nearly eliminates false alarms. The fixed grader
scored that trade as a large net win. Do not hide this; state it plainly once.

## IBM Bob

- Authored **100% of `engine/`**: 445 lines across `detect.py` (179) and
  `runbook.py` (266), including the original baseline. No human edits, ever.
- Verifiable on any clone: `git log --format='%an' -- 'engine/*.py' | sort -u`
  prints `IBM Bob` and nothing else.
- Ran headlessly via `bob run --format json --max-cost 3 --max-turns 12`,
  driven by `tools/forge_loop.py`.
- Uses a real reusable Bob skill: `.bob/skills/anomaly-forge-engineer/SKILL.md`.
- **12.2 Bobcoins spent of a 40-coin budget** across 10 ledger rows, 8 of which
  returned a task id.
- 8 versions of the detector exist: the baseline plus 7 revisions.
  1 revision passed the grader. 4 were reverted on score. 2 rounds produced
  nothing gradeable (one timed out; one was wrongly blamed on Bob by the
  harness and corrected in the ledger).

## IBM Granite

- `granite4:3b`, run locally through Ollama.
- Wrote an operator brief for **all 78 detections**, one each, no hand-curation.
- Decoding is pinned and `tools/make_briefs.py --check` re-prompts the model and
  diffs the result against what is committed. Measured on 2026-08-30: the first
  brief reproduces exactly in every run, including from a clean clone; briefs
  after it do not reproduce reliably (three runs of `--limit 8` across two
  hours gave 7 of 8, then 1 of 8, then 2 of 8). Do NOT write
  "byte-for-byte" or any claim that all 78 regenerate. Roughly 50s per brief.
- What does cover all 78 is `tools/audit_briefs.py`: every number in every brief
  traced back to the telemetry, no model call involved. 0 ungrounded numbers.

## The benchmark

- NASA telemetry: SMAP (Soil Moisture Active Passive satellite) and MSL
  (Curiosity rover). Faults labelled by mission engineers.
- 81 recordings, 509,555 readings total.
- 55 recordings available during development, 26 held out.
- `tools/score.py` was written and committed **before the engine existed** and
  IBM Bob cannot modify it. That is the core integrity claim.
- The detector runs on all 81 recordings and crashes on none.

## Caveats that must remain somewhere on the page

- 9 of the 78 alarms span more than half their recording; 7 cover nearly all of
  it. They count as correct because a real fault falls inside.
- Share of readings inside an alarm rose 11.9% -> 14.8% (merging bursts into
  single blocks).
- 16 of 35 marked faults on the hidden recordings are still missed.

## Forbidden

- No number not listed above.
- Never call the project or its outcome a failure.
- "F1", "holdout", "precision", "recall", "sigma", "z-score", "split" must not
  appear above the fold, and must be glossed in plain words if used at all.

## Robustness check (added after the console review, verified 2026-08-29)

Re-scored with every alarm covering more than half its recording deleted, so a
reader can see whether the result leans on the wide-window loophole. Reproduce
with `.venv/Scripts/python.exe tools/robustness_check.py`.

| Held-out recordings | Faults found | False alarms | Score |
|---|---|---|---|
| As shipped | 19 of 35 | 7 | 0.623 |
| Widest alarms deleted | 17 of 35 | 7 | 0.576 |

**False alarms stay at 7 either way.** The wide windows are not concealing false
positives, and the score stays far above the 0.266 baseline. Use this to answer
the wide-alarm caveat rather than leaving the doubt open.

## Verified terminal output (real, do not paraphrase into a terminal box)

`$ tools/make_briefs.py --check` actually prints:

    Granite model: granite4:3b
    warming up the runner (required for reproducible output)
    OK - A-5_2762-2806.md reproduces exactly from Granite.
