# Task 2 — Descriptive Statistics (Milestone A)

Descriptive and grouped statistical analysis of `2024_fb_ads_president_scored_anon.csv`
(246,745 rows, 41 columns), a 2024 U.S. presidential campaign Facebook ads
dataset scored with additional `illuminating_*` content-classification
flags. Implemented three independent ways — pure Python (standard library
only), Pandas, and Polars — with results cross-verified across all three.

## Getting the dataset

The CSV is not included in this repository. Download it and place it in the
same folder as the three scripts before running any of them.

Dataset source: provided as part of the Illuminating project's political
advertising research at Syracuse University's School of Information Studies
(the `*_illuminating` column naming matches this project). *[Add the exact
download link/location here.]*

```
Task_02_Descriptive_Stats/
├── 2024_fb_ads_president_scored_anon.csv   <- add this (not tracked in git)
├── pure_python_stats.py
├── pandas_stats.py
├── polars_stats.py
├── README.md
├── REFLECTION.md
└── requirements.txt
```

If you'd rather keep the CSV somewhere else, update the `CSV_PATH` constant
near the top of all three scripts — each currently defaults to
`2024_fb_ads_president_scored_anon.csv` in the working directory.

## Setup

```
pip install -r requirements.txt
```

`pure_python_stats.py` has no dependencies beyond the standard library.

## Running the scripts

```
python3 pure_python_stats.py
python3 pandas_stats.py
python3 polars_stats.py
```

All three files must stay in the same folder — `pandas_stats.py` and
`polars_stats.py` both import from `pure_python_stats.py` to reuse its
parsing/statistics functions and cross-check their own numbers against it.

Each script writes its own full output automatically —
`pure_python_output.txt`, `pandas_output.txt`, `polars_output.txt` — and
prints a one-line confirmation when done, rather than dumping the report to
the terminal. Full runs take roughly 5 minutes (pure Python) and well under
2 minutes each for Pandas and Polars.

`pandas_stats.py` and `polars_stats.py` additionally write full per-
`page_id`-group statistics (all 4,475 groups) to CSV
(`grouped_pandas_page_id_numeric.csv` / `_categorical.csv` and the Polars
equivalents). `pure_python_stats.py` writes the same for its largest 200
groups to `grouped_stats_page_id.txt` (see [REFLECTION.md](./REFLECTION.md)
for why it's capped there rather than covering all 4,475).

## Summary of findings

- **Spend is heavily concentrated in swing states.** By total spend in the
  `delivery_by_region` breakdown: Pennsylvania (~$31.1M), Michigan (~$26.5M),
  North Carolina (~$17.5M), Georgia (~$16.3M) — all ahead of California
  (~$19.6M) despite its much larger population and media market.
- **Older demographics received the most targeted spend.** By total spend in
  `demographic_distribution`: `female_65+` (~$44.0M), `female_55-64`
  (~$29.1M), `male_65+` (~$26.2M) top the list — older cohorts, and women in
  particular, were targeted with substantially more ad spend than younger
  groups.
- **`estimated_spend` doesn't fully reconcile with the nested breakdowns.**
  `estimated_spend` averages ~$1,061/ad, but summing each ad's own
  `delivery_by_region`/`demographic_distribution` breakdown gives ~$1,195–
  $1,200 — the two nested breakdowns agree with each other but not with the
  flat estimate, worth flagging as a data-quality note.
- **Donald Trump is mentioned far more than Biden or Harris** in
  `illuminating_mentions` (78,324 vs. 53,239 and 24,247), with "President
  Trump"/"President Biden" appearing as separate frequent variants —
  suggesting title usage wasn't normalized before this field was built.
- **Ads span 2021-07-06 to 2024-11-05** — despite being labeled "2024
  election" data, activity predates the 2024 campaign cycle itself.
  Anyone filtering to "the 2024 race" specifically should apply an explicit
  date cutoff.
- **Not everything is USD.** `currency` has 18 distinct values — 246,599 of
  246,745 rows are USD, but INR, GBP, EUR, PKR, and others appear in small,
  non-zero counts. Spend figures aren't strictly comparable across all rows
  without accounting for this.
- **Content flags:** `cta_msg_type_illuminating` (57.3%) and
  `advocacy_msg_type_illuminating` (54.9%) are the most common of the ~28
  binary content flags — most ads ask the viewer to do something.
  `incivility_illuminating` flags 18.75% of ads (nearly 1 in 5);
  `scam_illuminating` flags 7.16%; `fraud_illuminating` and
  `lgbtq_issues_topic_illuminating` are the rarest, both under 0.35%.
- **`ad_id` is already the dataset's atomic grain.** Grouping by
  `page_id`+`ad_id` produces exactly 246,745 groups for 246,745 rows — one
  ad per group. `page_id` alone (4,475 groups) is where meaningful grouped
  analysis actually happens — the top page alone ran 55,503 ads (~22% of
  the whole dataset), and the top 5 pages combined account for over 45%.

## Comparison of the three approaches

See [REFLECTION.md](./REFLECTION.md) for the full comparative analysis and
responses to the assignment's research questions.
