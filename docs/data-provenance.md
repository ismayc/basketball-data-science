# Data provenance: every source, every season, and why that vintage

Each study names its data inline, but the family-level question deserves a
family-level answer: what exactly was used, how current is it, and where a
source is not current, why not. The short version: **five of the six
studies run on data through the just-completed 2025-26 season or the most
recent season available. The one exception, raw tracking, uses 2015-16
because that is the only raw tracking the public has ever had.** The
vintage of every source below is a constraint of public availability, not
a convenience choice; the companion survey
([public-data-availability.md](public-data-availability.md)) documents the
full landscape of what exists.

## Season coverage at a glance

| Study | Data seasons | Currency |
|---|---|---|
| jersey-height-study | 1980-81 through 2025-26 (46 seasons) | Current: includes the just-completed season |
| playbyplay-study | 2023-24, full season | Most recent season with a complete, independently gateable archive at build time |
| tracking-study | Raw frames 2015-16 (10 games, 25 Hz); published aggregates 2013-14 through 2025-26 | Raw: **the only public raw tracking, ever** (see below). Aggregates: current |
| lineup-valuation-study | 2023-24 and 2025-26 | Current: includes the just-completed season |
| shot-quality-study | NBA 2023-24, 2024-25, 2025-26; G League 2023-24; WNBA 2024 and 2025 | Current: three NBA seasons, two WNBA seasons |
| draft-study | College 2011-2022; NBA outcomes 2011-12 through 2024-25 | By design: the 2022 class needs three NBA seasons of outcomes to score |
| scouting one-pagers | 2025-26, full season | Current |
| SQL layer | The same files as the studies above | Mirrors them |

## The tracking question, answered directly

The tracking study's 2015-16 data is a decade old, and no analysis of
today's game should lean on its basketball conclusions. It does not. Here
is the public-availability timeline that explains the choice:

- **2013-14 to 2015-16, SportVU.** The NBA had optical tracking in every
  arena, and for part of 2015-16 the raw game logs were served publicly
  from stats.nba.com. Community mirrors archived 636 games before access
  closed. This is the archive the study reads.
- **2016-17 to 2022-23, Second Spectrum.** The league changed vendors and
  stopped publishing raw logs entirely. Nothing public.
- **2023-24 onward, Hawk-Eye.** Current vendor; raw feeds remain private.
  What the public gets is aggregates (speed, distance, touches) through
  stats.nba.com endpoints, not frames.

So the real decision was "old raw frames or no raw-tracking work at all,"
and the study chooses the frames while being explicit about what that
buys. Its findings are deliberately methods-level, and they transfer to
any tracking feed: validate coordinates against the league's published
aggregates before trusting them, calibrate the play-by-play clock lag per
game before joining sources (2.5 to 6.0 seconds of scorer latency in this
sample), and hold out an event type the calibration never saw. The one
descriptive result (spacing shapes shot profile more than raw efficiency)
is bounded to its ten-game sample in the study's own limitations.

The aggregate side of the modern feed is used twice: the study's
validation gate checks the 2015-16 frames against `LeagueDashPtStats`
published numbers, and a longitudinal extension harvests that same
endpoint for all thirteen tracking-era seasons (2013-14 through 2025-26)
with a player-vs-team reconciliation gate per season. So the study's
tracking coverage runs to the current season; only the raw frames stop
where the league stopped publishing them. For the broadcast-video
computer-vision route (Basketball-51, NSVA, SportsMOT, DeepSportRadar),
see the survey: they provide video and annotations rather than tracking
output, and the pseudo-tracking study they enable is the next build
planned for the family (design in the tracking study's README).

## Source detail by study

### jersey-height-study

- **stats.nba.com `CommonTeamRoster`** (via nba_api): jersey number,
  listed height, position, and age for every team-season, 1980-81 through
  2025-26. 18,947 player-seasons. One call per team-season, cached and
  resumable. The 46-season span is the analysis: the 2019-20
  measured-height rule change is only visible against decades of context.

### playbyplay-study

- **stats.nba.com `PlayByPlayV3`** (via nba_api): every logged event for
  all 1,230 games of 2023-24, with game IDs from `LeagueGameFinder`.
  Court coordinates ride along on shot events.
- The 2-for-1 is a rules-and-clock phenomenon, not a style phenomenon, so
  one complete recent season is the right sample: the shot-quality
  study's backtest later confirmed the clock findings replicate in
  2024-25 and 2025-26.

### tracking-study

- **Raw SportVU game logs, 2015-16** (community GitHub mirrors of the
  briefly-public stats.nba.com feed): 10 games, 7.5 million de-duplicated
  frames at 25 Hz.
- **stats.nba.com `PlayByPlayV3`** for the same 10 games: the join
  target.
- **stats.nba.com `LeagueDashPtStats` (SpeedDistance)**: the league's own
  published aggregates, used two ways: as the external validation gate
  for the 2015-16 frames, and harvested for every season 2013-14 through
  2025-26 (player and team level, reconciled against each other) for the
  league-movement trend.

### lineup-valuation-study

- **stats.nba.com `LeagueDashLineups`** (Base + Advanced, per team):
  every five-man lineup for 2023-24 and 2025-26. Queried per team because
  the league-wide call silently caps at 2,000 rows.
- **stats.nba.com `LeagueDashPlayerStats` / `LeagueDashTeamStats`**:
  independent references that gate the lineup tables (team totals must
  reconstruct exactly).
- **shufinskiy/nba_data bulk play-by-play (`nbastats_2023`)** plus the
  **nba-on-court** package (offline substitution logic): the 69,767-stint
  dataset behind the opponent-adjusted stint RAPM, all 1,230 games of
  2023-24.

### shot-quality-study

- **shufinskiy/nba_data bulk `shotdetail`**: every NBA shot for 2023-24
  (the fitted season), 2024-25, and 2025-26 (the backtest seasons);
  219,000 shots per season.
- **shufinskiy/nba_data bulk `nbastats` play-by-play**: an independent
  feed used only to gate shot totals (0.002% agreement).
- **stats.nba.com `ShotChartDetail` with `league_id="20"`**: 94,128
  G League shots, 2023-24.
- **shufinskiy `wnba_shotdetail` + `wnba_nbastats`**: WNBA 2024 and 2025
  with their own play-by-play gate (the archive reaches back to 1997).

### draft-study

- **barttorvik.com advanced stats** (keyless CSV endpoint; the upstream
  of the cbbdata/toRvik ecosystem): 56,781 college player-seasons,
  2011-2022, with the headerless 67-column layout pinned empirically and
  gated.
- **stats.nba.com `DraftHistory`**: draft year, pick, and NBA person ID,
  which lets outcomes join by ID rather than by name.
- **stats.nba.com `LeagueDashPlayerStats`**: NBA minutes 2011-12 through
  2024-25, the outcome variable. The college window stops at 2022 by
  design: the outcome ("rotation player within three seasons") needs
  three NBA seasons after the draft, so 2022 is the newest class that can
  be scored honestly.

### Scouting one-pagers and the SQL layer

Both are composition layers over the files above: the one-pagers price
2025-26 shots with the shot-quality model (a transfer the backtest
validated) and read the 2025-26 lineup and RAPM outputs; the SQL layer
queries the same raw CSVs and parquet in place. Neither introduces a new
source, which is the point: every number they publish traces to a gated
pipeline.

## Shared provenance notes

- **Two independent routes into stats.nba.com data are used
  deliberately**: live nba_api calls for reference and validation tables,
  and the shufinskiy/nba_data bulk archives for full-season event data
  (one small download instead of a thousand rate-limited calls). Where
  both exist for the same quantity, one gates the other.
- Every harvest is cached and resumable; analyses never depend on the
  network being up.
- The full survey of what public basketball data exists (including
  sources the family does not yet use) lives in
  [public-data-availability.md](public-data-availability.md).
