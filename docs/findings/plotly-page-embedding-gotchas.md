# Plotly and page-embedding gotchas

Found 2026-07-26 while publishing this family's GitHub Pages sites. Each
cost real debugging time.

- **Plotly parses "YYYY-MM"-shaped category strings as dates.** Season
  labels like "2010-11" become the date November 2010: the axis turns
  into a date axis with month and day ticks and a truncated range. Fix:
  `fig.update_xaxes(type="category")`. Symptom to recognize: month+day
  tick labels on what should be a season axis.
- **`plotly.write_html` pins the wrapper div to the layout's fixed pixel
  size.** Responsive embedding needs that patched to 100% plus a resize
  listener calling `Plotly.relayout(gd, {autosize: true, width: null,
  height: null})`. See `report_builder.py` in basketball-analysis-tools.
- **Frames + slider carry exactly one control dimension.** A second
  control (bin size next to a season slider) means dropping frames:
  embed the raw data as JSON and drive the plot with a small vanilla-JS
  layer and `Plotly.react`.
- **Native `<abbr title>` tooltips read as broken** (help cursor, then a
  delayed unstyled OS tooltip). Published pages convert `title=` to
  `data-tip=` with a styled `:hover::after` tooltip; READMEs keep
  `title=` because GitHub renders it natively.
- **Round hover values in the data**, not only in d3 format specs.
- **nba_api `LeagueDashPtStats` takes `per_mode_simple`**, unlike the
  `per_mode_detailed` used by the LeagueDash* family.
