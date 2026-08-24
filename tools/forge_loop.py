"""The forge loop - the harness that lets IBM Bob author `engine/`, and grades it.

One iteration is:

    1. score      run the fixed ruler, get holdout F1 (the gate) and the dev failures
    2. prompt     build a self-contained brief: metrics, dev failure digest, engine source
    3. bob run    headless, JSON output, hard cost and turn caps
    4. guard      check Bob edited only `engine/`; anything else is a violation
    5. score      run the ruler again
    6. gate       holdout F1 improved -> commit as `IBM Bob`; otherwise revert
    7. ledger     append the outcome either way, including the failures

This file is outside the loop. Bob never edits it, and it never edits `engine/`. The
only things it writes into the repo are a commit of Bob's own work and a line in
`results/ledger.jsonl`.

Three decisions here are consequences of measurements taken on Day 2, not preferences:

* `--max-cost 3`, not 1. A run that hits its cap is still billed in full. Day 2's
  first attempt burned 1.09 coins against a 1-coin cap and produced no code at all.
  A cap set below the true cost of an iteration does not save coins, it destroys them.
* The prompt inlines everything - the failure report *and* the current engine source -
  and forbids exploratory reads. Day 2's cheap, successful run made three tool calls;
  the expensive, empty one made four, all of them orientation.
* Every scorer invocation uses the virtualenv interpreter. Bare `python` on this
  machine has no pandas and would fail on the import rather than on the metric.

Usage
-----
    .venv/Scripts/python.exe tools/forge_loop.py --iterations 1
    .venv/Scripts/python.exe tools/forge_loop.py --iterations 1 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_PY = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
LEDGER = REPO_ROOT / "results" / "ledger.jsonl"
RUNS_DIR = REPO_ROOT / "results" / "bob_runs"
ENGINE_DIR = REPO_ROOT / "engine"

# Paths Bob is allowed to change. Anything else in the diff is a guardrail violation
# and the whole iteration is discarded, improved score or not.
ALLOWED_PREFIXES = ("engine/",)

# Total Bobcoin grant for the competition trial.
TOTAL_BUDGET = 40.0

BOB_AUTHOR_NAME = "IBM Bob"
BOB_AUTHOR_EMAIL = "bob@ibm.invalid"


# --------------------------------------------------------------------------
# shell helpers
# --------------------------------------------------------------------------


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, **kw)


def git(*args: str) -> str:
    proc = run(["git", *args])
    if proc.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + " failed:\n" + proc.stderr.strip())
    return proc.stdout


def api_key() -> str:
    """Read the IBM API key from the gitignored competition.json.

    Never printed, never logged, never written into a ledger entry or a commit
    message. It goes into the child process environment and nowhere else.
    """
    path = REPO_ROOT / "competition.json"
    if not path.exists():
        sys.exit("competition.json not found. It holds the IBM API key and is gitignored.")
    return json.loads(path.read_text(encoding="utf-8"))["apikey"]


def bob_command() -> list[str]:
    """How to launch Bob, as an argv prefix.

    Two Windows facts, both learned the expensive way:

    * npm installs the CLI as `bob.CMD`. `subprocess` without a shell resolves only
      `.exe`, so a bare "bob" raises FileNotFoundError from Python while working in
      every terminal. `shutil.which` applies PATHEXT and finds the real file.
    * Going *through* that `.CMD` shim means going through `cmd.exe`, whose command
      line caps at 8191 characters. This harness deliberately inlines the engine
      source into the prompt, which puts it around 12000 — so the first live call
      died in 102ms with "The command line is too long" and cost nothing but time.
      The shim is a three-line wrapper around `node .../bobshell/dist/bob.js`, and
      calling that script directly raises the ceiling to the 32767 of CreateProcess.

    Falls back to the shim when the script cannot be located, so a differently
    packaged install still runs — just with the shorter limit.
    """
    shim = shutil.which("bob")
    if not shim:
        sys.exit("The `bob` CLI is not on PATH. Install it before running the forge loop.")
    if Path(shim).suffix.lower() in (".cmd", ".bat"):
        script = Path(shim).parent / "node_modules" / "bobshell" / "dist" / "bob.js"
        node = shutil.which("node")
        if script.exists() and node:
            return [node, str(script)]
    return [shim]


# The prompt has to fit whatever launcher we ended up with, and it is built before
# we know how big it got. Checked explicitly rather than discovered as a 102ms crash.
CMD_LINE_LIMIT = 32000


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------


def score_now() -> dict:
    """One full scoring pass: metrics for both splits plus every failure."""
    proc = run([str(VENV_PY), "tools/score_report.py"])
    if proc.returncode == 2 or not proc.stdout.strip():
        detail = (proc.stdout + proc.stderr).strip()[-800:]
        return {
            "error": "engine_unavailable",
            "detail": detail,
            "f1": 0.0,
            "splits": {},
            "failures": {"dev": [], "holdout": []},
        }
    return json.loads(proc.stdout)


def failure_digest(result: dict, max_channels: int = 12, max_missed: int = 14) -> str:
    """Turn the dev failure list into something worth paying tokens for.

    A flat sample of 268 false alarms tells Bob almost nothing. What is actionable is
    *where* they cluster (which channels produce them in bulk) and *what shape* they
    are - a spray of 5-sample windows is a different bug from a handful of 800-sample
    ones. Misses are listed individually because there are few of them and each one
    carries a class label worth reading.

    Holdout failures are deliberately excluded. Bob sees the holdout aggregate so it
    can report honestly; it never sees which held-out channel it got wrong.
    """
    dev = result["failures"]["dev"]
    false_alarms = [f for f in dev if f["kind"] == "false_alarm"]
    missed = [f for f in dev if f["kind"] == "missed"]
    crashes = [f for f in dev if f["kind"] == "engine_crash"]

    lines: list[str] = []

    per_chan: dict[str, int] = {}
    for f in false_alarms:
        per_chan[f["channel"]] = per_chan.get(f["channel"], 0) + 1
    worst = sorted(per_chan.items(), key=lambda kv: -kv[1])[:max_channels]

    lines.append(
        "FALSE ALARMS - {n} on dev, across {c} channels.".format(
            n=len(false_alarms), c=len(per_chan)
        )
    )
    if worst:
        lines.append(
            "  Worst offenders (top {k} of {c} channels):".format(k=len(worst), c=len(per_chan))
        )
        for chan, count in worst:
            lines.append("    {0:<6} {1:>3} false alarms".format(chan, count))
    if false_alarms:
        lens = sorted((f["window"][1] - f["window"][0] + 1) for f in false_alarms)
        deciles = statistics.quantiles(lens, n=10) if len(lens) >= 10 else [lens[0], lens[-1]]
        lines.append(
            "  Window lengths: min={0} p10={1} median={2} p90={3} max={4}".format(
                lens[0], int(deciles[0]), int(statistics.median(lens)),
                int(deciles[-1]), lens[-1],
            )
        )
        short = sum(1 for length in lens if length <= 10)
        lines.append(
            "  {0} of {1} false alarms are <= 10 samples long ({2:.0f}%).".format(
                short, len(lens), 100.0 * short / len(lens)
            )
        )

    lines.append("")
    lines.append(
        "MISSED - {n} labelled anomalies on dev that no prediction overlapped.".format(
            n=len(missed)
        )
    )
    for f in missed[:max_missed]:
        start, end = f["window"]
        lines.append(
            "    {0:<6} window [{1}, {2}] len={3:<5} class={4:<11} channel_len={5}".format(
                f["channel"], start, end, end - start + 1, f.get("class", "?"), f["n"]
            )
        )
    if len(missed) > max_missed:
        lines.append("    ... and {0} more".format(len(missed) - max_missed))

    if crashes:
        lines.append("")
        lines.append(
            "CRASHES - {n} channels the engine threw on. Fix these first.".format(n=len(crashes))
        )
        for f in crashes[:5]:
            lines.append("    {0:<6} {1}".format(f["channel"], f["detail"]))

    return "\n".join(lines)


# --------------------------------------------------------------------------
# the prompt
# --------------------------------------------------------------------------


PROMPT_TEMPLATE = """\
You are the sole author of `engine/` in a spacecraft anomaly-detection repository.
Everything you need is inlined below, including the current source of the file you
are editing. Do NOT read files. Do NOT list directories. Do NOT search the repo.
Exploration is billed and produces nothing: a previous run spent its entire budget
on orientation reads and wrote no code at all.

Make ONE minimal, explainable edit. Verify once. Report.

## Where the engine stands

           precision  recall      F1      tp     fp     fn
  dev         {dev_p:.3f}      {dev_r:.3f}   {dev_f1:.3f}   {dev_tp:>4}   {dev_fp:>4}   {dev_fn:>4}
  holdout     {ho_p:.3f}      {ho_r:.3f}   {ho_f1:.3f}   {ho_tp:>4}   {ho_fp:>4}   {ho_fn:>4}   <- THE GATE

The gate is holdout F1: {ho_f1:.6f}. Your edit is committed only if that number rises.
The held-out channels are hidden from you by design, so a change that works only by
memorising dev will be reverted. Aim for a rule that is true of telemetry in general.

{steer}

## Dev-split failure report

This is the only failure information you are allowed to see.

{digest}

## Current `engine/detect.py` - verbatim, do not open the file

```python
{detect_src}
```

`engine/runbook.py` also exists. It turns a detected window into an operator runbook
entry and does not affect the score. Leave it alone unless your change genuinely
requires it.

## What to do

1. Name ONE failure mode from the report above. One, not five.
2. Make the smallest edit to `engine/detect.py` that plausibly fixes it. Prefer
   retuning a named constant, or adding one explicit, well-commented rule, over
   rewriting the module. A small change the next iteration can build on is worth
   more here than a large one that scores the same.
3. Explain in a comment or docstring *why* the rule exists. A mission-ops engineer
   has to read this file and see why it fired.

## Hard rules

- Edit ONLY `engine/detect.py` and, if truly necessary, `engine/runbook.py`.
- NEVER edit `tools/score.py`. It is the ruler that grades you. Editing it to raise
  your own score is the one unforgivable failure in this repo; the harness diffs the
  working tree after you finish and discards the entire iteration if you touched it.
- Never read `data/telemanom/labeled_anomalies.csv`. Detection runs on telemetry
  alone. Only the scorer sees ground truth.
- Standard library, `numpy`, `pandas` only. Do not add a dependency.
- No per-channel hardcoding. Never name a channel id in code.
- Deterministic: same input, same output. No unseeded randomness.
- Must not crash on short, constant, or zero-variance channels. A crash scores zero.

## Verify - exactly once

```bash
{venv_py} tools/score.py
```

It reads 81 telemetry files and takes 30-60 seconds. That is normal, not a hang.
It prints a line beginning `GATE METRIC`. Read the number off that line.

## Report

The last thing you output must be this JSON object, with nothing after it:

```json
{{"target_failure":"...","hypothesis":"...","change":"...",
  "files_touched":["engine/detect.py"],
  "f1_before":{ho_f1:.6f},"f1_after":<the GATE METRIC actually printed>,
  "generalises":"dev F1 ... / holdout F1 ..."}}
```

Report the number the scorer printed. If it went down, say so - the harness will
revert the edit and record the attempt, and a logged failed experiment is a useful
result. A fabricated one poisons the ledger and the project's central claim with it.
"""


DEFAULT_STEER = """\
## Where to aim this iteration

Recall is already the strong half. Precision is the weak half and it is what holds
the F1 down: the engine flags far more windows than there are anomalies. Raising
precision without giving back the recall you already have is the work.
"""


def build_prompt(result: dict, steer: str) -> str:
    dev = result["splits"]["dev"]
    ho = result["splits"]["holdout"]
    return PROMPT_TEMPLATE.format(
        dev_p=dev["precision"], dev_r=dev["recall"], dev_f1=dev["f1"],
        dev_tp=dev["tp"], dev_fp=dev["fp"], dev_fn=dev["fn"],
        ho_p=ho["precision"], ho_r=ho["recall"], ho_f1=ho["f1"],
        ho_tp=ho["tp"], ho_fp=ho["fp"], ho_fn=ho["fn"],
        steer=steer.strip(),
        digest=failure_digest(result),
        detect_src=(ENGINE_DIR / "detect.py").read_text(encoding="utf-8").rstrip(),
        venv_py=".venv/Scripts/python.exe",
    )


# --------------------------------------------------------------------------
# bob
# --------------------------------------------------------------------------


def run_bob(prompt: str, max_cost: float, max_turns: int, tag: str) -> dict:
    """Invoke Bob headless and return the parsed JSON result.

    The transcript is written to `results/bob_runs/` before anything is parsed, so a
    malformed or truncated response is still auditable rather than lost.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / (tag + ".prompt.md")).write_text(prompt, encoding="utf-8")

    env = dict(os.environ)
    env["BOBSHELL_API_KEY"] = api_key()

    launcher = bob_command()
    cmd = launcher + [
        "run",
        "--format", "json",
        "--max-cost", str(max_cost),
        "--max-turns", str(max_turns),
        "--trust",
        "--accept-license",
        "--log-level", "error",
        "--disable-mcp",
        "--disable-subagents",
        prompt,
    ]
    budget = CMD_LINE_LIMIT if len(launcher) > 1 else 8000
    if sum(len(part) + 1 for part in cmd) > budget:
        sys.exit(
            "prompt is {0} chars, which will not fit this launcher's command line "
            "({1}). Trim the failure digest before spending a coin on a crash.".format(
                len(prompt), budget)
        )

    started = time.time()
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, shell=False
    )
    (RUNS_DIR / (tag + ".json")).write_text(proc.stdout, encoding="utf-8")
    (RUNS_DIR / (tag + ".err")).write_text(proc.stderr, encoding="utf-8")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        # Bob occasionally prefixes the JSON with a banner line. Recover the object
        # rather than throwing away an iteration that has already been paid for.
        match = re.search(r"\{.*\}\s*$", proc.stdout, re.S)
        if match:
            return json.loads(match.group(0))
        return {
            "status": "unparseable",
            "stats": {
                "task_id": None,
                "session_costs": 0.0,
                "tool_calls": None,
                "duration_ms": int((time.time() - started) * 1000),
            },
            "last_message": (proc.stdout[-2000:] or proc.stderr[-2000:]),
        }


# --------------------------------------------------------------------------
# guardrails and the gate
# --------------------------------------------------------------------------


def touched_paths() -> list[str]:
    """Every path currently changed, tracked or not, as repo-relative strings."""
    out = git("status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def harness_outputs(tag: str) -> set[str]:
    """Files this harness writes itself during an iteration.

    They have to be excluded from the guardrail, or the loop accuses Bob of editing
    `results/` on every single run — which is exactly what the first live call did,
    and then `git clean` ate the transcript it had just written. Only these exact
    paths are exempt: any *other* write under `results/` really would be Bob.
    """
    return {
        "results/ledger.jsonl",
        "results/bob_runs/" + tag + ".json",
        "results/bob_runs/" + tag + ".err",
        "results/bob_runs/" + tag + ".prompt.md",
    }


def classify(paths: list[str], ignore: set[str] | None = None) -> tuple[list[str], list[str]]:
    ignore = ignore or set()
    engine_paths: list[str] = []
    stray: list[str] = []
    for p in paths:
        if p in ignore:
            continue
        if any(p.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            engine_paths.append(p)
        else:
            stray.append(p)
    return engine_paths, stray


def revert_engine() -> None:
    run(["git", "checkout", "--", "engine/"])
    run(["git", "clean", "-fdq", "engine/"])


def revert_paths(paths: list[str]) -> None:
    for p in paths:
        run(["git", "checkout", "--", p])
        run(["git", "clean", "-fdq", "--", p])


def commit_engine(message: str) -> str:
    """Commit engine/ with IBM Bob as the git author.

    The author field is what `git log --format='%an' -- 'engine/*.py'` reads, and that
    command is the project's central falsifiable claim. Bob wrote the code; the commit
    says so.
    """
    git("add", "--", "engine/")
    run([
        "git",
        "-c", "user.name=" + BOB_AUTHOR_NAME,
        "-c", "user.email=" + BOB_AUTHOR_EMAIL,
        "commit",
        "--author", BOB_AUTHOR_NAME + " <" + BOB_AUTHOR_EMAIL + ">",
        "-m", message,
    ])
    return git("rev-parse", "--short", "HEAD").strip()


# --------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------


def ledger_entries() -> list[dict]:
    if not LEDGER.exists():
        return []
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def spent_so_far() -> float:
    return sum(float(e.get("cost") or 0.0) for e in ledger_entries())


def next_iteration_number() -> int:
    return max((int(e.get("iteration", 0)) for e in ledger_entries()), default=-1) + 1


def append_ledger(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def bob_report_json(payload: dict) -> str:
    """Bob's own structured report, if it produced one. Recorded verbatim."""
    msg = payload.get("last_message") or ""
    match = re.search(r"\{[^{}]*\"target_failure\".*?\}", msg, re.S)
    return (match.group(0) if match else msg[-600:]).strip()


def bob_change_summary(payload: dict) -> str:
    msg = payload.get("last_message") or ""
    match = re.search(r'"change"\s*:\s*"(.*?)"', msg, re.S)
    if match:
        return match.group(1).strip().replace("\n", " ")[:110]
    return "engine edit"


# --------------------------------------------------------------------------
# one iteration
# --------------------------------------------------------------------------


def iterate(args, iteration: int, before: dict) -> tuple[dict, dict]:
    """Run one iteration. Returns (ledger entry, score result to carry forward)."""
    f1_before = before["f1"]
    prompt = build_prompt(before, args.steer or DEFAULT_STEER)
    tag = "iter" + str(iteration)

    print("\n=== iteration {0} ===".format(iteration))
    print("  holdout F1 before : {0:.6f}".format(f1_before))
    print("  prompt size       : {0} chars".format(len(prompt)))

    if args.dry_run:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (RUNS_DIR / (tag + ".prompt.md")).write_text(prompt, encoding="utf-8")
        print("  DRY RUN - prompt written to results/bob_runs/{0}.prompt.md, "
              "no Bob call made".format(tag))
        return ({"dry_run": True, "iteration": iteration, "f1_before": f1_before}, before)

    remaining = TOTAL_BUDGET - spent_so_far()
    if remaining < args.budget_floor + args.max_cost:
        print("  BUDGET STOP - {0:.2f} coins left, floor is {1}".format(
            remaining, args.budget_floor))
        return ({"iteration": iteration, "outcome": "budget_stop",
                 "remaining_coins": round(remaining, 4)}, before)

    payload = run_bob(prompt, args.max_cost, args.max_turns, tag)
    stats = payload.get("stats") or {}
    cost = float(stats.get("session_costs") or 0.0)
    status = payload.get("status", "unknown")
    print("  bob status        : {0}  cost={1:.4f}  tool_calls={2}  {3}ms".format(
        status, cost, stats.get("tool_calls"), stats.get("duration_ms")))

    entry = {
        "iteration": iteration,
        "attempt": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task_id": stats.get("task_id"),
        "cost": cost,
        "max_cost": args.max_cost,
        "max_turns": args.max_turns,
        "tool_calls": stats.get("tool_calls"),
        "duration_ms": stats.get("duration_ms"),
        "bob_status": status,
        "f1_before": f1_before,
    }

    engine_paths, stray = classify(touched_paths(), ignore=harness_outputs(tag))

    if stray:
        # An edit outside engine/ is not a scoring question, it is an integrity
        # question. Discard the whole iteration regardless of what the metric says.
        print("  GUARDRAIL VIOLATION - touched outside engine/: {0}".format(stray))
        revert_paths(stray)
        revert_engine()
        entry.update({
            "f1_after": f1_before,
            "kept": False,
            "outcome": "guardrail_violation",
            "stray_paths": stray,
            "note": "Bob modified paths outside engine/. Reverted in full and discarded "
                    "without scoring; integrity outranks the metric.",
        })
        append_ledger(entry)
        return entry, before

    if not engine_paths:
        print("  no engine change produced")
        entry.update({
            "f1_after": f1_before,
            "kept": False,
            "outcome": "no_change",
            "note": (payload.get("last_message") or "")[-400:],
        })
        append_ledger(entry)
        return entry, before

    print("  changed           : {0}".format(engine_paths))
    after = score_now()
    if after.get("error"):
        print("  engine broken     : {0}".format(after["detail"][:200]))
        revert_engine()
        entry.update({
            "f1_after": 0.0,
            "kept": False,
            "outcome": "engine_broken",
            "files_touched": engine_paths,
            "note": after["detail"][:400],
        })
        append_ledger(entry)
        return entry, before

    f1_after = after["f1"]
    improved = f1_after > f1_before + 1e-9
    print("  holdout F1 after  : {0:.6f}  ({1})".format(
        f1_after, "KEEP" if improved else "REVERT"))

    entry.update({
        "f1_after": f1_after,
        "dev_f1": after["splits"]["dev"]["f1"],
        "holdout_f1": f1_after,
        "holdout_precision": after["splits"]["holdout"]["precision"],
        "holdout_recall": after["splits"]["holdout"]["recall"],
        "files_touched": engine_paths,
        "kept": improved,
    })

    if improved:
        commit = commit_engine(
            "Iteration {0}: {1}\n\n".format(iteration, bob_change_summary(payload))
            + "holdout F1 {0:.6f} -> {1:.6f}\n".format(f1_before, f1_after)
            + "Authored by IBM Bob, task {0}, {1:.4f} Bobcoins.\n".format(
                stats.get("task_id"), cost)
            + "Kept by tools/forge_loop.py because the held-out metric improved."
        )
        entry["commit"] = commit
        entry["outcome"] = "kept"
        print("  committed         : {0}".format(commit))
        carry = after
    else:
        revert_engine()
        entry["outcome"] = "reverted"
        carry = before

    entry["bob_report"] = bob_report_json(payload)
    append_ledger(entry)
    return entry, carry


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the Bob forge loop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--iterations", type=int, default=1)
    ap.add_argument("--max-cost", type=float, default=3.0,
                    help="per-call Bobcoin cap. 3, not 1: a capped run is billed in full.")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--budget-floor", type=float, default=5.0,
                    help="stop before the remaining balance would fall below this")
    ap.add_argument("--steer", default=None,
                    help="override the 'where to aim this iteration' section of the prompt")
    ap.add_argument("--dry-run", action="store_true",
                    help="score, build and save the prompt, then exit without calling Bob")
    args = ap.parse_args()

    if not VENV_PY.exists():
        sys.exit("virtualenv interpreter not found at " + str(VENV_PY))
    if not args.dry_run:
        # Fail here rather than after a 45-second scoring pass and a built prompt.
        bob_executable()

    dirty = [p for p in touched_paths() if not p.startswith("results/")]
    if dirty and not args.dry_run:
        sys.exit(
            "working tree is dirty, refusing to start: {0}\n".format(dirty)
            + "The keep/revert gate reverts engine/ wholesale; uncommitted work would be lost."
        )

    print("Bobcoins spent so far: {0:.4f} of {1}".format(spent_so_far(), TOTAL_BUDGET))
    print("Scoring current engine (30-60s)...")
    current = score_now()
    if current.get("error"):
        sys.exit("engine does not run: " + str(current["detail"]))

    start = next_iteration_number()
    for i in range(args.iterations):
        entry, current = iterate(args, start + i, current)
        if entry.get("outcome") == "budget_stop":
            break

    print("\nfinal holdout F1: {0:.6f}".format(current["f1"]))
    print("Bobcoins spent: {0:.4f} of {1}".format(spent_so_far(), TOTAL_BUDGET))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
