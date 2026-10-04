"""Historical 2-for-1 analysis from output/decisions.parquet.

Sample: windows with a known, non-pending ball-holder at the mark who acts
after it (choice != no_act). WNBA 2026 is a partial-season snapshot and is
flagged in every table that carries it.

Outputs
  output/adoption_by_season.csv  quick share at the real mark vs the placebo
                                 mark (natural pace) and the excess
  output/hazard_by_era.csv       per-second hazard of the first act after the
                                 mark, decision vs placebo, by league-era
  output/payoff_by_era.csv       quick vs not-quick: own/opp/net points, used
                                 possessions, last possession; bootstrap CI on
                                 the net difference
  output/payoff_by_era_fresh.csv same, restricted to possessions gained 1-10 s
                                 before the mark (a full, real choice)
  output/team_history.csv        franchise-season-pooled quick shares

Run: python python/04_analysis.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
N_BOOT = 4000
RNG = np.random.default_rng(20261004)
PARTIAL = {("WNBA", 2026)}


def era(league: str, year: int) -> str:
    if league == "NBA":
        if year <= 2003:
            return "1996-97 to 2003-04"
        if year <= 2010:
            return "2004-05 to 2010-11"
        if year <= 2016:
            return "2011-12 to 2016-17"
        return "2017-18 to 2024-25"
    if year <= 2005:
        return "1997-2005 (30s clock, halves)"
    if year <= 2015:
        return "2006-2015"
    return "2016-2025"


def load() -> pl.DataFrame:
    d = pl.read_parquet(OUT / "decisions.parquet")
    d = d.filter(pl.col("owner").is_not_null(), ~pl.col("pending"),
                 pl.col("choice") != "no_act")
    eras = d.select("league", "year").unique().with_columns(
        era=pl.struct("league", "year").map_elements(
            lambda r: era(r["league"], r["year"]), return_dtype=pl.String))
    return d.join(eras, on=["league", "year"]).with_columns(
        quick=pl.col("choice") == "quick",
        partial=pl.struct("league", "year").map_elements(
            lambda r: (r["league"], r["year"]) in PARTIAL, return_dtype=pl.Boolean))


def boot_diff(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    da = RNG.choice(a, (N_BOOT, a.size)).mean(1)
    db = RNG.choice(b, (N_BOOT, b.size)).mean(1)
    lo, hi = np.percentile(da - db, [2.5, 97.5])
    return float(lo), float(hi)


def adoption(d: pl.DataFrame) -> pl.DataFrame:
    g = (d.group_by("league", "year", "season", "era", "partial", "mark_kind")
         .agg(n=pl.len(), quick_share=pl.col("quick").mean(),
              hold_share=(pl.col("choice") == "hold").mean()))
    dec = g.filter(pl.col("mark_kind") == "decision").drop("mark_kind")
    pla = (g.filter(pl.col("mark_kind") == "placebo")
           .select("league", "year", placebo_n="n", placebo_quick_share="quick_share"))
    return (dec.join(pla, on=["league", "year"])
            .with_columns(excess=pl.col("quick_share") - pl.col("placebo_quick_share"))
            .sort("league", "year"))


def hazard(d: pl.DataFrame) -> pl.DataFrame:
    """Per-second hazard of the first act after the mark, decision vs placebo.

    rel = seconds elapsed since the mark. hazard(rel) = acts at rel / windows
    still without an act at rel. The placebo hazard is the natural pace of
    possessions in the same shot-clock state with no buzzer in play; the
    ratio isolates what the approaching buzzer does to timing.
    """
    x = d.with_columns(rel=(pl.col("mark") - pl.col("first_act_t")).cast(pl.Int32))
    counts = x.group_by("league", "era", "mark_kind", "rel").agg(acts=pl.len())
    tot = x.group_by("league", "era", "mark_kind").agg(n=pl.len())
    h = (counts.join(tot, on=["league", "era", "mark_kind"])
         .sort("league", "era", "mark_kind", "rel")
         .with_columns(at_risk=pl.col("n") - pl.col("acts").cum_sum().shift(1, fill_value=0)
                       .over("league", "era", "mark_kind"))
         .with_columns(hazard=pl.col("acts") / pl.col("at_risk")))
    dec = h.filter(pl.col("mark_kind") == "decision").drop("mark_kind", "n")
    pla = (h.filter(pl.col("mark_kind") == "placebo")
           .select("league", "era", "rel", placebo_hazard="hazard", placebo_at_risk="at_risk"))
    return (dec.join(pla, on=["league", "era", "rel"], how="left")
            .with_columns(ratio=pl.col("hazard") / pl.col("placebo_hazard"))
            .filter(pl.col("rel").is_between(0, 24))
            .sort("league", "era", "rel"))


def payoff(d: pl.DataFrame, fresh: bool) -> pl.DataFrame:
    dec = d.filter(pl.col("mark_kind") == "decision", ~pl.col("partial"))
    if fresh:
        dec = dec.filter((pl.col("poss_start_t") - pl.col("mark")).is_between(1, 10))
    rows = []
    for (league, era_), g in dec.group_by("league", "era", maintain_order=True):
        q, nq = g.filter(pl.col("quick")), g.filter(~pl.col("quick"))
        lo, hi = boot_diff(q["net_pts"].to_numpy().astype(float),
                           nq["net_pts"].to_numpy().astype(float))
        row = dict(league=league, era=era_, n_quick=q.height, n_not=nq.height)
        for lab, s in (("quick", q), ("not", nq)):
            row |= {f"own_{lab}": s["own_pts"].mean(), f"opp_{lab}": s["opp_pts"].mean(),
                    f"net_{lab}": s["net_pts"].mean(),
                    f"own_used_{lab}": s["owner_used"].mean(),
                    f"opp_used_{lab}": s["opp_used"].mean(),
                    f"last_{lab}": s["got_last_used"].mean()}
        row |= dict(net_diff=row["net_quick"] - row["net_not"], ci_lo=lo, ci_hi=hi)
        rows.append(row)
    return pl.DataFrame(rows).sort("league", "era")


def teams(d: pl.DataFrame) -> pl.DataFrame:
    dec = d.filter(pl.col("mark_kind") == "decision", ~pl.col("partial"),
                   pl.col("team").is_not_null())
    # franchise = team_id (stable through relocations); label with latest abbr
    latest = (dec.sort("year").group_by("league", "team_id")
              .agg(team=pl.col("team").last(), abbrs=pl.col("team").unique().sort()))
    t = (dec.group_by("league", "team_id")
         .agg(n=pl.len(), quick=pl.col("quick").sum(),
              first=pl.col("season").min(), last=pl.col("season").max()))
    lg = dec.group_by("league", "year").agg(lg=pl.col("quick").mean())
    # league-season-adjusted: compare each window with its own league-season
    adj = (dec.join(lg, on=["league", "year"])
           .group_by("league", "team_id")
           .agg(vs_league=(pl.col("quick").cast(pl.Float64) - pl.col("lg")).mean()))
    return (t.join(latest, on=["league", "team_id"]).join(adj, on=["league", "team_id"])
            .with_columns(quick_share=pl.col("quick") / pl.col("n"),
                          abbrs=pl.col("abbrs").list.join("/"))
            .filter(pl.col("n") >= 100)
            .sort("league", "vs_league", descending=[False, True]))


def main() -> None:
    d = load()
    a = adoption(d)
    a.write_csv(OUT / "adoption_by_season.csv")
    hz = hazard(d.filter(~pl.col("partial")))
    hz.write_csv(OUT / "hazard_by_era.csv")
    p = payoff(d, fresh=False)
    p.write_csv(OUT / "payoff_by_era.csv")
    pf = payoff(d, fresh=True)
    pf.write_csv(OUT / "payoff_by_era_fresh.csv")
    t = teams(d)
    t.write_csv(OUT / "team_history.csv")
    with pl.Config(tbl_rows=80, tbl_cols=30, tbl_width_chars=250, float_precision=3):
        print(a.select("league", "season", "n", "quick_share", "placebo_quick_share",
                       "excess", "hold_share", "partial"))
        print(hz.filter(pl.col("league") == "NBA").pivot(
            on="era", index="rel", values="ratio"))
        print(hz.filter(pl.col("league") == "WNBA").pivot(
            on="era", index="rel", values="ratio"))
        print(p)
        print(pf.select("league", "era", "n_quick", "n_not", "net_quick", "net_not",
                        "net_diff", "ci_lo", "ci_hi"))
        print(t.group_by("league").head(5))
        print(t.group_by("league").tail(5))


if __name__ == "__main__":
    main()
