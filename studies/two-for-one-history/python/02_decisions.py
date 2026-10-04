"""Build the end-of-period decision table for every league-season.

Design (the decision-team frame from playbyplay-study Finding 4, generalized
across leagues and eras):

    At the decision mark T = shot_clock + 16 seconds left in a non-final
    regulation period, exactly one team has the ball. That team faces the
    2-for-1 choice. Record:
      - when it first acts after the mark (FGA, turnover, or first FT of a
        trip): the CHOICE. quick = first act with >= shot_clock + 4 left,
        i.e. early enough that the opponent's full shot clock still expires
        before the buzzer.
      - possessions each side gets from the mark to the buzzer (the mechanism)
      - points each side scores from the mark to the buzzer (the payoff)

Shot clock / period structure by league-season (rule history, asserted
against the data where it is checkable):
    NBA  1996-97 .. 2024-25 : 24 s clock, 4 x 12 min      -> T = 40, Q1-Q3
    WNBA 1997 .. 2005       : 30 s clock, 2 x 20 min halves -> T = 46, H1 only
    WNBA 2006 ..            : 24 s clock, 4 x 10 min      -> T = 40, Q1-Q3

Possession is reconstructed from PlayByPlayV2 events (no possession field in
the feed):
    made FG by X           -> Y has the ball
    missed FG by X         -> X (pending the rebound)
    rebound by Z           -> Z  (team rebounds included)
    turnover by X          -> Y
    FT by X, last of trip  -> Y if made, else X pending the rebound
    jump ball             -> side of the player the ball is tipped to
Technical / flagrant FTs leave possession unchanged. Side comes from
PERSON1TYPE (4/2 = home, 5/3 = visitor), which is robust to the two
description columns both being populated on blocks and steals.

Windows whose ball-holder at the mark is "pending" (a shot in the air or an
unresolved missed FT) are flagged and excluded downstream: the true decision
team is unknowable from the feed there.

Input : data/raw/{nbastats,wnba_nbastats}_<yr>.parquet
Output: output/decisions.parquet (one row per game-period window)

Run: python python/02_decisions.py
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"

LAST_FT = ["10", "12", "15"]          # 1 of 1, 2 of 2, 3 of 3
TRIP_FT = ["10", "11", "12", "13", "14", "15"]
FIRST_FT = ["10", "11", "13"]
PLACEBO_OFFSET = 120.0


def rules(league: str, year: int) -> dict:
    if league == "NBA":
        return dict(shot_clock=24, periods=[1, 2, 3], period_min=12)
    if year <= 2005:
        return dict(shot_clock=30, periods=[1], period_min=20)
    return dict(shot_clock=24, periods=[1, 2, 3], period_min=10)


def season_label(league: str, year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}" if league == "NBA" else str(year)


def prepare(df: pl.DataFrame) -> pl.DataFrame:
    side1 = (pl.when(pl.col("PERSON1TYPE").is_in(["4", "2"])).then(pl.lit("h"))
             .when(pl.col("PERSON1TYPE").is_in(["5", "3"])).then(pl.lit("v")))
    side3 = (pl.when(pl.col("PERSON3TYPE").is_in(["4", "2"])).then(pl.lit("h"))
             .when(pl.col("PERSON3TYPE").is_in(["5", "3"])).then(pl.lit("v")))
    other = pl.when(side1 == "h").then(pl.lit("v")).when(side1 == "v").then(pl.lit("h"))
    desc = pl.coalesce(pl.when(side1 == "h").then(pl.col("HOMEDESCRIPTION"))
                       .otherwise(pl.col("VISITORDESCRIPTION")), pl.lit(""))
    typ, act = pl.col("EVENTMSGTYPE"), pl.col("EVENTMSGACTIONTYPE")
    ft_made = ~desc.str.contains("MISS")
    clock = pl.col("PCTIMESTRING").str.split(":")

    df = (df.with_columns(
            period=pl.col("PERIOD").cast(pl.Int32),
            eventnum=pl.col("EVENTNUM").cast(pl.Int64),
            t=(clock.list.get(0).cast(pl.Float64) * 60
               + clock.list.get(1).cast(pl.Float64)),
            side=side1)
          # chronological order is clock-descending within period. EVENTNUM is
          # NOT chronological in this feed (late-logged events carry a high
          # EVENTNUM with an early clock), and must be compared numerically
          # (the family's text-sort bug) when it breaks clock ties.
          .sort(["GAME_ID", "period", "t", "eventnum"],
                descending=[False, False, True, False]))

    sc = pl.col("SCORE").str.split(" - ")
    df = df.with_columns(
        offense_after=(
            pl.when(typ == "1").then(other)
            .when(typ == "2").then(side1)
            .when(typ == "4").then(side1)
            .when(typ == "5").then(other)
            .when((typ == "3") & act.is_in(LAST_FT) & ft_made).then(other)
            .when((typ == "3") & act.is_in(TRIP_FT)).then(side1)
            .when(typ == "10").then(side3)),
        pending=((typ == "2") | ((typ == "3") & act.is_in(LAST_FT) & ~ft_made)),
        owner_act=((typ.is_in(["1", "2", "5"]))
                   | ((typ == "3") & act.is_in(FIRST_FT))),
        # SCORE is "visitor - home"; forward-filled across the whole game
        v_score=sc.list.get(0, null_on_oob=True).cast(pl.Int32, strict=False),
        h_score=sc.list.get(1, null_on_oob=True).cast(pl.Int32, strict=False),
    ).with_columns(
        pl.col("v_score", "h_score").forward_fill().over("GAME_ID").fill_null(0))

    # ownership timeline within each period; a "start" is a change of hands
    df = df.with_columns(
        own=pl.col("offense_after").forward_fill().over(["GAME_ID", "period"]),
        relevant=pl.col("offense_after").is_not_null())
    df = df.with_columns(
        prev_own=pl.col("own").shift(1).over(["GAME_ID", "period"]))
    df = df.with_columns(
        is_start=(pl.col("own").is_not_null()
                  & (pl.col("prev_own").is_null() | (pl.col("own") != pl.col("prev_own")))))
    # possession index within the period; a possession is "used" if its team
    # logs a shot, turnover, or FT trip in it and it began with >= 2 s left
    # An act (make, turnover, ...) belongs to the possession held just BEFORE
    # the event: a make flips ownership on its own row.
    df = df.with_columns(
        poss_id=pl.col("is_start").cast(pl.Int32).cum_sum().over(["GAME_ID", "period"]))
    df = df.with_columns(
        start_t=pl.when(pl.col("is_start")).then(pl.col("t"))
        .forward_fill().over(["GAME_ID", "period"]))
    return df.with_columns(
        act_poss=pl.col("poss_id") - pl.col("is_start").cast(pl.Int32),
        # start time of the possession an act belongs to; a possession that
        # begins with under 2 s left (inbound heave) does not count as used.
        # This matches pbpstats' possession rows ~90% of the time (03_validate)
        act_start_t=pl.when(pl.col("is_start"))
        .then(pl.col("start_t").shift(1).over(["GAME_ID", "period"]))
        .otherwise(pl.col("start_t")))


def team_map(df: pl.DataFrame) -> pl.DataFrame:
    """Home/visitor team id + abbreviation per game, from player events."""
    p = df.filter(pl.col("PERSON1TYPE").is_in(["4", "5"]),
                  pl.col("PLAYER1_TEAM_ID").is_not_null())
    g = (p.group_by("GAME_ID", "PERSON1TYPE")
         .agg(team_id=pl.col("PLAYER1_TEAM_ID").mode().first(),
              team=pl.col("PLAYER1_TEAM_ABBREVIATION").mode().first()))
    h = g.filter(pl.col("PERSON1TYPE") == "4").select(
        "GAME_ID", h_team_id="team_id", h_team="team")
    v = g.filter(pl.col("PERSON1TYPE") == "5").select(
        "GAME_ID", v_team_id="team_id", v_team="team")
    return h.join(v, on="GAME_ID", how="inner")


def windows(df: pl.DataFrame, T: float, sc: int, periods: list[int]) -> pl.DataFrame:
    ev = df.filter(pl.col("period").is_in(periods))
    keys = ["GAME_ID", "period"]

    pre = ev.filter(pl.col("t") > T)
    rel = pre.filter(pl.col("relevant"))
    at_mark = (rel.group_by(keys).agg(
                   owner=pl.col("offense_after").last(),
                   pending=pl.col("pending").last()))
    starts_pre = (pre.filter(pl.col("is_start"))
                  .group_by(keys).agg(poss_start_t=pl.col("t").last()))
    score_mark = pre.group_by(keys).agg(
        h_mark=pl.col("h_score").last(), v_mark=pl.col("v_score").last())

    post = ev.filter(pl.col("t") <= T)
    score_end = ev.group_by(keys).agg(
        h_end=pl.col("h_score").last(), v_end=pl.col("v_score").last(),
        n_events=pl.len(), max_t=pl.col("t").max())

    w = (score_end.join(at_mark, on=keys, how="left")
         .join(starts_pre, on=keys, how="left")
         .join(score_mark, on=keys, how="left"))

    post = post.join(w.select(*keys, "owner"), on=keys, how="left")
    first_act = (post.filter(pl.col("owner_act") & (pl.col("side") == pl.col("owner")))
                 .group_by(keys).agg(first_act_t=pl.col("t").first()))
    # the first change of hands after the mark ends the decision possession
    starts_post = post.filter(pl.col("is_start"))
    end_t = (starts_post.filter(pl.col("own") != pl.col("owner"))
             .group_by(keys).agg(end_t=pl.col("t").first()))
    counts = (starts_post.filter(pl.col("t") > 0)
              .group_by(keys).agg(
                  owner_later=(pl.col("own") == pl.col("owner")).sum(),
                  opp_poss=(pl.col("own") != pl.col("owner")).sum()))
    used = (post.filter(pl.col("owner_act"), pl.col("side") == pl.col("prev_own"),
                        pl.col("act_start_t").fill_null(9) > 1)
            .group_by(keys).agg(
                owner_used=pl.col("act_poss").filter(pl.col("side") == pl.col("owner")).n_unique(),
                opp_used=pl.col("act_poss").filter(pl.col("side") != pl.col("owner")).n_unique(),
                last_used=pl.col("side").last()))
    last_start = (starts_post.filter(pl.col("t") > 0)
                  .group_by(keys).agg(last_poss=pl.col("own").last()))

    w = (w.join(first_act, on=keys, how="left")
         .join(end_t, on=keys, how="left")
         .join(counts, on=keys, how="left")
         .join(used, on=keys, how="left")
         .join(last_start, on=keys, how="left")
         .with_columns(pl.col("owner_later", "opp_poss", "owner_used", "opp_used")
                       .fill_null(0)))

    owner_is_h = pl.col("owner") == "h"
    h_pts = pl.col("h_end") - pl.col("h_mark").fill_null(pl.col("h_end"))
    v_pts = pl.col("v_end") - pl.col("v_mark").fill_null(pl.col("v_end"))
    first = pl.col("first_act_t")
    return w.with_columns(
        own_pts=pl.when(owner_is_h).then(h_pts).otherwise(v_pts),
        opp_pts=pl.when(owner_is_h).then(v_pts).otherwise(h_pts),
        margin_at_mark=pl.when(owner_is_h)
        .then(pl.col("h_mark") - pl.col("v_mark"))
        .otherwise(pl.col("v_mark") - pl.col("h_mark")),
        owner_poss=1 + pl.col("owner_later"),
        got_last=pl.coalesce(pl.col("last_poss"), pl.col("owner")) == pl.col("owner"),
        # who used the period's final possession (heaves under 2 s excluded)
        got_last_used=pl.coalesce(pl.col("last_used"), pl.col("owner")) == pl.col("owner"),
        # thresholds are relative to the mark (T = sc + 16): quick = first act
        # with >= sc + 4 left at the real mark, the same 12 s at a placebo mark
        choice=pl.when(first.is_null()).then(pl.lit("no_act"))
        .when(first >= T - 12).then(pl.lit("quick"))
        .when(first > T - 25).then(pl.lit("normal"))
        .otherwise(pl.lit("hold")),
    ).with_columns(net_pts=pl.col("own_pts") - pl.col("opp_pts"))


def build(league: str, year: int) -> pl.DataFrame | None:
    name = f"{'wnba_' if league == 'WNBA' else ''}nbastats_{year}.parquet"
    path = RAW / name
    if not path.exists():
        return None
    r = rules(league, year)
    T = float(r["shot_clock"] + 16)
    df = prepare(pl.read_parquet(path))
    # placebo: the same decision measured 120 s earlier, where the game clock
    # does not bind; its quick share is the natural pace baseline
    w = pl.concat([
        windows(df, T, r["shot_clock"], r["periods"]).with_columns(mark_kind=pl.lit("decision")),
        windows(df, T + PLACEBO_OFFSET, r["shot_clock"], r["periods"])
        .with_columns(mark_kind=pl.lit("placebo")),
    ])
    teams = team_map(df)
    w = w.join(teams, on="GAME_ID", how="left")
    owner_is_h = pl.col("owner") == "h"
    return w.with_columns(
        league=pl.lit(league), year=pl.lit(year),
        season=pl.lit(season_label(league, year)),
        shot_clock=pl.lit(r["shot_clock"]),
        mark=pl.when(pl.col("mark_kind") == "placebo")
        .then(pl.lit(T + PLACEBO_OFFSET)).otherwise(pl.lit(T)),
        period_min=pl.lit(r["period_min"]),
        team=pl.when(owner_is_h).then("h_team").otherwise("v_team"),
        team_id=pl.when(owner_is_h).then("h_team_id").otherwise("v_team_id"),
        opp=pl.when(owner_is_h).then("v_team").otherwise("h_team"),
    ).drop("last_poss", "last_used")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    parts = []
    for league, years in (("NBA", range(1996, 2025)), ("WNBA", range(1997, 2027))):
        for y in years:
            w = build(league, y)
            if w is None:
                print(f"{league} {y}: missing raw file")
                continue
            ok = w.filter(pl.col("owner").is_not_null(), ~pl.col("pending"),
                          pl.col("mark_kind") == "decision")
            print(f"{league} {season_label(league, y)}: {w.height:,} windows, "
                  f"{ok.height:,} clean, quick {(ok['choice'] == 'quick').mean():.3f}")
            parts.append(w)
    out = pl.concat(parts, how="diagonal_relaxed")
    out.write_parquet(OUT / "decisions.parquet")
    print(f"wrote {out.height:,} windows")


if __name__ == "__main__":
    main()
