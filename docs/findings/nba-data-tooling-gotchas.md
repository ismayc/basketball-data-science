# Gotchas in the public NBA data stack

*Recorded 2026-07-25, after each of these cost real debugging time during the
work-sample builds. Fuller evidence: `../analysis-audit.md` and
`../public-data-availability.md`; every item below is also guarded by a code
comment, test, or validation gate at the place it bit.*

## stats.nba.com / nba_api

- **Every column arrives as text.** Cast before sorting or comparing:
  `actionNumber` sorted as text puts `"100"` before `"2"`, which scrambled a
  score forward-fill and corrupted published numbers before review caught it
  (regression test: `tests/python/test_playbyplay.py`).
- **What looks like hours-long rate limiting can be a User-Agent
  fingerprint block.** After a heavy evening, all `boxscore*` endpoints
  read-timed-out (even at 60s) while `LeagueDash*` kept answering. But the
  next day the same requests failed 30/30 with nba_api's shipped
  `Firefox/72.0` UA *and* with a modern Chrome UA, while a generic
  `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36`
  (claiming no specific browser) returned 200 instantly. The edge apparently
  hangs UAs whose claimed browser the TLS fingerprint can't corroborate.
  Fix: mutate `nba_api.stats.library.http.STATS_HEADERS["User-Agent"]`
  before importing endpoints (`lineup-valuation-study/python/05_build_stints.py`).
  Consequences we kept anyway: every harvest is resumable, and validation
  gates cache their official reference data so they can run offline
  (`tracking-study/data/official_speeddistance_medians.parquet`).
- **League-wide `LeagueDashLineups` silently caps at 2,000 rows.** Per-team
  queries (30 calls) return complete lineup tables.
- **Lineup `POSS` (Advanced) is an offensive-possession count**;
  `100·PLUS_MINUS/POSS` sits on NET_RATING's scale (verified: slope 1.001).
  Zero-`POSS` lineup rows are defensive-only micro-stints whose points are
  real: exclude from rate models, keep in totals reconciliation.

## nba-on-court (players-on-court filler)

- Works offline from a PlayByPlayV2 frame, **but rewrites `PCTIMESTRING` in
  place** from `"MM:SS"` remaining to integer seconds *elapsed*.
- For periods where a player logged no events it falls back to
  `BoxScoreTraditionalV2` with a 10s default timeout: **pass `timeout=60`**
  as a kwarg, and know that its retry loop catches only `ConnectionError`,
  so `ReadTimeout` escapes on the first attempt.
- Calls `np.in1d`, which NumPy 2.x removed: shim `np.in1d = np.isin`
  before importing the package.

## shufinskiy/nba_data bulk archives

- A season of play-by-play in one ~10 MB download instead of 1,230 calls.
- The `pbpstats` variant has **one row per event within a possession**
  (dedup on `(GAMEID, PERIOD, STARTTIME, ENDTIME, OPPONENT)` to get
  possessions) and was missing 2 of 1,230 games for 2023-24.
- NBA coverage lags roughly a season behind the live endpoints.

## Under-used free sources (verified 2026-07-26)

- **G League shot data**: `ShotChartDetail(league_id="20")` returns ~94k
  shots/season in the identical NBA schema.
  `shot-quality-study/python/05_gleague.py` runs the NBA-fit model on it
  unchanged. pbpstats' `get-games/gleague` API returned empty for standard
  season params in our probe; the nba_api route is the verified one.
- **barttorvik.com** `getadvstats.php?year=Y&csv=1`: full college advanced
  stats, free, **no key** (the cbbdata/toRvik upstream; toRvik itself is
  deprecated). The CSV ships **no header row**: the 67-column order is
  pinned empirically in `draft-study/python/01_harvest.py` (verify a known
  player's height/pts/pick after any endpoint change).
- shufinskiy publishes `wnba_shotdetail_*` (regular season and `_po_`
  playoffs) back to **1997**, plus `wnba_nbastats_*` play-by-play
  companions. The shot-quality pipeline runs on them unchanged
  (`shot-quality-study/python/07_wnba.py`, gated against the WNBA pbp).
  Coverage quirk: NBA `shotdetail_2025` (2025-26) exists while
  `nbastats_2025` does not: shot detail leads play-by-play by a season.
