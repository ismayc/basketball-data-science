# Basketball data science

A family of basketball analytics studies and tools built on public data
(NBA, WNBA, G League, and college), sharing one discipline: every analysis
is implemented twice (R/tidyverse and Python/polars), reconciled to
numeric tolerance before any finding is written, validated against
independent external data, and explicit about its limitations.

<!-- terms -->
> **Terms used in this analysis.** Dotted-underlined terms anywhere below repeat these definitions on hover ([full glossary](docs/glossary.md)).
>
> - **xPTS**: Expected points: the modeled make probability times the shot's point value, summed over attempts.
> - **xMake**: The model's probability that a given shot goes in, estimated from location and shot type; the per-shot building block behind xPPS and xPTS.
> - **RAPM**: Regularized adjusted plus-minus: a ridge regression crediting each player with net points per 100 possessions while adjusting for the other nine players on the floor.
> - **stint**: A stretch of game time with no substitution at either end - the unit of observation for the stint-level RAPM model.
> - **2-for-1**: Shooting early with 25-36 seconds left in a period so your team gets two possessions to the opponent's one before the buzzer.
> - **empirical Bayes**: Estimate the spread of true skill across the league from the data, then pull each individual's noisy estimate toward the league mean in proportion to its noise.
> - **SportVU**: The NBA's 2013-16 optical tracking system: x,y for all ten players (plus z for the ball) at 25 frames per second.
> - **window function**: SQL construct computing a value over a set of rows related to the current row (a rank, running total, or centered average) without collapsing them.
> - **DuckDB**: An in-process analytical SQL engine that queries CSV and parquet files directly, with no server or load step.
<!-- /terms -->

## The studies

| Repo | Data | Headline |
|---|---|---|
| [jersey-height-study](https://github.com/ismayc/jersey-height-study) | 45 seasons of rosters (18k player-seasons) | The "players are getting shorter" trend is ~70% a 2019 measurement-rule change, proven within-player and with a regime-shift model |
| [playbyplay-study](https://github.com/ismayc/playbyplay-study) | Full 2023-24 play-by-play (1,230 games) | The <abbr title="Shooting early with 25-36 seconds left in a period so your team gets two possessions to the opponent's one before the buzzer.">2-for-1</abbr> adds a real possession at no shot-quality cost; on **net** points the comparable-sample edge is ~+0.2 and not distinguishable from zero |
| [tracking-study](https://github.com/ismayc/tracking-study) | 7.5M frames of raw 25 Hz <abbr title="The NBA's 2013-16 optical tracking system: x,y for all ten players (plus z for the ball) at 25 frames per second.">SportVU</abbr> + play-by-play join | Possession heuristic validated at 97.5%/93.5% after discovering a 2.5–6 s per-game clock latency that fabricates findings if unhandled |
| [lineup-valuation-study](https://github.com/ismayc/lineup-valuation-study) | Every five-man lineup, 2023-24 and 2025-26; 69,767 <abbr title="A stretch of game time with no substitution at either end - the unit of observation for the stint-level RAPM model.">stints</abbr> | <abbr title="Regularized adjusted plus-minus: a ridge regression crediting each player with net points per 100 possessions while adjusting for the other nine players on the floor.">RAPM</abbr>-family player & lineup value with exact team-total reconstruction and honest ±2–3 pts/100 error bars |
| [shot-quality-study](https://github.com/ismayc/shot-quality-study) | All 218,701 shots of 2023-24 (+94k G League, +71k WNBA) | <abbr title="The model's probability that a given shot goes in, estimated from location and shot type; the per-shot building block behind xPPS and xPTS.">xMake</abbr>/<abbr title="Expected points: the modeled make probability times the shot's point value, summed over attempts.">xPTS</abbr> model separating shot **selection** from shot **making**; selection repeats (r ≈ .9), making half-repeats (r ≈ .6); an <abbr title="Estimate the spread of true skill across the league from the data, then pull each individual's noisy estimate toward the league mean in proportion to its noise.">empirical-Bayes</abbr> projection built on that beats naive carry-forward by ~10% out of sample |
| [draft-study](https://github.com/ismayc/draft-study) | 56,781 college player-seasons + 12 draft classes | On held-out drafts, college box-score stats add **nothing** beyond the pick (the scouts already priced them in); byproduct: a pick-value curve for trades |

## The layers on top

| Repo | What |
|---|---|
| [basketball-sql-layer](https://github.com/ismayc/basketball-sql-layer) | The family's headline tables re-expressed as <abbr title="An in-process analytical SQL engine that queries CSV and parquet files directly, with no server or load step.">DuckDB</abbr> <abbr title="SQL construct computing a value over a set of rows related to the current row (a rank, running total, or centered average) without collapsing them.">window-function</abbr> SQL, reconciled column-for-column against the polars outputs (observed diff exactly 0.0) |
| [nba-scouting-onepagers](https://github.com/ismayc/nba-scouting-onepagers) | Auto-generated opponent scouting one-pagers for all 30 teams, full 2025-26 season, with a byte-for-byte staleness gate |
| [basketball-analysis-tools](https://github.com/ismayc/basketball-analysis-tools) | Shared tooling: the glossary/tooltip engine, nba_api compatibility shims, cross-study identity tests, and the family-wide check orchestrator |

## Analysis standards

- **Dual implementation, reconciled.** Each study is written independently
  in R and Python with a reconcile gate (non-zero exit) that must pass
  before findings are written. This is not ceremony: it caught a
  text-vs-numeric sort bug that silently corrupted every score in the
  play-by-play study, and a dplyr sequential-`summarise` masking bug that
  silently degraded an SE column, while every sum and ranking still
  matched.
- **Generated findings.** No number in any README is typed by hand;
  findings sections are regenerated from `output/` by a script.
- **External validation before self-reporting.** Tracking metrics reproduce
  the NBA's published aggregates; lineup tables reconstruct official team
  totals exactly; the roster pipeline reproduces the Bill Russell #6
  retirement it was never told about.
- **Stated limitations.** Every study says what it cannot claim; the audit
  trail of issues found and fixed is public in
  [docs/analysis-audit.md](docs/analysis-audit.md).
- **Documented provenance.** Every source and its season vintage is
  cataloged in [docs/data-provenance.md](docs/data-provenance.md),
  including why the one non-current source (raw 2015-16 <abbr title="The NBA's 2013-16 optical tracking system: x,y for all ten players (plus z for the ball) at 25 frames per second.">SportVU</abbr>) is the
  only public option for raw tracking work.
- **Defined terms.** Every term of art is defined at the top of each
  analysis and carries a hover tooltip at each use.
  [docs/glossary.md](docs/glossary.md) is the master list.

## Running the family

```bash
git clone https://github.com/ismayc/basketball-analysis-tools
bash basketball-analysis-tools/clone_family.sh   # sibling checkouts
bash basketball-analysis-tools/run_all_checks.sh # every gate, every repo
```

Each repo also stands alone: `./run_checks.sh` inside any study runs its
unit tests and reconciliation gate.

## Related public work

- **NBA Over/Under Projection Tracker**, six consecutive seasons with one
  live page each:
  [2020-21](https://ismayc.github.io/2021-nba-over-under.html),
  [2021-22](https://ismayc.github.io/2022-nba-over-under.html),
  [2022-23](https://ismayc.github.io/2023-nba-over-under.html),
  [2023-24](https://ismayc.github.io/2024-nba-over-under.html),
  [2024-25](https://ismayc.github.io/2025-nba-over-under.html),
  [2025-26](https://ismayc.github.io/2026-nba-over-under.html).
- **Dashboards & tools**:
  [NBA Player Finder](https://ismayc.github.io/nba-player-finder/),
  [NBA](https://ismayc.github.io/nba-schedule/) &
  [WNBA](https://ismayc.github.io/wnba-schedule/) schedule viewers,
  [men's](https://ismayc.github.io/mens-march-madness/) &
  [women's](https://ismayc.github.io/womens-march-madness/) March Madness
  bracket viewers, the
  [Sports Trackers hub](https://ismayc.github.io/sports-trackers/), and
  the rest of [chester.rbind.io/portfolio](https://chester.rbind.io/portfolio).
- **[ModernDive](https://moderndive.com)** (co-author, CRC Press, 2nd ed.
  2025) and the [`infer`](https://github.com/tidymodels/infer),
  [`fivethirtyeight`](https://github.com/rudeboybert/fivethirtyeight), and
  `moderndive` R packages.
