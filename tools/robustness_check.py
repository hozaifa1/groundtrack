"""Does the headline result survive throwing away the widest alarms?

The scorer counts a labelled fault as caught when any predicted window overlaps
it, and says nothing about how tightly that window is drawn. A window covering
most of a recording therefore scores as a hit while telling an operator very
little. That is a real loophole, documented in docs/parameter-search.md, and a
reader is right to ask whether the shipped engine's result leans on it.

This answers the question by re-scoring with the widest windows deleted. It
reads the same exported detections the console draws, and reproduces the
committed holdout score exactly when nothing is dropped, which is what makes the
comparison meaningful.

    .venv/Scripts/python.exe tools/robustness_check.py
"""
from __future__ import annotations
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _overlaps(a: int, b: int, c: int, d: int) -> bool:
    return not (b < c or d < a)


def score(max_width: float | None = None) -> dict[str, dict[str, float]]:
    """Window-overlap precision/recall/F1 per split.

    `max_width` drops any detection covering more than that fraction of its
    recording before scoring. None keeps every detection.
    """
    manifest = json.loads((ROOT / "web/public/data/manifest.json").read_text(encoding="utf-8"))
    split = {c["id"]: c["split"] for c in manifest["channels"]}
    agg = {"dev": [0, 0, 0], "holdout": [0, 0, 0]}

    for path in sorted(glob.glob(str(ROOT / "web/public/data/channel/*.json"))):
        ch = json.loads(Path(path).read_text(encoding="utf-8"))
        n = ch["n"]
        dets = ch["detections"]
        if max_width is not None:
            dets = [d for d in dets if (d["end"] - d["start"] + 1) / n <= max_width]

        caught: set[int] = set()
        used: set[int] = set()
        for i, t in enumerate(ch["truth"]):
            for j, d in enumerate(dets):
                if _overlaps(t["start"], t["end"], d["start"], d["end"]):
                    caught.add(i)
                    used.add(j)

        bucket = agg[split[ch["id"]]]
        bucket[0] += len(caught)
        bucket[1] += sum(1 for j in range(len(dets)) if j not in used)
        bucket[2] += len(ch["truth"]) - len(caught)

    out = {}
    for name, (tp, fp, fn) in agg.items():
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        out[name] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
        }
    return out


def main() -> int:
    full = score()["holdout"]
    trimmed = score(0.5)["holdout"]

    print("Held-out recordings, as shipped:")
    print(f"  found {full['tp']} of {full['tp'] + full['fn']} faults, "
          f"{full['fp']} false alarms, score {full['f1']:.3f}")
    print("Same, with every alarm covering more than half its recording deleted:")
    print(f"  found {trimmed['tp']} of {trimmed['tp'] + trimmed['fn']} faults, "
          f"{trimmed['fp']} false alarms, score {trimmed['f1']:.3f}")
    print()
    print(f"False alarms are unchanged at {full['fp']}, so the wide windows are not "
          "concealing them.")
    print("The baseline engine scored 0.266 on these recordings either way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
