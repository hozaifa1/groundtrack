"""Fetch the labelled NASA SMAP/MSL telemetry benchmark.

Source
------
Telemanom (Hundman et al., "Detecting Spacecraft Anomalies Using LSTMs and
Nonparametric Dynamic Thresholding", KDD 2018). Apache-2.0.

  labels    : github.com/khundman/telemanom  -> labeled_anomalies.csv
  telemetry : huggingface.co/datasets/appleparan/telemanom (parquet mirror)

The original S3 bundle (s3-us-west-2.amazonaws.com/telemanom/data.zip) now returns
403, and the upstream README points at Kaggle, which requires an API token. The
Hugging Face parquet mirror needs no key, no account, and no credit card, and the
whole benchmark is ~9 MB - small enough to commit, so a judge can clone the repo
and reproduce every number offline with zero external calls.

Usage
-----
    python tools/fetch_data.py            # fetch everything
    python tools/fetch_data.py --check    # verify what is already on disk
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "telemanom"

LABELS_URL = (
    "https://raw.githubusercontent.com/khundman/telemanom/master/labeled_anomalies.csv"
)
HF_BASE = "https://huggingface.co/datasets/appleparan/telemanom/resolve/main/data"

TIMEOUT = 60
MAX_WORKERS = 8


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "groundtrack/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def fetch_labels() -> Path:
    """Download the ground-truth anomaly windows."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / "labeled_anomalies.csv"
    dest.write_bytes(_get(LABELS_URL))
    return dest


def channel_ids(labels_csv: Path) -> list[str]:
    with labels_csv.open(newline="", encoding="utf-8") as fh:
        return [row["chan_id"] for row in csv.DictReader(fh)]


def _fetch_channel(split: str, chan: str) -> tuple[str, str, int | None, str | None]:
    dest = DATA_DIR / split / f"{chan}.parquet"
    if dest.exists() and dest.stat().st_size > 0:
        return split, chan, dest.stat().st_size, None
    try:
        payload = _get(f"{HF_BASE}/{split}/{chan}.parquet")
    except urllib.error.HTTPError as exc:
        return split, chan, None, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report, do not crash the batch
        return split, chan, None, str(exc)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    return split, chan, len(payload), None


def fetch_telemetry(chans: list[str]) -> list[str]:
    """Download train/test parquet for every channel. Returns list of failures."""
    jobs = [(split, chan) for split in ("train", "test") for chan in chans]
    failures: list[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_channel, s, c): (s, c) for s, c in jobs}
        for fut in as_completed(futures):
            split, chan, _size, err = fut.result()
            done += 1
            if err:
                failures.append(f"{split}/{chan}: {err}")
            if done % 40 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} files", flush=True)
    return failures


def check() -> int:
    labels = DATA_DIR / "labeled_anomalies.csv"
    if not labels.exists():
        print("MISSING labeled_anomalies.csv - run without --check first")
        return 1
    chans = channel_ids(labels)
    total_bytes = 0
    missing: list[str] = []
    for split in ("train", "test"):
        for chan in chans:
            p = DATA_DIR / split / f"{chan}.parquet"
            if p.exists():
                total_bytes += p.stat().st_size
            else:
                missing.append(f"{split}/{chan}")
    print(f"channels          : {len(chans)}")
    print(f"telemetry files   : {2 * len(chans) - len(missing)}/{2 * len(chans)}")
    print(f"on-disk size      : {total_bytes / 1e6:.1f} MB")
    if missing:
        print(f"MISSING ({len(missing)}): {', '.join(missing[:10])}")
        return 1
    print("OK - benchmark complete")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify local data only")
    args = ap.parse_args()

    if args.check:
        return check()

    print("Fetching ground-truth labels ...")
    labels = fetch_labels()
    chans = channel_ids(labels)
    print(f"  {len(chans)} channels labelled")

    print(f"Fetching telemetry for {len(chans)} channels (train + test) ...")
    failures = fetch_telemetry(chans)
    if failures:
        print(f"\n{len(failures)} download(s) failed:", file=sys.stderr)
        for f in failures[:20]:
            print(f"  {f}", file=sys.stderr)
        return 1

    print()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
