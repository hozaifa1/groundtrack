"""Check every committed Granite brief against the detection it was written from.

`make_briefs.py --check` proves the briefs really came out of Granite. It does not
prove they are *true*. This does the other half: it re-derives each detection from
the Bob-authored engine and confirms that what Granite wrote about it is grounded.

Three failure modes are worth catching automatically, because reading 78 briefs by
hand catches them unreliably:

* **A number that is not in the telemetry.** Every figure in a brief should trace to
  the record it was generated from - the sample range, the window and baseline
  statistics, or the peak deviation. A number that matches none of them is either a
  miscopy or an invention, and both are disqualifying in an operations note.
* **An invented identifier.** The system prompt forbids inventing subsystems, part
  numbers and procedure ids. Those have a recognisable shape (`SSR-2`, `PROC-1174`),
  and the only one legitimately present is the channel id itself.
* **A dropped section.** The template asks for exactly three. The 350m model dropped
  one, which is part of why it is not the shipped model.

This is a lint, not a proof. It cannot tell whether a *sentence* is a fair reading of
the numbers - that is the judgement a human keeps. What it does is make sure the
figures are real, so the human is reviewing prose rather than checking arithmetic.

Usage
-----
    .venv/Scripts/python.exe tools/audit_briefs.py
    .venv/Scripts/python.exe tools/audit_briefs.py --verbose

Exits non-zero if anything is flagged.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEFS_DIR = REPO_ROOT / "results" / "briefs"

sys.path.insert(0, str(REPO_ROOT))

SECTIONS = ("WHAT HAPPENED", "WHY IT MATTERS", "WHAT TO DO NEXT")

# The lookbehind makes a leading minus a sign only when a digit does not precede it,
# so "samples 5077-5126" reads as 5077 and 5126 rather than 5077 and -5126, while a
# genuinely negative "-0.9813" still parses with its sign.
NUMBER = re.compile(r"(?<![\d.])-?\d+(?:\.\d+)?")

# The shape of a part number or procedure id: two or more capitals, then digits.
# The channel id ("A-5", "P-11") has this shape too and is masked out before this
# runs, so anything left is something Granite supplied on its own.
IDENTIFIER = re.compile(r"\b[A-Z]{2,}[-_ ]?\d{1,4}\b")

# Where the generated body starts, in the header render() writes.
BODY_MARKER = "running locally via Ollama"

# Constants an operator brief may legitimately mention that are properties of the
# detector rather than of one window: the sigma thresholds and the rolling window.
DETECTOR_CONSTANTS = (4.0, 6.0, 100.0, 150.0)


def _command_names(d: dict) -> list[str]:
    """The command columns that were named in this detection's prompt, if any."""
    if d["cmds"] == "none":
        return []
    return [c.strip() for c in d["cmds"].split(",") if c.strip()]


def candidate_values(d: dict) -> list[float]:
    """Every number a truthful brief about this detection could quote."""
    vals = [
        d["start"], d["end"], d["length"], d["total"], d["z_peak"],
        d["w_mean"], d["w_std"], d["w_min"], d["w_max"],
        d["b_mean"], d["b_std"], d["b_min"], d["b_max"],
    ]
    # Differences a brief may reasonably compute rather than copy.
    vals.append(d["w_mean"] - d["b_mean"])
    vals.append(abs(d["w_mean"] - d["b_mean"]))
    vals.extend(DETECTOR_CONSTANTS)
    # Enumerating steps ("1.", "2.", "3.") in WHAT TO DO NEXT.
    vals.extend((1.0, 2.0, 3.0))
    return [float(v) for v in vals]


def is_grounded(value: float, cands: list[float]) -> bool:
    """True if `value` is any candidate, at any rounding a writer might use.

    Granite rounds freely - 11.657898 becomes "11.7", 0.6803 becomes "0.68". So a
    match is accepted at any decimal place, plus a small relative tolerance for
    figures it restates loosely.
    """
    for c in cands:
        if any(abs(round(c, nd) - value) < 1e-9 for nd in range(5)):
            return True
        if abs(value - c) <= max(0.05, abs(c) * 0.02):
            return True
    return False


def audit(verbose: bool = False) -> int:
    from tools.make_briefs import load_detections  # noqa: E402

    records = {
        f"{d['channel']}_{d['start']}-{d['end']}": d for d in load_detections()
    }
    briefs = sorted(BRIEFS_DIR.glob("*.md"))
    if not briefs:
        sys.exit("No briefs to audit. Run tools/make_briefs.py first.")

    stale: list[str] = []
    dropped_sections: list[tuple[str, str]] = []
    invented: list[tuple[str, str]] = []
    ungrounded: list[tuple[str, str, str]] = []

    for path in briefs:
        key = path.stem
        d = records.get(key)
        if d is None:
            # The engine no longer emits this window, so the brief describes a
            # detection that does not exist any more.
            stale.append(key)
            continue

        body = path.read_text(encoding="utf-8").split(BODY_MARKER, 1)[-1]
        # Mask names before scanning for numbers. The channel id ("A-5") and the
        # command columns ("cmd_22") carry digits that are identifiers, not
        # measurements, and both were supplied to Granite in the prompt.
        body = body.replace(d["channel"], "<CHAN>")
        for cmd in sorted(_command_names(d), key=len, reverse=True):
            body = body.replace(cmd, "<CMD>")

        for section in SECTIONS:
            if section not in body:
                dropped_sections.append((key, section))

        cands = candidate_values(d)
        for m in NUMBER.finditer(body):
            if not is_grounded(float(m.group()), cands):
                context = body[max(0, m.start() - 50): m.end() + 30]
                ungrounded.append((key, m.group(), " ".join(context.split())))

        for m in IDENTIFIER.finditer(body):
            invented.append((key, m.group()))

    print(f"briefs:      {len(briefs)}")
    print(f"detections:  {len(records)}")
    print(f"stale (no matching detection):  {len(stale)}")
    print(f"dropped sections:               {len(dropped_sections)}")
    print(f"invented identifiers:           {len(invented)}")
    print(f"ungrounded numbers:             {len(ungrounded)}")

    findings = len(stale) + len(dropped_sections) + len(invented) + len(ungrounded)
    if findings and (verbose or findings <= 40):
        print()
        for key in stale:
            print(f"  STALE      {key}")
        for key, section in dropped_sections:
            print(f"  MISSING    {key}: no '{section}' section")
        for key, token in invented:
            print(f"  IDENTIFIER {key}: {token}")
        for key, num, context in ungrounded:
            print(f"  UNGROUNDED {key}: {num}  ...{context}...")

    if findings == 0:
        print("\nOK - every brief matches a live detection, keeps all three sections,")
        print("quotes only numbers present in the telemetry, and invents no identifiers.")
        return 0
    print(f"\n{findings} finding(s).")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true", help="list every finding")
    args = ap.parse_args()
    return audit(verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
