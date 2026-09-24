"""Download the public labelled datasets used to train SENTINEL's baseline models.

    python scripts/fetch_datasets.py

Datasets (from the UCI Machine Learning Repository, CC BY 4.0):
  * SMS Spam Collection  (Almeida & Hidalgo, 2011)       -> data/raw/sms_spam/SMSSpamCollection
  * PhiUSIIL Phishing URL Dataset (Prasad & Chandra, 2024) -> data/raw/phiusiil/PhiUSIIL_Phishing_URL_Dataset.csv
Plus the Tranco top-1M list (tranco-list.eu) -> data/raw/tranco/top-1m.csv, used
to supplement the URL model's legitimate class with real popular domains.

Only zip archives from the fixed URLs below are fetched; members are extracted
with path-traversal protection. Nothing is executed.
"""

from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

DATASETS = {
    "sms_spam": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip",
    "phiusiil": "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip",
    # Tranco research top-sites ranking (Le Pochat et al., NDSS 2019) — popular, legitimate domains.
    "tranco": "https://tranco-list.eu/top-1m.csv.zip",
}
MAX_BYTES = 120 * 1024 * 1024


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> list[str]:
    dest = dest.resolve()
    names = []
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if not str(target).startswith(str(dest)):
            raise RuntimeError(f"Refusing unsafe path in archive: {member.filename}")
        if member.is_dir():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(target, "wb") as out:
            out.write(src.read())
        names.append(member.filename)
    return names


def fetch(name: str, url: str) -> None:
    dest = RAW / name
    if dest.exists() and any(dest.iterdir()):
        print(f"[skip] {name}: already present at {dest}")
        return
    print(f"[get ] {name}: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "sentinel-dataset-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError(f"{name}: archive larger than expected, aborting")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = _safe_extract(zf, dest)
    print(f"[ok  ] {name}: {len(data) / 1e6:.1f} MB, extracted {names}")


def main(which: list[str]) -> int:
    for name in which or DATASETS:
        try:
            fetch(name, DATASETS[name])
        except Exception as exc:  # keep going; training scripts degrade gracefully
            print(f"[fail] {name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
