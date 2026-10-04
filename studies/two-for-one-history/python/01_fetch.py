"""Fetch season play-by-play from the shufinskiy/nba_data bulk mirror of
stats.nba.com (PlayByPlayV2 schema) and slim each season to a parquet with
only the columns this study reads. Resumable: existing parquets are skipped.

  NBA  : nbastats_1996 .. nbastats_2024   (1996-97 .. 2024-25)
  WNBA : wnba_nbastats_1997 .. wnba_nbastats_2026
  Validation: pbpstats_<yr> / wnba_pbpstats_<yr> possession rows (selected years)

Run: python python/01_fetch.py [--only nba|wnba|pbpstats]
"""
from __future__ import annotations

import argparse
import io
import lzma
import tarfile
import urllib.request
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://raw.githubusercontent.com/shufinskiy/nba_data/main/datasets/"

KEEP = ["GAME_ID", "EVENTNUM", "EVENTMSGTYPE", "EVENTMSGACTIONTYPE", "PERIOD",
        "PCTIMESTRING", "HOMEDESCRIPTION", "NEUTRALDESCRIPTION",
        "VISITORDESCRIPTION", "SCORE", "PERSON1TYPE", "PLAYER1_ID",
        "PLAYER1_TEAM_ID", "PLAYER1_TEAM_ABBREVIATION", "PERSON3TYPE",
        "PLAYER3_TEAM_ID"]

NBA = [f"nbastats_{y}" for y in range(1996, 2025)]
WNBA = [f"wnba_nbastats_{y}" for y in range(1997, 2027)]
PBPSTATS = ["pbpstats_2023", "pbpstats_2012", "pbpstats_2001",
            "wnba_pbpstats_2024", "wnba_pbpstats_2012"]


def fetch(name: str) -> None:
    out = RAW / f"{name}.parquet"
    if out.exists():
        return
    with urllib.request.urlopen(BASE + f"{name}.tar.xz", timeout=300) as r:
        blob = r.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:xz") as tf:
        member = next(m for m in tf.getmembers() if m.name.endswith(".csv"))
        csv = tf.extractfile(member).read()
    df = pl.read_csv(io.BytesIO(csv), infer_schema_length=0)
    if not name.startswith(("pbpstats", "wnba_pbpstats")):
        df = df.select([c for c in KEEP if c in df.columns])
    df.write_parquet(out)
    print(f"{name}: {df.height:,} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["nba", "wnba", "pbpstats"])
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    groups = {"nba": NBA, "wnba": WNBA, "pbpstats": PBPSTATS}
    for g, names in groups.items():
        if a.only and a.only != g:
            continue
        for n in names:
            try:
                fetch(n)
            except Exception as e:  # noqa: BLE001 - report and continue
                print(f"{n}: FAILED {e!r}")


if __name__ == "__main__":
    main()
