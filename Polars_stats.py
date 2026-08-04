
import polars as pl
import polars.selectors as cs
from pure_python_stats import numeric_stats, parse_container

CSV_PATH = "2024_fb_ads_president_scored_anon.csv"

LIST_COLUMNS = ["publisher_platforms", "illuminating_mentions"]
DATE_COLUMNS = ["ad_creation_time"]
NESTED_DICT_COLUMNS = ["delivery_by_region", "demographic_distribution"]
PLAIN_CATEGORICAL_COLUMNS = ["bylines", "currency", "illuminating_scored_message"]
BINARY_FLAG_THRESHOLD = 2


def load_data():
    return pl.read_csv(CSV_PATH, infer_schema_length=None)


def numeric_columns(df):
    return df.select(cs.numeric()).columns


def show_structure(df):
    print("BASIC STRUCTURE")
    print(f"shape: {df.shape}  (rows, columns)\n")
    print("dtypes:")
    for c, dt in zip(df.columns, df.dtypes):
        print(f"  {c}: {dt}")


def show_missing(df):
    print("\nMISSING VALUES PER COLUMN")
    nulls = df.null_count()
    total = df.height
    for c in df.columns:
        miss = nulls[c][0]
        pct = miss / total * 100
        print(f"{c}: missing={miss} ({pct:.2f}%)")


def show_describe(df):
    num_cols = numeric_columns(df)
    non_num_cols = [c for c in df.columns if c not in num_cols]

    print("\nDataFrame.describe() -- NUMERIC COLUMNS")
    print(df.select(num_cols).describe())

    print("\nDataFrame.describe() -- NON-NUMERIC (STRING) COLUMNS")
    print(df.select(non_num_cols).describe())


def show_binary_flag_rates(df):
    print(f"\nBINARY FLAG COLUMNS (<= {BINARY_FLAG_THRESHOLD} distinct values) -- flag rate")
    for col in numeric_columns(df):
        nun = df[col].n_unique()
        if nun <= BINARY_FLAG_THRESHOLD:
            count = df[col].drop_nulls().len()
            flagged = int(df[col].sum())
            rate = df[col].mean()
            print(f"{col}: {flagged}/{count} ({rate*100:.2f}%) == 1")


def show_categorical_value_counts(df):
    print("\nCATEGORICAL COLUMNS -- value_counts() / n_unique()")
    for col in PLAIN_CATEGORICAL_COLUMNS + ["page_id", "ad_id"]:
        print(f"\n{col}  (n_unique={df[col].n_unique()})")
        print(df[col].value_counts(sort=True).head(5))


def explode_list_columns(df):
    print("\nLIST COLUMNS -- exploded item value_counts()")
    for col in LIST_COLUMNS:
        parsed = [parse_container(v, list) or [] for v in df[col].to_list() if v is not None]
        exploded = [item for sub in parsed for item in sub]
        s = pl.Series(col, exploded)
        print(f"\n{col}  (unique items={s.n_unique()})")
        print(s.value_counts(sort=True).head(5))


def parse_date_columns(df):
    for col in DATE_COLUMNS:
        df = df.with_columns(
            pl.col(col).str.strptime(pl.Date, format="%Y-%m-%d", strict=False).alias(col)
        )
    return df


def show_date_stats(df):
    print("\nDATE COLUMNS")
    for col in DATE_COLUMNS:
        s = df[col].drop_nulls()
        print(f"{col}: count={s.len()} min={s.min()} max={s.max()} unique={s.n_unique()}")


def process_nested_dict_columns(df):
    breakdowns = {}
    for col in NESTED_DICT_COLUMNS:
        row_spend, row_impr = [], []
        spend_by_key, impr_by_key, rows_by_key = {}, {}, {}
        for v in df[col].to_list():
            if v is None:
                row_spend.append(None)
                row_impr.append(None)
                continue
            parsed = parse_container(v, dict)
            if not parsed:
                row_spend.append(None)
                row_impr.append(None)
                continue
            total_spend, total_impr, found = 0.0, 0.0, False
            for key, sub in parsed.items():
                if isinstance(sub, dict):
                    found = True
                    s = sub.get("spend") or 0
                    i = sub.get("impressions") or 0
                    total_spend += s
                    total_impr += i
                    spend_by_key[key] = spend_by_key.get(key, 0) + s
                    impr_by_key[key] = impr_by_key.get(key, 0) + i
                    rows_by_key[key] = rows_by_key.get(key, 0) + 1
            row_spend.append(total_spend if found else None)
            row_impr.append(total_impr if found else None)
        df = df.with_columns([
            pl.Series(f"{col}_row_spend", row_spend),
            pl.Series(f"{col}_row_impr", row_impr),
        ])
        breakdowns[col] = (spend_by_key, impr_by_key, rows_by_key)
    return df, breakdowns


def show_nested_dict_stats(df, breakdowns):
    print("\nNESTED-DICT COLUMNS (row totals + per-key breakdown)")
    for col in NESTED_DICT_COLUMNS:
        print(f"\n{col} -- row-level totals:")
        print(df.select([f"{col}_row_spend", f"{col}_row_impr"]).describe())

        spend_by_key, impr_by_key, rows_by_key = breakdowns[col]
        top5 = sorted(spend_by_key.items(), key=lambda kv: kv[1], reverse=True)[:5]
        print(f"\n{col} -- top 5 sub-keys by total spend:")
        for key, total in top5:
            print(f"  {key}: spend={total:.2f} impressions={impr_by_key[key]:.2f} rows={rows_by_key[key]}")


def _full_numeric_agg_exprs(num_cols):
    exprs = []
    for c in num_cols:
        exprs += [
            pl.col(c).count().alias(f"{c}_count"),
            pl.col(c).mean().alias(f"{c}_mean"),
            pl.col(c).min().alias(f"{c}_min"),
            pl.col(c).max().alias(f"{c}_max"),
            pl.col(c).std().alias(f"{c}_std"),
            pl.col(c).median().alias(f"{c}_median"),
        ]
    return exprs


def grouped_analysis_page_id(df):
    print("\nGROUPED ANALYSIS BY page_id (Polars)")

    sizes = (
        df.group_by("page_id")
        .agg(pl.col("ad_id").count().alias("n_ads"))
        .sort("n_ads", descending=True)
    )
    print(f"total distinct groups: {sizes.height}")
    print("\ntop 5 groups by number of ads:")
    print(sizes.head(5))

    num_cols = numeric_columns(df)
    numeric_group_stats = df.group_by("page_id").agg(_full_numeric_agg_exprs(num_cols))
    numeric_group_stats.write_csv("grouped_polars_page_id_numeric.csv")
    print(f"\nfull numeric stats for all {numeric_group_stats.height} page_id groups "
          f"written to grouped_polars_page_id_numeric.csv")

    cat_cols = PLAIN_CATEGORICAL_COLUMNS
    cat_agg_exprs = []
    for c in cat_cols:
        cat_agg_exprs += [
            pl.col(c).count().alias(f"{c}_count"),
            pl.col(c).n_unique().alias(f"{c}_nunique"),
            pl.col(c).mode().first().alias(f"{c}_mode"),
        ]
    cat_group_stats = df.group_by("page_id").agg(cat_agg_exprs)
    cat_group_stats.write_csv("grouped_polars_page_id_categorical.csv")
    print(f"full categorical stats for all {cat_group_stats.height} page_id groups "
          f"written to grouped_polars_page_id_categorical.csv")

    print(f"\nfull per-column stats (describe()) for the top 5 groups by ad volume:")
    top_pages = sizes.head(5)["page_id"].to_list()
    for pid in top_pages:
        sub = df.filter(pl.col("page_id") == pid)
        print(f"\n--- GROUP page_id={pid} (n={sub.height}) ---")
        print(sub.select(num_cols).describe())
        print(sub.select(cat_cols).describe())


def grouped_analysis_page_id_ad_id(df):
    print("\nGROUPED ANALYSIS BY page_id+ad_id (Polars)")

    sizes = df.group_by(["page_id", "ad_id"]).agg(pl.col("ad_id").count().alias("n_ads"))
    print(f"total distinct groups: {sizes.height}")
    all_singleton = bool((sizes["n_ads"] == 1).all())
    print(f"all groups have exactly 1 row: {all_singleton}")

    if all_singleton:
        print(f"\nnote: all {sizes.height} groups have exactly 1 row, "
              f"ad_id is already the dataset's atomic grain")
        print("\nexample groups (confirming n=1):")
        print(sizes.head(2))
    else:
        num_cols = numeric_columns(df)
        combo_stats = df.group_by(["page_id", "ad_id"]).agg(_full_numeric_agg_exprs(num_cols))
        combo_stats.write_csv("grouped_polars_page_id_ad_id_numeric.csv")
        print("full numeric stats per page_id+ad_id group written to "
              "grouped_polars_page_id_ad_id_numeric.csv")


def verify_against_pure_python(df):
    print("\nVERIFICATION: POLARS vs PURE PYTHON")

    check_cols = ["incivility_illuminating", "scam_illuminating", "estimated_spend",
                  "estimated_impressions", "estimated_audience_size",
                  "delivery_by_region_row_spend", "demographic_distribution_row_spend"]

    for col in check_cols:
        series = df[col].drop_nulls()
        polars_mean = series.mean()
        polars_std = series.std()

        pure_values = [str(v) for v in series.to_list()]
        pure = numeric_stats(pure_values)

        match = (
            abs(polars_mean - pure["mean"]) < 1e-6
            and abs(polars_std - (pure["std"] or 0)) < 1e-6
        )
        print(f"\n{col}")
        print(f"  polars : mean={polars_mean:.6f}  std={polars_std:.6f}")
        print(f"  pure py: mean={pure['mean']:.6f}  std={(pure['std'] or 0):.6f}")
        print(f"  match  : {match}")


def main():
    df = load_data()
    show_structure(df)
    show_missing(df)
    show_describe(df)
    show_binary_flag_rates(df)
    show_categorical_value_counts(df)
    explode_list_columns(df)
    df = parse_date_columns(df)
    show_date_stats(df)
    df, breakdowns = process_nested_dict_columns(df)
    show_nested_dict_stats(df, breakdowns)

    grouped_analysis_page_id(df)
    grouped_analysis_page_id_ad_id(df)

    verify_against_pure_python(df)


if __name__ == "__main__":
    main()