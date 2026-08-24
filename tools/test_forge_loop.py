"""Tests for the harness - the parts that decide what gets kept.

The scorer has its own tests (`tools/test_score.py`). What this file covers is the
machinery around it: does the guardrail actually notice an edit outside `engine/`,
does the revert actually restore the tree, and does the prompt actually inline what
it claims to inline. Those are the three ways the loop could quietly stop meaning
anything while still printing numbers.

None of this spends a Bobcoin or calls Bob.

    .venv/Scripts/python.exe tools/test_forge_loop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import forge_loop as fl  # noqa: E402

PASSED = 0
FAILED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  ok   " + name)
    else:
        FAILED += 1
        print("  FAIL " + name + ("  -> " + detail if detail else ""))


# --------------------------------------------------------------------------


def test_classify() -> None:
    """`engine/` is the only writable surface. Everything else is a violation."""
    engine, stray = fl.classify([
        "engine/detect.py",
        "engine/runbook.py",
        "engine/helpers/smoothing.py",
        "tools/score.py",
        "data/telemanom/labeled_anomalies.csv",
        "results/ledger.jsonl",
    ])
    check("engine paths allowed", engine == [
        "engine/detect.py", "engine/runbook.py", "engine/helpers/smoothing.py"])
    check("scorer edit is a violation", "tools/score.py" in stray)
    check("data edit is a violation", "data/telemanom/labeled_anomalies.csv" in stray)
    check("ledger edit is a violation", "results/ledger.jsonl" in stray)
    check("nothing allowed by accident", len(stray) == 3, str(stray))


def test_harness_outputs_are_not_blamed_on_bob() -> None:
    """The harness writes into `results/` while Bob is running. That is not Bob.

    The first live call flagged its own transcript as a guardrail violation and then
    `git clean` deleted the file it had just written. The exemption is exactly four
    named paths, so a genuine Bob write anywhere else under `results/` still trips.
    """
    ignore = fl.harness_outputs("iter7")
    engine, stray = fl.classify([
        "results/bob_runs/iter7.json",
        "results/bob_runs/iter7.prompt.md",
        "results/ledger.jsonl",
        "engine/detect.py",
    ], ignore=ignore)
    check("own transcript is not a violation", stray == [], str(stray))
    check("engine edit still seen", engine == ["engine/detect.py"])

    _, stray2 = fl.classify([
        "results/bob_runs/iter3.json",   # a different iteration's transcript
        "results/briefs/A-5_2757-2807.md",
    ], ignore=ignore)
    check("another iteration's transcript is a violation",
          "results/bob_runs/iter3.json" in stray2)
    check("brief edit is a violation", "results/briefs/A-5_2757-2807.md" in stray2)


def test_pre_existing_dirt_is_not_blamed_on_bob() -> None:
    """The guardrail asks what changed *during* the call, not what is dirty after it.

    Iteration 4 was discarded — and 1.14 coins with it — because unrelated files were
    saved into the repo while Bob was mid-edit. The harness called that a violation,
    reverted Bob's work, and `git clean`ed the unrelated files out of existence. The
    snapshot taken before the call is what makes that impossible.
    """
    snapshot = {"docs/outreach/README.md", "notes/scratch.md"}
    engine, stray = fl.classify(
        ["docs/outreach/README.md", "notes/scratch.md", "engine/detect.py"],
        ignore=fl.harness_outputs("iter9") | snapshot,
    )
    check("files present before the call are exempt", stray == [], str(stray))
    check("Bob's actual edit is still seen", engine == ["engine/detect.py"])

    _, stray2 = fl.classify(
        ["docs/outreach/README.md", "tools/score.py"],
        ignore=fl.harness_outputs("iter9") | snapshot,
    )
    check("a scorer edit during the call still trips", stray2 == ["tools/score.py"], str(stray2))


def test_revert_restores_engine() -> None:
    """A reverted iteration must leave `engine/` byte-identical.

    The probe is a temporary non-Python file. It is never committed, so it cannot
    appear in `git log -- 'engine/*.py'`, and the assertion below is that it does not
    survive the revert either.

    Content, not bytes: this repo has `core.autocrlf=true`, so a checkout is entitled
    to hand back CRLF where Bob wrote LF. That renormalisation is invisible to Python
    and to `git status`. What the gate has to guarantee is that no *edit* survives.
    """
    probe = fl.ENGINE_DIR / "__forge_gate_probe.tmp"
    detect = fl.ENGINE_DIR / "detect.py"
    original = detect.read_bytes()

    def content(raw: bytes) -> bytes:
        return raw.replace(b"\r\n", b"\n")

    probe.write_text("this file exists only to prove the revert works\n", encoding="utf-8")
    detect.write_bytes(original + b"\n# harness probe: this line must not survive\n")

    seen = fl.touched_paths()
    check("harness sees the new file", any(p.endswith("__forge_gate_probe.tmp") for p in seen),
          str(seen))
    check("harness sees the modified file", "engine/detect.py" in seen, str(seen))

    fl.revert_engine()

    check("revert deleted the untracked probe", not probe.exists())
    check("revert restored detect.py exactly", content(detect.read_bytes()) == content(original))
    check("tree is clean again", "engine/detect.py" not in fl.touched_paths())


def test_prompt_is_self_contained() -> None:
    """The prompt must carry the engine source, or Bob pays to go read it.

    Day 2 measured this: the run that was told to orient itself spent its whole cap
    on reads and wrote nothing. `build_prompt` is checked against a synthetic score
    result so the test costs no scoring pass.
    """
    fake = {
        "f1": 0.25,
        "splits": {
            "dev": {"precision": 0.1, "recall": 0.6, "f1": 0.2,
                    "tp": 4, "fp": 40, "fn": 3, "channels": 56},
            "holdout": {"precision": 0.2, "recall": 0.7, "f1": 0.25,
                        "tp": 2, "fp": 8, "fn": 1, "channels": 26},
        },
        "failures": {
            "dev": [
                {"kind": "false_alarm", "channel": "X-1", "window": [10, 20], "n": 900},
                {"kind": "false_alarm", "channel": "X-1", "window": [30, 33], "n": 900},
                {"kind": "missed", "channel": "Y-2", "window": [100, 200],
                 "class": "[point]", "n": 900},
            ],
            "holdout": [
                {"kind": "missed", "channel": "SECRET-9", "window": [1, 2],
                 "class": "[point]", "n": 900},
                {"kind": "false_alarm", "channel": "SECRET-9", "window": [5, 9], "n": 900},
            ],
        },
    }
    prompt = fl.build_prompt(fake, fl.DEFAULT_STEER)

    check("engine source is inlined", "def detect(" in prompt)
    check("tunable constants are inlined", "DETECTION_THRESHOLD" in prompt)
    check("dev false alarms reach Bob", "X-1" in prompt)
    check("dev misses reach Bob", "Y-2" in prompt)
    check("holdout failures are withheld", "SECRET-9" not in prompt,
          "Bob must never see which held-out channel it got wrong")
    check("gate metric is stated", "0.250000" in prompt)
    check("exploration is forbidden", "Do NOT read files" in prompt)
    check("scorer is declared off limits", "NEVER edit `tools/score.py`" in prompt)
    check("venv interpreter is used", ".venv/Scripts/python.exe tools/score.py" in prompt)
    check("prompt fits a Windows command line", len(prompt) < 30000, str(len(prompt)))


def test_history_carries_reverted_levers() -> None:
    """Every `bob run` is a cold start. Reverted attempts must be handed forward.

    Otherwise iteration N pays to propose iteration N-1's reverted edit. The history
    is read from the real ledger, so this also asserts the ledger is still shaped the
    way the reader expects.
    """
    history = fl.attempt_history()
    kept_or_reverted = [e for e in fl.ledger_entries() if "bob_report" in e]
    if not kept_or_reverted:
        check("no history yet, nothing to carry", history == "")
        return
    check("history is non-empty", bool(history.strip()))
    check("verdicts are stated", "REVERTED" in history or "KEPT" in history)
    check("repeating a lever is forbidden", "do not propose it again" in history)
    check("history reaches the prompt", "## Already tried" in history)


def test_bob_is_launchable() -> None:
    """Both Windows launcher problems, asserted rather than rediscovered.

    A bare "bob" raises FileNotFoundError from Python while working in every
    terminal. And going through the `.CMD` shim caps the command line at cmd.exe's
    8191 characters, which this harness's ~12000-character prompt does not fit —
    the first live call died in 102ms on exactly that.
    """
    import subprocess

    cmd = fl.bob_command()
    check("launcher resolves to real files", all(Path(p).exists() for p in cmd), str(cmd))
    proc = subprocess.run(cmd + ["--version"], capture_output=True, text=True)
    check("bob is launchable from subprocess", proc.returncode == 0, proc.stderr[:200])
    check("launcher bypasses the cmd.exe shim", len(cmd) > 1,
          "falling back to " + str(cmd) + " caps the prompt at 8191 chars")


def test_commit_names_bob_as_author() -> None:
    """`git log --format='%an' -- 'engine/*.py'` is this project's central claim.

    It holds only if the harness sets the *author* — not just the committer — to IBM
    Bob on every kept iteration. Verified in a throwaway repo rather than by leaving
    a probe commit in the real history, and by monkeypatching REPO_ROOT so the very
    same `commit_engine` runs, not a copy of it.
    """
    import shutil
    import subprocess
    import tempfile

    sandbox = Path(tempfile.mkdtemp(prefix="forge-commit-test-"))
    real_root = fl.REPO_ROOT
    try:
        subprocess.run(["git", "init", "-q"], cwd=sandbox, check=True)
        subprocess.run(["git", "config", "user.name", "Some Human"], cwd=sandbox, check=True)
        subprocess.run(["git", "config", "user.email", "human@example.com"], cwd=sandbox,
                       check=True)
        (sandbox / "engine").mkdir()
        (sandbox / "engine" / "detect.py").write_text("def detect(df):\n    return []\n",
                                                      encoding="utf-8")

        fl.REPO_ROOT = sandbox
        sha = fl.commit_engine("Iteration 99: a test commit")

        log = subprocess.run(
            ["git", "log", "--format=%an|%ae|%cn", "--", "engine/detect.py"],
            cwd=sandbox, capture_output=True, text=True,
        ).stdout.strip()
        check("a commit was produced", bool(sha), sha)
        check("author is IBM Bob", log.startswith("IBM Bob|bob@ibm.invalid|"), log)
        check("committer is not the human either", log.endswith("|IBM Bob"), log)
    finally:
        fl.REPO_ROOT = real_root
        shutil.rmtree(sandbox, ignore_errors=True)


def test_budget_accounting() -> None:
    """The ledger is the only record of spend, so the arithmetic on it must hold."""
    entries = fl.ledger_entries()
    check("ledger parses", isinstance(entries, list) and len(entries) >= 1)
    check("every entry carries a cost", all("cost" in e for e in entries))
    check("spend is the sum of the ledger",
          abs(fl.spent_so_far() - sum(float(e.get("cost") or 0) for e in entries)) < 1e-9)
    check("spend is inside the grant", 0 < fl.spent_so_far() < fl.TOTAL_BUDGET)
    check("next iteration follows the ledger",
          fl.next_iteration_number() == max(int(e.get("iteration", 0)) for e in entries) + 1)


def test_report_extraction() -> None:
    """Bob's JSON report is fished out of prose. It has to survive a real transcript."""
    payload = {"last_message": (
        "Scorer ran cleanly.\n\n```json\n"
        '{"target_failure":"T-2 false alarms","hypothesis":"threshold too low",'
        '"change":"raised DETECTION_THRESHOLD from 4.0 to 5.5",'
        '"files_touched":["engine/detect.py"],"f1_before":0.265957,"f1_after":0.31,'
        '"generalises":"dev F1 0.27 / holdout F1 0.31"}\n```'
    )}
    check("report is recovered", '"target_failure"' in fl.bob_report_json(payload))
    check("change summary is recovered",
          fl.bob_change_summary(payload) == "raised DETECTION_THRESHOLD from 4.0 to 5.5",
          fl.bob_change_summary(payload))
    check("missing report degrades gracefully",
          fl.bob_change_summary({"last_message": "I could not improve it."}) == "engine edit")


def main() -> int:
    print("harness tests - no Bobcoins spent")
    for test in (test_classify, test_harness_outputs_are_not_blamed_on_bob,
                 test_pre_existing_dirt_is_not_blamed_on_bob,
                 test_revert_restores_engine, test_prompt_is_self_contained,
                 test_history_carries_reverted_levers, test_bob_is_launchable,
                 test_commit_names_bob_as_author, test_budget_accounting,
                 test_report_extraction):
        print("\n" + test.__name__)
        test()
    print("\n{0} passed, {1} failed".format(PASSED, FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
