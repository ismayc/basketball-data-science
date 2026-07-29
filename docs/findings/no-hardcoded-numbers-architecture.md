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

Why it exists: the first generator runs caught four real drifts that
hand-carried prose had accumulated, including a validation rate quoted
as 97.5% that the committed gate output puts at 97.6%. Careful hands
still rot; gates do not.
