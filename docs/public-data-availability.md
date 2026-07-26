# Public NBA data: what exists that is more recent, surveyed 2026-07-25
*(amended 2026-07-26 with sources verified while building the shot-quality
and draft studies: see "Newly verified" below)*

Question from Chester: *is there public data more recent than what the studies
use?* Short answer: **event/possession/lineup data is live through the just-
completed 2025-26 season and is now used where it helps; raw tracking remains
frozen at 2015-16 with nothing newer public.**

## What is live and current (usable today)

| Source | Granularity | Recency | Status in this repo |
|---|---|---|---|
| `stats.nba.com` via `nba_api` (PlayByPlayV3, LeagueDashLineups, LeagueDashPlayerStats, …) | event / lineup / player aggregates | **live, includes 2025-26** | ✅ **lineup-valuation-study now fits 2025-26 alongside 2023-24** |
| [pbpstats](https://github.com/dblackrun/pbpstats) ([docs](https://pbpstats.readthedocs.io/)) | **possession-level** parsed pbp with possession start type/time | live (NBA, WNBA, G-League) | ✅ **Wired in** (via the bulk archive's pbpstats variant): `playbyplay-study/python/05_possession_analysis.py`, the decision-team design |
| [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) | bulk pre-scraped pbp (stats + data.nba + pbpstats variants), shot details | through 2024-25 at survey time | ✅ **Wired in**: feeds both the possession analysis and the stint builder (`lineup-valuation-study/data/pbp_bulk/`) |
| [shufinskiy/nba-on-court](https://github.com/shufinskiy/nba-on-court) | fills **players-on-court** into pbp rows | current | ✅ **Wired in**: `05_build_stints.py` + `06_stint_rapm.py`: full opponent-adjusted stint RAPM, validated (two caveats found: it rewrites PCTIMESTRING to elapsed seconds, and its boxscore fallback needs `timeout=` raised) |
| [hoopR](https://github.com/sportsdataverse/hoopR) (sportsdataverse) | ESPN + NBA pbp/box, R-native data releases | current | Alternative R-side feed; different event coding |
| [dunksandthrees EPM](https://dunksandthrees.com/epm/actual), [DARKO](https://www.darko.app/), [nbarapm.com](https://www.nbarapm.com/) | modeled player value (EPM / DPM / RAPM) | current incl. 2025-26 | Used as *qualitative* reference points for the valuation study's face-validity check; no bulk CSV download confirmed, so not wired into the pipeline |

## Newly verified 2026-07-26 (all probed with working requests)

| Source | What | Status in this repo |
|---|---|---|
| `ShotChartDetail` bulk (via shufinskiy `shotdetail_2023`) | 218,701 shots with x/y, zone, action type, clock | ✅ **Wired in**: `shot-quality-study/` xMake/xPTS model |
| **G League** via `ShotChartDetail(league_id="20")` | 94,128 G League shots for 2023-24, identical schema; almost unused publicly | ✅ **Wired in**: `shot-quality-study/python/05_gleague.py`: cross-league execution-gap analysis. (pbpstats' `get-games/gleague` API returned empty for standard season params in our probe. The nba_api route is the one verified.) |
| [barttorvik.com](https://barttorvik.com) `getadvstats.php?year=Y&csv=1` | 67-column college advanced stats, 2008+, free, **no key** (upstream of cbbdata/toRvik; toRvik itself is deprecated) | ✅ **Wired in**: `draft-study/` (56,781 player-seasons, 2011-2022) |
| nba_api `DraftHistory` + `LeagueDashPlayerStats` | draft picks with NBA PERSON_ID; season minute totals | ✅ **Wired in**: `draft-study/` outcome construction, ID-joined |
| [HF `dcayton/nba_tracking_data_15_16`](https://huggingface.co/datasets/dcayton/nba_tracking_data_15_16) | the 2015-16 raw SportVU season repackaged with play-by-play merged | Verified reachable; documented as the cleaner modern mirror of what `tracking-study/` parses from the raw 7z logs |
| WNBA shot detail (shufinskiy `wnba_shotdetail_*`, **1997-present**) | same schema, WNBA | ✅ **Wired in**: `shot-quality-study/python/07_wnba.py`: refits 2024 + 2025 with a `wnba_nbastats` play-by-play gate; source of the corner-three rulebook finding |

## What is NOT public, still

| Feed | Why not |
|---|---|
| Second Spectrum raw optical tracking (2017-2023) | teams/licensees only ([confirmed](https://en.wikipedia.org/wiki/Player_tracking_(National_Basketball_Association))) |
| Hawk-Eye skeletal tracking (2023-present) | teams only |
| Raw SportVU beyond the 2015-16 archive | access was closed mid-2016; the GitHub mirrors are the frozen remainder |

The NBA does publish **aggregated** tracking stats (drives, touches, speed/
distance, matchups) through live endpoints. That is what `tracking-study/
04_validate.py` validates against, and those aggregates are current. What is
missing publicly is the raw 25 Hz feed itself.

## Decisions taken on the back of this survey

1. **lineup-valuation-study runs on 2025-26 too**: the harvest and model are
   season-parameterized; findings report both seasons side by side.
2. **Not** re-harvested the play-by-play study for 2025-26 in this pass: the
   pipeline is one `--season` flag away (`01_harvest_pbp.py --season 2025-26`,
   ~20 min rate-limited) and the study's conclusions are method-shaped rather
   than season-shaped. Documented rather than run.
3. **matchup data** (`stats.nba.com` matchups, 2017-18+) noted as the public
   route to opponent-adjusted defensive analysis, unexplored here.

Sources: [pbpstats docs](https://pbpstats.readthedocs.io/) ·
[pbpstats GitHub](https://github.com/dblackrun/pbpstats) ·
[shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) ·
[nba-on-court](https://github.com/shufinskiy/nba-on-court) ·
[hoopR](https://github.com/sportsdataverse/hoopR) ·
[dunksandthrees](https://dunksandthrees.com/epm/actual) ·
[darko.app](https://www.darko.app/) ·
[nbarapm.com](https://www.nbarapm.com/datasets/nba) ·
[NBA player tracking (Wikipedia)](https://en.wikipedia.org/wiki/Player_tracking_(National_Basketball_Association))

## Broadcast-video computer-vision datasets (verified 2026-07-26)

Raw tracking output stopped being public after 2015-16, but a different
family of public data has grown up since: computer-vision datasets built
from NBA broadcast footage. These provide video plus annotations, not
court-coordinate tracking, so they complement rather than replace the
SportVU archive:

| Dataset | What it provides | Typical task |
|---|---|---|
| Basketball-51 | Short broadcast clips labeled by event (2pt/3pt/free throw, make/miss) | Action recognition |
| NSVA | ~32k broadcast clips paired with play-by-play descriptions | Video understanding / captioning |
| SportsMOT | Player bounding boxes in image coordinates across basketball/soccer/volleyball clips | Multi-object tracking |
| DeepSportRadar | Player segmentation, re-identification, ball 3D localization, camera calibration | Vision pipeline components |

The limiting facts for analytics use: broadcast cameras follow the ball
(off-ball players leave frame), and image-space boxes only become court
coordinates through calibration/homography, which carries its own error.
The study these enable, broadcast pseudo-tracking error-quantified
against real tracking and gated on `LeagueDashPtStats` aggregates, is
planned as the family's next build; the design lives in the tracking
study's README.
