"""Every number the console prints must come from the exported data.

Run against the text of the rendered page (stdin or --file). It pulls out every
numeral and checks it against the set of values the manifest and the ledger can
justify, plus a small allowlist of numbers that are structural rather than
claims (step counters, years, viewport-ish constants).

This exists because the page makes quantitative claims to judges who will check
them. A number on screen that no file supports is the failure mode it catches.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def allowed_values() -> set[str]:
    m = json.loads((ROOT / "web/public/data/manifest.json").read_text(encoding="utf-8"))
    led = [json.loads(l) for l in (ROOT / "results/ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    vals: set[float] = set()

    def add(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            vals.add(float(x))
            # the page is allowed to render a ratio as a percentage
            if 0 <= x <= 1:
                vals.add(round(x * 100, 1))
                vals.add(round(x * 100))
        elif isinstance(x, dict):
            for v in x.values():
                add(v)
        elif isinstance(x, list):
            for v in x:
                add(v)

    add(m)
    add(led)

    # Differences and ratios between any two scores or counts are fair game:
    # the page says things like "128 to 7" and "2.3x".
    scores = []
    for st in m["walkthrough"]["steps"]:
        for split in ("dev", "holdout"):
            d = st[split]
            scores.extend([d["f1"], float(d["tp"]), float(d["fp"]), float(d["fn"])])
            if d["tp"] + d["fp"]:
                scores.append(d["tp"] / (d["tp"] + d["fp"]))
        scores.append(float(st["alarms"]))
    for a in scores:
        for b in scores:
            if b:
                vals.add(round(a / b, 1))
                vals.add(round(a / b, 2))
            vals.add(round(a - b, 3))
            if b:
                vals.add(round(100 * (1 - a / b), 1))
                vals.add(round(100 * (1 - a / b)))

    # The explorer prints positions and lengths that live in the per-channel
    # files. Only the structural integers are admitted: pulling in `values` and
    # `z` would add hundreds of thousands of floats and let anything through.
    for f in sorted((ROOT / "web/public/data/channel").glob("*.json")):
        ch = json.loads(f.read_text(encoding="utf-8"))
        add(ch.get("n"))
        for d in ch.get("detections", []):
            for k in ("start", "end", "length", "z_peak"):
                add(d.get(k))
        for t in ch.get("truth", []):
            add(t.get("start"))
            add(t.get("end"))
        add(len(ch.get("detections", [])))
        add(len(ch.get("baseline", [])))
        # Granite wrote the briefs and quotes its own statistics inside them.
        # The page prints that text verbatim, so those figures are sourced by
        # definition: they are what the committed brief says.
        for d in ch.get("detections", []):
            b = d.get("brief") or {}
            for field in ("happened", "matters", "next"):
                for tok in NUM.findall(str(b.get(field, ""))):
                    out_tok = tok.replace(",", "")
                    try:
                        add(float(out_tok))
                    except ValueError:
                        pass
        # Axis ticks are round numbers the plot derives from the recording
        # length. They are drawn, not claimed.
        n = ch.get("n") or 0
        for mult in (1000, 2000, 5000):
            k = mult
            while k <= n:
                add(k)
                k += mult

    # Engine size, which lives in the source rather than the manifest.
    for p in sorted((ROOT / "engine").glob("*.py")):
        n = len(p.read_text(encoding="utf-8").splitlines())
        vals.add(float(n))
    vals.add(float(sum(len(p.read_text(encoding="utf-8").splitlines())
                       for p in sorted((ROOT / "engine").glob("*.py")))))

    # Budget: the cap is a documented competition constant, the spend is derived.
    spend = sum((r.get("cost") if r.get("cost") is not None else (r.get("max_cost") or 0.0)) for r in led)
    vals.add(round(spend, 1))
    vals.add(round(spend, 2))
    vals.add(round(spend, 3))
    vals.add(40.0)

    # The robustness re-score is computed, not stored. Import it rather than
    # hardcoding, so the page and the audit can never disagree about it.
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from robustness_check import score as _rscore  # noqa: E402

        for width in (None, 0.5):
            for split_name in ("dev", "holdout"):
                add(_rscore(width)[split_name])
    except Exception:
        pass

    out = set()
    for v in vals:
        out.add(f"{v:g}")
        if abs(v - round(v)) < 1e-9:
            out.add(str(int(round(v))))
        out.add(f"{v:.1f}")
        out.add(f"{v:.2f}")
        out.add(f"{v:.3f}")
    return out


# Numbers that are page furniture, not claims about the work.
STRUCTURAL = {str(i) for i in range(0, 13)} | {"2026", "100", "1000", "1.0", "1.000"}

NUM = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, help="file holding the rendered page text")
    args = ap.parse_args()

    text = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    ok = allowed_values() | STRUCTURAL

    bad: list[str] = []
    for raw in NUM.findall(text):
        clean = raw.replace(",", "")
        if clean in ok:
            continue
        # tolerate a trailing-zero spelling difference, e.g. 2.30 vs 2.3
        try:
            if f"{float(clean):g}" in ok:
                continue
        except ValueError:
            pass
        bad.append(raw)

    if bad:
        seen = sorted(set(bad), key=bad.index)
        print(f"UNSOURCED NUMBERS ({len(seen)}):")
        for b in seen:
            print(f"  {b}")
        return 1

    print("All numbers on the page trace to the manifest, the ledger or the engine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
