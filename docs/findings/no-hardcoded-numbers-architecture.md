# How this family enforces "no number typed by hand"

Built 2026-07-26. Two layers, both wired into the family check suite:

1. **Generator-owned README regions.** Every study's findings script
   writes not just the Findings section but every numeric block, between
   HTML-comment markers (`<!-- gen:... -->`). Each generator has a
   `--check` mode that regenerates the regions in memory and fails the
   study's checks if the committed README has drifted from what the
   outputs say. Generators write plain text; the glossary tool re-adds
   hover tooltips afterward, so the drift checks strip those tags before
   comparing.
2. **Family-wide number verification.** `verify_numbers.py` extracts
   every numeric token from the narrative pages, BRIEFs, and remaining
   README prose (about 1,180 tokens across 21 files) and matches each
   against committed output cells, output row counts, and data-file row
   counts at the displayed precision. Unmatched tokens fail the suite
   unless allowlisted with a written reason; the allowlist holds only a
   handful of reconcile-tolerance magnitudes that the gates verify live.

   **Correction, October 18, 2026: layer 2 never verified anything.** It
   matched each token against one pool of every numeric cell in every
   study's `output/` (1,066,841 values, gitignored local files included),
   and 400 of 400 random wrong numbers passed at one decimal, one decimal
   with %, and two decimals. A wrong "40.7%" injected into the playoff
   series story passed. Re-scoped to each study's git-tracked outputs, 32
   tokens in five studies matched nothing: they had passed only on
   coincidental values in other studies. Two more were missed only by
   bugs that the large pool hid: a row count cut off by a capped file
   listing, and negative proportions shown as unsigned percentages. The
   interim gate (tools, October 18) scopes the pool per study, leaves
   `gen:` regions to their generators, marks those 32 tokens UNVERIFIED in
   the allowlists, and prints each file's measured chance that a nearby
   wrong number still passes (median 86%). Exact per-number bindings to
   output cells are the replacement. Layer 1 is unaffected.

Why it exists: the first generator runs caught four real drifts that
hand-carried prose had accumulated, including a validation rate quoted
as 97.5% that the committed gate output puts at 97.6%. Careful hands
still rot; gates do not.
