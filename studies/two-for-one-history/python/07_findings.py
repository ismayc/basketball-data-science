"""Write the README Findings section from the committed output/ tables.

Every number between the <!-- gen:findings --> markers is produced here.
With --check, exits non-zero if the README differs from what the outputs say
(the family drift gate) instead of rewriting it.

Run: python python/07_findings.py [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
README = ROOT / "README.md"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def pts(x: float) -> str:
    return f"{x:+.2f}"


def build() -> str:
    a = pl.read_csv(OUT / "adoption_by_season.csv")
    hz = pl.read_csv(OUT / "hazard_by_era.csv")
    p = pl.read_csv(OUT / "payoff_by_era.csv")
    pf = pl.read_csv(OUT / "payoff_by_era_fresh.csv")
    v = pl.read_csv(OUT / "validation_pbpstats.csv")
    t = pl.read_csv(OUT / "team_history.csv")
    full = a.filter(~pl.col("partial"))
    n_windows = int(full["n"].sum())

    def season(lg: str, yr: int) -> dict:
        return a.filter((pl.col("league") == lg) & (pl.col("year") == yr)).row(0, named=True)

    def era_mean(lg: str, lo: int, hi: int, col: str) -> float:
        return full.filter((pl.col("league") == lg) & pl.col("year").is_between(lo, hi))[col].mean()

    n0, n1 = season("NBA", 1996), season("NBA", 2024)
    nba_early_ex = era_mean("NBA", 1996, 2016, "excess")
    nba_late_ex = era_mean("NBA", 2021, 2024, "excess")
    w_mid_ex = era_mean("WNBA", 2006, 2017, "excess")
    w_late_ex = era_mean("WNBA", 2018, 2025, "excess")
    w_mid_q = era_mean("WNBA", 2006, 2017, "quick_share")
    w_late_q = era_mean("WNBA", 2018, 2025, "quick_share")

    def peak(lg: str, era: str) -> tuple[float, int]:
        e = (hz.filter((pl.col("league") == lg) & (pl.col("era") == era))
             .sort("rel").with_columns(sm=pl.col("ratio").rolling_mean(3, center=True))
             .filter(pl.col("rel").is_between(1, 20)))
        r = e.sort("sm", descending=True).row(0, named=True)
        return r["sm"], r["rel"]

    nba_eras = sorted(hz.filter(pl.col("league") == "NBA")["era"].unique().to_list())
    wnba_eras = sorted(hz.filter(pl.col("league") == "WNBA")["era"].unique().to_list())
    pk_first, rel_first = peak("NBA", nba_eras[0])
    pk_last, rel_last = peak("NBA", nba_eras[-1])
    wpk_last, wrel_last = peak("WNBA", wnba_eras[-1])

    lines = []
    lines.append(f"Based on **{n_windows:,} end-of-period decisions** with a known ball-holder "
                 f"(NBA 1996-97 to 2024-25, WNBA 1997 to 2025; the partial WNBA 2026 "
                 f"snapshot is shown in tables but kept out of pooled results).\n")

    lines.append("### 1. In the NBA the 2-for-1 is old; most of its recent \"rise\" is pace\n")
    lines.append(f"The share of ball-holders who released quickly enough to get the ball back "
                 f"went from **{pct(n0['quick_share'])}** in {n0['season']} to "
                 f"**{pct(n1['quick_share'])}** in {n1['season']}. But possessions everywhere got "
                 f"faster: at a placebo mark two minutes earlier, where the buzzer does not bind, "
                 f"the same release rate rose from {pct(n0['placebo_quick_share'])} to "
                 f"{pct(n1['placebo_quick_share'])}. The **excess** over the placebo, the part "
                 f"attributable to the buzzer, averaged **{100 * nba_early_ex:.1f} points** from "
                 f"1996-97 to 2016-17 and **{100 * nba_late_ex:.1f} points** from 2021-22 to "
                 f"2024-25: real but modest growth on top of a habit that was already "
                 f"established when play-by-play begins. See `figures/fig1_adoption.png`.\n")

    lines.append("### 2. What changed is the timing: modern NBA teams aim at the deadline\n")
    lines.append(f"Comparing the per-second rate of first shots after the mark to the placebo "
                 f"rate, {nba_eras[0]} teams peaked at **{pk_first:.2f}x** the natural rate "
                 f"({rel_first} s after the mark), a broad hump. In {nba_eras[-1]} the peak is "
                 f"**{pk_last:.2f}x** at {rel_last} s after the mark, a sharp spike just "
                 f"before the last second that still buys a 2-for-1. The behavior went "
                 f"from \"shoot a bit sooner\" to \"shoot at 30-32 seconds.\" See "
                 f"`figures/fig2_hazard.png`.\n")

    lines.append("### 3. The WNBA adopted it later, around 2018\n")
    lines.append(f"From 2006 (when the WNBA moved to quarters and a 24-second clock) through "
                 f"2017, WNBA quick share averaged {pct(w_mid_q)} with an excess over placebo "
                 f"of only **{100 * w_mid_ex:.1f} points**. From 2018 to 2025 it averaged "
                 f"{pct(w_late_q)} with an excess of **{100 * w_late_ex:.1f} points**, "
                 f"approaching the NBA's long-run level. The WNBA's timing spike is still flatter "
                 f"(peak **{wpk_last:.2f}x** in {wnba_eras[-1]}). The 30-second-clock, "
                 f"halves era (1997-2005, one decision per game) is too small to read "
                 f"season by season.\n")

    lines.append("### 4. The payoff association is stable across 30 years and both leagues\n")
    lines.append("Quick vs. not-quick decision possessions, net points from the mark to the buzzer:\n")
    lines.append("| League | Era | Quick n | Not n | Net quick | Net not | Difference [95% CI] "
                 "| Own used poss. (quick / not) | Opp. used poss. (quick / not) | Last possession (quick / not) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in p.iter_rows(named=True):
        lines.append(
            f"| {r['league']} | {r['era']} | {r['n_quick']:,} | {r['n_not']:,} | "
            f"{pts(r['net_quick'])} | {pts(r['net_not'])} | **{pts(r['net_diff'])}** "
            f"[{pts(r['ci_lo'])}, {pts(r['ci_hi'])}] | {r['own_used_quick']:.2f} / "
            f"{r['own_used_not']:.2f} | {r['opp_used_quick']:.2f} / {r['opp_used_not']:.2f} | "
            f"{pct(r['last_quick'])} / {pct(r['last_not'])} |")
    gain_own = (p["own_used_quick"] - p["own_used_not"]).mean()
    gain_opp = (p["opp_used_quick"] - p["opp_used_not"]).mean()
    lines.append("")
    lines.append(f"The mechanism is visible in the possession columns: going quick adds about "
                 f"**{gain_own:.2f}** used possessions for the ball-holder but also "
                 f"**{gain_opp:.2f}** for the opponent, and quick teams end up with the "
                 f"period's last used possession only {pct(p['last_quick'].min())}-"
                 f"{pct(p['last_quick'].max())} of the time (vs {pct(p['last_not'].min())}-"
                 f"{pct(p['last_not'].max())} when not quick). The 2-for-1 often "
                 f"becomes a 2-for-2 because the opponent can answer quickly too. Restricting "
                 f"to possessions gained 1-10 s before the mark (most of a shot clock left, so "
                 f"the choice is real) leaves the differences between "
                 f"{pts(pf['net_diff'].min())} and {pts(pf['net_diff'].max())} "
                 f"(`output/payoff_by_era_fresh.csv`). See `figures/fig3_payoff.png`.\n")
    lines.append("This is an association, not a causal effect: see Limitations.\n")

    nba_t = t.filter(pl.col("league") == "NBA").sort("vs_league", descending=True)
    top, bot = nba_t.row(0, named=True), nba_t.row(-1, named=True)
    lines.append("### 5. Franchises differ, but not by much\n")
    lines.append(f"Pooled over 1996-97 to 2024-25 and compared with their own league-season, "
                 f"NBA franchises range from {top['team']} at **{100 * top['vs_league']:+.1f} "
                 f"points** to {bot['team']} at **{100 * bot['vs_league']:+.1f} points** "
                 f"(`output/team_history.csv`). Coach-level attribution is the natural next "
                 f"step.\n")

    lines.append("### Validation\n")
    lines.append("The possession reconstruction is gated against pbpstats' independent "
                 "possession parser (`python/03_validate.py`):\n")
    lines.append("| League | Season | Same ball-holder at the mark | Decision possession ends within 2 s "
                 "| Same opponent used-possession count |")
    lines.append("|---|---|---|---|---|")
    for r in v.iter_rows(named=True):
        lines.append(f"| {r['league']} | {r['season']} | {100 * r['owner_agree']:.2f}% | "
                     f"{100 * r['end_within_2s']:.2f}% | {100 * r['opp_poss_agree']:.2f}% |")
    lines.append("")
    lines.append("Python and R implementations agree on every one of the windows "
                 "(decision and placebo) in every compared column (`python/05_reconcile.py`).")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    body = build()
    text = README.read_text()
    new = re.sub(r"(<!-- gen:findings -->\n).*?(<!-- /gen:findings -->)",
                 lambda m: m.group(1) + body + "\n" + m.group(2), text, flags=re.S)
    if a.check:
        if new != text:
            print("README findings are stale: run python/07_findings.py")
            sys.exit(1)
        print("README findings match output/")
        return
    README.write_text(new)
    print("README findings written")


if __name__ == "__main__":
    main()
