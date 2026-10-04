#!/usr/bin/env bash
# Every gate for this study; non-zero exit on the first failure.
set -euo pipefail
cd "$(dirname "$0")"
python python/05_reconcile.py      # Python vs R, every window
python python/03_validate.py       # reconstruction vs pbpstats
python python/07_findings.py --check  # README numbers match output/
