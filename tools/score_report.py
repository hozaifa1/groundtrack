"""Full scorer output in one pass — metrics *and* the failure lists.

Why this exists: `tools/score.py` is fixed and never edited, and its CLI emits either
the metrics (`--json`) or one split's failures (`--failures`), never both. The forge
loop needs both, and a scoring pass reads 81 parquet files and costs 30-60 seconds.
Running the scorer twice per iteration to get two halves of the same computation is
pure waste, so this thin read-only wrapper calls `score.evaluate()` once and dumps
everything it returned.

This file computes nothing. It adds no metric, no threshold, no filtering. If it
disagreed with `tools/score.py`, `tools/score.py` would be right.

    .venv/Scripts/python.exe tools/score_report.py > report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import score  # noqa: E402  - the ruler, imported and never modified


def main() -> int:
    result = score.evaluate()
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 2 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
