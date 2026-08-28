"""Freeze everything the web console needs into static JSON.

The console on Vercel is a viewer, not a service. It never runs Python, never
touches the parquet files, and never calls IBM Bob or Granite. Everything it
shows is computed here, once, from the committed repo and written to
`web/public/data/`. That is what makes the deployed page cheap to host, instant
to load, and impossible to break in a demo.

Three things are joined here that live apart in the repo:

  1. the Bob-authored engine's detections  (engine/detect.py + engine/runbook.py)
  2. the ground-truth anomaly labels        (data/telemanom/labeled_anomalies.csv)
  3. the committed Granite operator briefs  (results/briefs/*.md)

and one thing is recomputed rather than remembered: **iteration 0**. The console
claims the forge loop took the operator's inbox from 506 windows to 78. Quoting
that from the README would be an assertion. Instead this script pulls Bob's
original `engine/detect.py` out of git at the baseline commit, executes it, and
counts. If the claim ever stops being true, this script stops printing it.

The label file is read for *display only* - to draw where the truth actually was
next to where the engine looked. `engine/` never sees it, which is the rule that
makes the score meaningful. Nothing here is imported by the engine.

Usage
-----
    .venv/Scripts/python.exe tools/export_console.py
    .venv/Scripts/python.exe tools/export_console.py --check   # verify freshness
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import json
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = REPO_ROOT / "data" / "telemanom"
BRIEFS_DIR = REPO_ROOT / "results" / "briefs"
LEDGER = REPO_ROOT / "results" / "ledger.jsonl"
OUT_DIR = REPO_ROOT / "web" / "public" / "data"
CHAN_DIR = OUT_DIR / "channel"

# Bob's iteration-0 baseline. Named by commit rather than copied into this repo
# so the comparison cannot drift away from what Bob actually wrote.
BASELINE_COMMIT = "27577fe"

from engine.detect import detect as detect_shipped  # noqa: E402
from engine.runbook import match  # noqa: E402
from tools.score import _clamp, prf, score_channel, split_of  # noqa: E402


# --------------------------------------------------------------------------
# the iteration-0 engine, loaded out of git history
# --------------------------------------------------------------------------


def load_baseline_detect():
    """Execute Bob's original detector from the baseline commit.

    Reimplementing it here from the two constants that changed would be easier
    and would also quietly make the comparison a claim about this file rather
    than about Bob's code. `git show` is the honest version: whatever Bob wrote
    on day 2 is what runs.
    """
    source = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:engine/detect.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout

    module = types.ModuleType("engine_baseline")
    module.__dict__["__file__"] = f"git:{BASELINE_COMMIT}:engine/detect.py"
    exec(compile(source, module.__dict__["__file__"], "exec"), module.__dict__)
    return module.detect, {
        "threshold": module.DETECTION_THRESHOLD,
        "merge_gap": module.MERGE_GAP,
        "min_window": module.MIN_WINDOW_LEN,
        "rolling_window": module.ROLLING_WINDOW,
    }


def shipped_constants() -> dict:
    import engine.detect as d

    return {
        "threshold": d.DETECTION_THRESHOLD,
        "merge_gap": d.MERGE_GAP,
        "min_window": d.MIN_WINDOW_LEN,
        "rolling_window": d.ROLLING_WINDOW,
    }


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------


def load_labels() -> dict[str, dict]:
    with (DATA_DIR / "labeled_anomalies.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for row in rows:
        out[row["chan_id"]] = {
            "spacecraft": row["spacecraft"],
            "windows": [tuple(w) for w in ast.literal_eval(row["anomaly_sequences"])],
            # The `class` column is a bare-word list - `[point, contextual]` -
            # so it is not valid Python and literal_eval refuses it. Split it.
            "classes": [c.strip() for c in row.get("class", "").strip("[]").split(",") if c.strip()],
        }
    return out


def load_brief(channel: str, start: int, end: int) -> dict | None:
    """Split a committed brief into its front matter and its three sections.

    The console renders WHAT HAPPENED / WHY IT MATTERS / WHAT TO DO NEXT as
    separate blocks, so the parsing happens once here rather than in JavaScript
    on every render. The raw markdown ships alongside it: a reader who wants to
    check the file against the repo should not have to trust this parser.
    """
    path = BRIEFS_DIR / f"{channel}_{start}-{end}.md"
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8")

    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in raw.splitlines():
        hit = next(
            (h for h in ("WHAT HAPPENED", "WHY IT MATTERS", "WHAT TO DO NEXT")
             if line.strip().upper().startswith(h)),
            None,
        )
        if hit:
            if current:
                sections[current] = " ".join(buf).strip()
            current = hit
            buf = [line.strip()[len(hit):].lstrip(": ").strip()]
        elif current:
            buf.append(line.strip())
    if current:
        sections[current] = " ".join(buf).strip()

    return {
        "file": f"results/briefs/{path.name}",
        "happened": sections.get("WHAT HAPPENED", ""),
        "matters": sections.get("WHY IT MATTERS", ""),
        "next": sections.get("WHAT TO DO NEXT", ""),
        "markdown": raw,
    }


def demojibake(value):
    """Undo a cp1252/utf-8 round trip in ledger text, for display only.

    Some ledger lines were written through a console that encoded `->` and
    `--` as cp1252 bytes and then stored them as UTF-8, so `→` reads back as
    `â†’`. The ledger is append-only and harness-owned, so it is not
    rewritten here; the text is repaired on the way out to the console and the
    committed file stays exactly as the harness wrote it.
    """
    if not isinstance(value, str) or not any(c in value for c in ("Ã", "â", "Â")):
        return value
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    return demojibake(obj)


def load_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        # bob_report is a JSON string inside a JSON object. Unwrap it so the
        # console can show Bob's own words about the iteration without
        # double-parsing in the browser.
        report = row.get("bob_report")
        if isinstance(report, str):
            try:
                row["bob_report"] = json.loads(report)
            except json.JSONDecodeError:
                pass
        out.append(clean(row))
    return out


# --------------------------------------------------------------------------
# per-channel work
# --------------------------------------------------------------------------


def robust_z(values: np.ndarray, rolling_window: int, consistency: float) -> tuple[np.ndarray, float]:
    """Recompute the detector's own deviation measure, for drawing.

    This mirrors engine/detect.py rather than importing its internals, because
    the engine exposes only `detect(df) -> windows` and adding a hook for the
    console would mean editing Bob's file. The constants are read from the
    engine, so the trace cannot silently disagree with the threshold line
    plotted over it.
    """
    series = pd.Series(values)
    rolling = series.rolling(window=rolling_window, min_periods=1).median().to_numpy()
    residual = values - rolling
    mad = float(np.median(np.abs(residual))) * consistency
    if mad < 1e-10:
        std = float(np.std(residual))
        scale = std if std >= 1e-10 else 1.0
    else:
        scale = mad
    return np.abs(residual) / scale, scale


def describe(df: pd.DataFrame, values: np.ndarray, residual_z: np.ndarray,
             window: tuple[int, int], spacecraft: str, channel: str) -> dict:
    start, end = window
    inside = values[start : end + 1]
    outside = np.concatenate([values[:start], values[end + 1 :]])
    if outside.size == 0:
        outside = inside

    entry = match(df, (start, end)) or {}
    cmd_cols = [c for c in df.columns if c.startswith("cmd_")]
    active = [c for c in cmd_cols if float(df[c].to_numpy()[start : end + 1].max()) > 0]

    return {
        "id": f"{channel}_{start}-{end}",
        "start": start,
        "end": end,
        "length": end - start + 1,
        "signature": entry.get("signature", "unclassified"),
        "title": entry.get("title", "Anomaly detected"),
        "severity": entry.get("severity", "unknown"),
        "action": entry.get("action", ""),
        "z_peak": round(float(residual_z[start : end + 1].max()), 2),
        "w_mean": round(float(inside.mean()), 4),
        "w_std": round(float(inside.std()), 4),
        "b_mean": round(float(outside.mean()), 4),
        "b_std": round(float(outside.std()), 4),
        "cmds": active[:8],
        "brief": load_brief(channel, start, end),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and report drift instead of writing")
    args = ap.parse_args()

    labels = load_labels()
    detect_baseline, baseline_consts = load_baseline_detect()
    ship_consts = shipped_constants()
    consistency = __import__("engine.detect", fromlist=["x"]).MAD_CONSISTENCY_FACTOR

    channels: list[dict] = []
    per_channel_payloads: dict[str, dict] = {}

    totals = {
        "shipped": {"windows": 0, "channels_firing": 0, "flagged": 0, "samples": 0},
        "baseline": {"windows": 0, "channels_firing": 0, "flagged": 0, "samples": 0},
    }
    split_agg = {
        "dev": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
        "holdout": {"tp": 0, "fp": 0, "fn": 0, "channels": 0},
    }
    severity_totals = {"high": 0, "medium": 0, "low": 0}
    signature_totals: dict[str, int] = {}
    briefs_found = 0

    for chan in sorted(labels):
        path = DATA_DIR / "test" / f"{chan}.parquet"
        if not path.exists():
            continue

        df = pd.read_parquet(path)
        values = df["value"].to_numpy(dtype=float)
        n = len(values)
        split = split_of(chan)
        truth = _clamp(labels[chan]["windows"], n)

        z, _scale = robust_z(values, ship_consts["rolling_window"], consistency)

        shipped = _clamp([tuple(map(int, w)) for w in detect_shipped(df)], n)
        baseline = _clamp([tuple(map(int, w)) for w in detect_baseline(df)], n)

        tp, fp, fn = score_channel(truth, shipped)
        agg = split_agg[split]
        agg["tp"] += tp
        agg["fp"] += fp
        agg["fn"] += fn
        agg["channels"] += 1

        detections = [
            describe(df, values, z, w, labels[chan]["spacecraft"], chan) for w in shipped
        ]
        for d in detections:
            severity_totals[d["severity"]] = severity_totals.get(d["severity"], 0) + 1
            signature_totals[d["signature"]] = signature_totals.get(d["signature"], 0) + 1
            if d["brief"]:
                briefs_found += 1

        # Which detections actually landed on a labelled anomaly, and which
        # labelled anomalies nobody found. The console draws both; hiding the
        # misses would make the plot a highlight reel.
        for d in detections:
            d["hit"] = any(d["start"] <= t[1] and t[0] <= d["end"] for t in truth)
        truth_out = [
            {
                "start": s,
                "end": e,
                "caught": any(dd["start"] <= e and s <= dd["end"] for dd in detections),
                "class": labels[chan]["classes"][i] if i < len(labels[chan]["classes"]) else "",
            }
            for i, (s, e) in enumerate(truth)
        ]

        for key, wins in (("shipped", shipped), ("baseline", baseline)):
            t = totals[key]
            t["windows"] += len(wins)
            t["channels_firing"] += 1 if wins else 0
            t["flagged"] += sum(e - s + 1 for s, e in wins)
            t["samples"] += n

        channels.append({
            "id": chan,
            "spacecraft": labels[chan]["spacecraft"],
            "split": split,
            "n": n,
            "detections": len(shipped),
            "baseline_detections": len(baseline),
            "truth": len(truth),
            "caught": sum(1 for t in truth_out if t["caught"]),
            "severity": (
                "high" if any(d["severity"] == "high" for d in detections)
                else "medium" if any(d["severity"] == "medium" for d in detections)
                else "low" if detections else None
            ),
        })

        per_channel_payloads[chan] = {
            "id": chan,
            "spacecraft": labels[chan]["spacecraft"],
            "split": split,
            "n": n,
            # 3 dp on a series normalised to roughly [-1, 1] is finer than one
            # screen pixel at any plausible plot width, and roughly halves the
            # payload against full float repr.
            "values": [round(float(v), 3) for v in values],
            "z": [round(float(min(zz, 60.0)), 2) for zz in z],
            "truth": truth_out,
            "detections": detections,
            "baseline": [{"start": s, "end": e} for s, e in baseline],
        }

    splits = {}
    for name, agg in split_agg.items():
        p, r, f1 = prf(agg["tp"], agg["fp"], agg["fn"])
        splits[name] = {**agg, "precision": round(p, 6), "recall": round(r, 6), "f1": round(f1, 6)}

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True).stdout.strip(),
        "channels": channels,
        "splits": splits,
        "engine": {
            "shipped": ship_consts,
            "baseline": baseline_consts,
            "baseline_commit": BASELINE_COMMIT,
        },
        "totals": {
            "channels": len(channels),
            "briefs": briefs_found,
            "severity": severity_totals,
            "signature": signature_totals,
            "shipped": totals["shipped"],
            "baseline": totals["baseline"],
        },
        "ledger": load_ledger(),
    }

    if args.check:
        stale = []
        if not (OUT_DIR / "manifest.json").exists():
            stale.append("manifest.json missing")
        else:
            old = json.loads((OUT_DIR / "manifest.json").read_text(encoding="utf-8"))
            for field in ("splits", "totals", "engine"):
                if old.get(field) != manifest[field]:
                    stale.append(f"{field} differs")
        if stale:
            print("STALE - " + "; ".join(stale))
            print("Run: .venv/Scripts/python.exe tools/export_console.py")
            return 1
        print("OK - console data matches the current engine and briefs.")
        return 0

    CHAN_DIR.mkdir(parents=True, exist_ok=True)
    for chan, payload in per_channel_payloads.items():
        (CHAN_DIR / f"{chan}.json").write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, separators=(",", ":")), encoding="utf-8")

    sh, bl = totals["shipped"], totals["baseline"]
    print(f"channels        {len(channels)}")
    print(f"shipped engine  {sh['windows']} windows on {sh['channels_firing']} channels "
          f"({100 * sh['flagged'] / sh['samples']:.1f}% of samples flagged)")
    print(f"iteration 0     {bl['windows']} windows on {bl['channels_firing']} channels "
          f"({100 * bl['flagged'] / bl['samples']:.1f}% of samples flagged)")
    print(f"briefs matched  {briefs_found} / {sh['windows']}")
    print(f"holdout F1      {splits['holdout']['f1']:.3f}  "
          f"(P {splits['holdout']['precision']:.3f} / R {splits['holdout']['recall']:.3f})")
    print(f"written to      {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
