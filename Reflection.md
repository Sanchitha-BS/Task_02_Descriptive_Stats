# Reflection — Milestone A Research Questions

## Was it a challenge to produce identical numerical results across all three approaches? If so, what caused the discrepancies and how did you resolve them?

Yes — it surfaced two real bugs, not just formatting differences.

The nested-dict columns (`delivery_by_region`, `demographic_distribution`)
were originally parsed twice in pure Python — once for row-level totals,
once for the per-key breakdown. `ast.literal_eval` on dicts with up to ~18
sub-keys was the single biggest cost in the script; collapsing both
computations into one pass roughly halved runtime.

More seriously, the first Pandas draft summed spend/impressions across each
row's nested dict in a way that defaulted empty or missing sub-dicts to `0`
instead of excluding them — silently counting degenerate rows as legitimate
zero-spend data and skewing the mean downward. This was only caught by
cross-checking Pandas' numbers against an independent pure Python run on the
same data sample and noticing the counts didn't match (8,000 vs. 7,624).
Chasing that discrepancy down led straight to the bug. After the fix, both
agree exactly — `n=215,756` on the full file, matching to six decimal
places on mean and std.

A third issue was a memory bug, not a numerical one: storing the parsed
dict objects as a DataFrame column (to avoid re-parsing for the key-
breakdown step) exhausted available memory on the full 500MB file. Fixed by
computing row-totals and the per-key breakdown in a single pass without
persisting the parsed objects.

Beyond bugs, matching numbers required deliberately keeping certain things
identical across all three scripts: the same column classification (which
columns are numeric vs. categorical vs. date vs. nested-dict vs. list), the
same missing-value rules, and the same sample standard deviation convention
(`ddof=1`) — Pandas' and Polars' defaults already match Python's
`statistics.stdev`, so this one didn't need fixing, but it was worth
confirming rather than assuming.

## Do you find one approach easier or more performant than the others? Did you measure performance, or is your assessment based on developer experience?

Both, measured and experienced, and they don't always point the same
direction.

Performance was measured, not just felt: grouped analysis by `page_id`
(4,475 groups) is the clearest data point. Pandas and Polars compute full
per-column statistics for every group in well under two minutes each,
because `groupby`/`group_by` is vectorized. Pure Python, doing the
conceptually identical work, had to be capped to the largest 200 groups
(covering 85.8% of rows) to keep the full run to ~5 minutes — the total
work is bounded by total rows regardless of group count, but Python's
per-call/per-loop overhead makes the same work meaningfully slower without a
vectorized engine underneath.

Developer experience mattered just as much: pure Python required
hand-rolling every statistic (mean/std/median, mode/top-5, missing-value
handling) and every parsing step from scratch — the most instructive
approach, and the easiest place for a subtle bug to hide. Pandas was
fastest to get something working (`describe()`, `groupby().agg()` cover
most of the assignment in a few lines), but that same convenience is
exactly what let the empty-dict bug above slip in unnoticed. Polars was
close to Pandas in ergonomics for the vectorized parts, but has no native
equivalent for parsing arbitrary Python-literal dict/list strings out of a
CSV column — that part still had to be done with plain Python
(`ast.literal_eval`) in a loop, identical to the pure Python approach. For
this dataset's messiest columns specifically, Polars wasn't meaningfully
more "native" than pure Python was.

## If you were coaching a junior data analyst who had never used any of these tools, what approach would you recommend they learn first? Why?

Pandas. It has the largest amount of documentation and community history,
so a beginner gets unstuck faster, and `describe()`/`groupby()` map
directly onto "give me summary stats" and "give me summary stats per
category" — the two things a junior analyst needs constantly — with almost
no boilerplate. It's also the most direct on-ramp to Polars later, since
the mental model (DataFrame, column selection, groupby-aggregate) transfers
even though the syntax differs.

I'd still have them write a pure-Python `numeric_stats()` function once,
not as their working tool but as a teaching exercise — it's what makes
"mean" and "sample standard deviation" concrete rather than a black-box
method call. I wouldn't have them do real analysis in it, though; the
effort-per-line and bug-density in the pure Python script here, versus the
other two, makes that case on its own.

Polars I'd introduce once they hit an actual performance wall in Pandas —
not before. Its stricter typing and expression-based API
(`pl.col(...).mean().alias(...)`, versus Pandas' more permissive style) is a
bigger jump for a first tool than it's worth for someone still learning
what a groupby even does.

## Can coding AI tools (ChatGPT, Claude, Copilot, etc.) produce useful template code to jumpstart each approach? What do they recommend by default when asked to produce descriptive statistics? Do you agree with their recommendations?

Yes, with a caveat that matters. Claude produced complete, runnable
starting scripts for all three approaches in this project, and its default
instinct when asked for "descriptive statistics" leans heavily on Pandas'
`describe()`/`groupby()` idioms as the go-to pattern — a reasonable default
for a well-behaved, flat CSV. I'd agree with that default in the general
case.

Where it fell short was exactly the part that made this dataset hard: it
doesn't know a specific dataset's quirks until it actually runs against
real rows. Both bugs described above — the double-parse inefficiency and
the empty-dict-counted-as-zero correctness bug — came from AI-generated
first-draft code, and both only surfaced once the code was run at full
scale and cross-checked against an independently-implemented version. The
practical lesson: AI-generated template code is a legitimate way to
jumpstart each approach, but "runs without error" and "produces correct
numbers on messy real data" are different bars, and only the second one
actually matters for an assignment like this. Independent cross-
verification across the three approaches wasn't a formality — it's what
caught both bugs.

## Some columns in this dataset contain complex values (lists, nested structures, concatenated strings). What data cleaning was required before you could compute meaningful statistics? Did the three approaches handle this differently?

Three kinds of "complex" columns, three different cleaning needs:

- **Nested-dict columns** (`delivery_by_region`, `demographic_distribution`):
  stored as Python-literal dict strings, e.g.
  `{'Texas': {'spend': 249, 'impressions': 47499}}`. Needed `ast.literal_eval`
  parsing before any stat was meaningful, then a design decision: report
  row-level totals (sum across all sub-keys) *and* a per-key breakdown
  across the whole dataset (which region/demographic got the most spend —
  the actually interesting finding for a political-ads dataset). Row-totals
  alone would have just duplicated `estimated_spend`. About 12.5% of rows
  had empty or degenerate dicts here and had to be explicitly excluded, not
  zero-filled — the correctness bug described above happened precisely
  because that exclusion was missed in one implementation.
- **List-string columns** (`publisher_platforms`, `illuminating_mentions`):
  stored as `['facebook', 'instagram']`-style strings. Needed parsing plus
  exploding into individual items before `value_counts`/mode were
  meaningful — counting whole-list strings as categories would have made
  every multi-platform ad its own unique "category."
- **Binary flag columns** (~28 columns, `scam_illuminating`,
  `incivility_illuminating`, all the topic/message-type flags): technically
  parse as numeric (0/1), so a purely mechanical "does it parse as a float"
  rule would call them numeric — which is correct, but not obviously useful
  on its own. Added an explicit flag-rate annotation (count and % that are
  `1`) alongside the standard mean/std/median output so the numeric stats
  are interpretable as "how often is this flagged," not just an abstract
  mean.

Did the three approaches differ in handling these? Less than expected, and
the difference is informative. All three needed the identical
`ast.literal_eval`-based parsing for the nested-dict and list columns —
neither Pandas nor Polars has a built-in "parse this Python-literal string
safely" primitive, so this part of the cleaning was effectively pure Python
regardless of which script it lived in. The real difference was in what
happened after parsing: pure Python needed manual loops and `Counter`s for
every aggregation; Pandas and Polars could push the already-parsed numeric
row-totals through vectorized `describe()`/`groupby()`, which is where their
performance and conciseness advantage actually shows up. The lesson: for
messy, semi-structured source data, the tooling advantage of Pandas/Polars
is in the aggregation step, not in the initial cleaning step.
