# Reflection — Milestone A Research Questions

### 1. Was it a challenge to produce identical numerical results across all three approaches?

Yes. The Pandas script initially summed spend/impressions across nested dict columns by defaulting empty sub-dicts to 0 instead of excluding them, which skewed the mean. Cross-checking against the pure Python output caught the mismatch, and the fix was to exclude empty dicts consistently across all three scripts. Standard deviation used `ddof=1` in all three so they already matched on that front.

### 2. Do you find one approach easier or more performant than the others?

- **Pure Python** is the most tedious, especially for grouped analysis — full per-group stats had to be capped to the largest 200 of 4,475 `page_id` groups just to keep runtime under 5 minutes.
- **Pandas** is fast to write and computes full stats for all 4,475 groups in under 2 minutes via `groupby().agg()`.
- **Polars** was verified for correctness (matches Pandas and pure Python exactly) but wasn't separately timed, so no performance claim is made here — it's architecturally similar to Pandas (vectorized `group_by`), but that's an expectation, not a measurement. It has no built-in way to parse the nested dict/list string columns either, so that part still needed plain Python.

### 3. Recommendations for a junior data analyst

Learn **Pandas** first — largest ecosystem, and `describe()`/`groupby()` cover most real analysis needs immediately. Introduce **Polars** once they hit a performance wall. Pure Python is worth doing once as an exercise, not as a working tool.

### 4. AI-generated template code

Yes, useful as a starting point — Claude produced working scripts for all three approaches and defaults to Pandas idioms when asked for descriptive statistics. It doesn't know a dataset's specific quirks until it's actually run against real data — two bugs (a double-parsing inefficiency and the empty-dict bug above) only surfaced after running at full scale and cross-checking results.

### 5. Complex values and data cleaning

`delivery_by_region` and `demographic_distribution` are stringified dicts needing `ast.literal_eval` before any stat was meaningful. `publisher_platforms` and `illuminating_mentions` are stringified lists needing exploding before counts made sense. All three approaches needed the same manual parsing for these — neither Pandas nor Polars has a built-in parser for arbitrary Python-literal strings, so this step was effectively pure Python regardless of which script it lived in.
