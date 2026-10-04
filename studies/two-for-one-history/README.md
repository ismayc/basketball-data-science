# The 2-for-1 through history: NBA and WNBA

A study in the [basketball-data-science](https://github.com/ismayc/basketball-data-science)
family. It extends [playbyplay-study](https://github.com/ismayc/playbyplay-study),
which measured the end-of-quarter 2-for-1 on one NBA season (2023-24) and
listed "no test across eras or rule changes" as a limitation. This study runs
the same decision-team design on **every regular season with public
play-by-play in both leagues**: NBA 1996-97 to 2024-25 and WNBA 1997 to 2026.

**The questions.**
1. When did teams start hunting the 2-for-1, and is the rise real or just faster pace?
2. Did the WNBA follow the NBA, and how did its rule changes (30 s to 24 s
   clock, halves to quarters in 2006) change the decision?
3. Is the payoff the same in every era?
4. Which franchises hunt it most?

---

<!-- terms -->
> **Terms used in this analysis.**
>
> - **2-for-1**: Shooting early with 25-36 seconds left in a period so your team gets two possessions to the opponent's one before the buzzer.
> - **Decision mark**: shot clock + 16 seconds before the end of a period (40 s with a 24 s clock, 46 s with the WNBA's old 30 s clock). The team with the ball at the mark faces the 2-for-1 choice.
> - **Quick**: the ball-holder's first act (field-goal attempt, turnover, or first free throw of a trip) comes with at least shot clock + 4 seconds left, early enough that the opponent's full shot clock still expires before the buzzer.
> - **Placebo mark**: the same measurement 120 seconds earlier, where the game clock does not bind. Its quick share is the natural pace of possessions in that season.
> - **Used possession**: a possession that starts with at least 2 seconds left and in which the team logs a shot, turnover, or free-throw trip.
<!-- /terms -->

## Data

| Source | Content | Seasons |
|---|---|---|
| `stats.nba.com` `PlayByPlayV2`, via the [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) bulk mirror | every logged event, both leagues | NBA 1996-97 to 2024-25 (29), WNBA 1997 to 2026 (30) |
| pbpstats possession rows, same mirror | independent possession parser, validation only | NBA 2001-02, 2012-13, 2023-24; WNBA 2012, 2024 |

Regular season only. **WNBA 2026 is a partial-season snapshot** (the mirror
was captured mid-season) and is excluded from pooled results. **NBA 2025-26**
exists in the mirror only in the `PlayByPlayV3` schema and is not yet included.

## Pipeline

```
python/01_fetch.py       bulk mirror -> data/raw/*.parquet (slim columns, resumable)
python/02_decisions.py   possession reconstruction + decision/placebo windows
                         -> output/decisions.parquet
R/02_decisions.R         independent R/tidyverse implementation -> output/decisions_r.parquet
python/05_reconcile.py   Python vs R, every window, every column; non-zero exit on mismatch
python/03_validate.py    reconstruction vs pbpstats; non-zero exit if owner agreement < 97%
python/04_analysis.py    adoption, hazard, payoff, team tables -> output/*.csv
python/06_figures.py     figures/*.png + *.html
python/07_findings.py    writes the Findings section below (--check = drift gate)
```

```bash
pip install polars pyarrow numpy plotly kaleido
Rscript -e 'install.packages(c("dplyr","tidyr","stringr","nanoparquet"))'
python python/01_fetch.py            # ~3 min, ~400 MB
python python/02_decisions.py        # ~1 min
Rscript R/02_decisions.R             # ~7 min
python python/05_reconcile.py
python python/03_validate.py
python python/04_analysis.py
python python/06_figures.py          # needs a Chromium for kaleido (BROWSER_PATH)
python python/07_findings.py
```

## Method and every judgment call

| Decision | Value | Why |
|---|---|---|
| Unit | one window per non-final regulation period | Q4 and OT are dominated by score-state strategy; the WNBA halves era has one window per game (end of the first half) |
| Who decides | the team with the ball at the decision mark | Removes the "never had the ball" contamination of a shot-based design (playbyplay-study Finding 4) |
| Choice measure | time of the ball-holder's **first act** after the mark | That is the decision; possession end time (used by playbyplay-study) also moves with offensive rebounds and rebound delay |
| Mark and thresholds | relative to the shot clock: mark = SC + 16, quick = first act at mark minus 12 s or earlier | Keeps the decision comparable across the WNBA's 30 s and 24 s eras |
| Pace control | placebo mark 120 s earlier, identical measurement | Possessions got faster across the period; without a baseline, rising quick shares are mostly pace |
| Timing evidence | per-second hazard of the first act, decision vs placebo | A spike just inside the threshold is the deliberate behavior; a raw share cannot separate it from pace |
| Possession | rebuilt from events: makes, defensive rebounds, turnovers, last made FT, jump balls | The V2 feed has no possession field; validated against pbpstats |
| Event order | clock-descending within period, `EVENTNUM` (numeric) breaking ties | `EVENTNUM` is not chronological: late-logged events carry high numbers with early clocks. Sorting by `EVENTNUM` assigned the wrong ball-holder in the first build |
| Unknowable windows | excluded when a shot or missed last free throw is in the air at the mark | The decision team depends on a rebound the feed resolves after the mark (6-9% of windows) |
| Outcome | net points (own minus opponent) from the mark to the buzzer, from the running score | Counts free throws and and-ones; net captures the cost side of the trade |
| Uncertainty | bootstrap (4,000 resamples) | Points in a short window are lumpy counts |

<!-- gen:findings -->
Based on **110,203 end-of-period decisions** with a known ball-holder (NBA 1996-97 to 2024-25, WNBA 1997 to 2025; the partial WNBA 2026 snapshot is shown in tables but kept out of pooled results).

### 1. In the NBA the 2-for-1 is old; most of its recent "rise" is pace

The share of ball-holders who released quickly enough to get the ball back went from **84.1%** in 1996-97 to **93.5%** in 2024-25. But possessions everywhere got faster: at a placebo mark two minutes earlier, where the buzzer does not bind, the same release rate rose from 73.8% to 80.6%. The **excess** over the placebo, the part attributable to the buzzer, averaged **10.3 points** from 1996-97 to 2016-17 and **13.5 points** from 2021-22 to 2024-25: real but modest growth on top of a habit that was already established when play-by-play begins. See `figures/fig1_adoption.png`.

### 2. What changed is the timing: modern NBA teams aim at the deadline

Comparing the per-second rate of first shots after the mark to the placebo rate, 1996-97 to 2003-04 teams peaked at **1.46x** the natural rate (8 s after the mark), a broad hump. In 2017-18 to 2024-25 the peak is **1.90x** at 9 s after the mark, a sharp spike just before the last second that still buys a 2-for-1. The behavior went from "shoot a bit sooner" to "shoot at 30-32 seconds." See `figures/fig2_hazard.png`.

### 3. The WNBA adopted it later, around 2018

From 2006 (when the WNBA moved to quarters and a 24-second clock) through 2017, WNBA quick share averaged 81.9% with an excess over placebo of only **3.2 points**. From 2018 to 2025 it averaged 87.1% with an excess of **8.4 points**, approaching the NBA's long-run level. The WNBA's timing spike is still flatter (peak **1.33x** in 2016-2025). The 30-second-clock, halves era (1997-2005, one decision per game) is too small to read season by season.

### 4. The payoff association is stable across 30 years and both leagues

Quick vs. not-quick decision possessions, net points from the mark to the buzzer:

| League | Era | Quick n | Not n | Net quick | Net not | Difference [95% CI] | Own used poss. (quick / not) | Opp. used poss. (quick / not) | Last possession (quick / not) |
|---|---|---|---|---|---|---|---|---|---|
| NBA | 1996-97 to 2003-04 | 21,442 | 3,820 | +0.57 | +0.25 | **+0.32** [+0.26, +0.39] | 2.01 / 1.48 | 1.46 / 1.04 | 54.5% / 45.8% |
| NBA | 2004-05 to 2010-11 | 21,019 | 3,452 | +0.57 | +0.21 | **+0.36** [+0.29, +0.43] | 2.01 / 1.46 | 1.45 / 1.02 | 54.9% / 45.5% |
| NBA | 2011-12 to 2016-17 | 17,904 | 2,644 | +0.56 | +0.24 | **+0.32** [+0.25, +0.39] | 2.01 / 1.50 | 1.46 / 1.03 | 53.9% / 48.0% |
| NBA | 2017-18 to 2024-25 | 24,321 | 1,866 | +0.61 | +0.25 | **+0.36** [+0.27, +0.45] | 2.05 / 1.50 | 1.50 / 1.05 | 55.0% / 45.6% |
| WNBA | 1997-2005 (30s clock, halves) | 1,325 | 449 | +0.50 | +0.24 | **+0.26** [+0.05, +0.46] | 2.08 / 1.65 | 1.58 / 1.12 | 49.6% / 51.7% |
| WNBA | 2006-2015 | 4,997 | 1,114 | +0.54 | +0.22 | **+0.32** [+0.20, +0.44] | 2.02 / 1.54 | 1.48 / 1.08 | 53.4% / 46.9% |
| WNBA | 2016-2025 | 5,039 | 811 | +0.54 | +0.22 | **+0.32** [+0.18, +0.46] | 2.01 / 1.52 | 1.45 / 1.07 | 56.0% / 46.2% |

The mechanism is visible in the possession columns: going quick adds about **0.50** used possessions for the ball-holder but also **0.42** for the opponent, and quick teams end up with the period's last used possession only 49.6%-56.0% of the time (vs 45.5%-51.7% when not quick). The 2-for-1 often becomes a 2-for-2 because the opponent can answer quickly too. Restricting to possessions gained 1-10 s before the mark (most of a shot clock left, so the choice is real) leaves the differences between +0.33 and +0.39 (`output/payoff_by_era_fresh.csv`). See `figures/fig3_payoff.png`.

This is an association, not a causal effect: see Limitations.

### 5. Franchises differ, but not by much

Pooled over 1996-97 to 2024-25 and compared with their own league-season, NBA franchises range from UTA at **+4.4 points** to MIA at **-5.6 points** (`output/team_history.csv`). Coach-level attribution is the natural next step.

### Validation

The possession reconstruction is gated against pbpstats' independent possession parser (`python/03_validate.py`):

| League | Season | Same ball-holder at the mark | Decision possession ends within 2 s | Same opponent used-possession count |
|---|---|---|---|---|
| NBA | 2001-02 | 98.11% | 99.88% | 89.33% |
| NBA | 2012-13 | 98.42% | 99.94% | 89.91% |
| NBA | 2023-24 | 99.85% | 99.97% | 91.07% |
| WNBA | 2012 | 98.80% | 99.83% | 89.39% |
| WNBA | 2024 | 99.85% | 99.69% | 89.55% |

Python and R implementations agree on every one of the windows (decision and placebo) in every compared column (`python/05_reconcile.py`).
<!-- /gen:findings -->

## Limitations

1. **Observational.** Teams choose when to shoot. A team that does not go
   quick may have been denied a good look, so the not-quick group carries
   some defensive selection. The fresh-possession restriction narrows this
   but does not remove it. No score-margin, team-quality, or quarter controls
   yet.
2. **Possession is reconstructed**, not logged. The reconstruction is
   validated (see above), but opponent possession counts match pbpstats only
   ~90% of the time; disagreements are mostly last-second heaves and
   dead-ball team rebounds, which the two parsers define differently.
3. **Early feeds are thinner.** 1990s play-by-play is less complete than
   modern feeds; the stable placebo series and stable owner agreement in the
   2001-02 validation argue against a large era artifact, but it is not
   ruled out for 1996-2000.
4. **Pending windows are excluded** (a shot in the air at the mark), and their
   share rises slightly over time (more threes, longer rebounds).
5. **The WNBA halves era is small** (one window per game, 101-237 per season).
6. **Franchise, not coach.** Team rankings mix eras and coaching staffs.
7. **Missing seasons.** NBA 2025-26 (V3 schema only in the mirror) and the
   rest of WNBA 2026.

## Next steps

- Add NBA 2025-26 via the `PlayByPlayV3` files and the full WNBA 2026 season.
- Score-margin and team-quality adjustment of the payoff (a regression with
  league-season fixed effects).
- Coach-level adoption, from a coach-tenure table joined by team-season.
- The opponent's counter: how often the team that concedes the 2-for-1 answers
  quickly to take the last possession back, and whether that has grown too.
