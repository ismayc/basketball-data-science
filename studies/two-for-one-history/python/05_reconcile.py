"""Reconcile gate: Python and R decision tables must agree window by window.

Joins output/decisions.parquet (python/02_decisions.py) with
output/decisions_r.parquet (R/02_decisions.R) on league, year, mark kind,
game and period, then requires exact agreement on every compared column
(numeric columns within 1e-9; nulls must match nulls). Exits non-zero on any
mismatch, on any window present in only one table, or on a row-count change.

Run: python python/05_reconcile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
KEYS = ["league", "year", "mark_kind", "GAME_ID", "period"]
COLS = ["mark", "owner", "pending", "team_id", "poss_start_t", "first_act_t", "choice",
        "own_pts", "opp_pts", "net_pts", "owner_used", "opp_used", "got_last_used",
        "owner_later", "opp_poss"]


def main() -> None:
    py = pl.read_parquet(OUT / "decisions.parquet").select(KEYS + COLS)
    r = pl.read_parquet(OUT / "decisions_r.parquet").select(KEYS + COLS)
    r = r.with_columns(pl.col("year").cast(py.schema["year"]),
                       pl.col("period").cast(py.schema["period"]))
    j = py.join(r, on=KEYS, how="full", suffix="_r", coalesce=True)
    problems = []
    only = j.filter(pl.col("mark").is_null() | pl.col("mark_r").is_null())
    if only.height:
        problems.append(f"{only.height} windows present in only one table")
    for c in COLS:
        a, b = pl.col(c), pl.col(f"{c}_r")
        if py.schema[c].is_numeric():
            a, b = a.cast(pl.Float64), b.cast(pl.Float64)
            bad = ~(((a - b).abs() <= 1e-9) | (a.is_null() & b.is_null()))
        else:
            bad = ~((a.cast(pl.String) == b.cast(pl.String)) | (a.is_null() & b.is_null()))
        n = j.filter(bad.fill_null(True)).height
        print(f"{c:15s} mismatches: {n}")
        if n:
            problems.append(f"{c}: {n} mismatches")
    print(f"windows compared: {j.height:,} (python {py.height:,}, R {r.height:,})")
    if problems:
        print("RECONCILE FAILED: " + "; ".join(problems))
        sys.exit(1)
    print("reconcile passed: Python and R agree on every window")


if __name__ == "__main__":
    main()
