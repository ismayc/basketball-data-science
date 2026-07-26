# Analysis audit: 2026-07-25

A full second-pass review of the three work-sample studies: every claim in each
README checked against the code and regenerated outputs, plus targeted
re-derivations to hunt for issues the original pass could have missed. Each
finding lists the evidence, the resolution, and the commit that carries it.

*(A third pass later the same evening, covering the new valuation study and
the possession join as well, is recorded at the bottom under "Second full
scan".)*

Verification commands used throughout:

```bash
# jersey-height-study
../.venv/bin/python python/03_analysis.py && Rscript R/03_analysis.R
../.venv/bin/python python/04_reconcile.py     # exit 0 = all checks pass

# playbyplay-study
../.venv/bin/python python/02_analysis.py && Rscript R/02_analysis.R
../.venv/bin/python python/04_reconcile.py

# tracking-study
../.venv/bin/python python/03_analysis.py && ../.venv/bin/python python/04_validate.py
```

---

## playbyplay-study

### PBP-1 · BUG: text sort on `actionNumber` corrupted every window score  ❌→✅ fixed

**Severity: high. All headline numbers changed.**

`PlayByPlayV3` delivers every column as text. `02_analysis.py` sorted events by
`actionNumber` without casting it, so `"100"` sorted before `"2"`. The score
forward-fill ran in that scrambled order, and the "last event of the period /
last event before the 60s mark" selections picked lexicographically-last rather
than chronologically-last events.

**Evidence.** Re-deriving the window table with a numeric sort: 1,600 of 7,380
window rows differed; mean window points 1.47 (text sort) vs 2.20 (numeric).
Period 1 was hit hardest (action numbers 100–199 sort before 2).

**Impact on published findings** (old → corrected):

| Quantity | Before | After |
|---|---|---|
| Mean points, 2-for-1 group | 1.558 | 2.347 |
| Mean points, held group | 1.203 | 1.767 |
| Own-points gap | +0.355 [+0.254, +0.454] | **+0.579 [+0.475, +0.679]** |
| Restricted own-points gap | +0.229 [+0.086, +0.367] | **+0.364 [+0.216, +0.512]** |

Direction and significance survived; magnitudes did not. The first-shot timing
histogram and eFG-by-clock table were unaffected (order-independent).

**Fix.** Cast `actionNumber` to Int64 before sorting (`python/02_analysis.py`),
with a comment explaining why. The new R implementation (PBP-3) guards this
class of bug permanently.

### PBP-2 · MISSING OUTCOME: the analysis ignored the cost side of the trade  ❌→✅ fixed

The study measured **own points** in the window. But the case for *holding* is
precisely that it denies the opponent a reply: the cost of the 2-for-1 lives in
**opponent points**, which the outcome never counted.

Added a second outcome, `net = own − opponent points` in the same window
(complete for all 7,221 team-periods; the per-side score deltas exist even when
the opponent never attempted a shot). Corrected results:

- Full sample: net gap **+0.679 [+0.544, +0.816]**, inflated by selection
  (the "held" group includes windows the opponent controlled).
- Restricted comparable sample (first shot 20–45s): net gap
  **+0.188 [−0.002, +0.375]**. The own-points gap survives restriction
  (+0.364, excludes zero) but the net gap narrows to the edge of what one
  season can distinguish from zero.

The findings now state the honest version: the extra possession is real, the
"rushed bad shot" objection is still absent, and what limits the payoff is the
opponent's reply, not shot quality.

### PBP-3 · GAP: empty `R/` directory  ❌→✅ fixed

The original instruction was analysis in both Python and R; the study shipped
Python-only with an empty `R/` folder. Added `R/02_analysis.R` (tidyverse +
nanoparquet), an independent implementation of every table, plus
`python/04_reconcile.py` comparing all four tables row-by-row at 1e-9 and the
four bootstraps by CI overlap. **ALL CHECKS PASS**: R independently reproduces
the corrected numbers exactly.

---

## jersey-height-study

Reconciliation re-run in a fresh environment before any changes: ALL CHECKS
PASS. No correctness bugs found. Two places where the analysis stopped short of
what the data could support, both now implemented (in both languages, gated by
the reconcile step):

### JH-1 · UPGRADE: within-player check on the 2019 measurement step  ✅ added

The README attributed the −0.61 in single-season step to the 2019-20
measurement rule change, but the aggregate series cannot rule out roster
composition (who entered/left the league). The clean test is **within-player**:
same players rostered in both seasons, so composition cannot move.

Result: among 388 players rostered in both 2018-19 and 2019-20, **55.4% got
shorter on paper** (mean −0.57 in). In every normal offseason, 1–6% of
continuing players' listed heights fall. The within-player delta accounts for
~94% of the −0.606 aggregate step. Attribution is now proven at the player
level, not asserted. New output: `within_player_{python,r}.csv`, reconciled.

### JH-2 · UPGRADE: the piecewise model was the wrong model, by its own logic  ✅ added

The README argues a single straight line "would be the wrong model" and fits a
knot at 1990. But heights rose until 2002 then fell. The single-knot model
averages that into a near-flat post-1990 slope, and its fit is poor (R² 0.30;
AIC scan puts the best single knot near 2010, not 1990).

Added `height_regime`: knots at 1990 and 2002 **plus a level-shift term at
2019**. R² 0.85, AIC −54 vs +10. The shift term estimates the rule-change step
directly: **−0.636 in, 95% CI [−0.801, −0.472]**, a modeled estimate with
uncertainty instead of an eyeballed difference of consecutive seasons. The
original piecewise model is retained for continuity; findings quote both.

Minor: kept, not changed. The keep-first de-duplication of mid-season trades
takes whichever team's roster row happens to come first in the harvest. Heights
are identical across a player's rosters, so height metrics are unaffected;
jersey-number metrics could differ for the handful of players who changed
numbers mid-season. Documented here rather than churned.

---

## tracking-study

Validation against the NBA's published SpeedDistance aggregates re-run: PASSED
(2.00 vs 2.00 miles; +0.01 mph on speed). The de-duplication logic, clock-based
dt, and glitch-filter reasoning all held up under line-by-line review. Two
smaller issues:

### TS-1 · REPRODUCIBILITY: spacing subsample was nondeterministic  ❌→✅ fixed

`possession_frames()` returned rows in `group_by` order, which polars does not
guarantee; `spacing_by_frame()` then kept every 5th **row**. The sampled frames
therefore differed run-to-run, in a study that explicitly sells deterministic
reproducibility. Fixed by sorting into game order (period, clock descending)
before returning. Spacing numbers under the deterministic sample: median 529 sq
ft (was 531), IQR 370–708, n = 116,801 (README updated).

### TS-2 · STALE DOC: docstring cited a folklore benchmark  ❌→✅ fixed

`03_analysis.py`'s docstring described validation against "the NBA's published
figure of roughly 2.5 miles per game for a starter", a number the study itself
disproves (the real published median is ~2.0). The actual validation (against
`LeagueDashPtStats`) was always correct; the docstring now describes it.

### TS-3 · noted: possession heuristic still unvalidated

Limitation 3 (nearest-player possession heuristic never checked against
play-by-play possession labels) is the study's own stated next step. Addressed
separately as the tracking-study extension, not part of this audit.

---

## Cross-cutting

- **Environment.** The studies' venv lived in an ephemeral session scratchpad.
  Added a repo-root `requirements.txt` and `.venv` convention (gitignored) so
  every pipeline runs from a durable environment.
- **What did not change.** Harvest scripts (both studies), parse/de-dup logic,
  figure code, palette, and all cleaning rules survived review unchanged.
- **Pattern worth naming in an interview.** Two of the five real findings
  (PBP-1, TS-1) are silent-ordering bugs: the data was never wrong, the row
  order was. Both were caught by re-deriving a result through an independent
  path, which is the argument for the reconciliation discipline the studies
  were already built around.

---

# Second full scan: 2026-07-25, late evening

Fresh-eyes pass over the whole repo including the work added since the first
audit. Method: independent re-derivation of published numbers rather than
re-reading conclusions.

## Verified clean (independent re-derivations)

- **playbyplay window scores, by hand.** Game 0022300001 Q1: read the stamped
  scores directly off the raw feed (31–26 at 76s, 36–26 at 0s) → h=5, v=0.
  Matches `team_period_windows.csv` exactly, including the opponent column.
- **playbyplay location field.** All 218,702 FGA rows across 1,230 games carry
  `h`/`v`. The eFG-by-clock table (which doesn't filter location) is clean.
- **valuation POSS semantics.** Per-team lineup `POSS` sums land at
  8,206–8,793, an offensive-possession count. And `100·PM/POSS` regressed on
  the NBA's own NET_RATING: slope 1.001, intercept +0.07. Our outcome sits on
  the league's scale, verified rather than assumed.
- **tracking latency stability.** Calibrating each half of each game
  separately moves the chosen lead ≤2.5 s; agreement stays 94–100% at either
  optimum. The constant-within-game assumption is approximate and
  approximately harmless (README updated with the numbers).

## Found and fixed

### SCAN-1 · jersey: "1–6% in a normal offseason" was wrong, and hid a finding

The within-player table shows the 2019 break has **echoes**: 26% of continuing
players' listed heights changed across 2021-22→2022-23 (net *upward*) and 18%
across 2022-23→2023-24: follow-on re-measurements settling in. The true
baseline is a **median ~2%** churn, with nothing but the 2019 aftermath and a
1994 blip above 12%. The "1–6%" claim (docstrings, R comments, BRIEF) is
corrected everywhere, and the echo wave is now a generated finding in the
README ("The 2019 break has echoes"). The series from 2019–2023 is a settling
process, not a stable regime.

### SCAN-2 · valuation: cross-season stability, the missing backtest

Computed the honest reliability check the study lacked: for the 317 players
fitted in both seasons (two apart), estimates correlate at **r = 0.31**
(**0.38** for the 181 with 2,000+ possessions in both), squarely in the
documented range for single-season RAPM-family metrics, now quantified on this
data and reported in the generated findings. This is the empirical case for
the multi-season priors production metrics add.

### SCAN-3 · smaller fixes

- playbyplay BRIEF quoted "~52% eFG" for early shots; the value is 0.551 → "~55%".
- ATS resume "Libraries & Tools" omitted **polars and plotly**, the stack all
  four studies actually use. Added; parse and page count re-verified.
- valuation `fig2` carried a dead `if False else None` expression from
  drafting; removed and the pipeline re-run + re-reconciled.

## Judged fine, deliberately unchanged

- Jersey keep-first de-dup of mid-season trades (arbitrary team, height
  invariant): documented in the first audit; still the right call.
- The valuation model's lack of opponent adjustment: the study's central
  stated limitation with a documented upgrade path, not an oversight.
- CV fold assignment by row-index-mod-5 on sorted rows: deterministic and
  reproducible across languages, which is what it is for; a randomized
  assignment would trade that for nothing measurable here.

## Shot-quality study build (2026-07-26)

### BUILD-1 · R SE column silently degraded by dplyr sequential summarise

Found by the R↔Python reconcile gate on the new shot-quality study's first
run: every sum, mean, ranking, and rate matched to ~1e-12, but the
shot-making standard error diverged by up to 25 points per 100 for tiny
samples. Cause: in `summarise(..., xpts = sum(xpts), making_sd = sd(points -
xpts))` dplyr evaluates arguments **sequentially**, so `xpts` was already the
group's scalar sum when the sd referenced it, silently turning
`sd(points - xpts)` into `sd(points)`. Fixed by computing `making_sd` before
the sum redefines the name; a regression test now guards the exact failure
(`tests/R/test-shotquality.R`), and the study README reports the catch
rather than hiding it. This is the second real bug (after the actionNumber
text sort) that only the two-implementation discipline surfaced.

### BUILD-2 · calibration tightened by three deliberate feature rounds

The initial location-only model failed its own decile-calibration gate
(worst decile 0.019 vs the 0.01 threshold). Three diagnosed rounds brought
the worst decile to 0.0098: extra short-range distance knots,
family-specific distance slopes (a 5-ft putback is not a 5-ft jump shot),
and driving/cutting/running modifiers plus court side. The gate was left
at 0.01 rather
than loosened; the misses it caught were real model deficiencies, each
visible in a family-level residual table before the fix.
