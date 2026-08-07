# Milestone A: Descriptive Statistics Research Task

This project explores three different approaches to computing descriptive statistics and performing grouped analysis on a dataset of 2024 Facebook political ads.

## Approaches

1. **Pure Python (`pure_python_stats.py`)**: Uses only the Python standard library (csv, math, collections). Fully explicit — every statistic is computed by hand.
2. **Pandas (`pandas_stats.py`)**: Uses the Pandas library. Higher-level API, `describe()` and `groupby()` handle most of the work.
3. **Polars (`polars_stats.py`)**: Uses Polars, a Rust-based DataFrame library with strict typing and expression-based syntax.

## Dataset

`2024_fb_ads_president_scored_anon.csv` — 246,745 rows, 41 columns, 2024 U.S. presidential Facebook ads. Not included in this repo; download it and place it in the root directory. *[Add the exact download link/location here.]*

## How to Run

1. **Place the data**: put `2024_fb_ads_president_scored_anon.csv` in the root directory.
2. **Install dependencies**: `pip install -r requirements.txt`.
3. **Run the scripts**:
   - `python pure_python_stats.py`
   - `python pandas_stats.py`
   - `python polars_stats.py`

All three scripts also perform grouped analysis by `page_id` and by `page_id`+`ad_id`.

`pandas_stats.py` and `polars_stats.py` both import from `pure_python_stats.py` — all three files must stay in the same folder.

## Summary of Findings

- **Numeric columns** (`estimated_spend`, `estimated_impressions`, `estimated_audience_size`, and ~28 binary `illuminating_*` flags) were analyzed for count, mean, min, max, median, and standard deviation.
- **Categorical columns** (`page_id`, `bylines`, `currency`, etc.) were analyzed for unique counts and modes.
- **Nested-dict columns** (`delivery_by_region`, `demographic_distribution`) required parsing before analysis; the region/demographic spend breakdown shows swing states (PA, MI, NC, GA) and older demographics receiving the most targeted spend.
- **`currency` is not exclusively USD** — 18 distinct currencies appear in the data.
- **Grouped analysis** shows `page_id` (4,475 groups) is where meaningful aggregation happens — `page_id`+`ad_id` produces one group per row, since `ad_id` is already the dataset's atomic grain.

