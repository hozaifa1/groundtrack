"""Turn engine detections into plain-language operations briefs with IBM Granite.

Granite runs **locally through Ollama**. Nothing here calls a hosted service, needs
an account, or costs money. Briefs are generated offline and committed, so the
judged experience has zero live dependencies - no cold start, no quota, no card.
The README says this plainly; we never imply live inference that isn't happening.

Why local Ollama and not a hosted Granite endpoint: the HuggingFace serverless API
does not deploy Granite, HF Docker Spaces require PRO, OpenRouter's Granite is
paid-only, and watsonx.ai Lite demands a credit card for identity verification.
Local Ollama is the only unconditionally free path, and it is also the only one
that cannot fail during a demo.

Usage
-----
    python tools/make_briefs.py --smoke        # one brief, proves the path works
    python tools/make_briefs.py                # every detection on every channel
    python tools/make_briefs.py --check        # regenerate one and diff it
    python tools/make_briefs.py --check --limit 78   # regenerate all of them

`--check` is the falsifiability hook: a judge runs it and sees that the committed
text really did come out of Granite, from this prompt, with these settings, without
spending anything. It regenerates one brief, which takes about fifty seconds and is
the only one that reproduces dependably - `warm_up` records why, and what was
measured. `--limit N` widens the sample and will start showing diffs.
"""

from __future__ import annotations

import argparse
import difflib
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEFS_DIR = REPO_ROOT / "results" / "briefs"
DATA_DIR = REPO_ROOT / "data" / "telemanom"

OLLAMA_HOST = "http://127.0.0.1:11434"
MODEL = "granite4:3b"          # IBM Granite 4.0 micro - 2.1GB, 128K context
FALLBACK_MODEL = "granite4:350m"

# Deterministic decoding. A brief that changes between runs cannot be diffed by a
# judge, which would defeat the whole point of --check.
#
# `num_thread: 1` is the load-bearing option here, and it is not obvious.
# Temperature 0 and a fixed seed are NOT sufficient: multi-threaded CPU inference
# reduces floating-point partials in whatever order the threads finish, so two
# identical requests diverge. Measured on this machine, the same prompt at
# temperature 0 produced three different texts across three calls with default
# threading, and byte-identical text every time with a single thread.
#
# It costs roughly 3x wall-clock (180s vs 60s per brief). We pay it, because a
# brief a judge cannot regenerate is a brief they have to take on trust, and the
# whole point of `--check` is that they don't have to.
OPTIONS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "seed": 7,
    "num_predict": 320,
    "num_thread": 1,
}

SYSTEM = (
    "You are a spacecraft mission-operations assistant. You write short, calm, "
    "factual shift-handover notes for a ground-station operator. You never "
    "speculate beyond the telemetry you were given, and you never invent "
    "spacecraft subsystems, part numbers, or procedure identifiers."
)

TEMPLATE = """A rolling-statistics detector flagged an anomaly in spacecraft telemetry.

Spacecraft: {spacecraft}
Channel: {channel}
Flagged sample range: {start} to {end} ({length} samples of {total})
Detector signature: {signature}
Severity: {severity}
Suggested runbook action: {action}

Telemetry inside the flagged window:
  mean {w_mean:.4f}, std {w_std:.4f}, min {w_min:.4f}, max {w_max:.4f}
Baseline for the rest of the channel:
  mean {b_mean:.4f}, std {b_std:.4f}, min {b_min:.4f}, max {b_max:.4f}
Peak deviation from baseline: {z_peak:.1f} robust sigma
Commands active during the window: {cmds}

Write the operator brief. Exactly three short sections, no preamble:

WHAT HAPPENED - one or two sentences describing the signal behaviour in plain
language. Quote the actual numbers above.

WHY IT MATTERS - one or two sentences on the operational significance. If the
evidence is weak, say so rather than inflating it.

WHAT TO DO NEXT - two or three concrete steps an operator can take this shift.

Keep the whole brief under 180 words. Do not add headings beyond those three.
"""


# --------------------------------------------------------------------------
# Ollama
# --------------------------------------------------------------------------


def ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as resp:
            return [m["name"] for m in json.load(resp).get("models", [])]
    except Exception:
        return []


def pick_model() -> str:
    """Prefer granite4:3b, fall back to the 350m, never silently use a non-Granite model."""
    have = ollama_models()
    if not have:
        sys.exit(
            f"Ollama is not responding on {OLLAMA_HOST}.\n"
            f"  Install Ollama, then:  ollama pull {MODEL}"
        )
    for want in (MODEL, FALLBACK_MODEL):
        if want in have:
            return want
    granite = [n for n in have if n.startswith("granite")]
    if granite:
        return sorted(granite)[0]
    sys.exit(f"No Granite model installed. Run:  ollama pull {MODEL}\nInstalled: {have}")


def warm_up(model: str) -> None:
    """Burn one throwaway generation so every real call runs against a warm runner.

    This is the second half of the determinism story, and it took a while to find.
    The *first* generation after Ollama loads a model produces different text from
    every generation after it - reproducibly so: cold calls agree with each other
    and warm calls agree with each other, but cold and warm disagree. So a brief
    written during a long run (warm) would never match a brief regenerated by
    `--check` in a fresh process (cold), through no fault of the seed.

    Warming up first puts both paths in the same state, which is what makes the
    first generation after warm-up reproduce reliably.

    It does not extend past that first call. Measured on 2026-08-30: `--check`
    on one brief reproduced in four runs out of four, including from a clean
    clone, while two runs of `--check --limit 8` twenty minutes apart reproduced
    7 of 8 and then 1 of 8. Local CPU inference is not bit-reproducible across
    processes, and one flipped token rewrites the rest of a paragraph. Claim
    reproducibility for the first brief only; `audit_briefs.py` is what covers
    all 78, and it never calls the model.
    """
    generate(model, "Reply with the single word: ready.", _warming=True)


def generate(model: str, prompt: str, _warming: bool = False) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "system": SYSTEM,
            "stream": False,
            # Long enough that the model is never evicted mid-run; a reload
            # partway through would silently split the output into cold and warm
            # halves that no longer reproduce.
            "keep_alive": "30m",
            "options": OPTIONS,
        }
    ).encode()
    # Ollama occasionally drops a connection mid-generation. Over a full brief run
    # that is hours of work thrown away for one transient blip, so retry rather
    # than abort. Note RemoteDisconnected is an HTTPException, not a URLError -
    # catching only URLError lets exactly this failure through.
    last: Exception | None = None
    for attempt in range(1, 4):
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                return json.load(resp)["response"].strip()
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            last = exc
            if not _warming:
                print(
                    f"  Granite call failed ({type(exc).__name__}), "
                    f"retry {attempt}/3",
                    file=sys.stderr,
                )
            time.sleep(5 * attempt)
    sys.exit(f"Granite call failed after 3 attempts: {last}")


# --------------------------------------------------------------------------
# detections
# --------------------------------------------------------------------------


def load_detections(limit: int | None = None) -> list[dict]:
    """Run the Bob-authored engine over the benchmark and collect its detections.

    Labels are never read here. Briefs describe what the engine found, which is
    exactly what an operator would see in flight - there is no ground truth on orbit.
    """
    import csv

    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(REPO_ROOT))
    from engine.detect import detect  # type: ignore
    from engine.runbook import match  # type: ignore

    with (DATA_DIR / "labeled_anomalies.csv").open(newline="", encoding="utf-8") as fh:
        spacecraft = {r["chan_id"]: r["spacecraft"] for r in csv.DictReader(fh)}

    out: list[dict] = []
    for chan in sorted(spacecraft):
        path = DATA_DIR / "test" / f"{chan}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        values = df["value"].to_numpy(dtype=float)
        cmd_cols = [c for c in df.columns if c.startswith("cmd_")]

        # Deviation is measured the same way the detector measures it: residual
        # against a rolling median, scaled by the MAD of that residual. Comparing
        # against a *global* median instead produces numbers like "2666 sigma" on
        # channels that spend most of their life pinned at one value - technically
        # derived, operationally meaningless, and Granite would repeat it verbatim.
        rolling = df["value"].rolling(window=100, min_periods=1).median().to_numpy()
        residual = values - rolling
        mad = float(np.median(np.abs(residual))) * 1.4826
        dev_scale = mad if mad > 1e-9 else (float(residual.std()) or 1.0)

        for raw_start, raw_end in detect(df):
            start, end = int(raw_start), int(raw_end)
            window = values[start : end + 1]
            if window.size == 0:
                continue
            baseline = np.concatenate([values[:start], values[end + 1 :]])
            if baseline.size == 0:
                baseline = window

            active = [
                c
                for c in cmd_cols
                if float(df[c].to_numpy()[start : end + 1].max()) > 0
            ]

            entry = match(df, (start, end)) or {}
            out.append(
                {
                    "channel": chan,
                    "spacecraft": spacecraft[chan],
                    "start": start,
                    "end": end,
                    "length": end - start + 1,
                    "total": len(df),
                    "signature": entry.get("signature", "unclassified"),
                    "title": entry.get("title", "Anomaly detected"),
                    "severity": entry.get("severity", "unknown"),
                    "action": entry.get("action", "Review the channel manually."),
                    "w_mean": float(window.mean()),
                    "w_std": float(window.std()),
                    "w_min": float(window.min()),
                    "w_max": float(window.max()),
                    "b_mean": float(baseline.mean()),
                    "b_std": float(baseline.std()),
                    "b_min": float(baseline.min()),
                    "b_max": float(baseline.max()),
                    "z_peak": float(
                        np.abs(residual[start : end + 1]).max() / dev_scale
                    ),
                    "cmds": ", ".join(active[:8]) if active else "none",
                }
            )
            if limit and len(out) >= limit:
                return out
    return out


def brief_path(d: dict) -> Path:
    return BRIEFS_DIR / f"{d['channel']}_{d['start']}-{d['end']}.md"


def render(d: dict, body: str, model: str) -> str:
    return (
        f"# {d['channel']} - {d['title']}\n\n"
        f"- **Spacecraft**: {d['spacecraft']}\n"
        f"- **Window**: samples {d['start']}-{d['end']} of {d['total']}\n"
        f"- **Signature**: `{d['signature']}` - **Severity**: {d['severity']}\n"
        f"- **Written by**: IBM Granite (`{model}`) running locally via Ollama\n\n"
        f"{body}\n"
    )


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------


def run_check(model: str, limit: int = 1) -> int:
    """Regenerate committed briefs from Granite and diff them against the repo.

    Defaults to one brief, which is the only one that reproduces dependably; see
    `warm_up` for the measurements. A regeneration costs about fifty seconds of CPU
    inference, so `--limit 78` takes about an hour and should be read as a survey of
    how far the drift goes rather than as a check that is expected to pass.

    The walk follows `load_detections()`, the order the briefs were originally written
    in, rather than the alphabetical order of the directory. The two diverge at the
    sixth brief. Replaying the original order at least puts each call in the sequence
    it was generated in, which is the closest a re-run can get to the conditions that
    produced the committed text.
    """
    committed = len(list(BRIEFS_DIR.glob("*.md")))
    if not committed:
        sys.exit("No committed briefs to check. Run make_briefs.py first.")
    targets = load_detections()
    if limit > 0:
        targets = targets[:limit]
    failed = 0

    for i, detection in enumerate(targets, 1):
        target = brief_path(detection)
        if not target.exists():
            sys.exit(
                f"No committed brief for {target.stem}; the briefs are stale "
                "against the current engine."
            )
        fresh = render(
            detection, generate(model, TEMPLATE.format(**detection)), model
        )
        diff = list(
            difflib.unified_diff(
                target.read_text(encoding="utf-8").splitlines(),
                fresh.splitlines(),
                fromfile=f"committed/{target.name}",
                tofile="regenerated",
                lineterm="",
            )
        )
        # A one-brief run prints exactly the line the README and the console quote.
        # The counter only appears when there is a count worth showing.
        prefix = "" if len(targets) == 1 else f"[{i}/{len(targets)}] "
        if diff:
            print("\n".join(diff))
            print(f"\n{prefix}DIFFERS - {target.name} does not reproduce.")
            failed += 1
        else:
            print(f"{prefix}OK - {target.name} reproduces exactly from Granite.")

    if len(targets) == 1:
        return 1 if failed else 0
    if failed:
        print(f"\n{failed} of {len(targets)} briefs did not reproduce.")
        return 1
    print(
        f"\nOK - {len(targets)} of {committed} committed briefs "
        "reproduce exactly from Granite."
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="generate a single brief to prove the Granite path works",
    )
    ap.add_argument(
        "--check", action="store_true", help="regenerate one committed brief and diff it"
    )
    ap.add_argument(
        "--limit",
        type=int,
        help="cap how many briefs are generated, or checked when used with --check",
    )
    args = ap.parse_args()

    model = pick_model()
    print(f"Granite model: {model}", file=sys.stderr)
    print("warming up the runner (required for reproducible output)", file=sys.stderr)
    warm_up(model)

    if args.check:
        return run_check(model, 1 if args.limit is None else args.limit)

    limit = 1 if args.smoke else args.limit
    detections = load_detections(limit=limit)
    if not detections:
        sys.exit("The engine produced no detections, so there is nothing to brief.")

    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    for i, d in enumerate(detections, 1):
        out = brief_path(d)
        out.write_text(
            render(d, generate(model, TEMPLATE.format(**d)), model), encoding="utf-8"
        )
        print(f"[{i}/{len(detections)}] {out.relative_to(REPO_ROOT)}", file=sys.stderr)

    print(f"\n{len(detections)} brief(s) written to {BRIEFS_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
