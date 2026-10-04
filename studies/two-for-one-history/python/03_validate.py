"""External gate: the hand-built possession reconstruction in 02_decisions.py
against pbpstats' independent possession parser, on every league-season where
both exist in the bulk archive and were fetched (NBA 2001-02, 2012-13,
2023-24; WNBA 2012, 2024).

For each game-period window, pbpstats' ball-holder at the decision mark is the
possession whose clock span contains it (start > T >= end). Compared:
  owner_agree     : same team holds the ball at the mark
  end_within_2s   : decision possession ends within 2 s of pbpstats' end
  opp_poss_agree  : same count of opponent USED possessions from the mark
                    (pbpstats rows exist only for possessions with events)

Exits non-zero if owner agreement falls below 97% in any season: every
downstream number rests on knowing who faced the decision.

Output: output/validation_pbpstats.csv
Run: python python/03_validate.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"

spec = importlib.util.spec_from_file_location("dec", ROOT / "python" / "02_decisions.py")
dec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dec)

CASES = [("NBA", 2001), ("NBA", 2012), ("NBA", 2023), ("WNBA", 2012), ("WNBA", 2024)]
OWNER_GATE = 0.97


def mmss(col: str) -> pl.Expr:
    p = pl.col(col).str.split(":")
    return p.list.get(0).cast(pl.Float64) * 60 + p.list.get(1).cast(pl.Float64)


def pbpstats_windows(league: str, year: int, T: float, periods: list[int],
                     teams: pl.DataFrame) -> pl.DataFrame:
    name = f"{'wnba_' if league == 'WNBA' else ''}pbpstats_{year}.parquet"
    raw = pl.read_parquet(RAW / name)
    poss = (raw.unique(subset=["GAMEID", "PERIOD", "STARTTIME", "ENDTIME", "OPPONENT"])
            .with_columns(gid=pl.col("GAMEID").cast(pl.Int64),
                          period=pl.col("PERIOD").cast(pl.Int32),
                          s=mmss("STARTTIME"), e=mmss("ENDTIME"))
            .filter(pl.col("period").is_in(periods)))
    teams = teams.with_columns(gid=pl.col("GAME_ID").cast(pl.Int64))
    poss = (poss.join(teams.select("gid", "h_team", "v_team"), on="gid", how="inner")
            .with_columns(pb_owner=pl.when(pl.col("OPPONENT") == pl.col("h_team"))
                          .then(pl.lit("v"))
                          .when(pl.col("OPPONENT") == pl.col("v_team"))
                          .then(pl.lit("h"))))
    at = (poss.filter(pl.col("s") > T, pl.col("e") <= T)
          .group_by("gid", "period")
          .agg(pb_owner=pl.col("pb_owner").first(), pb_end=pl.col("e").first(),
               n_span=pl.len()))
    later = (poss.filter(pl.col("s") <= T, pl.col("s") > 0)
             .group_by("gid", "period").agg(pb_owner_starts=pl.col("pb_owner")))
    return at.join(later, on=["gid", "period"], how="left")


def main() -> None:
    rows, failed = [], False
    for league, year in CASES:
        r = dec.rules(league, year)
        T = float(r["shot_clock"] + 16)
        df = dec.prepare(pl.read_parquet(
            RAW / f"{'wnba_' if league == 'WNBA' else ''}nbastats_{year}.parquet"))
        teams = dec.team_map(df)
        mine = (dec.windows(df, T, r["shot_clock"], r["periods"])
                .filter(pl.col("owner").is_not_null(), ~pl.col("pending"))
                .with_columns(gid=pl.col("GAME_ID").cast(pl.Int64)))
        pb = pbpstats_windows(league, year, T, r["periods"], teams)
        j = mine.join(pb, on=["gid", "period"], how="inner").filter(pl.col("n_span") == 1)
        # opponent possessions per pbpstats: starts after the mark not by the owner
        j = j.with_columns(pb_opp_poss=pl.struct("pb_owner_starts", "pb_owner").map_elements(
            lambda x: sum(1 for o in (x["pb_owner_starts"] or []) if o != x["pb_owner"]),
            return_dtype=pl.Int64))
        owner_agree = (j["owner"] == j["pb_owner"]).mean()
        same = j.filter(pl.col("owner") == pl.col("pb_owner"))
        end_ok = ((same["end_t"].fill_null(0) - same["pb_end"]).abs() <= 2).mean()
        opp_ok = (same["opp_used"] == same["pb_opp_poss"]).mean()
        row = dict(league=league, season=dec.season_label(league, year),
                   windows_mine=mine.height, windows_pbpstats=pb.height,
                   matched=j.height, owner_agree=round(owner_agree, 4),
                   end_within_2s=round(end_ok, 4), opp_poss_agree=round(opp_ok, 4))
        rows.append(row)
        print(row)
        if owner_agree < OWNER_GATE:
            failed = True
    OUT.mkdir(exist_ok=True)
    pl.DataFrame(rows).write_csv(OUT / "validation_pbpstats.csv")
    if failed:
        print(f"GATE FAILED: owner agreement below {OWNER_GATE:.0%}")
        sys.exit(1)
    print("gate passed")


if __name__ == "__main__":
    main()
